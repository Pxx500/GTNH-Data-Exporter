import unittest
import tempfile
from pathlib import Path

from gtnh_data import Dataset
from gtnh_data.acquisition import acquisition_rank, analyze_grounding, summarize_acquisition, unification_preferences
from .artifacts import choice, process, resource, slot, snapshot


def variant(record):
    return {'process': record, 'selections': {str(i): {'choice_index': 0, 'resource_id': s['choices'][0]['resource_id']}
                                            for i, s in enumerate(record['inputs'])}}


def native_resource(id, prefix, material='Copper', **kwargs):
    record = resource(id, **kwargs)
    record['material_facts'] = {'status': 'associated', 'source_api': 'GTOreDictUnificator.getItemData',
        'association': {'prefix': prefix, 'primary': {'material': {'name': material, 'native_class': 'gregtech.api.enums.Materials'}}}}
    return record


def native_process(id, input, output, family='macerator'):
    record = process(id, [slot(choice(input))], [output], family='gregtech:gt.recipe.' + family)
    record['provenance'] = {'owner': 'GTRecipe', 'map': 'gt.recipe.' + family}
    return record


def native_mining(rid='raw'):
    return {'id': 'mining', 'kind': 'ore_mining', 'display_name': 'Mining', 'status': 'conditional',
        'outputs': [{'resource_id': rid, 'amount': 1, 'chance': {'numerator': 1, 'denominator': 1},
                     'resource_semantics': 'mined_item_baseline'}], 'environment_ids': [],
        'conditions': {'mining': {'material': 'Copper'}}, 'parameters': {},
        'provenance': {'owner': 'GTOreAdapter.getOreDrops'}}


class AcquisitionTests(unittest.TestCase):
    def dataset(self, **collections):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        return Dataset.import_snapshot(snapshot(root / 'snapshot', **collections), root / 'index.sqlite')

    def test_native_anchor_preference_is_not_replacement_and_preserves_nbt(self):
        group = lambda id, anchor, members: {'id': id, 'kind': 'unified', 'name': anchor, 'members': members,
            'provenance': {'owner': 'GTOreDictUnificator.getNonUnifiedStacks'}}
        empty = {'type': 'compound', 'value': {}}
        dataset = self.dataset(resources=[resource('legacy'), resource('canonical'), resource('tagged', nbt=empty)],
            groups=[group('unified:canonical', 'canonical', ['legacy', 'canonical']),
                    group('unified:tagged', 'tagged', ['legacy', 'tagged'])],
            coverage=[{'id': 'other-acquisition', 'domain': 'other-acquisition', 'status': 'unsupported',
                       'records': 0, 'reason': 'Fixture other sources are not captured', 'provenance': {}}])
        with dataset._connect() as conn:
            facts = unification_preferences(conn)
            summary = summarize_acquisition(conn, ['legacy', 'canonical', 'tagged'], snapshot_id=dataset.snapshot_id)
        self.assertEqual(facts['legacy']['preferred_resource_ids'], ['canonical'])
        self.assertEqual(facts['legacy']['status'], 'noncanonical_unification_variant')
        self.assertFalse(facts['legacy']['replacement_confirmed'])
        self.assertLess(acquisition_rank(facts['canonical']), acquisition_rank(facts['legacy']))
        self.assertEqual(summary['resources']['legacy']['acquisition']['status'], 'no_known_acquisition')
        self.assertFalse(summary['resources']['legacy']['acquisition']['obtainable_proven'])
        self.assertEqual(summary['coverage']['status_counts'], {'unsupported': 1})
        self.assertEqual(summary['coverage']['unsupported'][0]['id'], 'other-acquisition')

    def test_multiple_native_anchors_are_ambiguous(self):
        groups = [{'id': f'unified:{anchor}', 'kind': 'unified', 'name': anchor, 'members': ['variant', anchor],
                   'provenance': {'owner': 'GTOreDictUnificator.getNonUnifiedStacks'}} for anchor in ('a', 'b')]
        dataset = self.dataset(resources=[resource(id) for id in ('variant', 'a', 'b')], groups=groups)
        with dataset._connect() as conn:
            facts = unification_preferences(conn, ['variant'])
        self.assertEqual(facts['variant']['status'], 'ambiguous')
        self.assertEqual(facts['variant']['preferred_resource_ids'], ['a', 'b'])

    def test_dynamic_outputs_unknown_matchers_and_zero_chance_do_not_confirm_producers(self):
        dynamic = process('dynamic', [slot(choice('seed'))], ['template'], conditions={'dynamic_output': 'unresolved'})
        opaque = process('opaque', [slot(choice('seed', 'native_unknown'))], ['template'], executable=None)
        zero = process('zero', [slot(choice('seed'))], ['zero'])
        zero['outputs'][0]['chance']['numerator'] = 0
        unknown = process('chance_unknown', [slot(choice('seed'))], ['unknown'])
        unknown['outputs'][0]['chance'] = None
        good = process('good', [slot(choice('seed'))], ['product'])
        source = {'id': 'native', 'kind': 'ore_mining', 'display_name': 'conditional native rule',
                  'outputs': [{'resource_id': 'ore', 'amount': 1}], 'environment_ids': [],
                  'status': 'conditional', 'conditions': {}, 'parameters': {}, 'provenance': {}}
        dataset = self.dataset(resources=[resource(id) for id in ('seed', 'template', 'zero', 'unknown', 'product', 'ore')],
            processes=[dynamic, opaque, zero, unknown, good], sources=[source])
        with dataset._connect() as conn:
            facts = summarize_acquisition(conn, ['template', 'zero', 'unknown', 'product', 'ore'], snapshot_id=dataset.snapshot_id)['resources']
        self.assertEqual(facts['template']['acquisition']['unresolved_producer_count'], 2)
        self.assertEqual(facts['template']['acquisition']['eligible_producer_count'], 0)
        self.assertEqual(facts['zero']['acquisition']['status'], 'no_known_acquisition')
        self.assertEqual(facts['unknown']['acquisition']['status'], 'unresolved_producer_only')
        self.assertEqual(facts['product']['acquisition']['status'], 'eligible_producer')
        self.assertEqual(facts['ore']['acquisition']['status'], 'known_source')
        self.assertFalse(facts['ore']['acquisition']['obtainable_proven'])

    def test_closed_cycle_requires_a_seed_and_every_and_input(self):
        variants = [variant(process('ab', [slot(choice('a')), slot(choice('tool'), role='presence')], ['b'])),
                    variant(process('ba', [slot(choice('b'))], ['a']))]
        cold = analyze_grounding(variants, [], ['tool'], True)
        self.assertEqual(cold['resources'].get('a', {}).get('status'), 'no_known_grounded_path')
        self.assertEqual(cold['unseeded_cycles'][0]['resource_ids'], ['a', 'b'])
        self.assertNotIn('b', analyze_grounding(variants, [], ['a'], True)['reachable_resource_ids'])
        warm = analyze_grounding(variants, [], ['a', 'tool'], True)
        self.assertIn('b', warm['reachable_resource_ids'])

    def test_world_origin_distinguishes_generation_baseline_and_rule_candidates(self):
        def source(id, rid, semantics, status='conditional'):
            record = {'id': id, 'kind': 'ore_mining' if semantics != 'generated_ore_block_not_mining_drop' else 'ore_vein',
                'display_name': id, 'status': status, 'outputs': [{'resource_id': rid, 'amount': 1,
                    'chance': {'numerator': 1, 'denominator': 1}, 'resource_semantics': semantics}],
                'environment_ids': ['dim'], 'conditions': {'mining': {'material': 'Copper'}},
                'parameters': {'generated_source_id': 'generation', 'generated_resource_id': 'block'}, 'provenance': {}}
            if semantics == 'mined_item_rule_candidate':
                record['outputs'] = [{'resource_id': rid, 'resource_semantics': semantics}]
                record['parameters']['output_rule'] = {'kind': 'gt_small_ore_fortune0', 'version': 1,
                    'scope': 'per_qualifying_native_base_harvest', 'evaluation_order': ['primary', 'host'],
                    'primary': {'kind': 'weighted_draws_with_replacement', 'draw_count': 1, 'amount_per_draw': 1,
                        'total_weight': 1, 'candidates': [{'resource_id': rid, 'weight': 1}], 'empty_pool_behavior': 'emit_nothing'},
                    'host': {'kind': 'exclusive_choice', 'outcomes': [
                        {'probability': {'numerator': 2, 'denominator': 3}, 'outputs': [],
                            'native_cases': [{'case': 'none', 'probability': {'numerator': 2, 'denominator': 3}}]},
                        {'probability': {'numerator': 1, 'denominator': 3}, 'outputs': [{'resource_id': rid, 'amount': 1}],
                            'native_cases': [{'case': 'pure', 'probability': {'numerator': 1, 'denominator': 9}},
                                             {'case': 'impure', 'probability': {'numerator': 2, 'denominator': 9}}]}]}}
            return record
        dataset = self.dataset(resources=[resource(id) for id in ('block', 'raw', 'crushed', 'disabled')],
            processes=[process('recycle', [slot(choice('raw'))], ['raw'])],
            sources=[source('generation', 'block', 'generated_ore_block_not_mining_drop'),
                     source('baseline', 'raw', 'mined_item_baseline'),
                     source('rule', 'crushed', 'mined_item_rule_candidate'),
                     source('off', 'disabled', 'mined_item_baseline', 'disabled')],
            environments=[{'id': 'dim', 'name': 'Test world', 'dimension_id': 42, 'provider': None, 'properties': {}, 'provenance': {}}])
        with dataset._connect() as conn:
            facts = summarize_acquisition(conn, ['block', 'raw', 'crushed', 'disabled'],
                snapshot_id=dataset.snapshot_id, include_source_details=True)['resources']
        self.assertEqual(facts['block']['provenance']['world_source']['status'], 'generated_block_only')
        self.assertEqual(facts['raw']['provenance']['world_source']['status'], 'captured_inventory_source')
        self.assertEqual(facts['crushed']['provenance']['world_source']['status'], 'mining_rule_candidate_only')
        self.assertEqual(facts['disabled']['provenance']['world_source']['status'], 'no_active_source_evidence')
        evidence = facts['raw']['provenance']['world_source']['evidence'][0]
        self.assertEqual(evidence['environments'][0]['dimension_id'], 42)
        self.assertEqual(evidence['generated_resource_id'], 'block')
        self.assertEqual(facts['raw']['provenance']['renewable']['status'], 'unknown')
        self.assertTrue(facts['raw']['provenance']['basic_suggestion']['suggested'])
        self.assertFalse(facts['block']['provenance']['basic_suggestion']['suggested'])

    def test_selected_or_variant_does_not_require_unselected_choices(self):
        p = process('or', [slot(choice('seed'), choice('missing'))], ['result'])
        grounded = analyze_grounding([variant(p)], [], ['seed'], True)
        self.assertEqual(grounded['resources']['result']['status'], 'structural_reachable')
        incomplete = analyze_grounding([variant(p)], [], [], False, limit_reasons=['candidate_depth'])
        self.assertEqual(incomplete['resources']['result']['status'], 'incomplete')
        self.assertFalse(incomplete['execution_proven'])

    def test_initial_processing_follows_native_material_and_bounded_ore_steps(self):
        resources = [native_resource(id, prefix) for id, prefix in (
            ('raw', 'rawOre'), ('crushed', 'crushed'), ('impure', 'dustImpure'), ('dust', 'dust'),
            ('legacy_dust', 'dust'), ('ingot', 'ingot'), ('plate', 'plate'))]
        recipes = [native_process('crush', 'raw', 'crushed', 'hammer'),
                   native_process('grind', 'crushed', 'impure'), native_process('clean', 'impure', 'dust', 'centrifuge'),
                   native_process('smelt', 'dust', 'ingot'), native_process('form', 'ingot', 'plate'),
                   native_process('recycle', 'plate', 'legacy_dust')]
        dataset = self.dataset(resources=resources, processes=recipes, sources=[native_mining()],
            groups=[{'id': 'unified:dust', 'kind': 'unified', 'name': 'dust', 'members': ['dust', 'legacy_dust'],
                'provenance': {'owner': 'GTOreDictUnificator.getNonUnifiedStacks'}}])
        with dataset._connect() as conn:
            facts = summarize_acquisition(conn, [r['id'] for r in resources], snapshot_id=dataset.snapshot_id)['resources']
        for rid in ('crushed', 'impure', 'dust'):
            self.assertEqual(facts[rid]['provenance']['initial_processing']['status'], 'inferred')
            self.assertTrue(facts[rid]['provenance']['basic_suggestion']['suggested'])
        evidence = facts['dust']['provenance']['initial_processing']['evidence'][0]
        self.assertEqual(evidence['process_ids'], ['crush', 'grind', 'clean'])
        self.assertEqual(evidence['source_resource_id'], 'raw')
        self.assertEqual(evidence['source_semantics'], 'mined_item_baseline')
        for rid in ('raw', 'legacy_dust', 'ingot', 'plate'):
            self.assertEqual(facts[rid]['provenance']['initial_processing']['status'], 'no_bounded_evidence')

    def test_native_underground_fluid_definition_is_source_evidence_without_fixed_inventory_quantity(self):
        gas = resource('gas')
        gas.update(kind='fluid', metadata=None)
        source = {'id': 'gas_world', 'kind': 'underground_fluid', 'display_name': 'Gas world definition',
            'status': 'conditional', 'outputs': [{'resource_id': 'gas', 'chance': None}], 'environment_ids': [],
            'conditions': {'dimension_rule': '0'}, 'parameters': {'min_amount': 10, 'max_amount': 350},
            'provenance': {'owner': 'GTMod.proxy.mUndergroundOil'}}
        dataset = self.dataset(resources=[gas], sources=[source])
        with dataset._connect() as conn:
            fact = summarize_acquisition(conn, ['gas'], snapshot_id=dataset.snapshot_id)['resources']['gas']
        self.assertEqual(fact['provenance']['world_source']['evidence_counts']['direct_world_source'], 1)
        self.assertFalse(fact['provenance']['world_source']['inventory_obtainable_proven'])
        self.assertEqual(fact['provenance']['renewable']['status'], 'unknown')

    def test_underground_blacklist_metadata_is_preserved_without_changing_acquisition(self):
        gas = resource('gas')
        gas.update(kind='fluid', metadata=None)
        source = {'id': 'gas_world', 'kind': 'underground_fluid', 'display_name': 'Gas world definition',
            'status': 'conditional', 'outputs': [{'resource_id': 'gas', 'chance': None}],
            'environment_ids': ['rule'], 'conditions': {'dimension_rule': '0'},
            'parameters': {'min_amount': 10, 'max_amount': 350},
            'provenance': {'owner': 'GTMod.proxy.mUndergroundOil'}}
        captured = {'status': 'captured', 'source_api': 'gregtech.GTMod.proxy.mUndergroundOil.blackList',
            'scope': 'native_numeric_filter_not_resolved_availability'}
        cases = (None, dict(captured, dimension_ids=[-1, 0, 0, 7]), dict(captured, dimension_ids=[]),
            {'status': 'unresolved', 'source_api': captured['source_api'], 'dimension_ids': None,
             'reason': 'native_array_is_null', 'scope': captured['scope']})
        baseline = None
        for blacklist in cases:
            with self.subTest(blacklist=blacklist):
                properties = {'native_rule': '0', 'uninterpreted_optional': None}
                if blacklist is not None:
                    properties['dimension_blacklist'] = blacklist
                environment = {'id': 'rule', 'name': 'Native rule', 'dimension_id': None,
                    'provider': None, 'properties': properties, 'provenance': {}}
                dataset = self.dataset(resources=[gas], sources=[source], environments=[environment])
                result = dataset.inspect_acquisition('gas', max_depth=1, max_processes=1,
                    max_variants=1, max_resources=1)
                self.assertEqual(dataset.get_source('gas_world')['item'], source)
                fact = result['item']
                world = fact['provenance']['world_source']
                evidence = world['evidence'][0]
                self.assertEqual(evidence['environments'], [environment])
                self.assertEqual(evidence['status'], source['status'])
                self.assertEqual(evidence['classification'], 'direct_world_source')
                self.assertEqual(world['status'], 'captured_inventory_source')
                self.assertFalse(world['inventory_obtainable_proven'])
                if baseline is None:
                    baseline = fact['acquisition']
                self.assertEqual(fact['acquisition'], baseline)
                self.assertFalse(fact['acquisition']['obtainable_proven'])

    def test_initial_processing_rejects_material_changes_and_unproven_world_blocks(self):
        generation = native_mining('block')
        generation.update(id='generation', kind='ore_vein')
        generation['outputs'][0]['resource_semantics'] = 'generated_ore_block_not_mining_drop'
        recipes = [native_process('unmined', 'block', 'crushed'),
                   native_process('different_material', 'raw', 'other'),
                   native_process('unresolved', 'raw', 'dynamic')]
        recipes[-1]['conditions']['dynamic_output'] = 'unresolved'
        dataset = self.dataset(resources=[native_resource('block', 'ore'), native_resource('raw', 'rawOre'),
            native_resource('crushed', 'crushed'), native_resource('other', 'crushed', 'Tin'),
            native_resource('dynamic', 'crushed')], processes=recipes, sources=[native_mining(), generation])
        with dataset._connect() as conn:
            facts = summarize_acquisition(conn, ['crushed', 'other', 'dynamic'], snapshot_id=dataset.snapshot_id)['resources']
        for fact in facts.values():
            self.assertEqual(fact['provenance']['initial_processing']['status'], 'no_bounded_evidence')

    def test_initial_processing_stops_before_four_steps_and_rejects_byproducts_nbt_and_extra_solids(self):
        recipes = [native_process('crush', 'raw', 'crushed'),
                   native_process('wash', 'crushed', 'purified', 'orewasher'),
                   native_process('grind', 'purified', 'pure'),
                   native_process('clean', 'pure', 'dust', 'centrifuge'),
                   native_process('tagged', 'tagged_raw', 'tagged_crushed'),
                   native_process('compound', 'raw', 'compound_crushed'),
                   native_process('byproduct', 'raw', 'crushed')]
        recipes[-2]['inputs'].append(slot(choice('extra')))
        recipes[-1]['outputs'].append({'resource_id': 'byproduct', 'amount': 1, 'chance': {'numerator': 1, 'denominator': 1}})
        tagged_source = native_mining('tagged_raw')
        tagged_source['id'] = 'tagged_mining'
        dataset = self.dataset(resources=[native_resource(id, prefix) for id, prefix in (
            ('raw', 'rawOre'), ('crushed', 'crushed'), ('purified', 'crushedPurified'), ('pure', 'dustPure'),
            ('dust', 'dust'), ('tagged_crushed', 'crushed'), ('compound_crushed', 'crushed'), ('byproduct', 'crushed'))]
            + [resource('extra'), native_resource('tagged_raw', 'rawOre', nbt={'type': 'compound', 'value': {}})],
            processes=recipes, sources=[native_mining(), tagged_source])
        with dataset._connect() as conn:
            facts = summarize_acquisition(conn, ['dust', 'tagged_crushed', 'compound_crushed', 'byproduct'],
                snapshot_id=dataset.snapshot_id)['resources']
        for fact in facts.values():
            self.assertEqual(fact['provenance']['initial_processing']['status'], 'no_bounded_evidence')

    def test_initial_processing_uses_source_backed_native_group_choice_without_relabeling_output_variants(self):
        recipe = native_process('crush', 'representative', 'crushed')
        recipe['inputs'] = [slot(choice('representative', 'unified', group='native:ore'))]
        dataset = self.dataset(resources=[native_resource(id, prefix) for id, prefix in (
            ('raw', 'rawOre'), ('representative', 'rawOre'), ('crushed', 'crushed'), ('legacy_crushed', 'crushed'))],
            processes=[recipe], sources=[native_mining()], groups=[
                {'id': 'native:ore', 'kind': 'unified', 'name': 'representative', 'members': ['representative', 'raw'], 'provenance': {}},
                {'id': 'native:crushed', 'kind': 'unified', 'name': 'crushed', 'members': ['crushed', 'legacy_crushed'], 'provenance': {}}])
        with dataset._connect() as conn:
            facts = summarize_acquisition(conn, ['crushed', 'legacy_crushed'], snapshot_id=dataset.snapshot_id)['resources']
        self.assertEqual(facts['crushed']['provenance']['initial_processing']['status'], 'inferred')
        self.assertEqual(facts['crushed']['provenance']['initial_processing']['evidence'][0]['source_resource_id'], 'raw')
        self.assertEqual(facts['legacy_crushed']['provenance']['initial_processing']['status'], 'no_bounded_evidence')

    def test_unresolved_output_template_cannot_ground_a_resource(self):
        p = process('dynamic', [slot(choice('seed'))], ['template'], conditions={'dynamic_output': 'unresolved'})
        result = analyze_grounding([variant(p)], [], ['seed'], True)
        self.assertNotIn('template', result['reachable_resource_ids'])
        self.assertEqual(result['resources']['template']['status'], 'incomplete')


if __name__ == '__main__':
    unittest.main()
