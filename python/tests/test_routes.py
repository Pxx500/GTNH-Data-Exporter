import tempfile
import unittest
from pathlib import Path

from gtnh_data import Dataset
from .artifacts import choice, process, resource, slot, snapshot


class RouteTests(unittest.TestCase):
    def test_unrelated_branches_cannot_spend_the_route_budget(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ids = ['start', 'middle', 'target', 'circuit', 'byproduct']
            ids += [f'noise-{index}' for index in range(8)]
            rows = [process(f'a-noise-{index}', [slot(choice('start'))], [f'noise-{index}'])
                    for index in range(8)]
            rows += [process('z-first', [slot(choice('start')), slot(choice('circuit'), role='presence')],
                             ['middle', 'byproduct']),
                     process('z-finish', [slot(choice('middle'))], ['target'])]
            artifact = snapshot(root / 'capture', resources=[resource(id) for id in ids], processes=rows)
            dataset = Dataset.import_snapshot(artifact, root / 'index.sqlite')
            result = dataset.trace_processes(start_id='start', target_id='target', max_processes=2)
            self.assertEqual({row['id'] for row in result['processes']}, {'z-first', 'z-finish'})
            self.assertIn('byproduct', {row['id'] for row in result['resources']})
            self.assertIn('circuit', {row['id'] for row in result['resources']})
            first = next(row for row in result['processes'] if row['id'] == 'z-first')
            self.assertEqual(first['inputs'][1]['role'], 'presence')
            self.assertEqual(result['route']['process_ids'], ['z-first', 'z-finish'])

    def test_disconnected_and_identical_resources_are_explicit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = snapshot(root / 'capture', resources=[resource(id) for id in ('start', 'noise', 'target')],
                                processes=[process('unrelated', [slot(choice('start'))], ['noise'])])
            dataset = Dataset.import_snapshot(artifact, root / 'index.sqlite')
            result = dataset.trace_processes(start_id='start', target_id='target')
            self.assertEqual(result['route']['status'], 'not_found')
            self.assertFalse(result['truncated'])
            self.assertEqual(result['processes'], [])
            result = dataset.trace_processes(start_id='start', target_id='start')
            self.assertEqual(result['route']['status'], 'same_resource')
            self.assertEqual(result['route']['resource_ids'], ['start'])
            self.assertEqual(result['processes'], [])

    def test_limits_never_present_a_broken_route_as_found(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rows = [process('first', [slot(choice('start'))], ['middle']),
                    process('finish', [slot(choice('middle'))], ['target'])]
            artifact = snapshot(root / 'capture', resources=[resource(id) for id in ('start', 'middle', 'target')], processes=rows)
            dataset = Dataset.import_snapshot(artifact, root / 'index.sqlite')
            for options, reason in (({'max_depth': 1}, 'depth'), ({'max_processes': 1}, 'route_process_limit')):
                with self.subTest(options=options):
                    result = dataset.trace_processes(start_id='start', target_id='target', **options)
                    self.assertEqual(result['route']['status'], 'incomplete')
                    self.assertIn(reason, result['limit_reasons'])
                    self.assertTrue(result['truncated'])
                    self.assertEqual(result['route']['process_ids'], [])
                    self.assertEqual(result['processes'], [])

    def test_zero_yield_context_cannot_seed_a_cycle(self):
        for defect in ('zero_amount', 'zero_chance'):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                zero = process('zero-yield', [slot(choice('start'))], ['locked'])
                if defect == 'zero_amount':
                    zero['outputs'][0]['amount'] = 0
                else:
                    zero['outputs'][0]['chance'] = {'numerator': 0, 'denominator': 10000}
                rows = [process('finish', [slot(choice('start')), slot(choice('locked'))], ['target']),
                        process('to-loop', [slot(choice('locked'))], ['loop']),
                        process('to-locked', [slot(choice('loop'))], ['locked']), zero]
                artifact = snapshot(root / 'capture', resources=[resource(id) for id in ('start', 'locked', 'loop', 'target')], processes=rows)
                dataset = Dataset.import_snapshot(artifact, root / 'index.sqlite')
                result = dataset.trace_processes(start_id='start', target_id='target')
                self.assertEqual(result['route']['status'], 'found')
                leaves = {leaf['resource_id']: leaf for leaf in result['leaves']}
                for id in ('locked', 'loop'):
                    self.assertEqual(leaves[id]['status'], 'unresolved')
                    self.assertIn('cycle needs', leaves[id]['reason'])
                captured = next(row for row in result['processes'] if row['id'] == 'zero-yield')
                self.assertEqual(captured['outputs'], zero['outputs'])

    def test_unknown_matching_and_zero_outputs_cannot_form_route_edges(self):
        for defect in ('native_unknown', 'ungrouped_unified', 'zero_amount', 'zero_chance', 'disabled'):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                ingredient = choice('middle', 'native_unknown' if defect == 'native_unknown'
                                    else 'unified' if defect == 'ungrouped_unified' else 'exact')
                finish = process('finish', [slot(ingredient)], ['target'], executable=defect != 'disabled')
                if defect == 'zero_amount':
                    finish['outputs'][0]['amount'] = 0
                if defect == 'zero_chance':
                    finish['outputs'][0]['chance'] = {'numerator': 0, 'denominator': 10000}
                rows = [process('first', [slot(choice('start'))], ['middle']), finish]
                artifact = snapshot(root / 'capture', resources=[resource(id) for id in ('start', 'middle', 'target')], processes=rows)
                dataset = Dataset.import_snapshot(artifact, root / 'index.sqlite')
                result = dataset.trace_processes(start_id='start', target_id='target')
                self.assertEqual(result['route']['status'], 'not_found')
                self.assertEqual(result['processes'], [])


if __name__ == '__main__':
    unittest.main()
