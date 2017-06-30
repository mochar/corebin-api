import uuid
from datetime import datetime

from flask import session, jsonify

from app import app, db, q
from app.models import Assembly


def clear_session_object(db_object):
    db.session.expunge(db_object)
    db.make_transient(db_object)
    db_object.id = None
    return db_object


def create_demo_job(userid):
    # New assembly object
    new_assembly = Assembly.query.get(1)
    clear_session_object(new_assembly)
    
    # Demo assembly used as reference
    demo_assembly = Assembly.query.get(1)

    # Modify new assembly object
    new_assembly.userid = userid
    new_assembly.deleted = False
    new_assembly.demo = True
    new_assembly.submit_date = datetime.utcnow()

    #
    contig_mapper = {}
    for contig in demo_assembly.contigs.all():
        contig_id = contig.id
        essential_genes = contig.essential_genes.all()
        clear_session_object(contig)
        contig.essential_genes = essential_genes
        contig_mapper[contig_id] = contig
    new_assembly.contigs = list(contig_mapper.values())

    # Add bin sets
    for bin_set in demo_assembly.bin_sets.all():
        bins = []
        for bin in bin_set.bins.all():
            bin_contigs = [contig_mapper[c.id] for c in bin.contigs.all()]
            clear_session_object(bin)
            bin.contigs = bin_contigs
            bins.append(bin)
        clear_session_object(bin_set)
        bin_set.bins = bins
        new_assembly.bin_sets.append(bin_set)

    db.session.add(new_assembly)
    db.session.commit()

    return {'assembly': new_assembly.id}


@app.route('/demo')
def demo():
    if not 'userid' in session:
        session['userid'] = str(uuid.uuid4())
        session['jobs'] = []
        session.permanent = True

    # Create a job
    job_args = [session['userid']]
    job_meta = {'name': 'Demo', 'status': 'Setting up data...', 'type': 'A', 'notfound': []}
    job = q.enqueue(create_demo_job, args=job_args, meta=job_meta, timeout=60*60)
    session['jobs'].append(job.id)

    return jsonify(job_meta), 202, {'Location': '/jobs/{}'.format(job.id)}
