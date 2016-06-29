from flask_script import Manager
from app import app, db
from app.models import *

from scripts import export_data


manager = Manager(app)


@manager.command
def createdb():
    db.create_all()
    

@manager.option('-t', '--type', dest='type_')
@manager.option('-i', '--id', dest='id_')
@manager.option('-f', '--file', dest='file', default=None)
def export(type_, id_, file):
    if type_ in ('assembly', 'a'):
        export_data.export_assembly(id_, file)
    elif type_ in ('bin-set', 'b'):
        export_data.export_bin_set(id_, file)
        

@manager.command
def list():
    export_data.list_tables()


if __name__ == '__main__':
    manager.run()
