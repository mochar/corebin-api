from flask import session, abort

from app.models import Assembly, BinSet


def user_assembly_or_404(id):
    userid = session.get('userid')
    if userid is None:
        abort(404)
    assembly = Assembly.query.filter_by(userid=userid, id=id).first()
    if assembly is None:
        abort(404)
    return assembly


def bin_set_or_404(assembly_id, id):
    assembly = user_assembly_or_404(assembly_id)
    bin_set = assembly.bin_sets.filter_by(id=id).first()
    if bin_set is None:
        abort(404)
    return bin_set
    