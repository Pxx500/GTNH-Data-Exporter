import unittest
import tempfile
from pathlib import Path

from gtnh_data import Dataset
from gtnh_data.acquisition import acquisition_rank, analyze_grounding, summarize_acquisition, unification_preferences
from .artifacts import choice, process, resource, slot, snapshot


def variant(record):
    return {'process': record, 'selections': {str(i): {'choice_index': 0, 'resource_id': s['choices'][0]['resource_id']}
                                            for i, s in enumerate(record['inputs'])}}


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

    def test_selected_or_variant_does_not_require_unselected_choices(self):
        p = process('or', [slot(choice('seed'), choice('missing'))], ['result'])
        grounded = analyze_grounding([variant(p)], [], ['seed'], True)
        self.assertEqual(grounded['resources']['result']['status'], 'structural_reachable')
        incomplete = analyze_grounding([variant(p)], [], [], False, limit_reasons=['candidate_depth'])
        self.assertEqual(incomplete['resources']['result']['status'], 'incomplete')
        self.assertFalse(incomplete['execution_proven'])

    def test_unresolved_output_template_cannot_ground_a_resource(self):
        p = process('dynamic', [slot(choice('seed'))], ['template'], conditions={'dynamic_output': 'unresolved'})
        result = analyze_grounding([variant(p)], [], ['seed'], True)
        self.assertNotIn('template', result['reachable_resource_ids'])
        self.assertEqual(result['resources']['template']['status'], 'incomplete')


if __name__ == '__main__':
    unittest.main()
