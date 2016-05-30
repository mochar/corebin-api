from flask import abort
from flask.ext.restful import Resource, reqparse

from .utils import bin_or_404
from app import db, utils
from app.models import Bin, Contig


class BinApi(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('contigs', type=str, location='form')
        self.reqparse.add_argument('action', type=str, location='form',
                                    choices=['add', 'remove'])
        self.reqparse.add_argument('fields', type=str,
                                    default='id,name,color,bin_set_id,size'
                                            ',gc,n50')
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
        db.session.commit()
        
        cs = bin.contigs.with_entities(Contig.id, Contig.fourmerfreqs).all()
        p_components = utils.pca_fourmerfreqs(cs)
        result = {field: getattr(bin, field) for field in
                  'id,name,color,bin_set_id,size,gc,n50'.split(',')}
        result['pcs'] = {}
        for i, contig in enumerate(cs):
            result['pcs'][contig.id] = {
                'pc_1': p_components[i][0],
                'pc_2': p_components[i][1],
                'pc_3': p_components[i][2]
            }
        return result

    def delete(self, contigset_id, bin_set_id, id):
        pass
