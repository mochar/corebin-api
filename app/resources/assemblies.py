import tempfile
import os
import uuid
from itertools import product
from datetime import datetime
from subprocess import call

import werkzeug
from flask import session, abort
from flask_restful import Resource, reqparse
from rq import get_current_job

from app import db, utils, app, q
from app.models import Coverage, Contig, Assembly, EssentialGene


def save_contigs(assembly, fasta_filename, calculate_fourmers, essential_genes=None, 
                 bulk_size=5000):
    """
    :param assembly: A Assembly model object in which to save the contigs.
    :param fasta_filename: The file name of the fasta file where the contigs are stored.
    :param bulk_size: How many contigs to store per bulk.
    """
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
                        assembly_id=assembly.id)
        if essential_genes is not None:
            for gene in essential_genes[name]:
                all_genes[gene].contigs.append(contig)
        if calculate_fourmers:
            fourmer_count = len(sequence) - 4 + 1
            frequencies = ','.join(str(sequence.count(fourmer) / fourmer_count)
                                   for fourmer in fourmers)
            contig.fourmerfreqs = frequencies
        db.session.add(contig)
        if i % bulk_size == 0:
            app.logger.debug('At: ' + str(i))
            db.session.flush()
    db.session.commit()
    contigs = {contig.name: contig.id for contig in assembly.contigs}
    return contigs


def save_coverages(contigs, coverage_filename):
    """
    :param contigs: A dict contig_name -> contig_id.
    :param coverage_filename: The name of the dsv file.
    """
    coverage_file = utils.parse_dsv(coverage_filename)
    not_found = []

    # Determine if the file has a header.
    fields = next(coverage_file)
    has_header = not utils.is_number(fields[1])
    if has_header:
        samples = fields[1:]
    else:
        samples = ['sample_{}'.format(i) for i, _ in enumerate(fields[1:], 1)]

    def add_coverages(contig_name, _coverages):
        try:
            contig_id = contigs.pop(contig_name)
        except KeyError:
            not_found.append(contig_name)
            return
        for i, cov in enumerate(_coverages):
            db.session.add(Coverage(value=cov, sample=samples[i], contig_id=contig_id))

    if not has_header:
        contig_name, *_coverages = fields
        add_coverages(contig_name, _coverages)

    for contig_name, *_coverages in coverage_file:
        add_coverages(contig_name, _coverages)

    db.session.commit()
    os.remove(coverage_filename)
    return not_found


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


def save_assembly_job(name, userid, fasta_filename, calculate_fourmers,
                      search_genes, coverage_filename=None, 
                      bulk_size=5000):
    assembly = Assembly(name=name, userid=userid, submit_date=datetime.utcnow(),
                        has_fourmerfreqs=calculate_fourmers,
                        genes_searched=search_genes)
    db.session.add(assembly)
    db.session.flush()
    job = get_current_job()

    # Find essential genes
    essential_genes = None
    if search_genes:
        job.meta['status'] = 'Searching for essential genes per contig'
        job.save()
        essential_genes = find_essential_genes_per_contig(fasta_filename)

    # Save contigs to database
    job.meta['status'] = 'Saving contigs'
    job.save()
    contigs = save_contigs(assembly, fasta_filename, calculate_fourmers,
                           essential_genes, bulk_size)

    # Calculate and save coverages to database
    if coverage_filename is not None:
        job.meta['status'] = 'Saving coverage data'
        job.save()
        job.meta['notfound'].extend(save_coverages(contigs, coverage_filename))
        job.save()

    # Cleanup
    os.remove(fasta_filename)
    return {'assembly': assembly.id}
    

class AssembliesApi(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('name', type=str, default='assembly',
                                   location='form')
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
        result = [a.to_dict() for a in Assembly.query.filter_by(userid=userid, deleted=False).all()]
        return {'assemblies': result}

    def post(self):
        args = self.reqparse.parse_args()
        
        # Create user ID if first request
        if not 'userid' in session:
            session['userid'] = str(uuid.uuid4())
            session['jobs'] = []
            session.permanent = True

        if args.contigs.filename == '':
            return {}, 403, {}

        name = args.name or 'Assembly'

        fasta_file = tempfile.NamedTemporaryFile(delete=False)
        args.contigs.save(fasta_file)
        fasta_file.close()

        if args.coverage.filename != '':
            coverage_file = tempfile.NamedTemporaryFile(delete=False)
            args.coverage.save(coverage_file)
            coverage_file.close()
            
        # Send job
        job_args = [name, session['userid'], fasta_file.name, args.fourmers, args.hmmer]
        job_meta = {'name': name, 'status': 'pending', 'type': 'A', 'notfound': []}
        if args.coverage.filename != '':
            job_args.append(coverage_file.name)
        job = q.enqueue(save_assembly_job, args=job_args, meta=job_meta,
                        timeout=60*60*24)
        session['jobs'].append(job.id)

        return job_meta, 202, {'Location': '/jobs/{}'.format(job.id)}
