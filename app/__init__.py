from flask import Flask, jsonify, session, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Api
from flask_cors import CORS
from rq import Queue

from worker import conn
from app import randomcolor
from app.session import RedisSessionInterface

app = Flask(__name__)
app.session_interface = RedisSessionInterface()
app.config.from_object('config')
CORS(app, supports_credentials=True, expose_headers=['Location'])
db = SQLAlchemy(app)
q = Queue(connection=conn)
randcol = randomcolor.RandomColor()

from app.resources.assemblies import AssembliesApi
from app.resources.assembly import AssemblyApi
from app.resources.contigs import ContigsApi
from app.resources.contigs_plot import ContigsPlotApi
from app.resources.bin_sets import BinSetsApi
from app.resources.bin_set import BinSetApi
from app.resources.bins import BinsApi
from app.resources.bin import BinApi, BinExportApi
from app.resources.matrix import MatrixApi
from app.resources.hmmer import HmmerApi
from app.resources.jobs import JobsApi, JobApi
from app.resources.assess import AssessApi

api = Api(app)
api.add_resource(AssembliesApi, '/a')
api.add_resource(AssemblyApi, '/a/<int:id>')
api.add_resource(ContigsApi, '/a/<int:assembly_id>/c')
api.add_resource(ContigsPlotApi, '/a/<int:assembly_id>/c/plot')
api.add_resource(BinSetsApi, '/a/<int:assembly_id>/bs')
api.add_resource(BinSetApi, '/a/<int:assembly_id>/bs/<int:id>')
api.add_resource(AssessApi, '/a/<int:assembly_id>/bs/<int:id>/assess')
api.add_resource(BinsApi, '/a/<int:assembly_id>/bs/<int:id>/b')
api.add_resource(BinApi, '/a/<int:assembly_id>/bs/<int:bin_set_id>/b/<int:id>')
api.add_resource(BinExportApi, '/a/<int:assembly_id>/bs/<int:bin_set_id>/b/<int:id>/export')
api.add_resource(MatrixApi, '/a/<int:assembly_id>/matrix')
api.add_resource(HmmerApi, '/hmmer')
api.add_resource(JobsApi, '/jobs')
api.add_resource(JobApi, '/jobs/<string:job_id>')

from app import models
from app import views
