from flask_restful import Resource, reqparse, inputs

from .utils import user_assembly_or_404
from app import db, app, utils
from app.models import Contig, Bin


def filter_contigs(attr, value):
    _value = value
    value = value.rstrip('e').rstrip('l').rstrip('g')
    if not utils.is_number(value):
        return
    value = float(value)
    if _value.endswith('l'):
        filter = attr < value
    elif _value.endswith('le'):
        filter = attr <= value
    elif _value.endswith('g'):
        filter = attr > value
    elif _value.endswith('ge'):
        filter = attr >= value
    else:
        filter = attr == value
    return filter
    
    
class ContigsApi(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('items', type=int, default=50, dest='_items')
        self.reqparse.add_argument('index', type=int, default=1)
        self.reqparse.add_argument('sort', type=str, choices=[
            'id', 'name', 'gc', 'length', '-id', '-name', '-gc', '-length'])
        self.reqparse.add_argument('fields', type=str,
                                   default='id,name,length,gc,assembly_id')
        self.reqparse.add_argument('length', type=str, action='append', default=[])
        self.reqparse.add_argument('gc', type=str, action='append', default=[])
        self.reqparse.add_argument('bins', type=str)
        self.reqparse.add_argument('coverages', type=inputs.boolean)
        self.reqparse.add_argument('colors', type=inputs.boolean)
        self.reqparse.add_argument('contigs', type=inputs.boolean, default=True)
        self.reqparse.add_argument('pca', type=inputs.boolean, default=False)
        super(ContigsApi, self).__init__()

    def get(self, assembly_id):
        args = self.reqparse.parse_args()
        contigs = user_assembly_or_404(assembly_id).contigs
        if args.fields:
            fields = args.fields.split(',')
            contigs = contigs.options(db.load_only(*fields))
        if args.sort:
            order = db.desc(args.sort[1:]) if args.sort[0] == '-' else db.asc(args.sort)
            contigs = contigs.order_by(order)
        if args.length:
            for value in args.length:
                filter = filter_contigs(Contig.length, value)
                contigs = contigs.filter(filter)
        if args.gc:
            for value in args.gc:
                filter = filter_contigs(Contig.gc, value)
                contigs = contigs.filter(filter)
        if args.bins:
            contigs = contigs.options(db.joinedload('bins'))
            bin_ids = args.bins.split(',')
            contigs = contigs.join((Bin, Contig.bins)).filter(Bin.id.in_(bin_ids))
        if args.coverages:
            contigs = contigs.options(db.joinedload('coverages'))
        contig_pagination = contigs.paginate(args.index, args._items, False)
        
        if args.pca:
            p_components = utils.pca_fourmerfreqs(contig_pagination.items)
            
        result = []
        for i, contig in enumerate(contig_pagination.items):
            r = {}
            if args.fields:
                for field in fields:
                    r[field] = getattr(contig, field)
            if args.coverages:
                for cov in contig.coverages:
                    r[cov.sample] = cov.value
            if args.pca:
                r['pc_1'], r['pc_2'], r['pc_3'] = p_components[i]
            if args.colors:
                for bin in contig.bins:
                    r['color_{}'.format(bin.bin_set_id)] = bin.color
            result.append(r)

        return {
            'contigs': result if args.contigs else [], 
            'indices': contig_pagination.pages,
            'index': args.index, 'count': contigs.count(), 
            'items': args._items
        }
