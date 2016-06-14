import tempfile
import os
import uuid
from itertools import product

import werkzeug
from flask import session, abort
from flask.ext.restful import Resource, reqparse

from app import db, utils, app
from app.models import Coverage, Contig, Assembly


def save_contigs(assembly, fasta_filename, calculate_fourmers, bulk_size=5000):
    """
    :param assembly: A Assembly model object in which to save the contigs.
    :param fasta_filename: The file name of the fasta file where the contigs are stored.
    :param bulk_size: How many contigs to store per bulk.
    """
    fourmers = [''.join(fourmer) for fourmer in product('atcg', repeat=4)]
    for i, data in enumerate(utils.parse_fasta(fasta_filename), 1):
        name, sequence = data
        sequence = sequence.lower()
        contig = Contig(name=name, sequence=sequence, length=len(sequence),
                        gc=utils.gc_content(sequence), assembly=assembly)
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
    os.remove(fasta_filename)
    contigs = {contig.name: contig.id for contig in assembly.contigs}
    return contigs


def save_coverages(contigs, coverage_filename, samples):
    """
    :param contigs: A dict contig_name -> contig_id.
    :param coverage_filename: The name of the dsv file.
    :param samples: List of sample names.
    """
    coverage_file = utils.parse_dsv(coverage_filename)

    # Determine if the file has a header.
    fields = next(coverage_file)
    has_header = not utils.is_number(fields[1])

    def add_coverages(contig_name, _coverages):
        try:
            contig_id = contigs.pop(contig_name)
        except KeyError:
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


class AssembliesApi(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('name', type=str, default='assembly',
                                   location='form')
        self.reqparse.add_argument('fourmers', type=bool, default=False,
                                   location='form')
        self.reqparse.add_argument('samples[]', action='append',
                                   location='form', dest='samples')
        self.reqparse.add_argument('contigs', location='files',
                                   type=werkzeug.datastructures.FileStorage)
        self.reqparse.add_argument('coverage', location='files',
                                   type=werkzeug.datastructures.FileStorage)
        super(AssembliesApi, self).__init__()

    def get(self):
        userid = session.get('userid')
        if userid is None:
            abort(404)
        result = []
        for assembly in Assembly.query.filter_by(userid=userid).all():
            result.append({'name': assembly.name, 'id': assembly.id,
                           'size': assembly.contigs.count(),
                           'binSets': [bin_set.id for bin_set in assembly.bin_sets],
                           'samples': assembly.samples})
        return {'assemblies': result}

    def post(self):
        args = self.reqparse.parse_args()
        
        # Create user ID if first request
        if not 'userid' in session:
            session['userid'] = str(uuid.uuid4())

        assembly = Assembly(name=args.name, userid=session['userid'])
        db.session.add(assembly)
        db.session.commit()
        
        if args.contigs:
            fasta_file = tempfile.NamedTemporaryFile(delete=False)
            args.contigs.save(fasta_file)
            fasta_file.close()
            contigs = save_contigs(assembly, fasta_file.name, args.fourmers)

            if args.coverage:
                coverage_file = tempfile.NamedTemporaryFile(delete=False)
                args.coverage.save(coverage_file)
                coverage_file.close()
                save_coverages(contigs, coverage_file.name, args.samples)

        return {
            'id': assembly.id,
            'name': assembly.name,
            'size': assembly.contigs.count(),
            'samples': assembly.samples,
            'binSets': [bin_set.id for bin_set in assembly.bin_sets]
        }
