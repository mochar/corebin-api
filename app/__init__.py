from flask import Flask, jsonify, session
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.restful import Api
from rq import Queue

from worker import conn

app = Flask(__name__)
app.config.from_object('config')
db = SQLAlchemy(app)
q = Queue(connection=conn)

@app.route('/jobs/')
@app.route('/jobs/<job_id>')
def job(job_id=None):
    if job_id is None:
        jobs = []
        for job_id in session['jobs']:
            job = q.fetch_job(job_id)
            if job is None or job.is_finished:
                session['jobs'].remove(job_id)
            else:
                jobs.append({'id': job_id, 'meta': job.meta})
        return jsonify({'jobs': jobs})
    job = q.fetch_job(job_id)
    if job is None:
        return jsonify({'error': 'not found'})
    else:
        if job.is_finished:
            session['jobs'].remove(job.id)
        return jsonify({'id': job.id, 'meta': job.meta})

from app.resources.assemblies import AssembliesApi
from app.resources.assembly import AssemblyApi
from app.resources.contigs import ContigsApi
from app.resources.contigs_plot import ContigsPlotApi
from app.resources.bin_sets import BinSetsApi
from app.resources.bin_set import BinSetApi
from app.resources.bins import BinsApi
from app.resources.bin import BinApi

api = Api(app)
api.add_resource(AssembliesApi, '/a')
api.add_resource(AssemblyApi, '/a/<int:id>')
api.add_resource(ContigsApi, '/a/<int:assembly_id>/c')
api.add_resource(ContigsPlotApi, '/a/<int:assembly_id>/c/plot')
api.add_resource(BinSetsApi, '/a/<int:assembly_id>/bs')
api.add_resource(BinSetApi, '/a/<int:assembly_id>/bs/<int:id>')
api.add_resource(BinsApi, '/a/<int:assembly_id>/bs/<int:id>/b')
api.add_resource(BinApi, '/a/<int:assembly_id>/bs/<int:bin_set_id>/b/<int:id>')

from app import models
