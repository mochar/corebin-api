from app import db, utils


bincontig = db.Table('bincontig',
                     db.Column('bin_id', db.Integer, db.ForeignKey('bin.id')),
                     db.Column('contig_id', db.Integer, db.ForeignKey('contig.id')))


class Bin(db.Model):
    __tablename__ = 'bin'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(25))
    bin_set_id = db.Column(db.Integer, db.ForeignKey('bin_set.id'),
                           nullable=False)
    color = db.Column(db.String(7), default='#ffffff')
    gc = db.Column(db.Integer)
    n50 = db.Column(db.Integer)

    contigs = db.relationship('Contig', secondary=bincontig, lazy='dynamic',
                              backref=db.backref('bins'))

    def recalculate_values(self):
        self.gc = utils.gc_content_bin(self)
        self.n50 = utils.n50(self)

    @property
    def size(self):
        return self.contigs.count()


class Contig(db.Model):
    __tablename__ = 'contig'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    sequence = db.Column(db.String)
    length = db.Column(db.Integer)
    gc = db.Column(db.Integer)
    fourmerfreqs = db.Column(db.String)
    assembly_id = db.Column(db.Integer, db.ForeignKey('assembly.id'),
                            nullable=False)
    coverages = db.relationship('Coverage', backref='contig',
                                cascade='all, delete')


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


class Assembly(db.Model):
    __tablename__ = 'assembly'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    userid = db.Column(db.String(36))
    contigs = db.relationship('Contig', backref='assembly', lazy='dynamic',
                              cascade='all, delete')
    bin_sets = db.relationship('BinSet', backref='assembly', lazy='dynamic',
                               cascade='all, delete')
                               
    @property
    def samples(self):
        samples = Coverage.query.join(Coverage.contig) \
            .filter(Contig.assembly == self) \
            .with_entities(Coverage.sample) \
            .distinct() \
            .all()
        return [sample[0] for sample in samples]
