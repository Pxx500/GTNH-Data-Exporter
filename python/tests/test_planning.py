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

    def test_custom_proxy_and_explicit_unresolved_voltage_stay_unknown(self):
        records = []
        for id in ('proxy', 'normal', 'unresolved'):
            p = process(id, [slot(choice('feed'))], ['target'], family='gregtech:gt.recipe.eyeofharmony')
            p['provenance']['owner'] = 'GTRecipe'
            p['eu_per_tick'] = 0
            if id == 'proxy':
                p['conditions']['special_items'] = {'type': 'tectech.recipe.EyeOfHarmonyRecipe'}
            if id == 'unresolved':
                p['conditions']['recipe_voltage_tier_status'] = 'unresolved'
            records.append(p)
        dataset = self.dataset(records, ['feed', 'target'])
        trace = dataset.trace_processes(start_id='feed', target_id='target', max_tier=1,
                                        unknown_tier_policy='include')
        tiers = {t['process_id']: t for t in trace['recipe_tiers']}
        self.assertEqual(tiers['proxy']['status'], 'unknown')
        self.assertIsNone(tiers['proxy']['tier'])
        self.assertIn('Eye of Harmony', tiers['proxy']['reason'])
        self.assertEqual(tiers['unresolved']['status'], 'unknown')
        self.assertEqual(tiers['normal']['status'], 'known')
        self.assertEqual(tiers['normal']['name'], 'ULV')
        filtered = dataset.trace_processes(start_id='feed', target_id='target', max_tier=1)
        self.assertEqual({p['id'] for p in filtered['processes']}, {'normal'})
        discovery = dataset.discover_network('target', allowed_feed_ids=['feed'], max_tier=1)
        self.assertEqual({v['process_id'] for v in discovery['variants']}, {'normal'})

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

    def test_diverse_trace_reserves_shortest_and_covers_longer_and_branch(self):
        variants = [f'x{i}' for i in range(8)]
        records = [process(f'variant{i}', [slot(choice('a'))], [id]) for i, id in enumerate(variants)]
        records += [process('long1', [slot(choice('a'))], ['z1']), process('long2', [slot(choice('z1'))], ['z2']),
                    process('long3', [slot(choice('z2'))], ['z3']),
                    process('finish', [slot(*(choice(id) for id in variants)), slot(choice('z3'))], ['b'])]
        dataset = self.dataset(records, ['a', 'b', 'z1', 'z2', 'z3', *variants])
        diverse = dataset.trace_processes(start_id='a', target_id='b', max_paths=3)
        self.assertEqual(len(diverse['paths'][0]['process_ids']), 2)
        self.assertTrue(any('z3' in path['resource_ids'] for path in diverse['paths']))
        self.assertEqual(diverse['path_selection'], 'diverse')
        self.assertEqual({branch['slot_index'] for branch in diverse['branch_coverage'] if branch['status'] == 'represented'}, {0, 1})
        shortest = dataset.trace_processes(start_id='a', target_id='b', max_paths=3, path_selection='shortest')
        self.assertTrue(all(len(path['process_ids']) == 2 for path in shortest['paths']))
        filtered = dataset.trace_processes(start_id='a', target_id='b', max_paths=3, required_resource_ids=['z2'])
        self.assertTrue(filtered['paths'])
        self.assertTrue(all('z2' in path['resource_ids'] for path in filtered['paths']))
        excluded = dataset.trace_processes(start_id='a', target_id='b', max_paths=3, excluded_resource_ids=['z2'])
        self.assertTrue(all('z2' not in path['resource_ids'] for path in excluded['paths']))

    def test_diverse_single_slot_prefers_new_material_spine_before_recipe_variants(self):
        variants = [process(f'variant{i}', [slot(choice('a'))], ['x']) for i in range(8)]
        for index, record in enumerate(variants):
            record['duration_ticks'] += index
        records = variants + [process('long1', [slot(choice('a'))], ['z1']),
            process('long2', [slot(choice('z1'))], ['z2']), process('long3', [slot(choice('z2'))], ['x']),
            process('finish', [slot(choice('x'))], ['b'])]
        dataset = self.dataset(records, ['a', 'b', 'x', 'z1', 'z2'])
        diverse = dataset.trace_processes(start_id='a', target_id='b', max_paths=3)
        self.assertTrue(any('z2' in path['resource_ids'] for path in diverse['paths']))
        self.assertEqual(len(diverse['paths']), 3)
        shortest = dataset.trace_processes(start_id='a', target_id='b', max_paths=3, path_selection='shortest')
        self.assertTrue(all(len(path['process_ids']) == 2 for path in shortest['paths']))

    def test_prefix_recovers_primary_after_reverse_limit_without_extra_step_violation(self):
        records = [process('finish', [slot(choice('m'))], ['t']),
                   process('a_long3', [slot(choice('y'))], ['m']),
                   process('long1', [slot(choice('s'))], ['x']),
                   process('long2', [slot(choice('x'))], ['y']),
                   process('zz_direct', [slot(choice('s'))], ['m'])]
        for index in range(10001):
            record = process(f'noise{index:05}', [slot(choice('unreachable'))], ['m'])
            record['duration_ticks'] = index + 1
            records.append(record)
        dataset = self.dataset(records, ['s', 't', 'm', 'x', 'y', 'unreachable'])
        trace = dataset.trace_processes(start_id='s', target_id='t', max_extra_steps=0, max_processes=2)
        self.assertEqual(trace['route']['status'], 'found')
        self.assertEqual([len(p['process_ids']) for p in trace['paths']], [2])
        self.assertEqual({p['id'] for p in trace['processes']}, {'zz_direct', 'finish'})
        self.assertIn('search_process_limit', trace['limit_reasons'])
        self.assertLessEqual(trace['search']['queued_states'], trace['search']['state_limit'])

    def test_new_shorter_primary_takes_process_budget_before_old_bounded_primary(self):
        records = [process('end', [slot(choice('e'))], ['t']),
                   process('long_su', [slot(choice('s'))], ['u']),
                   process('long_uv', [slot(choice('u'))], ['v']),
                   process('long_vw', [slot(choice('v'))], ['w']),
                   process('long_we', [slot(choice('w'))], ['e']),
                   process('short_sx', [slot(choice('s'))], ['x']),
                   process('short_xe', [slot(choice('x'))], ['e'])]
        records += [process(f'shortcut_{id}', [slot(choice(id))], ['t']) for id in ['u', 'v', 'w']]
        for index in range(10001):
            record = process(f'noise{index:05}', [slot(choice('q'))], ['x'])
            record['duration_ticks'] = index + 1
            records.append(record)
        dataset = self.dataset(records, ['s', 't', 'u', 'v', 'w', 'e', 'x', 'q'])
        trace = dataset.trace_processes(start_id='s', target_id='t', max_extra_steps=6,
            max_processes=6, required_resource_ids=['e'])
        self.assertEqual(len(trace['route']['process_ids']), 3)
        self.assertIn('x', trace['route']['resource_ids'])
        self.assertEqual({p['id'] for p in trace['processes']}, {'short_sx', 'short_xe', 'end'})
        self.assertIn('path_process_limit', trace['limit_reasons'])
