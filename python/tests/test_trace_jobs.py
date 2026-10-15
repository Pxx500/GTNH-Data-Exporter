import itertools
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from gtnh_data import Dataset, DatasetError
from .artifacts import choice, process, resource, slot, snapshot


class TraceJobTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.dataset = Dataset.import_snapshot(snapshot(root / 'capture',
            resources=[resource(id) for id in ('start', 'middle', 'target')],
            processes=[process('direct', [slot(choice('start'))], ['target']),
                       process('first', [slot(choice('start'))], ['middle']),
                       process('last', [slot(choice('middle'))], ['target'])]), root / 'data.sqlite')
        self.addCleanup(lambda: self.dataset.shutdown_trace_searches())

    def wait(self, job):
        deadline = time.monotonic() + 10
        while job['status'] == 'running' and time.monotonic() < deadline:
            time.sleep(.01)
            job = self.dataset.get_trace_search(job['job_id'])
        self.assertNotEqual(job['status'], 'running', job)
        return job

    def test_job_result_matches_synchronous_trace_and_revision_poll_omits_result(self):
        args = dict(start_id='start', target_id='target', path_selection='material', view='compact')
        expected = self.dataset.trace_processes(**args)
        started = self.dataset.start_trace_search(**args)
        final = self.wait(started)
        self.assertEqual(final['status'], 'finished', final)
        for field in ('paths', 'resources', 'processes', 'edges', 'leaves', 'limit_reasons', 'path_details'):
            self.assertEqual(final['result'][field], expected[field], field)
        unchanged = self.dataset.get_trace_search(final['job_id'], after_revision=final['revision'])
        self.assertNotIn('result', unchanged)
        self.assertEqual(unchanged['result_revision'], final['result_revision'])
        closed = self.dataset.close_trace_search(final['job_id'])
        self.assertEqual(closed['status'], 'closed')
        self.assertEqual(self.dataset.close_trace_search(final['job_id'])['status'], 'closed')
        with self.assertRaises(DatasetError):
            self.dataset.continue_trace_search(final['job_id'])

    def test_partial_publication_pause_and_continue_preserve_work_and_final_result(self):
        args = dict(start_id='start', target_id='target', max_paths=8, path_selection='material')
        expected = self.dataset.trace_processes(**args)
        # Advance a deterministic clock at checkpoints so the public minimum budget
        # yields even on fast machines. The engine, SQL and trace rendering are real.
        engine_ticks, job_ticks = itertools.count(), itertools.count()
        engine_clock = SimpleNamespace(perf_counter=lambda: next(engine_ticks) * .1)
        job_clock = SimpleNamespace(monotonic=lambda: next(job_ticks) * .1)
        with patch('gtnh_data.flow_index.time', engine_clock), patch('gtnh_data.trace_jobs.time', job_clock):
            job = self.dataset.start_trace_search(**args, time_budget_seconds=.05)
            job_id, previous_work, partial = job['job_id'], 0, None
            self.dataset.pause_trace_search(job_id)
            for _ in range(100):
                job = self.wait(job)
                work = job['progress'].get('expansion_work', 0)
                self.assertGreaterEqual(work, previous_work)
                previous_work = work
                if job['status'] == 'finished':
                    break
                self.assertEqual(job['status'], 'paused', job)
                if job.get('result', {}).get('paths'):
                    partial = job
                    self.assertIn('first_result_seconds', job)
                    self.assertNotIn('time_limit', job['result']['limit_reasons'])
                    unchanged = self.dataset.get_trace_search(job_id, job['revision'])
                    self.assertNotIn('result', unchanged)
                    acknowledged = self.dataset.pause_trace_search(job_id)
                    self.assertEqual(acknowledged['result']['paths'], job['result']['paths'])
                job = self.dataset.continue_trace_search(job_id, time_budget_seconds=.05)
                self.assertEqual(job['job_id'], job_id)
            else:
                self.fail('finite synthetic job did not finish')
            self.assertIsNotNone(partial, 'No validated result was published before completion')
            self.assertEqual(job['result']['paths'], expected['paths'])
            self.assertGreater(job['elapsed_seconds'], partial['elapsed_seconds'])
            self.assertLess(partial['revision'], job['revision'])
            self.assertLessEqual(partial['first_result_seconds'], job['first_result_seconds'])

    def test_invalid_requests_match_synchronous_validation_and_do_not_start_jobs(self):
        base = dict(start_id='start', target_id='target', path_selection='material')
        for change in ({'max_depth': True}, {'view': 'unknown'}, {'start_id': 'missing'},
                       {'required_resource_ids': 'middle'}, {'excluded_resource_ids': ['missing']},
                       {'excluded_group_ids': ['missing']}, {'terminal_artifact_policy': 'unknown'}):
            args = dict(base, **change)
            with self.subTest(change=change):
                with self.assertRaises(DatasetError) as synchronous:
                    self.dataset.trace_processes(**args)
                with self.assertRaises(DatasetError) as progressive:
                    self.dataset.start_trace_search(**args)
                self.assertEqual(str(progressive.exception), str(synchronous.exception))
        for change in ({'time_budget_seconds': True}, {'time_budget_seconds': .01},
                       {'time_budget_seconds': float('nan')}, {'time_budget_seconds': float('inf')},
                       {'budget_multiplier': True}, {'budget_multiplier': 11},
                       {'path_selection': 'shortest'}, {'path_selection': 'diverse'}, {'unexpected': 1}):
            with self.subTest(change=change), self.assertRaises(DatasetError):
                self.dataset.start_trace_search(**dict(base, **change))

    def test_logical_path_cap_finishes_instead_of_pausing(self):
        job = self.wait(self.dataset.start_trace_search(start_id='start', target_id='target', max_paths=1))
        self.assertEqual(job['status'], 'finished', job)
        self.assertIn('path_limit', job['result']['limit_reasons'])
        with self.assertRaises(DatasetError):
            self.dataset.continue_trace_search(job['job_id'])

    def test_worker_failure_releases_job_and_allows_a_new_search(self):
        self.dataset.flow_index_status()
        # A missing prepared index is a real supported failure of material tracing.
        self.dataset.path.with_suffix('.flow.sqlite').unlink(missing_ok=True)
        job = self.wait(self.dataset.start_trace_search(start_id='start', target_id='target'))
        self.assertEqual(job['status'], 'failed', job)
        self.assertIn('index', job['error'].lower())
        self.dataset.close_trace_search(job['job_id'])
        self.dataset.rebuild_flow_index()
        next_job = self.wait(self.dataset.start_trace_search(start_id='start', target_id='target'))
        self.assertEqual(next_job['status'], 'finished', next_job)

    def test_replacement_waits_for_cooperative_close_and_then_can_start(self):
        started = self.dataset.start_trace_search(start_id='start', target_id='target')
        closing = self.dataset.close_trace_search(started['job_id'])
        self.assertIn(closing['status'], ('running', 'closed'))
        closed = self.wait(closing)
        self.assertEqual(closed['status'], 'closed', closed)
        replacement = self.wait(self.dataset.start_trace_search(start_id='start', target_id='target'))
        self.assertEqual(replacement['status'], 'finished', replacement)

    def test_retained_jobs_are_bounded_and_explicit_close_frees_capacity(self):
        jobs = [self.wait(self.dataset.start_trace_search(start_id='start', target_id='target')) for _ in range(4)]
        with self.assertRaisesRegex(DatasetError, 'retained'):
            self.dataset.start_trace_search(start_id='start', target_id='target')
        self.dataset.close_trace_search(jobs[0]['job_id'])
        self.assertEqual(self.dataset.get_trace_search(jobs[1]['job_id'])['status'], 'finished')
        replacement = self.wait(self.dataset.start_trace_search(start_id='start', target_id='target'))
        self.assertEqual(replacement['status'], 'finished')
