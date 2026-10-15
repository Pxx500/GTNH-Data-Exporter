import tempfile
import time
import unittest
from pathlib import Path

from gtnh_data import Dataset, DatasetError
from .artifacts import choice, process, resource, slot, snapshot


def detour_fixture(root, *, alternative=False):
    rows = [resource(id) for id in ('iron', 'tin', 'alloy', 'circuit')]
    tin = choice('tin')
    groups = []
    if alternative:
        rows.append(resource('tin-tagged', registry_name='test:tin', nbt={'type': 'int', 'value': 1}))
        tin = choice('tin', 'unified', group='unified:tin')
        groups.append({'id': 'unified:tin', 'kind': 'unified', 'name': 'tin',
                       'members': ['tin', 'tin-tagged'], 'provenance': {}})
    recipes = [process('mix', [slot(choice('iron')), slot(tin), slot(choice('circuit'), role='presence')], ['alloy']),
               process('separate', [slot(choice('alloy', amount=2))], ['tin', 'iron'])]
    recipes[0]['outputs'][0]['amount'] = 2
    dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=rows, processes=recipes, groups=groups), root / 'index.sqlite')
    return dataset, recipes


class DetourTests(unittest.TestCase):
    def test_trace_explains_exact_resource_return_and_startup_without_changing_recipe(self):
        with tempfile.TemporaryDirectory() as temporary:
            dataset, recipes = detour_fixture(Path(temporary))
            result = dataset.trace_processes(start_id='iron', target_id='tin', path_selection='material', view='compact')
            self.assertIn('material_detour_analysis', result)
            evidence = result['path_details'][0]['material_detours'][0]
            self.assertEqual(evidence['status'], 'zero_net')
            self.assertEqual((evidence['start_step'], evidence['end_step']), (0, 1))
            self.assertEqual(evidence['process_ids'], ['mix', 'separate'])
            self.assertEqual(evidence['resource_ids'], ['iron', 'alloy', 'tin'])
            self.assertEqual(evidence['scope'], 'all_concrete_choices')
            witness = evidence['witness']
            one = {'numerator': 1, 'denominator': 1}
            self.assertEqual(witness['net'], {})
            self.assertEqual(witness['required_start_stock'], {'iron': one, 'tin': one, 'circuit': one})
            self.assertEqual(witness['presence'], {'circuit': one})
            self.assertEqual({p['id']: p for p in result['processes']}, {p['id']: p for p in recipes})
            self.assertEqual(result['paths'][0], {'resource_ids': ['iron', 'alloy', 'tin'],
                                               'process_ids': ['mix', 'separate']})

    def test_explicit_choice_cannot_account_a_path_that_no_longer_consumes_its_predecessor(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rows = [resource(id) for id in ('iron', 'tin', 'alloy')]
            recipes = [process('mix', [slot(choice('iron'), choice('tin')), slot(choice('tin'))], ['alloy']),
                       process('separate', [slot(choice('alloy'))], ['iron', 'tin'])]
            dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=rows, processes=recipes), root / 'index.sqlite')
            with self.assertRaisesRegex(DatasetError, 'does not consume'):
                dataset.plan_recycling(main_path={'resource_ids': ['iron', 'alloy'], 'process_ids': ['mix']},
                    byproduct_id='tin', return_id='iron',
                    selections={'mix': {'0': {'choice_index': 1, 'resource_id': 'tin'}}})

    def test_unresolved_predecessor_or_choice_remains_unsupported_in_recycling(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rows = [resource(id) for id in ('iron', 'tin', 'alloy')]
            recipes = [process('mix', [slot(choice('iron'), choice('iron', amount=2)), slot(choice('tin'))], ['alloy']),
                       process('separate', [slot(choice('alloy'))], ['iron', 'tin'])]
            dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=rows, processes=recipes), root / 'index.sqlite')
            try:
                result = dataset.plan_recycling(main_path={'resource_ids': ['iron', 'alloy'], 'process_ids': ['mix']},
                    byproduct_id='tin', return_id='iron')
            except DatasetError as error:
                self.fail(f'An unresolved predecessor choice must remain unsupported: {error}')
            self.assertEqual(result['status'], 'unsupported')
            self.assertEqual(result['main_plan']['status'], 'unsupported')
            self.assertEqual(result['main_plan']['executions'], [])
            self.assertIsNone(result['main_plan']['ledger'])
            self.assertIn('Input slot 0 needs an explicit concrete OR/group selection',
                          [issue['reason'] for issue in result['main_plan']['unsupported']])

    def test_all_native_variants_are_checked_without_promoting_one_zero_case(self):
        with tempfile.TemporaryDirectory() as temporary:
            dataset, _ = detour_fixture(Path(temporary), alternative=True)
            result = dataset.trace_processes(start_id='iron', target_id='tin', path_selection='material')
            window = result['path_details'][0]['material_detours'][0]
            self.assertEqual(window['status'], 'conditional_zero_net')
            self.assertEqual(window['scope'], 'concrete_selection_witness_only')
            self.assertEqual(window['cases_checked'], 2)
            self.assertEqual(window['zero_net_cases'], 1)
            self.assertEqual(window['witness']['selections']['mix']['1']['resource_id'], 'tin')
            self.assertEqual(result['material_detour_analysis']['counts']['zero_net'], 0)
            self.assertEqual(next(r for r in result['resources'] if r['id'] == 'tin-tagged')['nbt'], {'type': 'int', 'value': 1})

    def test_productive_catalyst_regeneration_and_coproducts_are_not_zero_net(self):
        for control in ('catalyst', 'coproduct', 'different_nbt'):
            with self.subTest(control=control), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                rows = [resource(id) for id in ('iron', 'tin', 'alloy', 'extra')]
                recipes = [process('mix', [slot(choice('iron')), slot(choice('tin'))], ['alloy']),
                           process('separate', [slot(choice('alloy', amount=2))], ['tin', 'iron'])]
                recipes[0]['outputs'][0]['amount'] = 2
                if control == 'catalyst':
                    recipes[1]['outputs'][0]['resource_id'] = 'extra'
                    target = 'extra'
                elif control == 'coproduct':
                    recipes[1]['outputs'].append({'resource_id': 'extra', 'amount': 1, 'chance': {'numerator': 1, 'denominator': 1}})
                    target = 'tin'
                else:
                    rows[0].update(registry_name='test:shared', nbt={'type': 'int', 'value': 1})
                    rows[3].update(registry_name='test:shared', nbt={'type': 'int', 'value': 2})
                    recipes[1]['outputs'][1]['resource_id'] = 'extra'
                    target = 'tin'
                dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=rows, processes=recipes), root / 'index.sqlite')
                result = dataset.trace_processes(start_id='iron', target_id=target, path_selection='material')
                self.assertTrue(result['paths'])
                self.assertEqual(result['path_details'][0]['material_detours'], [])
                self.assertEqual(result['material_detour_analysis']['counts']['nonzero'], 1)

    def test_unknown_chance_or_effect_prevents_any_positive_window(self):
        for control in ('chance_none', 'chance_random', 'unknown_or', 'empty_group', 'keeping_nbt', 'extension'):
            with self.subTest(control=control), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                rows = [resource(id) for id in ('iron', 'tin', 'alloy')]
                recipes = [process('mix', [slot(choice('iron')), slot(choice('tin'))], ['alloy']),
                           process('separate', [slot(choice('alloy', amount=2))], ['tin', 'iron'])]
                recipes[0]['outputs'][0]['amount'] = 2
                groups = []
                if control.startswith('chance'):
                    recipes[1]['outputs'][0]['chance'] = None if control == 'chance_none' else {'numerator': 1, 'denominator': 2}
                elif control == 'unknown_or':
                    recipes[0]['inputs'][1]['choices'].append(choice(None, 'native_unknown'))
                elif control == 'empty_group':
                    recipes[0]['inputs'][1]['choices'].append(choice(None, 'ore_dict', group='empty'))
                    groups.append({'id': 'empty', 'kind': 'ore_dict', 'name': 'empty', 'members': [], 'provenance': {}})
                elif control == 'keeping_nbt':
                    recipes[1]['conditions']['keeping_nbt'] = True
                else:
                    recipes[1]['conditions']['unknown_material_effect'] = 'unresolved'
                dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=rows, processes=recipes, groups=groups), root / 'index.sqlite')
                result = dataset.trace_processes(start_id='iron', target_id='tin', path_selection='material')
                self.assertTrue(result['paths'])
                self.assertEqual(result['path_details'][0]['material_detours'], [])
                self.assertEqual(result['material_detour_analysis']['counts']['unknown'], 1)
                self.assertEqual(result['material_detour_analysis']['status'], 'partial')
                self.assertEqual(next(p for p in result['processes'] if p['id'] == 'separate'), recipes[1])

    def test_consensus_case_bound_is_checked_before_reading_native_member_rows(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rows = [resource(id) for id in ('iron', 'tin', 'alloy')]
            rows += [resource(f'alternate-{i}') for i in range(20)]
            recipes = [process('mix', [slot(choice('iron')), slot(choice('tin', 'ore_dict', group='g'))], ['alloy']),
                       process('separate', [slot(choice('alloy', amount=2))], ['tin', 'iron'])]
            recipes[0]['outputs'][0]['amount'] = 2
            group = {'id': 'g', 'kind': 'ore_dict', 'name': 'dustTin', 'members': ['tin'] + [f'alternate-{i}' for i in range(20)], 'provenance': {}}
            dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=rows, processes=recipes, groups=[group]), root / 'index.sqlite')
            result = dataset.trace_processes(start_id='iron', target_id='tin', path_selection='material')
            self.assertEqual(result['path_details'][0]['material_detours'], [])
            analysis = result['material_detour_analysis']
            self.assertEqual(analysis['status'], 'partial')
            self.assertEqual(analysis['work']['matching_rows'], 0)
            self.assertEqual(analysis['work']['cases'], 0)

    def test_three_step_window_uses_integer_batches_and_keeps_presence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rows = [resource(id) for id in ('iron', 'tin', 'alloy', 'formed', 'circuit')]
            recipes = [process('mix', [slot(choice('iron', amount=2)), slot(choice('tin', amount=2)),
                                      slot(choice('circuit'), role='presence')], ['alloy']),
                       process('form', [slot(choice('alloy'))], ['formed']),
                       process('separate', [slot(choice('formed', amount=6))], ['tin', 'iron'])]
            recipes[0]['outputs'][0]['amount'] = 3
            recipes[2]['outputs'][0]['amount'] = recipes[2]['outputs'][1]['amount'] = 4
            dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=rows, processes=recipes), root / 'index.sqlite')
            result = dataset.trace_processes(start_id='iron', target_id='tin', path_selection='material')
            evidence = result['path_details'][0]['material_detours'][0]
            self.assertEqual((evidence['start_step'], evidence['end_step']), (0, 2))
            self.assertEqual([s['runs'] for s in evidence['witness']['executions']],
                             [{'numerator': n, 'denominator': 1} for n in (2, 6, 1)])
            self.assertEqual(evidence['witness']['required_start_stock']['tin'], {'numerator': 4, 'denominator': 1})
            self.assertEqual(evidence['witness']['presence']['circuit'], {'numerator': 1, 'denominator': 1})

    def test_progressive_and_synchronous_views_share_detour_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            dataset, _ = detour_fixture(Path(temporary), alternative=True)
            self.addCleanup(dataset.shutdown_trace_searches)
            args = dict(start_id='iron', target_id='tin', path_selection='material', view='concise')
            synchronous = dataset.trace_processes(**args)
            job = dataset.start_trace_search(**args)
            deadline = time.monotonic() + 5
            while job['status'] == 'running' and time.monotonic() < deadline:
                time.sleep(.01)
                job = dataset.get_trace_search(job['job_id'])
            self.assertEqual(job['status'], 'finished', job)
            for field in ('paths', 'processes', 'path_details', 'material_detour_analysis'):
                self.assertEqual(job['result'][field], synchronous[field], field)

    def test_unsupported_later_choice_discards_an_earlier_zero_witness(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rows = [resource(id) for id in ('iron', 'tin', 'alloy')]
            recipes = [process('mix', [slot(choice('iron')), slot(choice('tin'), choice('tin', amount=.5))], ['alloy']),
                       process('separate', [slot(choice('alloy', amount=2))], ['tin', 'iron'])]
            recipes[0]['outputs'][0]['amount'] = 2
            dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=rows, processes=recipes), root / 'index.sqlite')
            result = dataset.trace_processes(start_id='iron', target_id='tin', path_selection='material')
            self.assertEqual(result['path_details'][0]['material_detours'], [])
            self.assertEqual(result['material_detour_analysis']['counts']['unknown'], 1)
            self.assertEqual(result['material_detour_analysis']['work']['cases'], 2)

    def test_whole_trace_window_bound_is_shared_across_retained_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rows = [resource('start'), resource('target')]
            recipes = []
            for branch in ('a', 'b'):
                ids = ['start'] + [f'{branch}-{i}' for i in range(39)] + ['target']
                rows += [resource(id) for id in ids[1:-1]]
                recipes += [process(f'{branch}-process-{i}', [slot(choice(left))], [right])
                            for i, (left, right) in enumerate(zip(ids, ids[1:]))]
            dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=rows, processes=recipes), root / 'index.sqlite')
            result = dataset.trace_processes(start_id='start', target_id='target', path_selection='material', max_depth=64)
            self.assertEqual(len(result['paths']), 2)
            analysis = result['material_detour_analysis']
            self.assertEqual(analysis['status'], 'partial')
            self.assertEqual(analysis['work']['windows'], 128)
            self.assertEqual(analysis['counts']['unknown'], 26)
            for key in ('windows', 'cases', 'matching_rows'):
                self.assertLessEqual(analysis['work'][key], analysis['limits'][key])

    def test_compact_view_embeds_the_concrete_presence_witness_variant(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rows = [resource(id) for id in ('iron', 'tin', 'alloy', 'circuit', 'alternative-circuit')]
            rows[-1]['display_name'] = 'Alternative circuit'
            recipes = [process('mix', [slot(choice('iron')), slot(choice('tin')),
                       slot(choice('circuit', 'ore_dict', group='circuits'), role='presence')], ['alloy']),
                       process('separate', [slot(choice('alloy', amount=2))], ['tin', 'iron'])]
            recipes[0]['outputs'][0]['amount'] = 2
            group = {'id': 'circuits', 'kind': 'ore_dict', 'name': 'circuits',
                     'members': ['circuit', 'alternative-circuit'], 'provenance': {}}
            dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=rows, processes=recipes, groups=[group]), root / 'index.sqlite')
            result = dataset.trace_processes(start_id='iron', target_id='tin', path_selection='material', view='compact')
            evidence = result['path_details'][0]['material_detours'][0]
            self.assertIn('alternative-circuit', evidence['witness']['presence'])
            returned = {r['id']: r for r in result['resources']}
            self.assertIn('alternative-circuit', returned)
            self.assertEqual(returned['alternative-circuit']['display_name'], 'Alternative circuit')
            self.assertEqual(result['presentation']['omitted_counts']['resources'], 0)
            self.assertFalse(any(r['process_id'] == 'mix' and r['slot_index'] == 2
                                 for r in result['presentation']['grouped_match_refs']))
