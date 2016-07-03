import tempfile
import os
import pickle
from subprocess import call

from flask import session, abort
from flask_restful import Resource, reqparse

from app import db, q
from app.models import Bin


def run_hmmer_job(bin_id, rank, taxon):
    bin = Bin.query.get(bin_id)
    with tempfile.TemporaryDirectory() as dirname:
        bins_dir = os.path.join(dirname, 'bins')
        output_dir = os.path.join(dirname, 'output')
        os.mkdir(bins_dir)
        os.mkdir(output_dir)
        bin.save_fa(os.path.join(bins_dir, 'bin.fa'))
        results_path = os.path.join(dirname, 'results')
        returncode = call(['checkm', 'taxonomy_wf', rank, taxon, 
            bins_dir, output_dir, '-x', 'fa', '-f', results_path,
            '-t', '4', '--tab_table'])
        with open(results_path, 'r') as f:
            fields = f.readlines()[-1].split('\t')
            bin.contamination = float(fields[-2])
            bin.completeness = float(fields[-3])
            db.session.commit()
    return {'contamination': bin.contamination, 
            'completeness': bin.completeness}
   
   
class HmmerApi(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('bin', type=str, required=True)
        self.reqparse.add_argument('rank', type=str, required=True)
        self.reqparse.add_argument('taxon', type=str, required=True)
        super(HmmerApi, self).__init__()
 
    def get(self):
        if not os.path.exists('data/taxon_list.pkl'):
            return {'taxonList': {}}
        with open('data/taxon_list.pkl', 'rb') as f:
            return {'taxonList': pickle.load(f)}
        
    def post(self): 
        args = self.reqparse.parse_args()
        
        bin = Bin.query.get_or_404(args.bin)
        if session['userid'] != bin.bin_set.assembly.userid:
            abort(403)
            
        job_args = [args.bin, args.rank, args.taxon]
        job_meta = {'bin': bin.id, 'binSet': bin.bin_set.id,
                    'assembly': bin.bin_set.assembly.id, 'type': 'C'}
        job = q.enqueue(run_hmmer_job, meta=job_meta, args=job_args, 
                        timeout=60*30)
        session['jobs'].append(job.id)

        return job_meta, 202, {'Location': '/jobs/{}'.format(job.id)}