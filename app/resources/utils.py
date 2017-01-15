from flask import session, abort

from app.models import Assembly, BinSet


def user_assembly_or_404(id):
    userid = session.get('userid')
    if userid is None:
        abort(404)
    return Assembly.query.filter_by(userid=userid, id=id).first_or_404()


def bin_set_or_404(assembly_id, id):
    assembly = user_assembly_or_404(assembly_id)
    return assembly.bin_sets.filter_by(id=id).first_or_404()
    
    
def bin_or_404(assembly_id, bin_set_id, id):
    bin_set = bin_set_or_404(assembly_id, bin_set_id)
    return bin_set.bins.filter_by(id=id).first_or_404()
