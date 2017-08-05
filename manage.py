import os
import subprocess
import shutil
import urllib.request
from collections import defaultdict

from flask_script import Manager
from app import app, db
from app.models import BinSet, EssentialGene

from scripts import export_data


manager = Manager(app)


def setup_database():
    db.drop_all()
    db.create_all()
    for line in open('data/essential.hmm', 'r'):
        if line.startswith('NAME'):
            gene = line.rstrip().split(' ')[-1]
            db.session.add(EssentialGene(name=gene, source='essential'))
    db.session.commit()


@manager.command
def createdb():
    setup_database()


@manager.command
def contigs_count():
    print('Assembly', '# Contigs', 'Bin set', '# Contigs', sep='\t')
    for bin_set in BinSet.query.all():
        count = sum([bin.contigs.count() for bin in bin_set.bins.all()])
        assembly_count = bin_set.assembly.contigs.count()
        print(bin_set.assembly.name, assembly_count, bin_set.name, count, sep='\t')
    
    
@manager.command
def setup():
    setup_database()
    shutil.rmtree('data')
    os.mkdir('data')
    urllib.request.urlretrieve('https://raw.githubusercontent.com/MadsAlbertsen/mmgenome/master/scripts/essential.hmm', 'data/essential.hmm')
    os.mkdir('data/assemblies')

@manager.option('-t', '--type', dest='type_')
@manager.option('-i', '--id', dest='id_')
@manager.option('-f', '--file', dest='file', default=None)
def export(type_, id_, file):
    if type_ in ('assembly', 'a'):
        export_data.export_assembly(id_, file)
    elif type_ in ('bin-set', 'b'):
        export_data.export_bin_set(id_, file)
        

@manager.command
def table():
    export_data.list_tables()


if __name__ == '__main__':
    manager.run()
