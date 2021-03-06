import tempfile
import os
import uuid
import json
from itertools import product
from collections import Counter
from datetime import datetime
from subprocess import call

import werkzeug
from flask import session, abort, request
from flask_restful import Resource, reqparse
from rq import get_current_job

from app import db, utils, app, q
from app.models import Contig, Assembly, EssentialGene


def save_contigs(assembly, fasta_filename, calculate_fourmers, essential_genes=None, 
                 bulk_size=5000, coverages=None):
    """
    :param assembly: A Assembly model object in which to save the contigs.
    :param fasta_filename: The file name of the fasta file where the contigs are stored.
    :param bulk_size: How many contigs to store per bulk.
    """
    notfound = []
    fourmers = [''.join(fourmer) for fourmer in product('atcg', repeat=4)]
    if essential_genes is not None:
        all_genes = EssentialGene.query.filter_by(source='essential').all()
        all_genes = {gene.name: gene for gene in all_genes}
    for i, data in enumerate(utils.parse_fasta(fasta_filename), 1):
        name, sequence = data
        name = name.split(' ')[0]
        sequence = sequence.lower()
        contig = Contig(name=name, length=len(sequence),
                        gc=utils.gc_content(sequence), 
                        assembly=assembly)
        if coverages is not None:
            try:
                coverage = coverages.pop(name)
                contig.coverage = '{}' if coverage is None else json.dumps(coverage)
            except KeyError:
                notfound.append(name)
        if essential_genes is not None:
            for gene in essential_genes[name]:
                all_genes[gene].contigs.append(contig)
        if calculate_fourmers:
            fourmer_count = len(sequence) - 4 + 1
            counts = Counter([sequence[k:k+4] for k in range(fourmer_count)])
            frequencies = ','.join([str(counts[fourmer] / fourmer_count) for fourmer in fourmers])
            contig.fourmerfreqs = frequencies
        db.session.add(contig)
        if i % bulk_size == 0:
            app.logger.debug('At: ' + str(i))
            db.session.flush()
    db.session.commit()
    if calculate_fourmers:
        pcs = utils.pca_fourmerfreqs(assembly.contigs)
        for i, contig in enumerate(assembly.contigs): # TODO: load nothing?
            contig.pc_1, contig.pc_2, contig.pc_3 = pcs[i]
    db.session.commit()
    return notfound


def read_coverages(filename):
    coverage_file = utils.parse_dsv(filename)
    coverages = {}

    # Determine if the file has a header.
    fields = next(coverage_file)
    has_header = not utils.is_number(fields[1])
    if has_header:
        samples = fields[1:]
    else:
        samples = ['sample_{}'.format(i) for i, _ in enumerate(fields[1:], 1)]
        contig_name, *_coverages = fields
        coverages[contig_name] = {samples[i]: _coverages[i] for i, _ in enumerate(samples)}

    for contig_name, *_coverages in coverage_file:
        coverages[contig_name] = {samples[i]: _coverages[i] for i, _ in enumerate(samples)}

    os.remove(filename)
    return samples, coverages

    
def find_essential_genes_per_contig(assembly_path):
    """
    :param assembly_path: Fasta file with the assembly contigs.
    1. Run prodigal to predict genes. 
    2. Run Hmmer to find out which of these genes are essential.
    3. Return # essential genes per contig.
    """
    with tempfile.TemporaryDirectory() as dirname:
        # Prodigal
        proteins_path = os.path.join(dirname, 'proteins.faa')
        prodigal_path = os.path.join(dirname, 'prodigal.txt') 
        returncode = call(['prodigal', 
            '-p', 'meta',          # Metagenomics mode
            '-q',                  # Sssht
            '-a', proteins_path,   # Protein-coded predicted genes
            '-i', assembly_path,   # Assembly file (input)
            '-o', prodigal_path])  # Output
        # Hmmer
        model_path = 'data/essential.hmm'
        orfs_path = os.path.join(dirname, 'orfs.txt')
        returncode = call(['hmmsearch', 
            '--tblout', orfs_path,
            '--cut_tc', '--notextw',
            model_path, proteins_path],
            stdout=open(os.devnull, 'wb'))

        return utils.parse_hmmsearch_table(orfs_path)


def save_assembly_job(assembly, fasta_path, calculate_fourmers,
                      search_genes, email=None, 
                      coverage_filename=None, bulk_size=5000):
    job = get_current_job()

    # Find essential genes
    essential_genes = None
    if search_genes:
        job.meta['status'] = 'Searching for essential genes per contig'
        job.save()
        essential_genes = find_essential_genes_per_contig(fasta_path)

    # Save contigs to database
    job.meta['status'] = 'Saving contigs'
    job.save()
    args = [assembly, fasta_path, calculate_fourmers, essential_genes, bulk_size]
    if coverage_filename is not None:
        samples, coverages = read_coverages(coverage_filename)
        args.append(coverages)
        assembly.samples = ','.join(samples)
    notfound = save_contigs(*args)
    job.meta['notfound'].extend(notfound)
    job.save()

    assembly.busy = False
    db.session.add(assembly)
    db.session.commit()

    if email:
        utils.send_completion_email(email, assembly.name)

    return {'assembly': assembly.id}
    

class AssembliesApi(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('name', type=str, default='assembly',
                                   location='form')
        self.reqparse.add_argument('email', type=str, location='form')
        self.reqparse.add_argument('fourmers', type=bool, default=False,
                                   location='form')
        self.reqparse.add_argument('hmmer', type=bool, default=False,
                                   location='form')
        self.reqparse.add_argument('contigs', location='files',
                                   type=werkzeug.datastructures.FileStorage)
        self.reqparse.add_argument('coverage', location='files',
                                   type=werkzeug.datastructures.FileStorage)
        super(AssembliesApi, self).__init__()

    def get(self):
        userid = session.get('userid')
        if userid is None:
            return {'assemblies': []}
        assemblies = Assembly.query.filter_by(userid=userid, deleted=False, busy=False).all()
        assemblies = [a.to_dict() for a in assemblies]
        return {'assemblies': assemblies}

    def post(self):
        args = self.reqparse.parse_args()
        
        # Create user ID if first request
        if not 'userid' in session:
            session['userid'] = str(uuid.uuid4())
            session['jobs'] = []
            session.permanent = True

        # Only one assembly allowed for now
        job_types = [q.fetch_job(job_id).meta['type'] for job_id in session['jobs']]
        if 'A' in job_types:
            return {'message': 'You already have an assembly job running.'}, 403, {}

        if args.contigs.filename == '':
            return {'message': 'Please provide an assembly file.'}, 403, {}

        # Create assembly
        name = args.name or 'Assembly'
        assembly = Assembly(name=name, 
                            ip=request.headers.get('X-Forwarded-For', request.remote_addr),
                            userid=session['userid'], 
                            email=args.email,
                            busy=True,
                            submit_date=datetime.utcnow(),
                            has_fourmerfreqs=args.fourmers,
                            genes_searched=args.hmmer)
        db.session.add(assembly)
        db.session.commit()

        fasta_path = os.path.join(app.config['BASEDIR'], 
                                  'data/assemblies', 
                                  '{}.fa'.format(assembly.id))
        with open(fasta_path, 'wb') as f:
            args.contigs.save(f)

        if args.coverage.filename != '':
            coverage_file = tempfile.NamedTemporaryFile(delete=False)
            args.coverage.save(coverage_file)
            coverage_file.close()
            
        # Send job
        job_args = [assembly, fasta_path, args.fourmers, args.hmmer, args.email]
        job_meta = {'name': name, 'status': 'pending', 'type': 'A', 'notfound': []}
        if args.coverage.filename != '':
            job_args.append(coverage_file.name)
        job = q.enqueue(save_assembly_job, args=job_args, meta=job_meta,
                        timeout=60*60*24)
        session['jobs'].append(job.id)

        return job_meta, 202, {'Location': '/jobs/{}'.format(job.id)}
