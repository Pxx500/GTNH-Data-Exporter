import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from contextlib import closing

from gtnh_data import Dataset, DatasetError
from .artifacts import choice, process, resource, slot, snapshot


def material(id, name, components=()):
    row = resource(id)
    row['material_facts'] = {'association': {'primary': {'material': {
        'name': name, 'components': [{'material': {'name': component, 'components': []}}
                                   for component in components]}}}}
    return row


def associated_material(id, name, prefix, components=(), *, explicit=False):
    row = material(id, name, components)
    row['material_facts'].update(status='associated', source_api='GTOreDictUnificator.getItemData')
    row['material_facts']['association'].update(prefix=prefix, has_explicit_composition=explicit)
    return row


def recovery_fixture(root, *, explicit=True):
    rows = [associated_material('start', 'Iron', 'dust'),
            associated_material('anvil', 'Iron', None),
            associated_material('machine', 'Alloy', None, ['Iron'], explicit=explicit),
            associated_material('steel-ingot', 'Steel', 'ingot', ['Iron']),
            associated_material('steel-dust', 'Steel', 'dust', ['Iron']),
            associated_material('alloy-dust', 'Alloy', 'dust', ['Iron']),
            associated_material('alloy-ingot', 'Alloy', 'ingot', ['Iron']),
            associated_material('target', 'Alloy', None, ['Iron']),
            *[resource(id) for id in ('alloy-feed', 'alternate-feed', 'carbon', 'tungsten', 'tool')]]
    recipes = [process('anvil-maker', [slot(choice('start'))], ['anvil']),
               process('machine-maker', [slot(choice('anvil')),
                   slot(choice('alloy-feed', amount=8), choice('alternate-feed', amount=8)),
                   slot(choice('tool'), role='presence')], ['machine'], family='gregtech:gt.recipe.assembler'),
               process('machine-recovery', [slot(choice('machine'))], ['alloy-ingot'], family='gregtech:gt.recipe.arcfurnace'),
               process('steel-maker', [slot(choice('start')), slot(choice('carbon'))], ['steel-ingot']),
               process('steel-grinding', [slot(choice('steel-ingot'))], ['steel-dust'], family='gregtech:gt.recipe.macerator'),
               process('alloy-mixing', [slot(choice('steel-dust')), slot(choice('tungsten'))], ['alloy-dust']),
               process('alloy-forming', [slot(choice('alloy-dust'))], ['alloy-ingot']),
               process('finish', [slot(choice('alloy-ingot'))], ['target'])]
    dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=rows, processes=recipes), root / 'index.sqlite')
    return dataset, {row['id']: row for row in recipes}


class FlowIndexTests(unittest.TestCase):
    def test_material_route_prefers_processing_over_composite_recovery(self):
        with tempfile.TemporaryDirectory() as temporary:
            dataset, recipes = recovery_fixture(Path(temporary))
            shortest = dataset.trace_processes(start_id='start', target_id='target', path_selection='shortest', max_paths=1)
            self.assertEqual(shortest['paths'][0]['resource_ids'], ['start', 'anvil', 'machine', 'alloy-ingot', 'target'])
            result = dataset.trace_processes(start_id='start', target_id='target', path_selection='material', max_paths=1)
            self.assertEqual(result['paths'][0]['resource_ids'],
                             ['start', 'steel-ingot', 'steel-dust', 'alloy-dust', 'alloy-ingot', 'target'])
            records = {row['id']: row for row in result['processes']}
            self.assertEqual(records['steel-maker'], recipes['steel-maker'])
            self.assertEqual(records['alloy-mixing'], recipes['alloy-mixing'])
            self.assertTrue({'carbon', 'tungsten'} <= {row['resource_id'] for row in result['leaves']})
            self.assertEqual(result['search']['hop_reference']['hops'], 4)

    def test_material_recovery_remains_available_when_required_or_only_route(self):
        with tempfile.TemporaryDirectory() as temporary:
            dataset, recipes = recovery_fixture(Path(temporary))
            only_route = dataset.trace_processes(start_id='machine', target_id='alloy-ingot',
                path_selection='material', max_paths=1, max_extra_steps=0)
            self.assertEqual(only_route['paths'][0]['resource_ids'], ['machine', 'alloy-ingot'])
            for required in ([], ['machine']):
                with self.subTest(required=required):
                    result = dataset.trace_processes(start_id='start', target_id='target',
                        path_selection='material', max_paths=1, max_extra_steps=0, required_resource_ids=required)
                    self.assertEqual(result['paths'][0]['resource_ids'],
                                     ['start', 'anvil', 'machine', 'alloy-ingot', 'target'])
                    records = {row['id']: row for row in result['processes']}
                    self.assertEqual(records['machine-maker'], recipes['machine-maker'])
                    self.assertEqual(records['machine-recovery'], recipes['machine-recovery'])
                    self.assertTrue({'alloy-feed', 'alternate-feed', 'tool'} <=
                                    {row['resource_id'] for row in result['leaves']})
                    self.assertEqual(result['search']['hop_reference']['hops'], 4)

    def test_material_plate_to_dust_recovery_remains_legal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            recipe = process('grind', [slot(choice('plate'))], ['dust'], family='gregtech:gt.recipe.macerator')
            dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=[
                associated_material('plate', 'Steel', 'plate'), associated_material('dust', 'Steel', 'dust')],
                processes=[recipe]), root / 'index.sqlite')
            result = dataset.trace_processes(start_id='plate', target_id='dust', path_selection='material', max_extra_steps=0)
            self.assertEqual(result['paths'][0]['resource_ids'], ['plate', 'dust'])
            self.assertEqual(result['processes'], [recipe])

    def test_material_unknown_recycling_composition_keeps_existing_preference(self):
        with tempfile.TemporaryDirectory() as temporary:
            dataset, _ = recovery_fixture(Path(temporary), explicit=None)
            result = dataset.trace_processes(start_id='start', target_id='target', path_selection='material', max_paths=1)
            self.assertEqual(result['paths'][0]['resource_ids'], ['start', 'anvil', 'machine', 'alloy-ingot', 'target'])

    def test_large_ingredient_group_keeps_both_target_branch_spines(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            members = [f'variant-{i:04d}' for i in range(2000)]
            groups = [{'id': 'wide', 'kind': 'ore_dict', 'name': 'reachableVariants',
                       'members': members, 'provenance': {}}]
            wide = process('wide-a', [slot(choice(members[0], mode='ore_dict', group='wide')) for _ in range(12)], ['a'])
            final = process('final', [slot(choice('a')), slot(choice('b'))], ['target'])
            recipes = [process(f'producer-{i:04d}', [slot(choice('start'))], [id]) for i, id in enumerate(members)]
            recipes.extend([wide, process('simple-b', [slot(choice('start'))], ['b']), final])
            rows = [material(id, 'Base') for id in ['start', 'a', 'b', 'target', *members]]
            dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=rows, groups=groups,
                                                      processes=recipes), root / 'index.sqlite')

            result = dataset.trace_processes(start_id='start', target_id='target', path_selection='material', view='compact')

            self.assertEqual(result['route']['status'], 'found')
            self.assertEqual({path['resource_ids'][-2] for path in result['paths']}, {'a', 'b'})
            self.assertTrue(all(branch['status'] == 'represented' for branch in result['branch_coverage']))
            records = {record['id']: record for record in result['processes']}
            self.assertEqual(records['wide-a'], wide)
            self.assertEqual(records['final'], final)

    def test_compact_retains_declared_group_anchor_outside_resolved_members(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            groups = [{'id': 'group', 'kind': 'ore_dict', 'name': 'fixtureGroup', 'members': ['matched'], 'provenance': {}}]
            dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=[resource(id) for id in ('anchor', 'matched', 'target')],
                groups=groups, processes=[process('make', [slot(choice('anchor', mode='ore_dict', group='group'))], ['target'])]), root / 'index.sqlite')
            full = dataset.trace_processes(start_id='matched', target_id='target')
            self.assertNotIn('anchor', {row['id'] for row in full['resources']})
            compact = dataset.trace_processes(start_id='matched', target_id='target', view='compact')
            self.assertEqual({row['id'] for row in compact['resources']}, {'anchor', 'matched', 'target'})
            self.assertEqual(compact['processes'], full['processes'])
            self.assertEqual(compact['leaves'], full['leaves'])
            self.assertEqual(compact['presentation']['added_declared_anchor_resource_count'], 1)
            self.assertEqual(compact['presentation']['omitted_counts']['resources'], 0)

    def test_compact_trace_preserves_native_recipes_and_matched_variant(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            members = [f'member-{i}' for i in range(2000)]
            groups = [{'id': 'alternatives', 'kind': 'ore_dict', 'name': 'fixtureAlternatives',
                       'members': members, 'provenance': {}}]
            maker = process('make', [slot(choice(members[0], mode='ore_dict', group='alternatives')),
                                     slot(choice(members[0], mode='ore_dict', group='alternatives'), role='presence')], ['target'])
            unknown = process('unknown-member-maker', [slot(choice(members[1], mode='native_unknown'))], [members[23]])
            dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=[resource(id) for id in [*members, 'target']],
                                                      groups=groups, processes=[maker, unknown]), root / 'index.sqlite')
            for selection in ('shortest', 'diverse', 'material'):
                arguments = {'start_id': members[1789], 'target_id': 'target', 'path_selection': selection, 'max_paths': 1}
                full = dataset.trace_processes(**arguments)
                compact = dataset.trace_processes(**arguments, view='compact')
                self.assertEqual(compact['processes'], full['processes'])
                for key in ('paths', 'path_details', 'route', 'branch_coverage', 'coverage', 'cycles', 'limit_reasons', 'tier_filter'):
                    self.assertEqual(compact[key], full[key])
                runtime = {'distance_seconds', 'distance_cache_hit', 'distance_work'}
                self.assertEqual({key: value for key, value in compact['search'].items() if key not in runtime},
                                 {key: value for key, value in full['search'].items() if key not in runtime})
                self.assertEqual({row['id'] for row in compact['resources']}, {members[0], members[1789], 'target'})
                self.assertEqual({row['resource_id']: row for row in compact['leaves']},
                                 {row['resource_id']: row for row in full['leaves'] if row['resource_id'] in (members[0], members[1789])})
                metadata = compact['presentation']
                self.assertEqual(metadata['omitted_counts'], {'resources': 1998, 'edges': 3996, 'leaves': 1998})
                self.assertEqual(metadata['omitted_leaf_status_counts'], {'unresolved': 1998})
                self.assertEqual(len(metadata['grouped_match_refs']), 2)
                self.assertTrue(all(row['candidate_count'] == 2000 and row['group_id'] == 'alternatives'
                                    for row in metadata['grouped_match_refs']))
                self.assertEqual(metadata['omitted_leaf_reason_counts']['Producer inputs, matching or outputs are unresolved'], 1)
                self.assertNotIn('presentation', full)
            with self.assertRaisesRegex(DatasetError, 'view'):
                dataset.trace_processes(start_id=members[1789], target_id='target', view='unknown')

    def test_expanded_tool_alternatives_preserve_unresolved_producer_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tools = ['native', 'dynamic-input', 'dynamic-output', 'ordinary']
            recipes = [process('make', [slot(choice('start')), slot(*(choice(id) for id in tools), role='presence')], ['target']),
                       process('native-maker', [slot(choice('start', mode='native_unknown'))], ['native']),
                       process('dynamic-input-maker', [slot(choice('start'))], ['dynamic-input'], conditions={'dynamic_inputs': 'unresolved'}),
                       process('dynamic-output-maker', [slot(choice('start'))], ['dynamic-output'], conditions={'dynamic_output': 'unresolved'}),
                       process('ordinary-maker', [slot(choice('start'))], ['ordinary'])]
            coverage = [{'id': 'sources', 'domain': 'acquisition', 'status': 'complete', 'records': 0,
                         'reason': 'Fixture acquisition boundary is fully captured', 'provenance': {}}]
            dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=[resource(id) for id in ['start', 'target', *tools]],
                                                      processes=recipes, coverage=coverage), root / 'index.sqlite')
            for selection in ('shortest', 'diverse', 'material'):
                result = dataset.trace_processes(start_id='start', target_id='target', path_selection=selection, max_paths=1)
                leaves = {row['resource_id']: row for row in result['leaves']}
                self.assertEqual(set(tools) - leaves.keys(), set())
                for id in tools[:3]:
                    self.assertEqual(leaves[id]['status'], 'unresolved')
                    self.assertEqual(leaves[id]['reason'], 'Producer inputs, matching or outputs are unresolved')
                self.assertEqual(leaves['ordinary']['status'], 'no_known_source')

    def test_depth_cutoff_and_required_waypoint_cutoff_are_incomplete(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            recipes = [process('direct', [slot(choice('a'))], ['b']),
                       process('detour', [slot(choice('a'))], ['waypoint']),
                       process('rejoin', [slot(choice('waypoint'))], ['b']),
                       process('finish', [slot(choice('b'))], ['c'])]
            dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=[resource(id) for id in ('a', 'b', 'c', 'waypoint', 'isolated')],
                                                      processes=recipes), root / 'index.sqlite')
            for arguments in ({'max_depth': 1}, {'max_depth': 2, 'required_resource_ids': ['waypoint']}):
                result = dataset.trace_processes(start_id='a', target_id='c', path_selection='material', **arguments)
                self.assertEqual(result['route']['status'], 'incomplete')
                self.assertIn('depth', result['limit_reasons'])
                self.assertTrue(result['truncated'])
            found = dataset.trace_processes(start_id='a', target_id='c', path_selection='material', max_depth=3,
                                            required_resource_ids=['waypoint'])
            self.assertEqual(found['route']['status'], 'found')
            self.assertNotIn('depth', found['limit_reasons'])
            disconnected = dataset.trace_processes(start_id='a', target_id='isolated', path_selection='material', max_depth=1)
            self.assertEqual(disconnected['route']['status'], 'not_found')
            self.assertEqual(disconnected['limit_reasons'], [])

    def test_same_resource_has_no_recipe_branch_explanation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=[resource('a')]), root / 'index.sqlite')
            result = dataset.trace_processes(start_id='a', target_id='a', path_selection='material')
            self.assertEqual(result['route']['status'], 'same_resource')
            self.assertEqual(result['path_details'], [])
            self.assertEqual(result['branch_coverage'], [])

    def test_verified_crafting_grid_voltage_is_not_applicable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            crafting = process('craft', [slot(choice('a'))], ['b'], family='minecraft:crafting', conditions={
                'recipe_voltage_applicability': 'not_applicable_crafting_grid',
                'native_class': 'gregtech.api.util.GTShapedRecipe', 'dynamic_output': 'resolved_static'})
            crafting['provenance']['owner'] = 'CraftingManager'
            crafting.update(eu_per_tick=None, duration_ticks=None, amperage=None)
            machine = process('machine', [slot(choice('b'))], ['c'], family='gregtech:assembler')
            machine['provenance']['owner'] = 'GTRecipe'
            machine['eu_per_tick'] = 120
            dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=[resource(id) for id in ('a', 'b', 'c')],
                                                      processes=[crafting, machine]), root / 'index.sqlite')
            for selection in ('shortest', 'diverse', 'material'):
                result = dataset.trace_processes(start_id='a', target_id='c', path_selection=selection, min_tier=2, max_tier=2)
                self.assertEqual(result['route']['status'], 'found')
                self.assertEqual(next(row for row in result['recipe_tiers'] if row['process_id'] == 'craft')['status'], 'not_applicable')
                self.assertIsNone(next(row for row in result['processes'] if row['id'] == 'craft')['eu_per_tick'])
                for filters in ({'max_tier': 1}, {'min_tier': 15}):
                    self.assertEqual(dataset.trace_processes(start_id='a', target_id='b', path_selection=selection, **filters)['route']['status'], 'found')
            for field, value in (('family', 'gregtech:assembler'), ('eu_per_tick', 0)):
                spoof = dict(crafting, **{field: value})
                with self.subTest(field=field):
                    invalid = Dataset.import_snapshot(snapshot(root / f'spoof-{field}', resources=[resource('a'), resource('b')], processes=[spoof]), root / f'spoof-{field}.sqlite')
                    result = invalid.trace_processes(start_id='a', target_id='b', path_selection='material', max_tier=1)
                    self.assertEqual(result['paths'], [])
                    self.assertEqual(invalid._recipe_tier(spoof)['status'], 'unknown')
    def test_material_selection_prefers_continuity_and_keeps_byproduct_branch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rows = [material('start', 'Base'), material('alloy', 'Alloy', ['Base', 'Carbon']),
                    material('plate', 'Alloy', ['Base', 'Carbon']), material('gas', 'Gas'),
                    material('target', 'Alloy', ['Base', 'Carbon']), resource('side')]
            recipes = [process('a-byproduct', [slot(choice('start'))], ['side', 'gas']),
                       process('b-gas-finish', [slot(choice('gas'))], ['target']),
                       process('c-alloy', [slot(choice('start')), slot(choice('side'))], ['alloy']),
                       process('d-plate', [slot(choice('alloy'))], ['plate']),
                       process('e-assemble', [slot(choice('plate'))], ['target'])]
            dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=rows, processes=recipes), root / 'index.sqlite')
            shortest = dataset.trace_processes(start_id='start', target_id='target', path_selection='shortest', max_paths=1)
            self.assertEqual(shortest['paths'][0]['resource_ids'], ['start', 'gas', 'target'])
            result = dataset.trace_processes(start_id='start', target_id='target', path_selection='material', max_paths=2)
            self.assertEqual(result['paths'][0]['resource_ids'], ['start', 'alloy', 'plate', 'target'])
            self.assertEqual({tuple(path['resource_ids']) for path in result['paths']},
                             {('start', 'alloy', 'plate', 'target'), ('start', 'gas', 'target')})
            self.assertEqual(result['path_details'][0]['material_continuity'], 'supported')
            self.assertTrue(result['path_details'][1]['byproduct_steps'])
            self.assertIn('side', {row['resource_id'] for row in result['leaves']})
            bounded = dataset.trace_processes(start_id='start', target_id='target', path_selection='material', max_extra_steps=0, max_paths=1)
            self.assertEqual(bounded['paths'][0]['resource_ids'], ['start', 'gas', 'target'])
            self.assertEqual(bounded['search']['hop_reference']['hops'], 2)
            required = dataset.trace_processes(start_id='start', target_id='target', path_selection='material',
                                              required_resource_ids=['plate'], max_extra_steps=0, max_paths=1)
            self.assertEqual(required['paths'][0]['resource_ids'], ['start', 'alloy', 'plate', 'target'])
            excluded = dataset.trace_processes(start_id='start', target_id='target', path_selection='material', excluded_resource_ids=['alloy'])
            self.assertEqual(excluded['paths'][0]['resource_ids'], ['start', 'gas', 'target'])

    def test_preparation_is_rebuildable_and_bound_to_manifest_and_version(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=[resource('start'), resource('target')],
                processes=[process('make', [slot(choice('start'))], ['target'])]), root / 'index.sqlite')
            before = dataset.path.read_bytes()
            prepared = dataset.rebuild_flow_index()
            self.assertEqual(before, dataset.path.read_bytes())
            self.assertEqual(prepared['snapshot_id'], dataset.snapshot_id)
            self.assertEqual(dataset.flow_index_status()['status'], 'ready')
            path = Path(prepared['database'])
            with closing(sqlite3.connect(path)) as connection, connection:
                connection.execute("UPDATE metadata SET value='0' WHERE key='analysis_version'")
            self.assertEqual(dataset.flow_index_status()['status'], 'incompatible')
            with self.assertRaisesRegex(DatasetError, 'rebuild'):
                dataset.trace_processes(start_id='start', target_id='target', path_selection='material')
            dataset.rebuild_flow_index()
            with closing(sqlite3.connect(path)) as connection, connection:
                connection.execute("UPDATE metadata SET value=? WHERE key='manifest'", (json.dumps({'snapshot_id': 'other'}),))
            with self.assertRaisesRegex(DatasetError, 'rebuild'):
                dataset.trace_processes(start_id='start', target_id='target', path_selection='material')

    def test_prepared_matching_preserves_nbt_or_presence_and_tiers(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rows = [resource('start', registry_name='test:shared', nbt={'type': 'int', 'value': 1}),
                    resource('other', registry_name='test:shared', nbt={'type': 'int', 'value': 2}),
                    resource('tool'), resource('mid'), resource('target')]
            match = choice('other')
            match['match']['nbt_sensitive'] = True
            wrong = process('wrong-nbt', [slot(match)], ['target'])
            good = process('good-or', [slot(choice('other'), choice('start')), slot(choice('tool'), role='presence')], ['mid'])
            finish = process('finish', [slot(choice('mid'))], ['target'])
            finish['eu_per_tick'] = 120
            recipes = [wrong, good, finish, process('presence-only', [slot(choice('start'), role='presence')], ['target']),
                       process('cycle', [slot(choice('mid'))], ['start'])]
            for recipe in recipes:
                recipe['family'] = 'gregtech:assembler'
                recipe['provenance']['owner'] = 'GTRecipe'
            dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=rows, processes=recipes), root / 'index.sqlite')
            lv = dataset.trace_processes(start_id='start', target_id='target', path_selection='material', max_tier=1)
            self.assertEqual(lv['paths'], [])
            mv = dataset.trace_processes(start_id='start', target_id='target', path_selection='material', max_tier=2)
            self.assertEqual(mv['paths'], [{'resource_ids': ['start', 'mid', 'target'], 'process_ids': ['good-or', 'finish']}])
            self.assertIn('tool', {row['resource_id'] for row in mv['leaves']})
            self.assertTrue(mv['processes'][1]['inputs'][1]['role'] == 'presence')

    def test_group_variants_and_zero_yield_retain_exact_matching_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rows = [resource('canonical'), resource('variant'), resource('target'), resource('zero')]
            groups = [{'id': 'metal', 'kind': 'ore_dict', 'name': 'ingotBase',
                       'members': ['canonical', 'variant'], 'provenance': {}}]
            make = process('make', [slot(choice('canonical', mode='unified', group='metal'))], ['target', 'zero'])
            make['outputs'][1]['chance']['numerator'] = 0
            dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=rows, groups=groups, processes=[make]), root / 'index.sqlite')
            for source in ('canonical', 'variant'):
                result = dataset.trace_processes(start_id=source, target_id='target', path_selection='material')
                self.assertEqual(result['paths'][0]['resource_ids'], [source, 'target'])
                zero = dataset.trace_processes(start_id=source, target_id='zero', path_selection='material')
                self.assertEqual(zero['paths'], [])


if __name__ == '__main__':
    unittest.main()
