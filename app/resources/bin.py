import os

from flask import abort, session, make_response
from flask_restful import Resource, reqparse

from .utils import bin_or_404
from app import db, utils, app
from app.models import Bin, Contig


def calculate_pcs(bin):
    cs = bin.contigs.with_entities(Contig.id, Contig.fourmerfreqs).all()
    p_components = utils.pca_fourmerfreqs(cs)
    pcs = {}
    for i, contig in enumerate(cs):
        pcs[contig.id] = {
            'pc_1': p_components[i][0],
            'pc_2': p_components[i][1],
            'pc_3': p_components[i][2]
        }
    return pcs


class BinApi(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('name', type=str)
        self.reqparse.add_argument('color', type=str)
        self.reqparse.add_argument('contigs', type=str, location='form')
        self.reqparse.add_argument('action', type=str, location='form',
                                    choices=['add', 'remove'])
        self.reqparse.add_argument('fields', type=str,
            default='id,name,contamination,completeness,'
                    'color,bin_set_id,size,gc,n50')
        super(BinApi, self).__init__()

    def get(self, assembly_id, bin_set_id, id):
        args = self.reqparse.parse_args()
        bin = bin_or_404(assembly_id, bin_set_id, id)
        result = {}
        for field in args.fields.split(','):
            if field == 'contigs':
                result['contigs'] = [contig.id for contig in bin.contigs]
            else:
                result[field] = getattr(bin, field)
        return result
        
    def put(self, assembly_id, bin_set_id, id):
        args = self.reqparse.parse_args()
        bin = bin_or_404(assembly_id, bin_set_id, id)

        if args.contigs:
            contig_ids = [int(id) for id in args.contigs.split(',')]
            if args.action == 'add':
                contigs = bin.bin_set.assembly.contigs. \
                    filter(Contig.id.in_(contig_ids)). \
                    all()
                bin.contigs.extend(contigs)
            elif args.action == 'remove':
                bin.contigs = [c for c in bin.contigs if c.id not in contig_ids]
            else:
                contigs = bin.binset.contigset.contigs. \
                    filter(Contig.id.in_(contig_ids)). \
                    all()
                bin.contigs = contigs
            bin.recalculate_values()
        if args.name is not None or args.color is not None:
            if bin.unbinned:
                return {}, 405
            bin.name = args.name or bin.name
            bin.color = args.color or bin.color
        db.session.commit()
        
        result = bin.to_dict()
        if args.name is None and bin.contigs.count() > 0:
            # "args.name is None" because we dont want de pcs when we
            # are just renaming the bin.
            result['pcs'] = calculate_pcs(bin)
        return result

    def delete(self, assembly_id, bin_set_id, id):
        args = self.reqparse.parse_args()
        bin_set, bin = bin_or_404(assembly_id, bin_set_id, id, return_bin_set=True)
        if bin.unbinned:
            return {}, 405
        unbinned = bin_set.bins.filter_by(unbinned=True).first_or_404()
        contigs = bin.contigs.all()
        bin.contigs = []
        unbinned.contigs.extend(contigs)
        db.session.flush()
        unbinned.recalculate_values()
        db.session.delete(bin)
        db.session.commit()


class BinExportApi(Resource):
    def get(self, assembly_id, bin_set_id, id):
        bin_set, bin = bin_or_404(assembly_id, bin_set_id, id, return_bin_set=True)
        if bin_set.assembly.demo:
            assembly_id = 1
        q = bin.contigs.options(db.load_only('name'))
        contig_names = [c.name for c in q.all()]
        fasta_path = os.path.join(app.config['BASEDIR'], 
                                  'data/assemblies', 
                                  '{}.fa'.format(assembly_id))
        fasta_string = '\n'.join(['\n'.join((name, sequence))
                                  for name, sequence in utils.parse_fasta(fasta_path) 
                                  if name in contig_names])
        response = make_response(fasta_string)
        response.headers['Content-Disposition'] = 'attachment; filename='
        response.headers['Content-Disposition'] += '{}.fa'.format(bin.name)
        return response
 