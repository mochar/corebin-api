import collections

from flask_restful import Resource, reqparse

from .utils import bin_set_or_404
from app import db
from app.models import bincontig, Contig, Bin


class MatrixApi(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('binset1', type=int, required=True)
        self.reqparse.add_argument('binset2', type=int, required=True)
        self.reqparse.add_argument('by', type=str, choices=['bp', 'count'],
                                    default='count')

    def _create_matrix(self, bins1, bins2):
        matrix = []
        for bin1, contigs1 in bins1:
            matching = [0] * len(bins1)
            for bin2, contigs2 in bins2:
                matching.append(len([c for c in contigs1 if c in contigs2]))
            matrix.append(matching)
        for bin2, contigs2 in bins2:
            matching = []
            for bin1, contigs1 in bins1:
                matching.append(len([c for c in contigs2 if c in contigs1]))
            matching.extend([0] * len(bins2))
            matrix.append(matching)
        return matrix
        
    def _create_matrix_by_bp(self, bins1, bins2):
        matrix = []
        for bin1 in bins1:
            matching = [0] * len(bins1)
            for bin2 in bins2:
                matching.append(sum([c.length for c in bin1.contigs_eager if c in bin2.contigs_eager]))
            matrix.append(matching)
        for bin2 in bins2:
            matching = []
            for bin1 in bins1:
                matching.append(sum([c.length for c in bin2.contigs_eager if c in bin1.contigs_eager]))
            matching.extend([0] * len(bins2))
            matrix.append(matching)
        return matrix
        
    def generate_matrix_by_count(self, bin_set1, bin_set2):
        bins1 = [bin.id for bin in sorted(bin_set1.without_unbinned.all(), key=lambda x: x.gc)]
        bins2 = [bin.id for bin in sorted(bin_set2.without_unbinned.all(), key=lambda x: x.gc, reverse=True)]
        all_bins = bins1 + bins2

        data = db.session.query(bincontig). \
            filter(bincontig.c.bin_id.in_(all_bins)). \
            all()
        bins = collections.defaultdict(list)
        for bin, contig in data:
            bins[bin].append(contig)

        bins11 = [(bin, bins[bin]) for bin in bins1]
        bins22 = [(bin, bins[bin]) for bin in bins2]
        matrix = self._create_matrix(bins11, bins22)
        return {'matrix': matrix, 'bins1': bins1, 'bins2': bins2}
        
    def generate_matrix_by_bp(self, bin_set1, bin_set2):
        # Get contigs for bin set 1 bins
        q = bin_set1.without_unbinned.options(
            db.Load(Bin).load_only('id', 'gc'),
            db.Load(Contig).load_only('length')
        )
        bins1 = sorted(q.all(), key=lambda x: x.gc)
        
        # Get contigs for bin set 2 bins
        q = bin_set2.without_unbinned.options(
            db.Load(Bin).load_only('id', 'gc'),
            db.Load(Contig).load_only('length')
        )
        bins2 = sorted(q.all(), key=lambda x: x.gc, reverse=True)
        
        return {
            'matrix': self._create_matrix_by_bp(bins1, bins2),
            'bins1': [bin.id for bin in bins1], 
            'bins2': [bin.id for bin in bins2]
        }
        
    def get(self, assembly_id):
        args = self.reqparse.parse_args()
        bin_set1 = bin_set_or_404(assembly_id, args.binset1)
        bin_set2 = bin_set_or_404(assembly_id, args.binset2)
        if args.by == 'count':
            return self.generate_matrix_by_count(bin_set1, bin_set2)
        return self.generate_matrix_by_bp(bin_set1, bin_set2)
