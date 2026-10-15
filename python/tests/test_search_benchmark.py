import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from gtnh_data import Dataset
from .artifacts import choice, process, resource, slot, snapshot


SPEC = importlib.util.spec_from_file_location(
    "benchmark_search", Path(__file__).resolve().parents[2] / "scripts" / "benchmark_search.py")
benchmark = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(benchmark)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class SearchBenchmarkTests(unittest.TestCase):
    def test_wall_time_preserves_failed_job_receipt_and_closes_worker(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            dataset = Dataset.import_snapshot(snapshot(root / 'snapshot',
                resources=[resource(id) for id in ('start', 'target')],
                processes=[process('make', [slot(choice('start'))], ['target'])]), root / 'index.sqlite')
            dataset.rebuild_flow_index()
            request = dict(benchmark.DEFAULT_REQUEST, start_id='start', target_id='target', path_selection='material')
            baseline = dataset.trace_processes(**request)
            dataset.path.with_suffix('.flow.sqlite').unlink()
            report = benchmark.run_wall_time(dataset, {'name': 'failed', 'request': request},
                                             baseline, root, 'failed', [1, 5, 15])
            self.assertEqual(len(report['checkpoints']), 1)
            self.assertEqual(report['checkpoints'][0]['terminal_reason']['status'], 'failed')
            self.assertEqual(report['cleanup']['status'], 'closed')
            self.assertIsNone(report['checkpoints'][0]['metrics'])
            self.assertTrue((root / 'failed-job.json').is_file())

    def test_wall_time_continues_real_frontier_and_records_cooperative_overrun(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            dataset = Dataset.import_snapshot(snapshot(root / 'snapshot',
                resources=[resource(id) for id in ('start', 'middle', 'target')],
                processes=[process('direct', [slot(choice('start'))], ['target']),
                           process('first', [slot(choice('start'))], ['middle']),
                           process('last', [slot(choice('middle'))], ['target'])]), root / 'index.sqlite')
            dataset.rebuild_flow_index()
            request = dict(benchmark.DEFAULT_REQUEST, start_id='start', target_id='target', path_selection='material')
            case = {'name': 'paused', 'request': request, 'expected': {'resource_sequence': ['start', 'target']}}
            baseline = dataset.trace_processes(**request)
            engine_ticks, job_ticks = itertools.count(), itertools.count()
            with patch('gtnh_data.flow_index.time', SimpleNamespace(perf_counter=lambda: next(engine_ticks) * .1)), \
                    patch('gtnh_data.trace_jobs.time', SimpleNamespace(monotonic=lambda: next(job_ticks) * .1)):
                report = benchmark.run_wall_time(dataset, case, baseline, root, 'paused', [.05, .5, 2, 5])
            rows = report['checkpoints']
            self.assertEqual(rows[0]['envelope']['status'], 'paused')
            self.assertGreater(rows[0]['cooperative_overrun_seconds'], 0)
            self.assertEqual({row['envelope']['job_id'] for row in rows}, {report['job_id']})
            actual = [row['actual_active_seconds'] for row in rows]
            self.assertEqual(actual, sorted(actual))
            self.assertGreater(actual[-1], actual[0])
            self.assertEqual(report['cleanup']['status'], 'closed')

    def test_witness_proof_uses_native_unified_consume_match_and_rejects_presence_only(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            sensitive = choice('anchor', 'unified', group='metals')
            sensitive['match']['nbt_sensitive'] = True
            recipes = [process('consume', [slot(choice('anchor', 'unified', group='metals'))], ['target']),
                       process('presence', [slot(choice('start'), role='presence')], ['target']),
                       process('sensitive', [slot(sensitive)], ['target']),
                       process('unresolved', [slot(choice('start'))], ['target'],
                               conditions={'dynamic_inputs': 'unresolved'})]
            dataset = Dataset.import_snapshot(snapshot(root / 'snapshot', resources=[
                resource('start', registry_name='test:metal', nbt={'type': 'byte', 'value': 1}),
                resource('anchor', registry_name='test:metal'),
                resource('target')], groups=[{'id': 'metals', 'kind': 'unified', 'name': 'metals',
                    'members': ['anchor'], 'provenance': {'owner': 'fixture'}}], processes=recipes), root / 'index.sqlite')
            case = {'name': 'alias', 'request': {'start_id': 'start', 'target_id': 'target'},
                    'expected': {'witness': {'resource_ids': ['start', 'target'], 'process_ids': ['consume']}}}
            self.assertEqual(benchmark.validate_witness(dataset, case)['status'], 'valid')
            case['expected']['witness']['process_ids'] = ['presence']
            self.assertEqual(benchmark.validate_witness(dataset, case)['status'], 'invalid')
            case['expected']['witness']['process_ids'] = ['sensitive']
            self.assertEqual(benchmark.validate_witness(dataset, case)['status'], 'invalid')
            case['expected']['witness']['process_ids'] = ['unresolved']
            self.assertEqual(benchmark.validate_witness(dataset, case)['status'], 'unknown')

    def test_read_only_run_preserves_native_and_inputs_and_saves_raw_response(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            recipes = [process('make', [slot(choice('start')), slot(choice('cofeed'))], ['target'])]
            dataset = Dataset.import_snapshot(snapshot(root / 'snapshot',
                resources=[resource(id) for id in ('start', 'cofeed', 'target')],
                processes=recipes), root / 'index.sqlite')
            dataset.rebuild_flow_index()
            request = dict(benchmark.DEFAULT_REQUEST, start_id='start', target_id='target')
            baseline = root / 'baseline.json'
            baseline.write_text(json.dumps({'measurement': {'request': request},
                                           'result': dataset.trace_processes(**request)}))
            sidecar = dataset.path.with_suffix('.flow.sqlite')
            case = {'name': 'miniature', 'request': request,
                    'expected': {'witness': {'resource_ids': ['start', 'target'], 'process_ids': ['make']}},
                    'baseline': {'path': 'baseline.json', 'sha256': benchmark.sha256(baseline)}}
            manifest = {'schema_version': 1, 'binding': {'snapshot_id': 'fixture',
                'cohort_sha256': digest({'mods': []}), 'database_sha256': benchmark.sha256(dataset.path),
                'prepared_index_sha256': benchmark.sha256(sidecar)}, 'regime': 'fixed_work', 'cases': [case]}
            path = root / 'cases.json'
            path.write_text(json.dumps(manifest))
            protected = {p: p.read_bytes() for p in (path, baseline, dataset.path, sidecar)}
            report = benchmark.run_benchmark(dataset.path, path, root / 'run')
            proof = report['preflight']['cases'][0]['witness']
            self.assertEqual(proof['status'], 'valid')
            self.assertEqual(proof['processes'], recipes)
            self.assertEqual(len(proof['processes'][0]['inputs']), 2)
            self.assertEqual(report['runs'][0]['metrics']['expected_witness_path_indices'], [0])
            self.assertTrue(report['inputs_unchanged'])
            self.assertEqual(protected, {p: p.read_bytes() for p in protected})
            saved = json.loads((root / 'run' / report['runs'][0]['response']).read_text())
            self.assertEqual(saved['snapshot_id'], 'fixture')
            with self.assertRaises(FileExistsError):
                benchmark.run_benchmark(dataset.path, path, root / 'run')

    def test_manifest_binds_saved_query_and_requires_material_wall_time_checkpoints(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            dataset = Dataset.import_snapshot(snapshot(root / 'snapshot'), root / 'index.sqlite')
            request = {'start_id': 'start', 'target_id': 'target'}
            baseline = root / 'saved.json'
            baseline.write_text(json.dumps({'measurement': {'request': request},
                                           'result': {'snapshot_id': 'fixture'}}))
            manifest = {'schema_version': 1, 'binding': {'snapshot_id': 'fixture',
                'cohort_sha256': digest({'mods': []}),
                'database_sha256': hashlib.sha256(dataset.path.read_bytes()).hexdigest()},
                'regime': 'fixed_work', 'cases': [{'name': 'control',
                    'request': dict(request, max_depth=13),
                    'baseline': {'path': 'saved.json',
                                 'sha256': hashlib.sha256(baseline.read_bytes()).hexdigest()}}]}
            path = root / 'cases.json'
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'saved request'):
                benchmark.load_manifest(dataset, path)
            manifest['cases'][0]['request'] = request
            manifest['regime'] = 'wall_time'
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'checkpoints'):
                benchmark.load_manifest(dataset, path)

    def test_wall_time_checkpoints_keep_one_real_job_and_close_early_terminal(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            dataset = Dataset.import_snapshot(snapshot(root / 'snapshot',
                resources=[resource(id) for id in ('start', 'target')],
                processes=[process('make', [slot(choice('start'))], ['target'])]), root / 'index.sqlite')
            dataset.rebuild_flow_index()
            request = dict(benchmark.DEFAULT_REQUEST, start_id='start', target_id='target', path_selection='material')
            baseline = dataset.trace_processes(**request)
            case = {'name': 'tiny', 'request': request, 'budget_multiplier': 1,
                    'expected': {'resource_sequence': ['start', 'target']}}
            report = benchmark.run_wall_time(dataset, case, baseline, root, 'tiny', [1, 5, 15])
            checkpoints = report['checkpoints']
            self.assertEqual([row['requested_cumulative_seconds'] for row in checkpoints], [1, 5, 15])
            self.assertEqual({row['envelope']['job_id'] for row in checkpoints}, {report['job_id']})
            self.assertTrue(all(row['early_terminal'] for row in checkpoints))
            self.assertTrue(all(row['envelope']['status'] == 'finished' for row in checkpoints))
            self.assertEqual(report['cleanup']['status'], 'closed')
            self.assertIsNotNone(report['first_observed_expected_story'])
            self.assertIsNotNone(checkpoints[0]['envelope']['first_result_seconds'])
            self.assertTrue((root / checkpoints[0]['response']).is_file())
            self.assertEqual(dataset.get_trace_search(report['job_id'])['status'], 'closed')

    def test_metrics_separate_path_identity_story_order_and_branch_coverage(self):
        original = {'resource_ids': ['start', 'acid', 'oxide', 'target'],
                    'process_ids': ['a', 'b', 'c']}
        alternate = dict(original, process_ids=['a2', 'b2', 'c2'])
        direct = {'resource_ids': ['start', 'target'], 'process_ids': ['direct']}
        case = {'request': {'start_id': 'start', 'target_id': 'target', 'max_paths': 8,
                            'max_depth': 12, 'max_processes': 300},
                'expected': {'witness': original, 'resource_sequence': original['resource_ids'],
                             'family_sequence': ['acid', 'heat', 'reduce'],
                             'target_jobs': [['c2', 0], ['other', 1]]}}
        result = {'paths': [direct, alternate], 'route': direct,
                  'processes': [{'id': id, 'family': family} for id, family in
                                [('direct', 'shortcut'), ('a2', 'acid'), ('b2', 'heat'), ('c2', 'reduce')]],
                  'branch_coverage': [{'target_process_id': 'c2', 'slot_index': 0, 'path_indices': [1]},
                                      {'target_process_id': 'other', 'slot_index': 1, 'path_indices': []}],
                  'search': {'expansion_work': 25, 'requirement_classes': {'represented_classes': 1}},
                  'limit_reasons': ['work_limit']}
        baseline = dict(result, paths=[original, direct], route=original)
        metrics = benchmark.evaluate_result(case, result, baseline)
        self.assertEqual(metrics.get('path_set'), {'common': 1, 'added': 1, 'removed': 1,
                                                  'precision': 0.5, 'recall': 0.5})
        self.assertFalse(metrics['first_route']['same_as_baseline'])
        self.assertEqual(metrics['expected_witness_path_indices'], [])
        self.assertEqual(metrics['resource_sequence_path_indices'], [1])
        self.assertEqual(metrics['family_sequence_path_indices'], [1])
        self.assertEqual(metrics['target_jobs']['represented'], 1)
        self.assertEqual(metrics['target_jobs']['expected_recall'], 0.5)
        self.assertEqual(metrics['search']['expansion_work'], 25)
        self.assertEqual(metrics['structural_errors'], [])

    def test_manifest_refuses_different_snapshot_or_mod_cohort(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            dataset = Dataset.import_snapshot(snapshot(root / 'snapshot'), root / 'index.sqlite')
            manifest = {'schema_version': 1, 'binding': {
                'snapshot_id': 'another-snapshot', 'cohort_sha256': digest({'mods': []})},
                'regime': 'fixed_work', 'cases': []}
            path = root / 'cases.json'
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'snapshot'):
                benchmark.load_manifest(dataset, path)
            manifest['binding'].update(snapshot_id='fixture', cohort_sha256='0' * 64)
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'cohort'):
                benchmark.load_manifest(dataset, path)


if __name__ == '__main__':
    unittest.main()
