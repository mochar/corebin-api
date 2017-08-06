from flask import session, abort

from app.models import Assembly, BinSet


def user_assembly_or_404(id):
    userid = session.get('userid')
    if userid is None:
        abort(404)
    return Assembly.query.filter_by(userid=userid, id=id).first_or_404()


def bin_set_or_404(assembly_id, id, return_assembly=False):
    assembly = user_assembly_or_404(assembly_id)
    bin_set = assembly.bin_sets.filter_by(id=id).first_or_404()
    if return_assembly:
        return assembly, bin_set
    return bin_set
    
    
def bin_or_404(assembly_id, bin_set_id, id, return_bin_set=False):
    bin_set = bin_set_or_404(assembly_id, bin_set_id)
    bin = bin_set.bins.filter_by(id=id).first_or_404()
    if return_bin_set:
        return bin_set, bin
    return bin
