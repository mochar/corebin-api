from flask import session, jsonify, url_for
from flask_restful import Resource

from app import q, app


class JobsApi(Resource):
    def __init__(self):
        super(JobsApi, self).__init__()
 
    def get(self):
        jobs = []
        job_ids = session.get('jobs', []).copy()
        for job_id in job_ids:
            job = q.fetch_job(job_id)
            if job is None or job.is_finished:
                session['jobs'].remove(job_id)
            else:
                jobs.append({
                    'location': '{}/{}'.format(url_for('jobsapi', _external=True), job_id),
                    'meta': job.meta
                })
        return {'jobs': jobs}
       
        
class JobApi(Resource):
    def __init__(self):
        super(JobApi, self).__init__()
 
    def _create_job_response(self, job):
        if job is None:
            return {}, 404
        elif job.is_finished:
            response = [job.result, 201, {}]
            if job.meta['type'] == 'A':
                response[2]['Location'] = '/a/{}'.format(job.result['assembly'])
            elif job.meta['type'] == 'B':
                location = '/a/{}/bs/{}'.format(job.result['assembly'],
                                                job.result['binSet']) 
                response[2]['Location'] = location
            return tuple(response)

    def get(self, job_id):
        job = q.fetch_job(job_id)
        if job is None or job.is_finished:
            session['jobs'].remove(job_id)
            return self._create_job_response(job)
        return job.meta

    def delete(self, job_id):
        session['jobs'].remove(job_id)
        q.fetch_job(job_id).cancel()
        return {}
