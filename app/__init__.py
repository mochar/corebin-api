from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.restful import Api

app = Flask(__name__)
app.config.from_object('config')
db = SQLAlchemy(app)

from app.resources.assemblies import AssembliesApi
from app.resources.assembly import AssemblyApi
from app.resources.contigs import ContigsApi
from app.resources.contigs_plot import ContigsPlotApi
from app.resources.bin_sets import BinSetsApi
from app.resources.bin_set import BinSetApi
from app.resources.bins import BinsApi

api = Api(app)
api.add_resource(AssembliesApi, '/a')
api.add_resource(AssemblyApi, '/a/<int:id>')
api.add_resource(ContigsApi, '/a/<int:assembly_id>/c')
api.add_resource(ContigsPlotApi, '/a/<int:assembly_id>/c/plot')
api.add_resource(BinSetsApi, '/a/<int:assembly_id>/bs')
api.add_resource(BinSetApi, '/a/<int:assembly_id>/bs/<int:id>')
api.add_resource(BinsApi, '/a/<int:assembly_id>/bs/<int:id>/b')

from app import models
