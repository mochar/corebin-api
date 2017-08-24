import tempfile
import os
from collections import defaultdict
from datetime import datetime

import werkzeug
from flask import session
from flask_restful import Resource, reqparse
from sqlalchemy.orm import load_only

from .utils import user_assembly_or_404
from app import db, utils, randcol, app, q
from app.models import Contig, Bin, BinSet, Assembly


def save_bin_set_job(name, assembly_id, filename=None):
    assembly = Assembly.query.get(assembly_id)
    bin_set = BinSet(name=name, 
                     color=randcol.generate(luminosity='dark')[0],
                     submit_date=datetime.utcnow(),
                     assembly=assembly)
    db.session.add(bin_set)
    db.session.flush()

    # Query the contigs from the db to dict contig-name -> contig object
    query = assembly.contigs.options(load_only('name'))
    contigs = {c.name: c for c in query.all()}

    notfound = []
    if filename:
        # Dict: bin -> contigs
        bins = defaultdict(list)
        for contig_name, bin_name in utils.parse_dsv(filename):
            if contig_name in contigs:
                bins[bin_name].append(contig_name)
            else:
                notfound.append(contig_name)

        for bin_name, bin_contigs in bins.items():
            notfound.extend([c for c in bin_contigs if c not in contigs])
            bin_contigs = [contigs.pop(c) for c in bin_contigs]
            Bin(name=bin_name, color=randcol.generate(luminosity='dark')[0],
                bin_set_id=bin_set.id, contigs=bin_contigs)
        os.remove(filename)
    
    # Create a bin for the unbinned contigs.
    bin = Bin(name='unbinned', color='#939393', bin_set_id=bin_set.id,
              contigs=list(contigs.values()), unbinned=True)
    db.session.add(bin)

    db.session.flush()
    for bin in bin_set.bins:
        bin.recalculate_values()
    db.session.commit()
    return {
        'assembly': assembly.id, 
        'binSet': bin_set.id,
        'missing': list(contigs.keys()), 
        'notfound': notfound
    }
    

class BinSetsApi(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('name', type=str, default='bin_set',
                                   location='form')
        self.reqparse.add_argument('bins', required=True,
                                   type=werkzeug.datastructures.FileStorage, location='files')
        super(BinSetsApi, self).__init__()

    def get(self, assembly_id):
        assembly = user_assembly_or_404(assembly_id)
        result = [bin_set.to_dict() for bin_set in assembly.bin_sets.all()]
        return {'binSets': result}

    def post(self, assembly_id):
        assembly = user_assembly_or_404(assembly_id)
        args = self.reqparse.parse_args()

        name = args.name or 'Binset'

        if args.bins.filename != '':
            bin_file = tempfile.NamedTemporaryFile(delete=False)
            args.bins.save(bin_file)
            bin_file.close()
        
        # Send job
        job_args = [name, assembly.id]
        if args.bins.filename != '':
            job_args.append(bin_file.name)
        job_meta = {'type': 'B', 'name': name, 'assembly': assembly.id}
        job = q.enqueue(save_bin_set_job, args=job_args, meta=job_meta)
        session['jobs'].append(job.id)

        return job_meta, 202, {'Location': '/jobs/{}'.format(job.id)}