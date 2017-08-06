import os
import io
import zipfile

from flask import make_response
from flask_restful import Resource, reqparse

from .utils import bin_set_or_404
from app import db, app, utils
from app.models import Contig, Assembly


class BinSetApi(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('name', type=str)
        self.reqparse.add_argument('contigs', action='append', type=int, default=[])
        self.reqparse.add_argument('to_bin', type=int)
        super(BinSetApi, self).__init__()

    def get(self, assembly_id, id):
        bin_set = bin_set_or_404(assembly_id, id)
        return {
            'id': bin_set.id, 'name': bin_set.name, 'color': bin_set.color,
            'bins': [bin.id for bin in bin_set.bins],
            'assembly': bin_set.assembly.id
        }

    def put(self, assembly_id, id):
        args = self.reqparse.parse_args()
        bin_set = bin_set_or_404(assembly_id, id)
        # Renaming bin set
        if args.name is not None:
            bin_set.name = args.name
        # Refinement: moving and deleting contigs
        if args.to_bin and len(args.contigs) > 0:
            to_bin = bin_set.bins.filter_by(id=args.to_bin).first_or_404()
            contigs = bin_set.assembly.contigs. \
                filter(Contig.id.in_(args.contigs)). \
                all()
            for bin in bin_set.bins.options(db.lazyload('contigs_eager')).all():
                if bin.id == args.to_bin:
                    bin.contigs.extend(contigs)
                else:
                    bin.contigs = [c for c in bin.contigs if c.id not in args.contigs]
                bin.recalculate_values()
        db.session.commit()

    def delete(self, assembly_id, id):
        bin_set = bin_set_or_404(assembly_id, id)
        # Remove all realtions to contigs so that the contigs will 
        # not be removed.
        for bin in bin_set.bins:
            bin.contigs = []
        db.session.flush()
        db.session.delete(bin_set)
        db.session.commit()


class BinSetExportApi(Resource):
    def get(self, assembly_id, id):
        bin_set = bin_set_or_404(assembly_id, id)
        assembly = Assembly.query.get(assembly_id)

        # Map contig -> bin name
        mapping = {}
        for contig in assembly.contigs.all():
            bin_ = [b for b in contig.bins if b.bin_set_id == bin_set.id][0]
            mapping[contig.name] = bin_.name
        
        # Build fasta strings. Map bin -> fasta string
        fastas = {b: '' for b in set(mapping.values())}
        fasta_path = os.path.join(app.config['BASEDIR'], 'data/assemblies', 
                                  '{}.fa'.format(1 if assembly.demo else assembly.id))
        for name, sequence in utils.parse_fasta(fasta_path):
            name = name.split(' ')[0]
            fastas[mapping[name]] += '>{}\n{}\n'.format(name, sequence)
        
        # Create zip file in memory
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'a', zipfile.ZIP_DEFLATED) as z:
            for bin_, fasta_string in fastas.items():
                z.writestr('{}.fa'.format(bin_), fasta_string)

        # Return zip file for download
        buffer.seek(0)
        response = make_response(buffer.read())
        buffer.close()
        response.headers['Content-Disposition'] = 'attachment; filename='
        response.headers['Content-Disposition'] += '{}.zip'.format(bin_set.name)
        return response
