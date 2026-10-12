import tempfile
import unittest
from pathlib import Path

from gtnh_data import Dataset, DatasetError
from .artifacts import choice, process, resource, slot, snapshot


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def dataset(self, records, ids):
        return Dataset.import_snapshot(snapshot(self.root / 'snapshot',
            resources=[resource(id) for id in ids], processes=records), self.root / 'index.sqlite')

    def test_recipe_voltage_bounds_are_exact_and_unknown_policy_is_explicit(self):
        records = []
        for id, voltage in [('zero', 0), ('ulv', 8), ('lv_min', 9), ('lv_max', 32), ('mv', 33), ('generator', None)]:
            p = process(id, [slot(choice('a'))], ['b'], family='gregtech:gt.recipe.fixture')
            p['eu_per_tick'] = voltage
            p['provenance']['owner'] = 'GTRecipe'
            records.append(p)
        records.append(process('rf', [slot(choice('a'))], ['b'], family='enderio:sag_mill'))
        assembly = process('assembly', [slot(choice('a'))], ['b'], family='gregtech:assembly_line')
        assembly['eu_per_tick'] = 32
        assembly['provenance']['owner'] = 'RecipeAssemblyLine.sAssemblylineRecipes'
        records.append(assembly)
        dataset = self.dataset(records, ['a', 'b'])
        trace = dataset.trace_processes(start_id='a', target_id='b', min_tier=1, max_tier=1)
        self.assertEqual({p['id'] for p in trace['processes']}, {'lv_min', 'lv_max', 'assembly'})
        self.assertEqual(trace['tier_filter']['excluded_unknown'], 2)
        self.assertEqual(trace['tier_filter']['excluded_out_of_range'], 3)
        self.assertTrue(all(t['tier'] == 1 for t in trace['recipe_tiers']))
        included = dataset.trace_processes(start_id='a', target_id='b', min_tier=1, max_tier=1,
            unknown_tier_policy='include')
        self.assertEqual({p['id'] for p in included['processes']}, {'lv_min', 'lv_max', 'assembly', 'rf', 'generator'})
        self.assertEqual({t['process_id'] for t in included['recipe_tiers'] if t['status'] == 'unknown'}, {'rf', 'generator'})
        self.assertEqual(len(dataset.trace_processes(start_id='a', target_id='b')['paths']), 8)
        for args in ({'min_tier': True}, {'max_tier': 16}, {'min_tier': 3, 'max_tier': 2}, {'unknown_tier_policy': 'guess'}):
            with self.assertRaises(DatasetError):
                dataset.trace_processes(start_id='a', target_id='b', **args)

    def test_recycling_preserves_extra_and_inputs_startup_and_net_return(self):
        main = process('main', [slot(choice('a')), slot(choice('d', amount=4))], ['b', 'c'])
        main['outputs'][1]['amount'] = 2
        recovery = process('recovery', [slot(choice('c', amount=2)), slot(choice('x', amount=3)),
            slot(choice('tool'), role='presence')], ['d'])
        false_loop = process('false_loop', [slot(choice('c', amount=2)), slot(choice('d'))], ['d'])
        dataset = self.dataset([main, recovery, false_loop], ['a', 'b', 'c', 'd', 'x', 'tool'])
        result = dataset.plan_recycling(main_path={'resource_ids': ['a', 'b'], 'process_ids': ['main']},
            byproduct_id='c', return_id='d')
        alternatives = {p['path']['process_ids'][0]: p for p in result['alternatives']}
        good = alternatives['recovery']
        self.assertEqual(good['recovery']['net_returned'], {'numerator': 1, 'denominator': 1})
        self.assertEqual(good['recovery']['main_input_returned_percent'], {'numerator': 25, 'denominator': 1})
        self.assertEqual(good['external_inputs'], [{'resource_id': 'x', 'amount': {'numerator': 3, 'denominator': 1}}])
        self.assertEqual(good['ledger']['presence']['tool'], {'numerator': 1, 'denominator': 1})
        self.assertEqual(good['combined_startup']['required_start_stock']['d'], {'numerator': 4, 'denominator': 1})
        bad = alternatives['false_loop']
        self.assertEqual(bad['recovery']['net_returned'], {'numerator': 0, 'denominator': 1})
        self.assertEqual(bad['recovery']['side_consumed'], {'numerator': 1, 'denominator': 1})
        self.assertEqual(bad['combined_startup']['required_start_stock']['d'], {'numerator': 5, 'denominator': 1})

    def test_chance_recovery_is_not_guaranteed_and_bounds_are_reported(self):
        main = process('main', [slot(choice('a')), slot(choice('d', amount=4))], ['b', 'c'])
        side = process('side', [slot(choice('c'))], ['d'])
        side['outputs'][0]['chance'] = {'numerator': 1, 'denominator': 2}
        dataset = self.dataset([main, side], ['a', 'b', 'c', 'd'])
        args = {'main_path': {'resource_ids': ['a', 'b'], 'process_ids': ['main']}, 'byproduct_id': 'c', 'return_id': 'd', 'max_paths': 1}
        guaranteed = dataset.plan_recycling(**args)
        self.assertEqual(guaranteed['alternatives'][0]['status'], 'unsupported')
        self.assertTrue(guaranteed['secondary_trace']['truncated'])
        self.assertIn('path_limit', guaranteed['secondary_trace']['limit_reasons'])
        expected = dataset.plan_recycling(**args, yield_mode='expected')
        self.assertEqual(expected['alternatives'][0]['recovery']['net_returned'], {'numerator': 1, 'denominator': 2})
        self.assertEqual(expected['alternatives'][0]['recovery']['main_input_returned_percent'], {'numerator': 25, 'denominator': 2})
        self.assertIsNone(expected['alternatives'][0]['combined_startup']['feasible'])

    def test_recycling_needs_a_concrete_offpath_or_choice(self):
        main = process('main', [slot(choice('a')), slot(choice('d'))], ['b', 'c'])
        side = process('side', [slot(choice('c')), slot(choice('x'), choice('y'))], ['d'])
        dataset = self.dataset([main, side], ['a', 'b', 'c', 'd', 'x', 'y'])
        args = {'main_path': {'resource_ids': ['a', 'b'], 'process_ids': ['main']}, 'byproduct_id': 'c', 'return_id': 'd'}
        unresolved = dataset.plan_recycling(**args)
        self.assertEqual(unresolved['alternatives'][0]['status'], 'unsupported')
        chosen = dataset.plan_recycling(**args, selections={'side': {'1': {'choice_index': 1, 'resource_id': 'y'}}})
        self.assertEqual(chosen['alternatives'][0]['external_inputs'], [{'resource_id': 'y', 'amount': {'numerator': 1, 'denominator': 1}}])

    def test_loop_owner_bounds_tiers_and_keeps_external_debit(self):
        first = process('first', [slot(choice('a'))], ['b'], family='gregtech:gt.recipe.fixture')
        last = process('last', [slot(choice('b')), slot(choice('external'))], ['a'], family='gregtech:gt.recipe.fixture')
        last['outputs'][0]['amount'] = 2
        for p in [first, last]:
            p['provenance']['owner'] = 'GTRecipe'
            p['eu_per_tick'] = 32
        dataset = self.dataset([first, last], ['a', 'b', 'external'])
        result = dataset.find_loops(start_id='a', min_tier=1, max_tier=1)
        self.assertEqual(len(result['witnesses']), 1)
        loop = result['witnesses'][0]
        self.assertEqual(loop['classification'], 'gaining')
        self.assertFalse(loop['autonomous'])
        self.assertEqual(loop['external_consumption']['external'], {'numerator': 1, 'denominator': 1})
        self.assertEqual(loop['required_start_stock']['a'], {'numerator': 1, 'denominator': 1})
        self.assertEqual(dataset.find_loops(start_id='a', max_tier=0)['witnesses'], [])
        limited = dataset.find_loops(start_id='a', max_processes=1)
        self.assertIn('candidate_process_limit', limited['limit_reasons'])
        self.assertEqual(limited['status'], 'limited')
        inspection = dataset.inspect_chemistry('a')
        self.assertEqual(inspection['resource_id'], 'a')
        self.assertEqual(inspection['status'], 'unsupported')

    def test_later_side_input_cannot_spend_the_same_byproduct_twice(self):
        main = process('main', [slot(choice('a')), slot(choice('d'))], ['b', 'c'])
        main['outputs'][1]['amount'] = 4
        first = process('first', [slot(choice('c'))], ['x'])
        second = process('second', [slot(choice('x')), slot(choice('c'))], ['d'])
        dataset = self.dataset([main, first, second], ['a', 'b', 'c', 'd', 'x'])
        plan = dataset.plan_recycling(main_path={'resource_ids': ['a', 'b'], 'process_ids': ['main']},
            byproduct_id='c', return_id='d')
        alternative = next(a for a in plan['alternatives'] if a['path']['process_ids'] == ['first', 'second'])
        self.assertEqual(alternative['recovery']['net_returned'], {'numerator': 2, 'denominator': 1})
        self.assertEqual(alternative['external_inputs'], [])
        self.assertNotIn('c', alternative['combined_startup']['required_start_stock'])

    def test_recycling_group_variant_uses_the_dataset_nbt_matcher(self):
        for sensitive in (False, True):
            with self.subTest(sensitive=sensitive):
                c = choice('d1', 'ore_dict', group='g')
                c['match']['nbt_sensitive'] = sensitive
                main = process('main', [slot(choice('a')), slot(c)], ['b', 'c'])
                side = process('side', [slot(choice('c'))], ['d2'])
                resources = [resource(id) for id in ['a', 'b', 'c']]
                resources += [resource('d1', registry_name='test:d', nbt={'type': 'compound', 'value': {'mode': {'type': 'int', 'value': 1}}}),
                              resource('d2', registry_name='test:d', nbt={'type': 'compound', 'value': {'mode': {'type': 'int', 'value': 2}}})]
                dataset = Dataset.import_snapshot(snapshot(self.root / str(sensitive), resources=resources, processes=[main, side],
                    groups=[{'id': 'g', 'kind': 'ore_dict', 'name': 'testD', 'members': ['d1'], 'provenance': {}}]),
                    self.root / f'{sensitive}.sqlite')
                args = {'main_path': {'resource_ids': ['a', 'b'], 'process_ids': ['main']}, 'byproduct_id': 'c', 'return_id': 'd2'}
                result = dataset.plan_recycling(**args)
                if sensitive:
                    self.assertEqual(result['status'], 'unsupported')
                    with self.assertRaises(DatasetError):
                        dataset.plan_recycling(**args, selections={'main': {'1': {'choice_index': 0, 'resource_id': 'd2'}}})
                else:
                    self.assertEqual(result['main_plan']['selected_inputs']['main']['1']['resource_id'], 'd2')
                    self.assertEqual(result['alternatives'][0]['recovery']['main_input_returned_percent'], {'numerator': 100, 'denominator': 1})

    def test_recovery_ranking_is_exact_and_only_covers_searched_paths(self):
        main = process('main', [slot(choice('a')), slot(choice('d', amount=4))], ['b', 'c'])
        main['outputs'][1]['amount'] = 2
        unresolved = process('0_unresolved', [slot(choice('c')), slot(choice('x'), choice('y'))], ['d'])
        low = process('a_low', [slot(choice('c'))], ['d'])
        high = process('z_high', [slot(choice('c'))], ['d'])
        high['outputs'][0]['amount'] = 3
        dataset = self.dataset([main, unresolved, low, high], ['a', 'b', 'c', 'd', 'x', 'y'])
        args = {'main_path': {'resource_ids': ['a', 'b'], 'process_ids': ['main']}, 'byproduct_id': 'c', 'return_id': 'd'}
        plan = dataset.plan_recycling(**args)
        self.assertEqual([p['path']['process_ids'][0] for p in plan['alternatives']], ['z_high', 'a_low', '0_unresolved'])
        self.assertEqual(plan['alternatives'][0]['recovery']['main_input_returned_percent'], {'numerator': 150, 'denominator': 1})
        limited = dataset.plan_recycling(**args, max_paths=2)
        self.assertEqual(limited['alternatives'][0]['path']['process_ids'], ['a_low'])
        self.assertIn('path_limit', limited['secondary_trace']['limit_reasons'])
        self.assertFalse(limited['ranking']['global_optimum_proven'])

    def test_returned_byproduct_uses_finite_startup_budget_not_zero_net_debit(self):
        main = process('main', [slot(choice('a')), slot(choice('d'))], ['b', 'c'])
        main['outputs'][1]['amount'] = 4
        first = process('first', [slot(choice('c'))], ['x', 'c'])
        second = process('second', [slot(choice('x'))], ['d'])
        dataset = self.dataset([main, first, second], ['a', 'b', 'c', 'd', 'x'])
        plan = dataset.plan_recycling(main_path={'resource_ids': ['a', 'b'], 'process_ids': ['main']},
            byproduct_id='c', return_id='d')
        alternative = plan['alternatives'][0]
        self.assertEqual(alternative['recovery']['net_returned'], {'numerator': 4, 'denominator': 1})
        self.assertEqual(alternative['startup']['required_start_stock']['c'], {'numerator': 4, 'denominator': 1})
        self.assertEqual(alternative['external_inputs'], [])
        self.assertEqual(len(alternative['executions']), 2)
