from app import db
from app.models import *


def export_bin_set(bin_set_name, file_name):
    bin_set = BinSet.query.filter_by(name=bin_set_name).first()
    with open(file_name, 'w') as file:
        for bin in bin_set.without_unbinned:
            for contig in bin.contigs.with_entities(Contig.name):
                file.write('{},{}\n'.format(contig[0], bin.name))


def export_assembly(assembly_name, file_name):
    assembly = Assembly.query.filter_by(name=assembly_name).first()
    with open(file_name, 'w') as file:
        for contig in assembly.contigs.with_entities(Contig.name, Contig.sequence).yield_per(1000):
            file.write('>{}\n{}\n'.format(contig[0], contig[1]))
