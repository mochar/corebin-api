from flask.ext.restful import Resource, reqparse, inputs
from flask import abort

from .utils import user_assembly_or_404
from app import db, app, utils
from app.models import Contig, Bin


def find_lengths(contigs):
    return {
        '< 1.0': contigs.filter(Contig.length <= 1000).count(),
        '1.0 - 3.5': contigs.filter(Contig.length > 1000, Contig.length <= 3500).count(),
        '3.5 - 7.0': contigs.filter(Contig.length > 3500, Contig.length <= 7000).count(),
        '7.0 - 15.0': contigs.filter(Contig.length > 7000, Contig.length <= 15000).count(),
        '15.0 - 30.0': contigs.filter(Contig.length > 15000, Contig.length <= 30000).count(),
        '30.0 - 60.0': contigs.filter(Contig.length > 30000, Contig.length <= 60000).count(),
        '> 60.0': contigs.filter(Contig.length > 60000).count()
    }


def find_gcs(contigs):
    data = {}
    for i in range(10):
        i = i / 10
        data[str(i)] = contigs.filter(Contig.gc > i, Contig.gc <= i + 0.1).count()
    return data


def create_length_data(assembly, bin_set_id=None):
    if bin_set_id is None:
        return find_lengths(assembly.contigs)
    bin_set = assembly.bin_sets.filter_by(id=bin_set_id).first()
    if bin_set is None:
        abort(404)
    data = {bin.name: find_lengths(bin.contigs) for bin in bin_set.bins}
    return data
    

def create_gc_data(assembly, bin_set_id=None):
    if bin_set_id is None:
        return find_gcs(assembly.contigs)
    bin_set = assembly.bin_sets.filter_by(id=bin_set_id).first()
    if bin_set is None:
        abort(404)
    data = {bin.name: find_gcs(bin.contigs) for bin in bin_set.bins}
    return data


class ContigsPlotApi(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('bs', type=int)
        super(ContigsPlotApi, self).__init__()
        
    def get(self, assembly_id):
        args = self.reqparse.parse_args()
        assembly = user_assembly_or_404(assembly_id)
        return {'length': create_length_data(assembly, args.bs),
                'gc': create_gc_data(assembly, args.bs)}