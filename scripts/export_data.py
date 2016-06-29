from app import db
from app.models import *


def list_tables():
    print('Assembly', '-'*20, sep='\n')
    print('id', 'name', 'userid', sep='\t')
    for assembly in Assembly.query.all():
        print(assembly.id, assembly.name, assembly.userid, sep='\t')
        
    print('\nBin set', '-'*20, sep='\n')
    print('id', 'name', 'assembly', sep='\t')
    for bin_set in BinSet.query.all():
        print(bin_set.id, bin_set.name, bin_set.assembly_id, sep='\t')


def export_bin_set(bin_set_id, file_name):
    bin_set = BinSet.query.get(bin_set_id)
    file_name = '{}.csv'.format(bin_set.name) if file_name is None else file_name
    with open(file_name, 'w') as file:
        for bin in bin_set.without_unbinned:
            for contig in bin.contigs.with_entities(Contig.name):
                file.write('{},{}\n'.format(contig[0], bin.name))


def export_assembly(assembly_id, file_name):
    assembly = Assembly.query.get(assembly_id)
    file_name = '{}.fa'.format(assembly.name) if file_name is None else file_name
    with open(file_name, 'w') as file:
        for contig in assembly.contigs.with_entities(Contig.name, Contig.sequence).yield_per(1000):
            file.write('>{}\n{}\n'.format(contig[0], contig[1]))
