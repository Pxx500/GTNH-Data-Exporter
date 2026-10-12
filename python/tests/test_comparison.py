import gzip
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from .artifacts import choice, process, resource, slot, snapshot


module_path = Path(__file__).resolve().parents[2] / 'scripts' / 'compare_nei.py'
spec = importlib.util.spec_from_file_location('compare_nei', module_path)
comparison = importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparison)


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def replace_records(self, directory, name, records, manifest_name):
        path = directory / name
        with gzip.open(path, 'wt', encoding='utf-8') as stream:
            for record in records:
                stream.write(json.dumps(record) + '\n')
        manifest_path = directory / manifest_name
        manifest = json.loads(manifest_path.read_text())
        manifest['files'][name] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'records': len(records)}
        manifest_path.write_text(json.dumps(manifest))
        if manifest_name == 'manifest.json' and (directory / 'nei-reference/presentation-context.json').exists():
            reference = directory / 'nei-reference'
            context_path = reference / 'presentation-context.json'
            context = json.loads(context_path.read_text())
            context['canonical_files'] = {name: manifest['files'][name] for name in ('resources.jsonl.gz', 'processes.jsonl.gz')}
            context_path.write_text(json.dumps(context))
            self.bind_context_pointer(reference)

    def bind_context_pointer(self, reference):
        summary_path = reference / 'summary.json'
        summary = json.loads(summary_path.read_text())
        summary['files']['presentation-context.json'] = {'sha256': hashlib.sha256((reference / 'presentation-context.json').read_bytes()).hexdigest()}
        summary_path.write_text(json.dumps(summary))

    def context(self, directory, reference, *, aliases=None, pools=None, complete=True, failures=None):
        manifest = json.loads((directory / 'manifest.json').read_text())
        metadata = {'schema_version': 1, 'canonical_snapshot_id': manifest['snapshot_id'],
                    'canonical_pack': manifest['pack'],
                    'canonical_files': {name: manifest['files'][name] for name in ('resources.jsonl.gz', 'processes.jsonl.gz')},
                    'scope': {'gt_families': sorted(comparison.GT_FAMILIES), 'furnace_family': 'minecraft:smelting',
                              'alias_template_amount': 1},
                    'readiness': {'start': {}, 'end': {}}, 'complete': complete, 'failures': failures or [], 'files': {}}
        (reference / 'presentation-context.json').write_text(json.dumps(metadata))
        for name, records in [('gt-display-aliases.jsonl.gz', aliases or []), ('item-pools.jsonl.gz', pools or [])]:
            self.replace_records(reference, name, records, 'presentation-context.json')
        summary_path = reference / 'summary.json'
        summary = json.loads(summary_path.read_text())
        summary['files']['presentation-context.json'] = {'sha256': hashlib.sha256((reference / 'presentation-context.json').read_bytes()).hexdigest()}
        summary_path.write_text(json.dumps(summary))

    def typed(self, name, *, metadata=0, nbt=None, amount=1):
        return {'registry_name': name, 'metadata': metadata, 'nbt': nbt, 'amount': amount}

    def read_records(self, directory, name):
        with gzip.open(directory / name, 'rt', encoding='utf-8') as stream:
            return [json.loads(line) for line in stream]

    def capture(self, *, amount=2, chance=5000, alternatives=None, resources=None):
        resources = resources or [resource('in', registry_name='test:input'), resource('alt', registry_name='test:alternative'), resource('out', registry_name='test:output')]
        canonical = process('p', [slot(choice('in', 'unified', group='g', amount=2))], ['out'], family='gregtech:gt.recipe.alloysmelter')
        canonical['outputs'][0]['chance'] = {'numerator': 1, 'denominator': 2}
        canonical['inputs'][0]['consumption_chance'] = {'numerator': 1, 'denominator': 1}
        canonical['inputs'][0]['choices'][0]['native_amount'] = 2
        canonical['conditions']['hidden'] = False
        members = ['in', 'alt'] if alternatives is not None else ['in']
        directory = snapshot(self.root / 'snapshot', resources=resources, groups=[{'id': 'g', 'kind': 'unified', 'name': 'g', 'members': members, 'provenance': {}}], processes=[canonical])
        manifest_path = directory / 'manifest.json'
        manifest = json.loads(manifest_path.read_text())
        manifest['pack'] = {'mods': [
            {'id': 'NotEnoughItems', 'version': '2.8.159-GTNH', 'sha256': '050b2440952adc930e871586f496607959344aa2d7c3be781fd922a5b253a3af'},
            {'id': 'gregtech', 'version': '5.09.54.221', 'sha256': '60ceb229cd894dd28393efb6d0013de2835289eeef6fcf84ad3e17a6475baf5b'}], 'config_script_digests': {}}
        manifest_path.write_text(json.dumps(manifest))
        stack = {'strId': 'test:input', 'Count': amount, 'Damage': 0}
        if resources[0]['nbt']:
            stack['tag'] = {'v': '1B'}
        positioned = lambda stacks, probability: {'x': 1, 'y': 1, 'chance': probability, 'native_class': 'gregtech.nei.GTNEIDefaultHandler$FixedPositionedStack', 'real_stack_size': stacks[0]['Count'], 'alternatives': [{'native_stack': value, 'failure': None} for value in stacks]}
        view = {'handler_key': 'h0', 'recipe_index': 0, 'ingredients': [positioned(alternatives or [stack], 10000)], 'result': None,
                'other_stacks': [positioned([{'strId': 'test:output', 'Count': 1, 'Damage': 0}], chance)], 'failure': None,
                'displayed_fields': {'render_real_stack_sizes': True, 'unificate_output': False, 'frontend_class': 'gregtech.api.recipe.RecipeMapFrontend'}}
        handler = {'handler_key': 'h0', 'native_class': 'gregtech.nei.GTNEIDefaultHandler', 'handler_id': 'test', 'handler_name': 'test',
                   'gt_recipe_map_id': canonical['family'], 'enumeration_status': 'ok', 'recipe_count': 1, 'failure': None}
        reference = directory / 'nei-reference'
        reference.mkdir()
        files = {}
        for name, records in [('handlers', [handler]), ('handler-views', [view]), ('signatures', [{'handler_key': 'h0', 'recipe_index': 0, 'projection': 'native_recipe_id_api', 'signature': {}, 'failure': None}])]:
            path = reference / f'{name}.jsonl.gz'
            with gzip.open(path, 'wt', encoding='utf-8') as stream:
                for record in records:
                    stream.write(json.dumps(record) + '\n')
            files[path.name] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'records': len(records)}
        summary = {'schema_version': 1, 'canonical_snapshot_id': manifest['snapshot_id'], 'canonical_pack': manifest['pack'], 'files': files,
                   'counts': {'handlers': 1, 'signatures': 1, 'handler_views': 1}, 'complete': True,
                   'failed_handlers': 0, 'failed_signatures': 0, 'failed_views': 0, 'failed_stacks': 0}
        (reference / 'summary.json').write_text(json.dumps(summary))
        aliases = []
        for value in resources:
            stacks = [self.typed(value['registry_name'], metadata=value['metadata'], nbt=value['nbt'])]
            if value['id'] == 'in' and alternatives is not None:
                stacks.append(self.typed(resources[1]['registry_name'], metadata=resources[1]['metadata'], nbt=resources[1]['nbt']))
            aliases.append({'resource_id': value['id'], 'status': 'ok', 'alternatives': stacks, 'failure': None})
        self.context(directory, reference, aliases=aliases)
        return directory, reference

    def test_context_expands_aliases_before_wildcards_and_uses_pool_nbt_and_first_choice_amount(self):
        original_nbt = {'type': 'compound', 'value': {'source': {'type': 'int', 'value': 1}}}
        pool_nbt = {'type': 'compound', 'value': {'pool': {'type': 'int', 'value': 2}}}
        resources = [resource('in', registry_name='test:input', metadata=32767, nbt=original_nbt),
                     resource('alt', registry_name='test:declared'), resource('out', registry_name='test:output')]
        directory, reference = self.capture(resources=resources)
        canonical = self.read_records(directory, 'processes.jsonl.gz')[0]
        canonical['inputs'][0]['choices'] = [dict(choice('in', 'ore_dict', group='g', amount=2), native_amount=2),
                                            dict(choice('alt', amount=7), native_amount=7)]
        self.replace_records(directory, 'processes.jsonl.gz', [canonical], 'manifest.json')
        self.context(directory, reference, aliases=[
            {'resource_id': 'in', 'status': 'ok', 'alternatives': [self.typed('test:input', metadata=32767, nbt=original_nbt),
                                                                 self.typed('test:alias')], 'failure': None},
            {'resource_id': 'alt', 'status': 'ok', 'alternatives': [self.typed('test:declared')], 'failure': None}],
            pools=[{'registry_name': 'test:input', 'status': 'ok',
                    'entries': [self.typed('test:input', metadata=4, nbt=pool_nbt, amount=99)], 'failure': None}])
        view = self.read_records(reference, 'handler-views.jsonl.gz')[0]
        view['ingredients'][0]['real_stack_size'] = 2
        view['ingredients'][0]['alternatives'] = [{'native_stack': stack, 'failure': None} for stack in [
            {'strId': 'test:input', 'Damage': 4, 'Count': 2, 'tag': {'pool': 2}},
            {'strId': 'test:alias', 'Damage': 0, 'Count': 2},
            {'strId': 'test:declared', 'Damage': 0, 'Count': 7}]]
        self.replace_records(reference, 'handler-views.jsonl.gz', [view], 'summary.json')
        report = comparison.compare(directory, reference)
        self.assertEqual(report['counts']['matched'], 1)
        self.assertEqual(report['counts']['differences'], 0)
        self.assertEqual(report['counts']['unsupported'], 0)
        self.assertTrue(report['presentation_context']['complete'])

    def test_partial_context_uses_successful_entries_and_marks_failed_dependencies_unsupported(self):
        directory, reference = self.capture()
        failure = {'phase': 'alias', 'message': 'native lookup failed'}
        self.context(directory, reference, aliases=[
            {'resource_id': 'in', 'status': 'ok', 'alternatives': [self.typed('test:input')], 'failure': None},
            {'resource_id': 'alt', 'status': 'failed', 'alternatives': [], 'failure': failure}], complete=False,
            failures=[{'process_id': 'unrelated', 'native_slot': 0, 'native_item': {'status': 'unregistered'}}])
        report = comparison.compare(directory, reference)
        self.assertEqual(report['counts']['matched'], 1)
        self.assertFalse(report['presentation_context']['complete'])
        self.assertEqual(report['presentation_context']['failure_count'], 2)
        self.assertEqual(comparison.main([str(directory), '--report', str(self.root / 'partial.json')]), 1)
        self.context(directory, reference, aliases=[
            {'resource_id': 'in', 'status': 'failed', 'alternatives': [], 'failure': failure}], complete=False)
        report = comparison.compare(directory, reference)
        self.assertEqual(report['counts']['matched'], 0)
        self.assertEqual(report['counts']['missing_canonical'], 0)
        self.assertTrue(any('alias context is failed for in' in reason for reason in report['unsupported_reasons']))
        cases = [case for case in report['examples']['unsupported'] if case.get('side') == 'nei']
        self.assertEqual([(case['handler_key'], case['recipe_index']) for case in cases], [('h0', 0)])

    def test_empty_pool_keeps_original_nbt_and_uses_metadata_zero(self):
        nbt = {'type': 'compound', 'value': {'v': {'type': 'int', 'value': 6}}}
        directory, reference = self.capture(resources=[resource('in', registry_name='test:input', metadata=32767, nbt=nbt),
                                                       resource('alt'), resource('out', registry_name='test:output')])
        self.context(directory, reference, aliases=[{'resource_id': 'in', 'status': 'ok',
                     'alternatives': [self.typed('test:input', metadata=32767, nbt=nbt)], 'failure': None}],
                     pools=[{'registry_name': 'test:input', 'status': 'empty', 'entries': [], 'failure': None}])
        view = self.read_records(reference, 'handler-views.jsonl.gz')[0]
        view['ingredients'][0]['alternatives'][0]['native_stack'] = {'strId': 'test:input', 'Damage': 0, 'Count': 2, 'tag': {'v': 6}}
        self.replace_records(reference, 'handler-views.jsonl.gz', [view], 'summary.json')
        self.assertEqual(comparison.compare(directory, reference)['counts']['matched'], 1)

    def test_normalized_gt_quantities_keep_the_first_declared_representative(self):
        directory, reference = self.capture()
        canonical = self.read_records(directory, 'processes.jsonl.gz')[0]
        canonical['inputs'][0]['choices'].append(dict(choice('alt', amount=7), native_amount=7))
        self.replace_records(directory, 'processes.jsonl.gz', [canonical], 'manifest.json')
        view = self.read_records(reference, 'handler-views.jsonl.gz')[0]
        view['displayed_fields']['render_real_stack_sizes'] = False
        view['ingredients'][0]['real_stack_size'] = 2
        view['ingredients'][0]['alternatives'] = [{'native_stack': {'strId': name, 'Damage': 0, 'Count': 1}, 'failure': None}
                                                   for name in ('test:input', 'test:alternative')]
        self.replace_records(reference, 'handler-views.jsonl.gz', [view], 'summary.json')
        report = comparison.compare(directory, reference)
        self.assertEqual(report['counts']['matched'], 1)
        canonical['inputs'][0]['choices'].reverse()
        self.replace_records(directory, 'processes.jsonl.gz', [canonical], 'manifest.json')
        report = comparison.compare(directory, reference)
        self.assertEqual(report['counts']['differences'], 1)
        self.assertEqual(report['examples']['differences'][0]['fields'], ['amounts'])

    def test_unified_output_alias_templates_keep_recipe_quantities_after_wildcard_expansion(self):
        directory, reference = self.capture()
        canonical = self.read_records(directory, 'processes.jsonl.gz')[0]
        canonical['outputs'][0]['amount'] = 5
        self.replace_records(directory, 'processes.jsonl.gz', [canonical], 'manifest.json')
        self.context(directory, reference, aliases=[
            {'resource_id': 'in', 'status': 'ok', 'alternatives': [self.typed('test:input')], 'failure': None},
            {'resource_id': 'out', 'status': 'ok', 'alternatives': [self.typed('test:output'),
                    self.typed('test:output_alias', metadata=32767)], 'failure': None}],
            pools=[{'registry_name': 'test:output_alias', 'status': 'ok',
                    'entries': [self.typed('test:output_alias', metadata=8, amount=64)], 'failure': None}])
        view = self.read_records(reference, 'handler-views.jsonl.gz')[0]
        view['displayed_fields']['unificate_output'] = True
        view['other_stacks'][0]['real_stack_size'] = 5
        view['other_stacks'][0]['alternatives'] = [{'native_stack': stack, 'failure': None} for stack in [
            {'strId': 'test:output', 'Damage': 0, 'Count': 5}, {'strId': 'test:output_alias', 'Damage': 8, 'Count': 5}]]
        self.replace_records(reference, 'handler-views.jsonl.gz', [view], 'summary.json')
        self.assertEqual(comparison.compare(directory, reference)['counts']['matched'], 1)

    def test_furnace_wildcard_pool_keeps_output_amount_and_normalizes_every_input_alternative(self):
        directory, reference = self.capture(resources=[resource('in', registry_name='test:input', metadata=32767),
                                                       resource('alt'), resource('out', registry_name='test:output')])
        canonical = self.read_records(directory, 'processes.jsonl.gz')[0]
        canonical['family'] = 'minecraft:smelting'
        canonical['inputs'][0]['choices'][0]['match'] = {'mode': 'wildcard'}
        canonical['outputs'][0]['amount'] = 9
        self.replace_records(directory, 'processes.jsonl.gz', [canonical], 'manifest.json')
        self.context(directory, reference, pools=[{'registry_name': 'test:input', 'status': 'ok',
                     'entries': [self.typed('test:input', metadata=3, amount=32), self.typed('test:input', metadata=4, amount=64)],
                     'failure': None}])
        handler = self.read_records(reference, 'handlers.jsonl.gz')[0]
        handler['native_class'] = comparison.FURNACE_HANDLER
        handler['gt_recipe_map_id'] = None
        self.replace_records(reference, 'handlers.jsonl.gz', [handler], 'summary.json')
        view = self.read_records(reference, 'handler-views.jsonl.gz')[0]
        view['ingredients'][0]['alternatives'] = [{'native_stack': {'strId': 'test:input', 'Damage': meta, 'Count': 1}, 'failure': None}
                                                   for meta in (3, 4)]
        view['result'] = view['other_stacks'][0]
        view['result']['alternatives'][0]['native_stack']['Count'] = 9
        view['other_stacks'] = []
        self.replace_records(reference, 'handler-views.jsonl.gz', [view], 'summary.json')
        self.assertEqual(comparison.compare(directory, reference)['counts']['matched'], 1)

    def test_context_binding_and_each_checksum_and_count_are_required(self):
        directory, reference = self.capture()
        context_path = reference / 'presentation-context.json'
        original = json.loads(context_path.read_text())
        for field, value in [('schema_version', 2), ('canonical_snapshot_id', 'other'), ('canonical_pack', {}),
                             ('canonical_files', {})]:
            with self.subTest(field=field):
                context = dict(original, **{field: value})
                context_path.write_text(json.dumps(context))
                self.bind_context_pointer(reference)
                with self.assertRaises(comparison.ComparisonError):
                    comparison.compare(directory, reference)
        context_path.write_text(json.dumps(original))
        self.bind_context_pointer(reference)
        context_path.write_text(context_path.read_text() + ' ')
        with self.assertRaisesRegex(comparison.ComparisonError, 'presentation-context.json: checksum'):
            comparison.compare(directory, reference)
        context_path.write_text(json.dumps(original))
        self.bind_context_pointer(reference)
        for name in ('gt-display-aliases.jsonl.gz', 'item-pools.jsonl.gz'):
            with self.subTest(stream=name):
                path = reference / name
                captured = path.read_bytes()
                path.write_bytes(b'changed')
                with self.assertRaisesRegex(comparison.ComparisonError, name + ': checksum'):
                    comparison.compare(directory, reference)
                path.write_bytes(captured)
                context = json.loads(json.dumps(original))
                context['files'][name]['records'] += 1
                context_path.write_text(json.dumps(context))
                self.bind_context_pointer(reference)
                with self.assertRaisesRegex(comparison.ComparisonError, name + ': record count'):
                    comparison.compare(directory, reference)
                context_path.write_text(json.dumps(original))
                self.bind_context_pointer(reference)

    def test_context_anchor_ids_are_nonnull_and_unique_and_pools_are_unique(self):
        directory, reference = self.capture()
        alias = {'resource_id': 'in', 'status': 'ok', 'alternatives': [self.typed('test:input')], 'failure': None}
        pool = {'registry_name': 'test:input', 'status': 'empty', 'entries': [], 'failure': None}
        for aliases, pools in [([dict(alias, resource_id=None)], []), ([alias, alias], []), ([alias], [pool, pool])]:
            with self.subTest(aliases=aliases, pools=pools):
                self.context(directory, reference, aliases=aliases, pools=pools)
                with self.assertRaisesRegex(comparison.ComparisonError, 'null, invalid or duplicate'):
                    comparison.compare(directory, reference)

    def test_missing_context_never_uses_matching_groups_as_display_aliases(self):
        directory, reference = self.capture()
        summary_path = reference / 'summary.json'
        summary = json.loads(summary_path.read_text())
        del summary['files']['presentation-context.json']
        summary_path.write_text(json.dumps(summary))
        report = comparison.compare(directory, reference)
        self.assertEqual(report['counts']['matched'], 0)
        self.assertEqual(report['counts']['missing_canonical'], 0)
        self.assertTrue(any('alias context was not captured' in reason for reason in report['unsupported_reasons']))
        self.assertFalse(report['presentation_context']['available'])
        # Historical static furnace projection remains independently established.
        canonical = self.read_records(directory, 'processes.jsonl.gz')[0]
        canonical['family'] = 'minecraft:smelting'
        canonical['outputs'][0]['chance'] = {'numerator': 1, 'denominator': 1}
        self.replace_records(directory, 'processes.jsonl.gz', [canonical], 'manifest.json')
        handler = self.read_records(reference, 'handlers.jsonl.gz')[0]
        handler['native_class'] = comparison.FURNACE_HANDLER
        handler['gt_recipe_map_id'] = None
        self.replace_records(reference, 'handlers.jsonl.gz', [handler], 'summary.json')
        summary = json.loads(summary_path.read_text())
        summary['files'].pop('presentation-context.json', None)
        summary_path.write_text(json.dumps(summary))
        view = self.read_records(reference, 'handler-views.jsonl.gz')[0]
        view['ingredients'][0]['alternatives'][0]['native_stack']['Count'] = 1
        view['result'] = view['other_stacks'][0]
        view['other_stacks'] = []
        self.replace_records(reference, 'handler-views.jsonl.gz', [view], 'summary.json')
        self.assertEqual(comparison.compare(directory, reference)['counts']['matched'], 1)

    def test_failed_output_alias_dependency_is_unsupported_rather_than_a_missing_recipe(self):
        directory, reference = self.capture()
        self.context(directory, reference, aliases=[
            {'resource_id': 'in', 'status': 'ok', 'alternatives': [self.typed('test:input')], 'failure': None},
            {'resource_id': 'out', 'status': 'failed', 'alternatives': [], 'failure': {'message': 'native output alias failure'}}],
            complete=False)
        view = self.read_records(reference, 'handler-views.jsonl.gz')[0]
        view['displayed_fields']['unificate_output'] = True
        self.replace_records(reference, 'handler-views.jsonl.gz', [view], 'summary.json')
        report = comparison.compare(directory, reference)
        self.assertEqual(report['counts']['missing_canonical'], 0)
        self.assertEqual(report['counts']['matched'], 0)
        self.assertTrue(any('alias context is failed for out' in reason for reason in report['unsupported_reasons']))
        cases = [case for case in report['examples']['unsupported'] if case.get('side') == 'nei']
        self.assertEqual(cases[0]['canonical_process_ids'], ['p'])

    def test_pool_failure_and_missing_pool_do_not_become_empty_pool_behavior(self):
        directory, reference = self.capture(resources=[resource('in', registry_name='test:input', metadata=32767),
                                                       resource('alt'), resource('out', registry_name='test:output')])
        aliases = [{'resource_id': 'in', 'status': 'ok', 'alternatives': [self.typed('test:input', metadata=32767)], 'failure': None}]
        for pools, complete, reason in [([], True, 'item pool is missing'),
                ([{'registry_name': 'test:input', 'status': 'failed', 'entries': [], 'failure': {'message': 'native failure'}}], False, 'item pool failed')]:
            with self.subTest(reason=reason):
                self.context(directory, reference, aliases=aliases, pools=pools, complete=complete)
                report = comparison.compare(directory, reference)
                self.assertEqual(report['counts']['matched'], 0)
                self.assertTrue(any(reason in item for item in report['unsupported_reasons']))

    def test_context_typed_nbt_collisions_are_ambiguous_even_without_a_canonical_variant(self):
        byte = {'type': 'compound', 'value': {'v': {'type': 'byte', 'value': 1}}}
        string = {'type': 'compound', 'value': {'v': {'type': 'string', 'value': '1B'}}}
        directory, reference = self.capture(resources=[resource('in', registry_name='test:input', nbt=byte),
                                                       resource('alt'), resource('out', registry_name='test:output')])
        self.context(directory, reference, aliases=[{'resource_id': 'in', 'status': 'ok',
                     'alternatives': [self.typed('test:input', nbt=byte), self.typed('test:input', nbt=string)], 'failure': None}])
        report = comparison.compare(directory, reference)
        self.assertEqual(report['counts']['matched'], 0)
        self.assertEqual(report['ambiguous_resource_projections'], 1)
        self.assertTrue(any('Ambiguous identity' in reason for reason in report['unsupported_reasons']))

    def test_quantity_discrepancy_is_reported_independently_from_canonical_data(self):
        directory, reference = self.capture(amount=3)
        report = comparison.compare(directory, reference)
        self.assertEqual(report['counts']['differences'], 1)
        self.assertIn('amounts', report['examples']['differences'][0]['fields'])

    def test_furnace_normalizes_only_input_count_and_keeps_result_quantity(self):
        directory, reference = self.capture()
        process = self.read_records(directory, 'processes.jsonl.gz')[0]
        process['family'] = 'minecraft:smelting'
        process['inputs'][0]['choices'][0]['match'] = {'mode': 'exact'}
        process['outputs'][0]['amount'] = 9
        process['outputs'][0]['chance'] = {'numerator': 1, 'denominator': 1}
        self.replace_records(directory, 'processes.jsonl.gz', [process], 'manifest.json')
        handler = self.read_records(reference, 'handlers.jsonl.gz')[0]
        handler['native_class'] = 'codechicken.nei.recipe.FurnaceRecipeHandler'
        handler['gt_recipe_map_id'] = None
        self.replace_records(reference, 'handlers.jsonl.gz', [handler], 'summary.json')
        view = self.read_records(reference, 'handler-views.jsonl.gz')[0]
        view['ingredients'][0]['alternatives'][0]['native_stack']['Count'] = 1
        view['result'] = view['other_stacks'][0]
        view['result']['alternatives'][0]['native_stack']['Count'] = 9
        view['other_stacks'] = [{'alternatives': [{'native_stack': {'strId': 'minecraft:coal', 'Count': 1, 'Damage': 0}, 'failure': None}]}]
        self.replace_records(reference, 'handler-views.jsonl.gz', [view], 'summary.json')
        report = comparison.compare(directory, reference)
        self.assertEqual(report['counts']['matched'], 1)
        self.assertEqual(report['counts']['differences'], 0)
        self.assertEqual(report['counts']['missing_canonical'], 0)

    def test_chance_and_alternative_discrepancies_keep_their_specific_fields(self):
        directory, reference = self.capture(chance=10000)
        report = comparison.compare(directory, reference)
        self.assertEqual(report['counts']['differences'], 1)
        self.assertEqual(report['examples']['differences'][0]['fields'], ['chances'])
        with tempfile.TemporaryDirectory() as second:
            self.root = Path(second)
            directory, reference = self.capture(alternatives=[{'strId': 'test:input', 'Count': 2, 'Damage': 0}])
            report = comparison.compare(directory, reference)
            self.assertEqual(report['counts']['differences'], 1)
            self.assertEqual(report['examples']['differences'][0]['fields'], ['alternatives'])

    def test_typed_nbt_projection_collision_is_unverified_not_an_identity_match(self):
        byte = {'type': 'compound', 'value': {'v': {'type': 'byte', 'value': 1}}}
        string = {'type': 'compound', 'value': {'v': {'type': 'string', 'value': '1B'}}}
        resources = [resource('in', registry_name='test:input', nbt=byte), resource('alt', registry_name='test:input', nbt=string), resource('out', registry_name='test:output')]
        directory, reference = self.capture(resources=resources)
        report = comparison.compare(directory, reference)
        self.assertEqual(report['counts']['matched'], 0)
        self.assertGreater(report['counts']['unsupported'], 0)
        self.assertEqual(report['ambiguous_resource_projections'], 1)
        self.assertTrue(any('Ambiguous identity' in reason for reason in report['unsupported_reasons']))

    def test_streamed_unmapped_records_still_count_all_capture_failure_events(self):
        directory, reference = self.capture()
        handlers = self.read_records(reference, 'handlers.jsonl.gz')
        handlers.append(dict(handlers[0], handler_key='h1', native_class='unmapped.Handler', gt_recipe_map_id=None))
        views = self.read_records(reference, 'handler-views.jsonl.gz')
        failure = {'phase': 'stack', 'class': 'IllegalArgumentException', 'message': 'unsupported stack'}
        views.append(dict(views[0], handler_key='h1', ingredients=[{'alternatives': [{'native_stack': None, 'failure': failure}]}]))
        signatures = self.read_records(reference, 'signatures.jsonl.gz')
        signatures.append(dict(signatures[0], handler_key='h1', signature=None, failure=failure))
        for name, records in (('handlers.jsonl.gz', handlers), ('handler-views.jsonl.gz', views), ('signatures.jsonl.gz', signatures)):
            self.replace_records(reference, name, records, 'summary.json')
        summary_path = reference / 'summary.json'
        summary = json.loads(summary_path.read_text())
        summary['counts'] = {'handlers': 2, 'handler_views': 2, 'signatures': 2}
        summary_path.write_text(json.dumps(summary))
        report = comparison.compare(directory, reference)
        self.assertEqual(report['counts']['matched'], 1)
        self.assertEqual(report['counts']['reference_views'], 2)
        self.assertEqual(report['counts']['unsupported'], 1)
        self.assertEqual(report['capture_failures'], 2)
        self.assertEqual(report['capture_failure_unit'], 'events, not distinct affected recipes')

    def test_binding_hashes_and_threshold_exit_are_public_contracts(self):
        directory, reference = self.capture()
        report = comparison.compare(directory, reference)
        self.assertEqual(report['counts']['matched'], 1)
        output = self.root / 'report.json'
        self.assertEqual(comparison.main([str(directory), '--report', str(output)]), 0)
        self.assertTrue(json.loads(output.read_text())['thresholds']['passed'])
        (reference / 'handler-views.jsonl.gz').write_bytes(b'changed')
        with self.assertRaisesRegex(comparison.ComparisonError, 'checksum'):
            comparison.compare(directory, reference)
        self.assertEqual(comparison.main([str(directory), '--report', str(output)]), 2)
        self.assertEqual(json.loads(output.read_text())['status'], 'invalid_reference_or_canonical_artifact')


if __name__ == '__main__':
    unittest.main()
