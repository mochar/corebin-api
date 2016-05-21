from flask import abort
from flask.ext.restful import Resource, reqparse

from .utils import bin_set_or_404
from app import db
from app.models import Bin


class BinsApi(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('ids', type=str)
        self.reqparse.add_argument('contigs', type=bool)
        self.reqparse.add_argument('fields', type=str,
                                   default='id,name,color,bin_set_id,size,gc,n50')
        super(BinsApi, self).__init__()

    def get(self, assembly_id, id):
        bin_set = bin_set_or_404(assembly_id, id)
        args =  self.reqparse.parse_args()
        result = []
        for bin in bin_set.without_unbinned:
            r = {}
            for field in args.fields.split(','):
                r[field] = getattr(bin, field)
            if args.contigs:
                r['contigs'] = [contig.id for contig in bin.contigs]
            result.append(r)
        return {'bins': result}

    def delete(self, contigset_id, id):
        bin_set = bin_set_or_404(contigset_id, id)
        args =  self.reqparse.parse_args()
        if args.ids is None:
            abort(400)
        ids = [int(id) for id in args.ids.split(',')]
        bin_set.bins.filter(Bin.id.in_(ids)).delete(synchronize_session='fetch')
        db.session.commit()
