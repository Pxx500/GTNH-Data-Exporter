import tempfile
import unittest
from pathlib import Path

from gtnh_data import Dataset, DatasetError
from .artifacts import choice, process, resource, slot, snapshot


class NetworkPlanningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def dataset(self, records, ids, **collections):
        return Dataset.import_snapshot(snapshot(self.root / 'snapshot',
            resources=[resource(id) for id in ids], processes=records, **collections), self.root / 'index.sqlite')

    def test_candidate_discovery_keeps_all_and_inputs_presence_and_regeneration(self):
        main = process('main', [slot(choice('feed')), slot(choice('reagent')),
            slot(choice('tool'), role='presence')], ['target', 'spent'])
        regenerate = process('regenerate', [slot(choice('spent'))], ['reagent'])
        dataset = self.dataset([main, regenerate], ['feed', 'target', 'reagent', 'spent', 'tool'])
        result = dataset.discover_network('target', allowed_feed_ids=['feed', 'tool'])
        self.assertEqual({v['process_id'] for v in result['variants']}, {'main', 'regenerate'})
        variant = next(v for v in result['variants'] if v['process_id'] == 'main')
        self.assertEqual(set(variant['selections']), {'0', '1', '2'})
        self.assertEqual(result['processes']['main'], main)
        self.assertTrue(result['coverage_complete'])

    def test_profile_is_persistent_snapshot_bound_and_scope_is_explicit(self):
        dataset = self.dataset([], ['feed', 'target'])
        saved = dataset.save_boundary_profile('basic', name='Basic feeds', base_resource_ids=['feed'],
            scope={'excluded_resource_ids': ['target']})
        reopened = Dataset(dataset.path)
        self.assertEqual(reopened.get_boundary_profile('basic')['item'], saved['item'])
        self.assertEqual(reopened.find_resources(profile_id='basic')['total'], 1)
        self.assertEqual(reopened.find_resources(q='target', profile_id='basic')['total'], 0)
        self.assertEqual(reopened.get_resource('target')['item']['id'], 'target')
        with self.assertRaises(DatasetError):
            reopened.save_boundary_profile('basic', name='Stale', base_resource_ids=['feed'], expected_revision=0)

    def test_or_variants_are_concrete_and_scope_never_implies_unreachable(self):
        dataset = self.dataset([process('main', [slot(choice('a'), choice('b'))], ['target'])], ['a', 'b', 'target'])
        result = dataset.discover_network('target', allowed_feed_ids=['a', 'b'])
        self.assertEqual({v['selections']['0']['resource_id'] for v in result['variants']}, {'a', 'b'})
        filtered = dataset.discover_network('target', allowed_feed_ids=['a'], scope={'excluded_resource_ids': ['b']})
        self.assertEqual([v['selections']['0']['resource_id'] for v in filtered['variants']], ['a'])
        self.assertEqual(filtered['exclusions']['counts']['resource_scope'], 1)
        limited = dataset.discover_network('target', allowed_feed_ids=['a', 'b'], max_variants=1)
        self.assertFalse(limited['coverage_complete'])
        self.assertIn('candidate_variant_limit', limited['limit_reasons'])

    def test_selected_group_variant_preserves_quantity_and_raw_declaration(self):
        records = [process('main', [slot(choice('anchor', 'unified', group='g', amount=3))], ['target'])]
        records[0]['inputs'][0]['consumption_chance'] = {'numerator': 1, 'denominator': 2}
        dataset = self.dataset(records, ['anchor', 'other', 'target'], groups=[
            {'id': 'g', 'kind': 'unified', 'name': 'g', 'members': ['anchor', 'other'], 'provenance': {}}])
        result = dataset.discover_network('target', allowed_feed_ids=['other'],
            selections={'main': {'0': {'choice_index': 0, 'resource_id': 'other'}}})
        variant = result['variants'][0]
        self.assertEqual(variant['process']['inputs'][0]['choices'][0]['resource_id'], 'other')
        self.assertEqual(variant['process']['inputs'][0]['choices'][0]['amount'], 3)
        self.assertEqual(variant['process']['inputs'][0]['consumption_chance'], {'numerator': 1, 'denominator': 2})
        self.assertEqual(result['processes']['main'], records[0])
        self.assertEqual(dataset.get_process('main')['item'], records[0])
        with self.assertRaises(DatasetError):
            dataset.discover_network('target', allowed_feed_ids=['other'],
                selections={'main': {'8': {'choice_index': 0, 'resource_id': 'other'}}})

    def test_scope_filters_groups_namespaces_and_families_without_mutating_records(self):
        records = [process('main', [slot(choice('a'))], ['target'], family='test:machine')]
        dataset = self.dataset(records, ['a', 'b', 'target'], groups=[
            {'id': 'g', 'kind': 'ore_dict', 'name': 'ingotTest', 'members': ['a', 'b'], 'provenance': {}}])
        self.assertEqual(dataset.find_resource_groups(q='ingot', limit=1)['items'][0]['member_count'], 2)
        self.assertEqual(dataset.find_resources(scope={'excluded_group_ids': ['g']})['total'], 1)
        self.assertEqual(dataset.find_resources(q='target', scope={'excluded_namespaces': ['test']})['total'], 0)
        result = dataset.discover_network('target', allowed_feed_ids=['a'], scope={'excluded_family_ids': ['test:machine']})
        self.assertEqual(result['variants'], [])
        self.assertEqual(result['exclusions']['counts']['family_scope'], 1)
        self.assertFalse(result['coverage_complete'])
        self.assertEqual(dataset.get_scope_catalog()['families'], [{'id': 'test:machine', 'processes': 1}])

    def test_excluded_coproduct_removes_the_whole_producer_without_hiding_output(self):
        main = process('main', [slot(choice('feed'))], ['iron', 'nickel'])
        dataset = self.dataset([main], ['feed', 'iron', 'nickel'])
        report = dataset.discover_network('iron', allowed_feed_ids=['feed'],
            scope={'excluded_resource_ids': ['nickel']})
        self.assertEqual(report['variants'], [])
        self.assertEqual(report['processes'], {})
        self.assertEqual(report['exclusions']['counts']['output_resource_scope'], 1)
        self.assertFalse(report['coverage_complete'])
        self.assertEqual(dataset.get_process('main')['item'], main)

    def test_energy_audit_preserves_benchmark_cofeeds_and_equal_target_quantity(self):
        direct = process('direct', [slot(choice('water')), slot(choice('cell'))], ['hydrogen', 'filled'])
        direct['outputs'][0]['amount'] = 2
        cheap = process('cheap', [slot(choice('water'))], ['hydrogen'])
        cheap['eu_per_tick'] = 1
        dataset = self.dataset([direct, cheap], ['water', 'cell', 'hydrogen', 'filled'])
        result = dataset.audit_energy('water', 'hydrogen', benchmark_process_id='direct', target_amount=4,
            max_solutions=1)
        self.assertEqual(result['benchmark']['runs'], {'numerator': 2, 'denominator': 1})
        self.assertEqual(result['benchmark']['cofeeds'], {'cell': {'numerator': 2, 'denominator': 1}})
        self.assertEqual(result['benchmark']['energy']['total_eu'], {'numerator': 320, 'denominator': 1})
        self.assertEqual(result['allowed_feed_ids'], ['water'])
        self.assertEqual(result['solutions'][0]['nominal_energy']['total_eu'], {'numerator': 80, 'denominator': 1})
        self.assertEqual(result['solutions'][0]['savings']['percent'], {'numerator': 75, 'denominator': 1})

    def test_unseeded_regeneration_is_not_a_fully_grounded_base_plan(self):
        first = process('first', [slot(choice('water')), slot(choice('seed'))], ['target', 'spent'])
        regenerate = process('regenerate', [slot(choice('spent'))], ['seed'])
        dataset = self.dataset([first, regenerate], ['water', 'seed', 'spent', 'target'])
        dataset.save_boundary_profile('base', name='Water', base_resource_ids=['water'])
        result = dataset.plan_to_bases('target', profile_id='base', max_solutions=1)
        solution = result['solutions'][0]
        self.assertEqual(solution['net_imports'], {'water': {'numerator': 1, 'denominator': 1}})
        self.assertEqual(solution['base_boundary']['status'], 'requires_startup')
        self.assertEqual(solution['base_boundary']['unresolved_startup'], {'seed': {'numerator': 1, 'denominator': 1}})

    def test_native_canonical_ranking_precedes_pagination_without_merging_aliases(self):
        alias = resource('a_alias', registry_name='IC2:iron')
        canonical = resource('z_canonical', registry_name='gregtech:iron')
        for item in (alias, canonical):
            item['display_name'] = 'Iron Dust'
        dataset = Dataset.import_snapshot(snapshot(self.root / 'snapshot', resources=[alias, canonical], groups=[
            {'id': 'unified:z_canonical', 'kind': 'unified', 'name': 'z_canonical',
             'members': ['a_alias', 'z_canonical'],
             'provenance': {'owner': 'GTOreDictUnificator.getNonUnifiedStacks'}}]), self.root / 'index.sqlite')
        first = dataset.find_resources(q='iron dust', limit=1)
        second = dataset.find_resources(q='dust iron', limit=1, offset=1)
        self.assertEqual(first['items'][0]['id'], 'z_canonical')
        self.assertEqual(second['items'][0]['id'], 'a_alias')
        self.assertEqual(first['total'], 2)
        self.assertEqual(second['items'][0]['acquisition_analysis']['unification']['status'], 'noncanonical_unification_variant')
        self.assertEqual(dataset.get_resource('a_alias')['item'], alias)

    def test_acquisition_grounding_does_not_seed_generated_blocks(self):
        p = process('smelt', [slot(choice('ore'))], ['target'])
        generation = {'id': 'generation', 'kind': 'ore_generation', 'display_name': 'Ore block',
            'outputs': [{'resource_id': 'ore', 'amount': 1, 'chance': {'numerator': 1, 'denominator': 1},
                         'resource_semantics': 'generated_ore_block_not_mining_drop'}],
            'environment_ids': [], 'status': 'conditional', 'conditions': {'worldgen': True},
            'parameters': {}, 'provenance': {}}
        dataset = self.dataset([p], ['ore', 'target'], sources=[generation])
        result = dataset.inspect_acquisition('target')
        self.assertNotIn('target', result['grounding']['reachable_resource_ids'])
        mined = dict(generation, id='mined', kind='ore_mining', outputs=[
            {'resource_id': 'ore', 'amount': 1, 'chance': {'numerator': 1, 'denominator': 1},
             'resource_semantics': 'mined_item_baseline'}])
        dataset = Dataset.import_snapshot(snapshot(self.root / 'with-drop', resources=[resource('ore'), resource('target')],
            processes=[p], sources=[generation, mined]), self.root / 'with-drop.sqlite')
        result = dataset.inspect_acquisition('target')
        self.assertIn('target', result['grounding']['reachable_resource_ids'])
        self.assertEqual(len(dataset.find_sources(resource_id='ore')['items']), 2)

    def test_target_tagged_as_base_stops_without_an_invented_process(self):
        dataset = self.dataset([process('make', [slot(choice('feed'))], ['target'])], ['feed', 'target'])
        dataset.save_boundary_profile('base', name='Ready casings', base_resource_ids=['target'])
        result = dataset.plan_to_bases('target', profile_id='base', target_amount=3)
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(result['solutions'], [])
        self.assertEqual(result['base_requirements'], {'target': {'numerator': 3, 'denominator': 1}})
        self.assertEqual(result['execution_scope'], 'assumed_external_feed_boundary')

    def test_statistics_share_scope_and_attach_only_reported_original_processes(self):
        low = process('low', [slot(choice('a'))], ['target'], family='test:machine')
        high = process('high', [slot(choice('a'))], ['target'], family='test:machine')
        high['duration_ticks'] = 40
        noise = process('noise', [slot(choice('a'))], ['excluded'], family='test:machine')
        other = process('other', [slot(choice('a'))], ['target'], family='other:machine')
        dataset = self.dataset([low, high, noise, other], ['a', 'target', 'excluded'])
        report = dataset.analyze_statistics(scope={'excluded_resource_ids': ['excluded'],
            'excluded_family_ids': ['other:machine']})
        self.assertEqual(report['overview']['resources']['count'], 2)
        self.assertEqual(report['overview']['processes']['count'], 2)
        self.assertEqual(set(report['processes']), {'low', 'high'})
        self.assertEqual(report['processes']['high'], high)
        self.assertIn('Raw input predicates remain unchanged', report['search']['scope_semantics'])
