from flask import session, jsonify, make_response
from flask_restful import Resource

from app import q, app



class JobsApi(Resource):
    def __init__(self):
        super(JobsApi, self).__init__()
 
    def get(self):
        app.logger.debug(session)
        jobs = []
        job_ids = session.get('jobs', []).copy()
        for job_id in job_ids:
            job = q.fetch_job(job_id)
            if job is None or job.is_finished:
                session['jobs'].remove(job_id)
            else:
                jobs.append({'location': '/jobs/{}'.format(job_id), 'meta': job.meta})
        return jsonify({'jobs': jobs})
       
        
class JobApi(Resource):
    def __init__(self):
        super(JobApi, self).__init__()
 
    def _create_job_response(self, job):
        if job is None:
            return make_response(jsonify({}), 404)
        elif job.is_finished:
            response = make_response(jsonify(job.result), 201)
            if job.meta['type'] == 'A':
                response.headers['Location'] = '/a/{}'.format(job.result['assembly'])
            elif job.meta['type'] == 'B':
                location = '/a/{}/bs/{}'.format(job.result['assembly'],
                                                job.result['binSet']) 
                response.headers['Location'] = location
            return response

    def get(self, job_id):
        app.logger.debug(session)
        job = q.fetch_job(job_id)
        if job is None or job.is_finished:
            return self._create_job_response(job)
        return jsonify(job.meta)
