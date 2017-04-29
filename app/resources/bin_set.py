from flask_restful import Resource, reqparse

from .utils import bin_set_or_404
from app import db, app
from app.models import Contig


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

