import os
import subprocess
import pickle
from collections import defaultdict

from flask_script import Manager
from app import app, db
from app.models import BinSet, EssentialGene

from scripts import export_data


manager = Manager(app)


@manager.command
def createdb():
    db.create_all()
    for line in open('data/essential.hmm', 'r'):
        if line.startswith('NAME'):
            gene = line.rstrip().split(' ')[-1]
            db.session.add(EssentialGene(name=gene, source='essential'))
    db.session.commit()


@manager.command
def contigs_count():
    print('Assembly', '# Contigs', 'Bin set', '# Contigs', sep='\t')
    for bin_set in BinSet.query.all():
        count = sum([bin.contigs.count() for bin in bin_set.bins.all()])
        assembly_count = bin_set.assembly.contigs.count()
        print(bin_set.assembly.name, assembly_count, bin_set.name, count, sep='\t')
    
    
@manager.command
def setup():
    db.create_all()
    if not os.path.exists('data'):
        os.mkdir('data')
    o = subprocess.check_output(['checkm', 'taxon_list'], 
        universal_newlines=True)
    rank_taxon = defaultdict(list)
    for line in o.split('\n')[4:-2]:
        rank, taxon, *_ = line.strip().split()
        rank_taxon[rank].append(taxon)
    with open('data/taxon_list.pkl', 'wb') as f:
        pickle.dump(rank_taxon, f, pickle.HIGHEST_PROTOCOL)


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
