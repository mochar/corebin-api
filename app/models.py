from collections import Counter

from sqlalchemy.orm import Load
from sqlalchemy import func

from app import db, utils, app


bincontig = db.Table('bincontig',
                     db.Column('bin_id', db.Integer, db.ForeignKey('bin.id')),
                     db.Column('contig_id', db.Integer, db.ForeignKey('contig.id')))


gencontig = db.Table('gencontig',
                     db.Column('gene_id', db.Integer, db.ForeignKey('essential_gene.id')),
                     db.Column('contig_id', db.Integer, db.ForeignKey('contig.id')))


class FastaMixin:
    def save_fa(self, path):
        with open(path, 'w') as f:
            for contig in self.contigs.yield_per(50):
                f.write('>{}\n{}\n'.format(contig.name, contig.sequence))


class Bin(db.Model, FastaMixin):
    __tablename__ = 'bin'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(25))
    bin_set_id = db.Column(db.Integer, db.ForeignKey('bin_set.id'),
                           nullable=False)
    color = db.Column(db.String(7), default='#ffffff')
    gc = db.Column(db.Integer)
    n50 = db.Column(db.Integer)
    contamination = db.Column(db.Integer)
    completeness = db.Column(db.Integer)

    # contigs = db.relationship('Contig', secondary=bincontig, lazy='dynamic',
    #                           backref=db.backref('bins'), viewonly=True)
    contigs = db.relationship('Contig', secondary=bincontig, lazy='dynamic',
                              backref=db.backref('bins'))
    contigs_eager = db.relationship('Contig', secondary=bincontig)

    def recalculate_values(self):
        self.gc = utils.gc_content_bin(self)
        self.n50 = utils.n50(self)
        if self.bin_set.assembly.genes_searched:
            self.calculate_cont_comp()

    def calculate_cont_comp(self):
        all_genes = [gene.name for contig in self.contigs for gene in contig.essential_genes]
        gene_count = Counter(all_genes)
        contaminated_count = len([gene for gene, count in gene_count.items() if count > 1])
        total_reference = EssentialGene.query.filter_by(source='essential').count()
        self.completeness = round(len(gene_count) / total_reference, 4)
        self.contamination = round(contaminated_count / total_reference, 4)

    @property
    def size(self):
        return self.contigs.count()

    @property
    def bp(self):
        if self.size == 0:
            return 0
        return self.contigs.with_entities(func.sum(Contig.length)).scalar()
        
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'binSetId': self.bin_set_id,
            'color': self.color,
            'gc': self.gc,
            'n50': self.n50,
            'size': self.size,
            'mbp': self.bp / 1000000,
            'contamination': self.contamination,
            'completeness': self.completeness
        }


class Contig(db.Model):
    __tablename__ = 'contig'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    length = db.Column(db.Integer)
    gc = db.Column(db.Integer)
    fourmerfreqs = db.Column(db.String)
    assembly_id = db.Column(db.Integer, db.ForeignKey('assembly.id'),
                            nullable=False)
    coverages = db.relationship('Coverage', backref='contig',
                                cascade='all, delete')
    essential_genes = db.relationship('EssentialGene', secondary=gencontig, 
                                      lazy='dynamic', backref=db.backref('contigs'))


class Coverage(db.Model):
    __tablename__ = 'coverage'
    id = db.Column(db.Integer, primary_key=True)
    contig_id = db.Column(db.Integer, db.ForeignKey('contig.id'), nullable=False)
    sample = db.Column(db.String(60))
    value = db.Column(db.Integer)


class BinSet(db.Model):
    __tablename__ = 'bin_set'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    color = db.Column(db.String(7))
    bins = db.relationship('Bin', backref='bin_set', lazy='dynamic',
                           cascade='all, delete')
    assembly_id = db.Column(db.Integer, db.ForeignKey('assembly.id'),
                            nullable=False)
    @property
    def without_unbinned(self):
        return self.bins.filter(Bin.name != 'unbinned')


class Assembly(db.Model, FastaMixin):
    __tablename__ = 'assembly'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    userid = db.Column(db.String(36))
    submit_date = db.Column(db.DateTime)
    has_fourmerfreqs = db.Column(db.Boolean)
    genes_searched = db.Column(db.Boolean)
    contigs = db.relationship('Contig', backref='assembly', lazy='dynamic',
                              cascade='all, delete')
    bin_sets = db.relationship('BinSet', backref='assembly', lazy='dynamic',
                               cascade='all, delete')
                               
    @property
    def samples(self):
        samples = self.contigs.join(Coverage.contig) \
            .options(Load(Coverage).load_only('sample')) \
            .with_entities('sample') \
            .distinct() \
            .all()
        return [sample[0] for sample in samples]
        
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'size': self.contigs.count(),
            'hasFourmerfreqs': self.has_fourmerfreqs,
            'genesSearched': self.genes_searched,
            'binSets': self.bin_sets.count(),
            'samples': self.samples,
            'submitDate': self.submit_date.isoformat(' ')
        }


class EssentialGene(db.Model):
    __tablename__ = 'essential_gene'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    source = db.Column(db.String(50), nullable=False)
