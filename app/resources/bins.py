from flask import abort
from flask_restful import Resource, reqparse

from .utils import bin_set_or_404
from app import db, randomcolor
from app.models import Bin


class BinsApi(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('ids', type=int, action='append')
        self.reqparse.add_argument('name', type=str)
        self.reqparse.add_argument('color', type=str)
        self.reqparse.add_argument('contigs', type=bool)
        self.reqparse.add_argument('fields', type=str)
        super(BinsApi, self).__init__()

    def get(self, assembly_id, id):
        bin_set = bin_set_or_404(assembly_id, id)
        args =  self.reqparse.parse_args()
        result = []
        for bin in bin_set.bins:
            r = bin.to_dict()
            if args.contigs:
                r['contigs'] = [contig.id for contig in bin.contigs]
            result.append(r)
        return {'bins': result}

    def delete(self, assembly_id, id):
        bin_set = bin_set_or_404(assembly_id, id)
        args = self.reqparse.parse_args()
        if args.ids is None:
            abort(400)
        bins = bin_set.bins.filter(Bin.id.in_(args.ids)). \
                            filter(Bin.name != 'unbinned'). \
                            all()
        unbinned = bin_set.bins.filter_by(name='unbinned').first_or_404()
        for bin in bins:
            contigs = bin.contigs.all()
            bin.contigs = []
            unbinned.contigs.extend(contigs)
        db.session.flush()
        for bin in bins:
            db.session.delete(bin)
        unbinned.recalculate_values()
        db.session.commit()

    def post(self, assembly_id, id):
        args = self.reqparse.parse_args()
        bin_set = bin_set_or_404(assembly_id, id)
        randcol = randomcolor.RandomColor()
        if args.name:
            color = args.color or randcol.generate()[0]
            bin = Bin(name=args.name, bin_set=bin_set, color=color)
            bin.recalculate_values()
            db.session.add(bin)
            db.session.commit()
            return bin.to_dict()
