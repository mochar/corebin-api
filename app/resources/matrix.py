import collections

from flask_restful import Resource, reqparse
import numpy as np

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
        size = len(bins1) + len(bins2)
        matrix = np.zeros((size, size))
        lbins1 = len(bins1)
        for i, d in enumerate(bins1):
            for j, d2 in enumerate(bins2, lbins1):
                matrix[i][j] = len(d[1].intersection(d2[1]))
        matrix[lbins1:, :lbins1] = np.swapaxes(matrix[:lbins1, lbins1:], 1, 0)
        return matrix.tolist()
        
    def _create_matrix_by_bp(self, bins1, bins2):
        size = len(bins1) + len(bins2)
        matrix = np.zeros((size, size))
        lbins1 = len(bins1)
        for i, bin1 in enumerate(bins1):
            for j, bin2 in enumerate(bins2, lbins1):
                matrix[i][j] = sum([c.length for c in set(bin1.contigs_eager).intersection(set(bin2.contigs_eager))])
        matrix[lbins1:, :lbins1] = np.swapaxes(matrix[:lbins1, lbins1:], 1, 0)
        return matrix.tolist()
        
    def generate_matrix_by_count(self, bin_set1, bin_set2):
        bins1 = [bin.id for bin in sorted(bin_set1.bins.all(), key=lambda x: x.gc)]
        bins2 = [bin.id for bin in sorted(bin_set2.bins.all(), key=lambda x: x.gc, reverse=True)]
        all_bins = bins1 + bins2

        data = db.session.query(bincontig). \
            filter(bincontig.c.bin_id.in_(all_bins)). \
            all()
        bins = collections.defaultdict(set)
        for bin, contig in data:
            bins[bin].add(contig)

        bins11 = [(bin, bins[bin]) for bin in bins1]
        bins22 = [(bin, bins[bin]) for bin in bins2]
        matrix = self._create_matrix(bins11, bins22)
        return {'matrix': matrix, 'bins1': bins1, 'bins2': bins2}
        
    def generate_matrix_by_bp(self, bin_set1, bin_set2):
        # Get contigs for bin set 1 bins
        q = bin_set1.bins.options(
            db.Load(Bin).load_only('id', 'gc'),
            db.Load(Contig).load_only('length')
        )
        bins1 = sorted(q.all(), key=lambda x: x.gc)
        
        # Get contigs for bin set 2 bins
        q = bin_set2.bins.options(
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
