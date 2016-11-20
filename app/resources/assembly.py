from flask_restful import Resource, reqparse

from .utils import user_assembly_or_404
from app import db


class AssemblyApi(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('name', type=str)
        super(AssemblyApi, self).__init__()

    def get(self, id):
        assembly = user_assembly_or_404(id)
        return assembly.to_dict()

    def put(self, id):
        args = self.reqparse.parse_args()
        assembly = user_assembly_or_404(id)
        if args.name is not None:
            assembly.name = args.name
        db.session.commit()

    def delete(self, id):
        assembly = user_assembly_or_404(id)
        db.session.delete(assembly)
        db.session.commit()

