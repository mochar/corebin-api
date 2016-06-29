import tempfile
import os
from collections import defaultdict

import werkzeug
from flask_restful import Resource, reqparse

from .utils import user_assembly_or_404
from app import db, utils, randomcolor
from app.models import Contig, Bin, BinSet


class BinSetsApi(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('name', type=str, default='bin_set',
                                   location='form')
        self.reqparse.add_argument('bins', required=True,
                                   type=werkzeug.datastructures.FileStorage, location='files')
        self.randcol = randomcolor.RandomColor()
        super(BinSetsApi, self).__init__()

    def get(self, assembly_id):
        assembly = user_assembly_or_404(assembly_id)
        result = []
        for bin_set in assembly.bin_sets:
            result.append({
                'name': bin_set.name, 'id': bin_set.id, 'assembly': assembly.id,
                'color': bin_set.color, 'bins': [bin.id for bin in bin_set.bins]})
        return {'binSets': result}

    def post(self, assembly_id):
        assembly = user_assembly_or_404(assembly_id)
        args = self.reqparse.parse_args()

        bin_file = tempfile.NamedTemporaryFile(delete=False)
        args.bins.save(bin_file)
        bin_file.close()
        
        bin_set = BinSet(name=args.name, color=self.randcol.generate()[0],
                         assembly=assembly)
        db.session.add(bin_set)
        db.session.flush()

        # Dict: bin -> contigs
        bins = defaultdict(list)
        for contig_name, bin_name in utils.parse_dsv(bin_file.name):
            bins[bin_name].append(contig_name)

        bin_objects = []
        contigs = {c.name: c for c in assembly.contigs}
        for bin_name, bin_contigs in bins.items():
            bin_contigs = [contigs.pop(c) for c in bin_contigs if c in contigs]
            bin = Bin(name=bin_name, color=self.randcol.generate()[0],
                      bin_set_id=bin_set.id, contigs=bin_contigs)
            bin.recalculate_values()
            bin_objects.append(bin)

        # Create a bin for the unbinned contigs.
        bin = Bin(name='unbinned', color='#939393', bin_set_id=bin_set.id,
                  contigs=list(contigs.values()))
        bin.recalculate_values()
        bin_objects.append(bin)
        
        bin_set.bins = bin_objects

        os.remove(bin_file.name)
        db.session.commit()
        return {'id': bin_set.id, 'name': bin_set.name, 'color': bin_set.color,
                'bins': [bin.id for bin in bin_set.bins], 'assembly': assembly.id}
