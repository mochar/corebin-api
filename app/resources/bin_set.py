from flask_restful import Resource, reqparse


from .utils import bin_set_or_404
from app import db


class BinSetApi(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('name', type=str)
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
        if args.name is not None:
            bin_set.name = args.name
        db.session.commit()

    def delete(self, assembly_id, id):
        bin_set = bin_set_or_404(assembly_id, id)
        db.session.delete(bin_set)
        db.session.commit()

