from flask_script import Manager
from app import app, db

from scripts.export_data import export_bin_set, export_assembly


manager = Manager(app)


@manager.command
def createdb():
    db.create_all()
    

@manager.option('-t', '--type', dest='type_')
@manager.option('-n', '--name', dest='name')
@manager.option('-f', '--file', dest='file', default=None)
def export(type_, name, file):
    if type_ in ('assembly', 'a'):
        export_assembly(name, file if file else '{}.fa'.format(name))
    elif type_ in ('bin-set', 'b'):
        export_bin_set(name, file if file else '{}.csv'.format(name))


if __name__ == '__main__':
    manager.run()
