from collections import OrderedDict
from time import time

from flask.ext.restful import Resource, reqparse, inputs
from flask import abort
import numpy as np

from .utils import user_assembly_or_404
from app import db, app, utils
from app.models import Contig, Bin


def find_lengths(contigs):
    # bins = [0, 1000, 3500, 7000, 15000, 30000, 60000]
    values = [x[0] for x in contigs.with_entities(Contig.length).all()]
    hist, bins = np.histogram(values, bins=13)
    data = {'hist': hist.tolist(), 'bins': bins.tolist()}
    return data


def find_gcs(contigs):
    bins = [round(bin, 1) for bin in np.linspace(0, 1, 11).tolist()]
    values = [x[0] for x in contigs.with_entities(Contig.gc).all()]
    hist, _ = np.histogram(values, bins=bins)
    data = {'hist': hist.tolist(), 'bins': bins}
    return data


def create_length_data(contigs, bin_set=None):
    if bin_set is None:
        return find_lengths(contigs)
    data = {bin.name: find_lengths(bin.contigs) for bin in bin_set.bins}
    return data
    

def create_gc_data(contigs, bin_set=None):
    if bin_set is None:
        return find_gcs(contigs)
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
        bin_set = None
        if args.bs:
            bin_set = assembly.bin_sets.filter_by(id=args.bs).first()
            if bin_set is None:
                abort(404)
        contigs = assembly.contigs        
        return {'length': create_length_data(contigs, bin_set),
                'gc': create_gc_data(contigs, bin_set)}