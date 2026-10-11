import tempfile
import unittest
from pathlib import Path

from gtnh_data import Dataset, DatasetError
from .artifacts import choice, process, resource, slot, snapshot


class RouteTests(unittest.TestCase):
    def test_multiple_complete_paths_filter_materials_and_reserve_whole_path_budget(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ids = ('start', 'a', 'b', 'target', 'side', 'tool', 'byproduct', 'detour')
            rows = [process('a-first', [slot(choice('start')), slot(choice('side')), slot(choice('tool'), role='presence')], ['a', 'byproduct']),
                    process('a-finish', [slot(choice('a'))], ['target']),
                    process('b-first', [slot(choice('start'))], ['b']),
                    process('b-finish', [slot(choice('b'))], ['target']),
                    process('side-maker', [slot(choice('byproduct'))], ['side']),
                    process('recycle', [slot(choice('a'))], ['start']),
                    process('tool-only', [slot(choice('start'), role='presence')], ['target']),
                    process('detour-first', [slot(choice('a'))], ['detour']),
                    process('detour-finish', [slot(choice('detour'))], ['target'])]
            dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=[resource(id) for id in ids], processes=rows), root / 'index.sqlite')
            result = dataset.trace_processes(start_id='start', target_id='target', max_processes=4)
            self.assertEqual({row['id'] for row in result['processes']}, {'a-first', 'a-finish', 'b-first', 'b-finish'})
            self.assertEqual(result['paths'], [
                {'resource_ids': ['start', 'a', 'target'], 'process_ids': ['a-first', 'a-finish']},
                {'resource_ids': ['start', 'b', 'target'], 'process_ids': ['b-first', 'b-finish']}])
            self.assertEqual(result['route']['resource_ids'], result['paths'][0]['resource_ids'])
            self.assertIn('path_process_limit', result['limit_reasons'])
            self.assertIn('side', {leaf['resource_id'] for leaf in result['leaves']})
            self.assertIn('tool', {leaf['resource_id'] for leaf in result['leaves']})
            filtered = dataset.trace_processes(start_id='start', target_id='target', required_resource_ids=['b'], excluded_resource_ids=['a'])
            self.assertEqual(filtered['paths'], [result['paths'][1]])
            self.assertEqual({row['id'] for row in filtered['processes']}, {'b-first', 'b-finish'})
            shortest = dataset.trace_processes(start_id='start', target_id='target', max_extra_steps=0)
            self.assertEqual(shortest['paths'], result['paths'])
            required_detour = dataset.trace_processes(start_id='start', target_id='target', required_resource_ids=['detour'], max_extra_steps=0)
            self.assertEqual(required_detour['paths'], [{'resource_ids': ['start', 'a', 'detour', 'target'], 'process_ids': ['a-first', 'detour-first', 'detour-finish']}])
            exclude_side_inputs = dataset.trace_processes(start_id='start', target_id='target', excluded_resource_ids=['side', 'tool'], max_extra_steps=0)
            self.assertEqual(exclude_side_inputs['paths'], result['paths'])
            require_tool = dataset.trace_processes(start_id='start', target_id='target', required_resource_ids=['tool'])
            self.assertEqual(require_tool['paths'], [])
            bounded = dataset.trace_processes(start_id='start', target_id='target', max_paths=1)
            self.assertEqual(bounded['paths'], result['paths'][:1])
            self.assertIn('path_limit', bounded['limit_reasons'])
            broken = dataset.trace_processes(start_id='start', target_id='target', max_processes=1)
            self.assertEqual(broken['paths'], [])
            self.assertEqual(broken['processes'], [])
            self.assertEqual(broken['route']['status'], 'incomplete')
            for arguments in ({'max_paths': True}, {'max_extra_steps': -1}, {'required_resource_ids': 'a'}, {'excluded_resource_ids': [3]}, {'required_resource_ids': ['missing']}):
                with self.subTest(arguments=arguments), self.assertRaises(DatasetError):
                    dataset.trace_processes(start_id='start', target_id='target', **arguments)

    def test_captured_duplicates_do_not_hide_different_process_semantics(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            base = process('a-original', [slot(choice('start'))], ['target'])
            base['provenance']['index'] = 1
            duplicate = dict(base, id='b-duplicate', provenance={'owner': 'fixture', 'index': 2})
            different = dict(base, id='c-different-energy', eu_per_tick=9)
            different_class = dict(base, id='d-different-class', provenance={'owner': 'fixture', 'index': 3, 'recipe_class': 'special'})
            dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=[resource('start'), resource('target')],
                                                        processes=[base, duplicate, different, different_class]), root / 'index.sqlite')
            result = dataset.trace_processes(start_id='start', target_id='target')
            self.assertEqual([path['process_ids'] for path in result['paths']], [['a-original'], ['c-different-energy'], ['d-different-class']])
            self.assertEqual(result['duplicate_process_records'], [{'representative_id': 'a-original', 'duplicate_ids': ['b-duplicate']}])
            self.assertEqual(dataset.get_process('b-duplicate')['item'], duplicate)
            self.assertEqual(dataset.find_processes(output_id='target')['total'], 4)

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
            for options, reason in (({'max_depth': 1}, 'depth'), ({'max_processes': 1}, 'path_process_limit')):
                with self.subTest(options=options):
                    result = dataset.trace_processes(start_id='start', target_id='target', **options)
                    self.assertEqual(result['route']['status'], 'incomplete')
                    self.assertIn(reason, result['limit_reasons'])
                    self.assertTrue(result['truncated'])
                    self.assertEqual(result['route']['process_ids'], [])
                    self.assertEqual(result['processes'], [])

    def test_zero_yield_coproduct_cannot_seed_a_required_input(self):
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
                rows[0]['outputs'].append(zero['outputs'][0])
                artifact = snapshot(root / 'capture', resources=[resource(id) for id in ('start', 'locked', 'loop', 'target')], processes=rows)
                dataset = Dataset.import_snapshot(artifact, root / 'index.sqlite')
                result = dataset.trace_processes(start_id='start', target_id='target')
                self.assertEqual(result['route']['status'], 'found')
                leaves = {leaf['resource_id']: leaf for leaf in result['leaves']}
                self.assertEqual(leaves['locked']['status'], 'unresolved')
                self.assertIn('cycle needs', leaves['locked']['reason'])
                self.assertEqual({p['id'] for p in result['processes']}, {'finish'})
                self.assertEqual(result['processes'][0]['outputs'][1], zero['outputs'][0])

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
