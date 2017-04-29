from collections import Counter

from flask_restful import Resource, reqparse

from .utils import bin_set_or_404
from app import db, app
from app.models import Contig, EssentialGene


class AssessApi(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('contigs', action='append', type=int, default=[],
                                    required=True)
        self.reqparse.add_argument('to_bin', type=int, required=True)
        super(AssessApi, self).__init__()

    def put(self, assembly_id, id):
        bin_set = bin_set_or_404(assembly_id, id)
        args = self.reqparse.parse_args()
        refine_contigs_ids = set(args.contigs)
        refine_contigs = bin_set.assembly.contigs. \
            filter(Contig.id.in_(refine_contigs_ids)). \
            all()
        bins = []
        for bin in bin_set.bins.options(db.lazyload('contigs_eager')).all():
            contigs = bin.contigs.all()

            if bin.id == args.to_bin:
                contigs.extend(refine_contigs)
            elif len(refine_contigs_ids.intersection([contig.id for contig in contigs])) > 0:
                contigs = [contig for contig in contigs if contig.id not in refine_contigs_ids]
            else:
                continue
            
            all_genes = [gene.name for contig in contigs for gene in contig.essential_genes]
            gene_count = Counter(all_genes)
            contaminated_count = len([gene for gene, count in gene_count.items() if count > 1])
            total_reference = EssentialGene.query.filter_by(source='essential').count()
            completeness = round(len(gene_count) / total_reference, 4)
            contamination = round(contaminated_count / total_reference, 4)

            data = {}
            data['bin'] = {'name': bin.name, 'id': bin.id, 'color': bin.color}
            data['before'] = {'contamination': bin.contamination, 'completeness': bin.completeness}
            data['after'] = {'contamination': contamination, 'completeness': completeness}
            bins.append(data)
        return {'bins': bins}