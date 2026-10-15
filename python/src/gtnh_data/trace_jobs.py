"""Process-local material trace lifetimes on one SQLite-owning worker per Dataset."""

import atexit
import math
import threading
import time
import uuid
from copy import deepcopy

from .dataset import DatasetError, _json


MAX_JOBS = 4
IDLE_SECONDS = 15 * 60
SLICE_SECONDS = .25


def validate_time_budget(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not .05 <= value <= 60:
        raise DatasetError('time_budget_seconds must be finite and between 0.05 and 60')


class TraceJobs:
    def __init__(self, dataset):
        self.dataset = dataset
        self.jobs = {}
        self.condition = threading.Condition()
        self.stopping = False
        self.worker = threading.Thread(target=self._work, name='material-trace', daemon=True)
        self.worker.start()
        atexit.register(self.shutdown)

    def _job(self, job_id):
        if not isinstance(job_id, str) or job_id not in self.jobs:
            raise DatasetError(f'Unknown trace search job: {job_id}')
        job = self.jobs[job_id]
        job['_touched'] = time.monotonic()
        return job

    def _envelope(self, job, after_revision=None):
        fields = ('job_id', 'snapshot_id', 'revision', 'status', 'phase', 'elapsed_seconds',
                  'progress', 'result_revision', 'request', 'error', 'first_result_seconds')
        answer = {key: job[key] for key in fields if key in job}
        if 'result' in job and (after_revision is None or job['result_revision'] > after_revision):
            answer['result'] = job['result']
        # Published records are detached and never mutated by the worker.
        return answer

    def start(self, request, seconds, multiplier):
        with self.condition:
            if self.stopping:
                raise DatasetError('Trace searches have been shut down')
            if any(job['status'] == 'running' for job in self.jobs.values()):
                raise DatasetError('A trace search is already running. Pause or close it before starting another')
            for key, job in list(self.jobs.items()):
                if job['status'] == 'closed' and job.get('_disposed', False):
                    del self.jobs[key]
            if len(self.jobs) >= MAX_JOBS:
                raise DatasetError(f'At most {MAX_JOBS} trace search jobs may be retained. Close an existing job')
            job_id = uuid.uuid4().hex
            job = dict(job_id=job_id, snapshot_id=self.dataset.snapshot_id, revision=1, status='running',
                       phase='initializing', elapsed_seconds=0., progress={}, result_revision=0,
                       request=dict(deepcopy(request), budget_multiplier=multiplier), _remaining=seconds,
                       _created=time.monotonic(), _touched=time.monotonic(), _pause=False, _close=False, _handle=None, _connection=None,
                       _context=None, _signature=None, _disposed=False)
            self.jobs[job_id] = job
            answer = self._envelope(job)
            self.condition.notify_all()
        return deepcopy(answer)

    def get(self, job_id, after_revision=None):
        if after_revision is not None and (type(after_revision) is not int or after_revision < 0):
            raise DatasetError('after_revision must be a nonnegative integer')
        with self.condition:
            job = self._job(job_id)
            answer = self._envelope(job, after_revision)
        return deepcopy(answer)

    def pause(self, job_id):
        with self.condition:
            job = self._job(job_id)
            if job['status'] == 'running':
                job['_pause'] = True
                self.condition.notify_all()
            answer = self._envelope(job)
        return deepcopy(answer)

    def resume(self, job_id, seconds):
        validate_time_budget(seconds)
        with self.condition:
            job = self._job(job_id)
            if job['status'] != 'paused' or job['_close']:
                raise DatasetError('Only a paused trace search may be continued')
            if any(other['status'] == 'running' for other in self.jobs.values()):
                raise DatasetError('A trace search is already running')
            job.update(status='running', revision=job['revision'] + 1, _remaining=seconds, _pause=False)
            self.condition.notify_all()
            answer = self._envelope(job)
        return deepcopy(answer)

    def close(self, job_id):
        with self.condition:
            job = self._job(job_id)
            job['_close'] = True
            if job['status'] != 'running' and job['status'] != 'closed':
                self._mark_closed(job)
            self.condition.notify_all()
            answer = self._envelope(job, job['revision'])
        return deepcopy(answer)

    @staticmethod
    def _mark_closed(job):
        job.update(status='closed', phase='closed', revision=job['revision'] + 1)
        job.pop('result', None)

    def shutdown(self):
        with self.condition:
            self.stopping = True
            for job in self.jobs.values():
                job['_close'] = True
            self.condition.notify_all()
        if threading.current_thread() is not self.worker:
            self.worker.join()
        atexit.unregister(self.shutdown)

    def _dispose(self, job):
        # Called only by the worker which constructed these SQLite handles.
        handle, context = job['_handle'], job['_context']
        job['_handle'], job['_context'], job['_connection'] = None, None, None
        job.pop('_trace_context', None)
        job['_signature'] = None
        try:
            if handle is not None:
                handle.close()
        finally:
            if context is not None:
                context.__exit__(None, None, None)
            job['_disposed'] = True

    def _work(self):
        while True:
            with self.condition:
                now = time.monotonic()
                disposable = []
                for job in self.jobs.values():
                    if job['status'] != 'running' and now - job['_touched'] >= IDLE_SECONDS:
                        job['_close'] = True
                    if job['_close'] and job['status'] != 'running':
                        if job['status'] != 'closed':
                            self._mark_closed(job)
                        if not job['_disposed']:
                            disposable.append(job)
                running = next((job for job in self.jobs.values() if job['status'] == 'running'), None)
                if running is None and not disposable:
                    if self.stopping:
                        return
                    self.condition.wait(timeout=30)
                    continue
            for job in disposable:
                self._dispose(job)
            if running is not None:
                self._slice(running)

    def _slice(self, job):
        started = time.monotonic()
        try:
            with self.condition:
                stop = job['_close'] or self.stopping
                pause = job['_pause']
            if stop or pause:
                with self.condition:
                    if stop:
                        self._mark_closed(job)
                    else:
                        job.update(status='paused', revision=job['revision'] + 1)
                if stop:
                    self._dispose(job)
                return
            if job['_handle'] is None:
                from .flow_index import begin_search
                context = self.dataset._connect()
                connection = context.__enter__()
                job['_context'], job['_connection'] = context, connection
                request = job['request']
                trace_context = self.dataset._trace_context(connection, request)
                required, excluded, _, tier_filter = trace_context
                job['_trace_context'] = trace_context
                job['_handle'] = begin_search(self.dataset, connection, request['start_id'], request['target_id'],
                    request['max_depth'], request['max_processes'], request['max_paths'], required, excluded,
                    request['max_extra_steps'], tier_filter, request['terminal_artifact_policy'],
                    budget_multiplier=request['budget_multiplier'])
            handle = job['_handle']
            step = handle.advance(min(SLICE_SECONDS, max(.001, job['_remaining'])))
            snapshot = handle.snapshot()
            route, paths, progress, reasons, duplicates, branches = snapshot
            signature = _json([route, paths, reasons, duplicates, branches])
            finished = step['status'] == 'finished'
            result = None
            if finished or (paths and signature != job['_signature']):
                result = self.dataset._render_trace(job['_connection'], job['request'], job['_trace_context'], snapshot)
            elapsed = time.monotonic() - started
            with self.condition:
                job['elapsed_seconds'] += elapsed
                job['_remaining'] -= elapsed
                job.update(progress=deepcopy(progress), phase=step['phase'], revision=job['revision'] + 1)
                if result is not None:
                    job.update(result=result, result_revision=job['revision'], _signature=signature)
                    if result['paths'] and 'first_result_seconds' not in job:
                        job['first_result_seconds'] = time.monotonic() - job['_created']
                if job['_close'] or self.stopping:
                    self._mark_closed(job)
                elif finished:
                    job.update(status='finished', phase='finished')
                elif job['_pause'] or job['_remaining'] <= 0:
                    job['status'] = 'paused'
                job['_touched'] = time.monotonic()
                terminal = job['status'] in ('closed', 'finished')
            if terminal:
                self._dispose(job)
        except Exception as error:
            with self.condition:
                job.update(status='failed', phase='failed', error=str(error), revision=job['revision'] + 1)
                job['elapsed_seconds'] += time.monotonic() - started
            self._dispose(job)
