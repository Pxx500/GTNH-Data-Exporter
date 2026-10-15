import tempfile
import time
import itertools
import unittest
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from gtnh_data import Dataset
from .artifacts import choice, process, resource, slot, snapshot


class RecipeGroupTests(unittest.TestCase):
    def dataset(self, rows, *, resources=None, groups=()):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        if resources is None:
            ids = {c['resource_id'] for p in rows for s in p['inputs'] for c in s['choices']}
            ids.update(o['resource_id'] for p in rows for o in p['outputs'])
            resources = [resource(id) for id in sorted(ids)]
        dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=resources,
            processes=rows, groups=list(groups)), root / 'index.sqlite')
        self.addCleanup(dataset.shutdown_trace_searches)
        return dataset

    def test_native_shaped_alternatives_and_repeated_singletons_group_with_assembler(self):
        craft = process('craft', [slot(choice('start', amount=1)), slot(choice('start', amount=1)),
            slot(choice('c1', 'exact'), choice('c2', 'exact'))], ['target'], family='minecraft:crafting')
        craft['conditions'] = {'native_class': 'gregtech.api.util.GTShapedRecipe',
            'declared_inputs': 'captured', 'dynamic_output': 'resolved_static',
            'container_returns': 'native_unknown', 'tool_accounting': 'container_damage_and_breakage_unresolved',
            'input_accounting': 'declared_consumption_without_container_return_credit', 'keeping_nbt': False,
            'output_transformations': {'status': 'static', 'configured_enchantments': 'none',
                'electric_charge_transfer': 'not_applicable', 'native_item_update': 'verified_no_op'}}
        assembler = process('assembler', [slot(choice('start', amount=2)),
            slot(choice('c1', 'unified', group='circuits')), slot(choice('tool'), role='presence')], ['target'])
        assembler['outputs'][0]['chance'] = {'numerator': 10000, 'denominator': 10000}
        assembler['inputs'][0]['consumption_chance'] = {'numerator': 10000, 'denominator': 10000}
        groups = [{'id': 'circuits', 'kind': 'unified', 'name': 'circuits', 'members': ['c1', 'c2'], 'provenance': {}}]
        dataset = self.dataset([craft, assembler], groups=groups)
        for view in ('full', 'compact', 'concise'):
            with self.subTest(view=view):
                result = dataset.trace_processes(start_id='start', target_id='target', view=view)
                self.assertIn('recipe_groups', result)
                self.assertEqual(len(result['recipe_groups']), 1)
                group = result['recipe_groups'][0]
                self.assertEqual(group['basis'], 'declared_material_transformation')
                self.assertEqual(group['process_ids'], ['assembler', 'craft'])
                self.assertEqual(group['auxiliary_input_indices'], {'assembler': [2], 'craft': []})
                self.assertEqual(result['path_groups'], [{'id': result['path_groups'][0]['id'],
                    'representative_path_index': 0, 'path_indices': [0, 1]}])
                self.assertEqual({p['id']: p for p in result['processes']}, {'craft': craft, 'assembler': assembler})

    def test_material_changes_unknown_effects_and_stochastic_rolls_do_not_merge(self):
        base = process('base', [slot(choice('start')), slot(choice('a'))], ['target', 'byproduct'])
        cases = {}
        changed = deepcopy(base)
        changed['inputs'][1]['choices'][0]['amount'] = 2
        cases['amount'] = changed
        changed = deepcopy(base)
        changed['inputs'][1]['choices'].append(choice('b'))
        cases['alternative'] = changed
        changed = deepcopy(base)
        changed['inputs'][1]['consumption_chance'] = {'numerator': 1, 'denominator': 2}
        cases['consumption'] = changed
        changed = deepcopy(base)
        changed['outputs'][1]['chance'] = {'numerator': 1, 'denominator': 2}
        cases['chance'] = changed
        changed = deepcopy(base)
        changed['outputs'][1]['chance'] = None
        cases['unknown_chance'] = changed
        changed = deepcopy(base)
        changed['inputs'][1]['choices'][0]['match']['mode'] = 'native_unknown'
        cases['unknown_match'] = changed
        changed = deepcopy(base)
        changed['conditions']['keeping_nbt'] = True
        cases['nbt_transfer'] = changed
        changed = deepcopy(base)
        changed['conditions']['native_metadata'] = {'material_multiplier': 2}
        cases['native_effect'] = changed
        changed = deepcopy(base)
        changed['outputs'][1]['native_effect'] = 'unknown'
        cases['output_effect'] = changed
        changed = deepcopy(base)
        changed['inputs'][1]['choices'][0]['native_effect'] = 'unknown'
        cases['input_effect'] = changed
        for label, changed in cases.items():
            with self.subTest(label=label):
                changed.update(id='changed', family='different')
                dataset = self.dataset([base, changed], resources=[resource(id) for id in ('start', 'a', 'b', 'target', 'byproduct')])
                result = dataset.trace_processes(start_id='start', target_id='target')
                self.assertEqual({tuple(g['process_ids']) for g in result['recipe_groups']}, {('base',), ('changed',)})

    def test_repeated_or_slots_and_independent_stochastic_outputs_keep_their_structure(self):
        repeated = process('repeated', [slot(choice('start')),
            slot(choice('a'), choice('b')), slot(choice('a'), choice('b'))], ['target'])
        batch = process('batch', [slot(choice('start')), slot(choice('a', amount=2), choice('b', amount=2))], ['target'])
        dataset = self.dataset([repeated, batch])
        result = dataset.trace_processes(start_id='start', target_id='target')
        self.assertEqual(len(result['recipe_groups']), 2)
        repeated = process('two-rolls', [slot(choice('start'))], ['target', 'side', 'side'])
        for output in repeated['outputs'][1:]:
            output['chance'] = {'numerator': 1, 'denominator': 2}
        batch = process('one-roll', [slot(choice('start'))], ['target', 'side'])
        batch['outputs'][1].update(amount=2, chance={'numerator': 1, 'denominator': 2})
        dataset = self.dataset([repeated, batch])
        result = dataset.trace_processes(start_id='start', target_id='target')
        self.assertEqual(len(result['recipe_groups']), 2)
        self.assertTrue(all(g['basis'] == 'native_process' for g in result['recipe_groups']))

    def test_matching_preserves_nbt_sensitivity_and_precise_fractional_amounts(self):
        strict = process('strict', [slot(choice('start')), slot(choice('a', amount=.1)), slot(choice('a', amount=.2))], ['target'])
        batch = process('batch', [slot(choice('start')), slot(choice('a', amount=.3))], ['target'])
        insensitive = deepcopy(batch)
        insensitive['id'] = 'insensitive'
        insensitive['inputs'][1]['choices'][0]['match']['nbt_sensitive'] = False
        resources = [resource(id) for id in ('start', 'a', 'target')]
        resources.append(resource('a-nbt', registry_name='test:a', nbt={'type': 'string', 'value': 'variant'}))
        dataset = self.dataset([strict, batch, insensitive], resources=resources)
        result = dataset.trace_processes(start_id='start', target_id='target')
        self.assertEqual({tuple(g['process_ids']) for g in result['recipe_groups']}, {('batch', 'strict'), ('insensitive',)})

    def test_native_tool_projection_requires_the_whole_verified_category(self):
        machine = process('machine', [slot(choice('start'))], ['target'])
        craft = process('craft', [slot(choice('start')), slot(choice('file-a'), choice('file-b'))], ['target'], family='minecraft:crafting')
        craft['conditions'] = {'native_class': 'gregtech.api.util.GTShapedRecipe', 'declared_inputs': 'captured',
            'tool_accounting': 'container_damage_and_breakage_unresolved'}
        craft['provenance']['owner'] = 'CraftingManager'
        for c in craft['inputs'][1]['choices']:
            c.update(native_amount=1, declared_stack_size=1)
            c['match']['nbt_sensitive'] = False
        partial = deepcopy(craft)
        partial['id'] = 'partial-category'
        partial['inputs'][1]['choices'].pop()
        ordinary = deepcopy(craft)
        ordinary['id'] = 'ordinary-consumed-tool'
        ordinary['conditions'] = {}
        unknown_effect = deepcopy(craft)
        unknown_effect['id'] = 'unknown-effect'
        unknown_effect['inputs'][1]['choices'][0]['native_effect'] = 'extra_consumption'
        groups = [{'id': 'ore:craftingToolFile', 'kind': 'ore_dict', 'name': 'craftingToolFile',
            'members': ['file-a', 'file-b'], 'provenance': {'owner': 'Forge OreDictionary'}}]
        dataset = self.dataset([machine, craft, partial, ordinary, unknown_effect], groups=groups)
        result = dataset.trace_processes(start_id='start', target_id='target')
        expected = {('craft', 'machine'), ('ordinary-consumed-tool',), ('partial-category',), ('unknown-effect',)}
        self.assertEqual({tuple(g['process_ids']) for g in result['recipe_groups']}, expected)
        shared = next(g for g in result['recipe_groups'] if 'craft' in g['process_ids'])
        self.assertEqual(shared['auxiliary_input_indices'], {'craft': [1], 'machine': []})
        captured = next(p for p in result['processes'] if p['id'] == 'craft')
        self.assertEqual(captured['inputs'][1]['role'], 'consume')
        self.assertEqual(captured['conditions']['tool_accounting'], 'container_damage_and_breakage_unresolved')

    def test_groups_cover_only_retained_original_paths_and_keep_stable_ids_as_results_grow(self):
        rows = [process('first-a', [slot(choice('start'))], ['middle'], family='a'),
            process('first-b', [slot(choice('start'))], ['middle'], family='b'),
            process('last-a', [slot(choice('middle'))], ['target'], family='a'),
            process('last-b', [slot(choice('middle'))], ['target'], family='b')]
        dataset = self.dataset(rows)
        smaller = dataset.trace_processes(start_id='start', target_id='target', max_paths=1, path_selection='material')
        larger = dataset.trace_processes(start_id='start', target_id='target', max_paths=3, path_selection='material')
        self.assertEqual(len(smaller['paths']), 1)
        self.assertGreater(len(larger['paths']), len(smaller['paths']))
        self.assertEqual(smaller['path_groups'][0]['id'], larger['path_groups'][0]['id'])
        self.assertEqual(larger['path_groups'][0]['path_indices'], list(range(len(larger['paths']))))
        small_ids = {id: g['id'] for g in smaller['recipe_groups'] for id in g['process_ids']}
        large_ids = {id: g['id'] for g in larger['recipe_groups'] for id in g['process_ids']}
        self.assertEqual(small_ids, {id: large_ids[id] for id in small_ids})
        self.assertEqual(set(small_ids), {id for p in smaller['paths'] for id in p['process_ids']})
        started = dataset.start_trace_search(start_id='start', target_id='target', max_paths=3, view='concise')
        deadline = time.monotonic() + 5
        while started['status'] == 'running' and time.monotonic() < deadline:
            time.sleep(.01)
            started = dataset.get_trace_search(started['job_id'])
        self.assertEqual(started['status'], 'finished')
        self.assertEqual(started['result']['recipe_groups'], larger['recipe_groups'])
        self.assertEqual(started['result']['path_groups'], larger['path_groups'])

    def test_tier_filtered_native_variants_do_not_appear_in_groups(self):
        rows = [process('low', [slot(choice('start'))], ['target'], family='gregtech:gt.recipe.assembler'),
            process('high', [slot(choice('start'))], ['target'], family='gregtech:gt.recipe.assembler')]
        for tier, p in enumerate(rows, 1):
            p['conditions'].update(recipe_voltage_tier=tier, recipe_voltage_tier_name=('LV', 'MV')[tier - 1],
                recipe_voltage_tier_source='GTUtility.getTier(mEUt)')
        rows[0]['eu_per_tick'] = 32
        rows[1]['eu_per_tick'] = 128
        dataset = self.dataset(rows)
        result = dataset.trace_processes(start_id='start', target_id='target', max_tier=1)
        self.assertEqual([g['process_ids'] for g in result['recipe_groups']], [['low']])

    def test_progressive_partial_results_keep_existing_group_ids_and_original_path_indices(self):
        rows = [process('direct-a', [slot(choice('start'))], ['target'], family='a'),
            process('direct-b', [slot(choice('start'))], ['target'], family='b'),
            process('first', [slot(choice('start'))], ['middle']),
            process('last', [slot(choice('middle'))], ['target'])]
        dataset = self.dataset(rows)
        engine_ticks, job_ticks = itertools.count(), itertools.count()
        engine_clock = SimpleNamespace(perf_counter=lambda: next(engine_ticks) * .1)
        job_clock = SimpleNamespace(monotonic=lambda: next(job_ticks) * .1)
        observed, partial_results = {}, 0
        with patch('gtnh_data.flow_index.time', engine_clock), patch('gtnh_data.trace_jobs.time', job_clock):
            job = dataset.start_trace_search(start_id='start', target_id='target', time_budget_seconds=.05)
            dataset.pause_trace_search(job['job_id'])
            for _ in range(100):
                deadline = time.monotonic() + 5
                while job['status'] == 'running' and time.monotonic() < deadline:
                    time.sleep(.001)
                    job = dataset.get_trace_search(job['job_id'])
                self.assertIn(job['status'], ('paused', 'finished'))
                result = job.get('result')
                if result and result['paths']:
                    partial_results += job['status'] == 'paused'
                    for group in result['recipe_groups']:
                        for id in group['process_ids']:
                            self.assertEqual(observed.setdefault(id, group['id']), group['id'])
                    indices = [index for group in result['path_groups'] for index in group['path_indices']]
                    self.assertEqual(sorted(indices), list(range(len(result['paths']))))
                    for group in result['path_groups']:
                        self.assertIn(group['representative_path_index'], group['path_indices'])
                if job['status'] == 'finished':
                    break
                job = dataset.continue_trace_search(job['job_id'], time_budget_seconds=.05)
            else:
                self.fail('finite trace did not finish')
        self.assertGreater(partial_results, 0)
