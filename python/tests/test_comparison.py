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

    def context(self, directory, reference, *, aliases=None, pools=None, complete=True, failures=None, projections=None, projection_version=2):
        manifest = json.loads((directory / 'manifest.json').read_text())
        metadata = {'schema_version': projection_version if projections is not None else 1, 'canonical_snapshot_id': manifest['snapshot_id'],
                    'canonical_pack': manifest['pack'],
                    'canonical_files': {name: manifest['files'][name] for name in ('resources.jsonl.gz', 'processes.jsonl.gz')},
                    'scope': {'gt_families': sorted(comparison.GT_FAMILIES), 'furnace_family': 'minecraft:smelting',
                              'alias_template_amount': 1},
                    'readiness': {'start': {}, 'end': {}}, 'complete': complete, 'failures': failures or [], 'files': {}}
        (reference / 'presentation-context.json').write_text(json.dumps(metadata))
        for name, records in [('gt-display-aliases.jsonl.gz', aliases or []), ('item-pools.jsonl.gz', pools or [])]:
            self.replace_records(reference, name, records, 'presentation-context.json')
        if projections is not None:
            metadata = json.loads((reference / 'presentation-context.json').read_text())
            metadata['item_projection'] = {'api': 'StackInfo.itemStackToNBT(stack,true)->NBTJson.toJsonObject',
                'template_item_amount': 1, 'classification': 'pinned_builtin_default_item_count',
                'serializer_classes': ['codechicken.nei.recipe.stackinfo.DefaultStackStringifyHandler',
                    'codechicken.nei.recipe.stackinfo.FluidDisplayStackStringifyHandler', 'codechicken.nei.recipe.stackinfo.GTFluidStackStringifyHandler']}
            if projection_version == 3:
                metadata['scope']['supplementary_families'] = ['botania:mana_infusion']
                metadata['item_projection']['api'] = 'StackInfo.stackStringifyHandlers.reverse.convertItemStackToNBT(stack,true)->NBTJson.toJsonObject'
                metadata['item_projection']['classification'] = 'selected_pinned_default_item_count'
            (reference / 'presentation-context.json').write_text(json.dumps(metadata))
            self.replace_records(reference, 'item-projections.jsonl.gz', projections, 'presentation-context.json')
        summary_path = reference / 'summary.json'
        summary = json.loads(summary_path.read_text())
        summary['files']['presentation-context.json'] = {'sha256': hashlib.sha256((reference / 'presentation-context.json').read_bytes()).hexdigest()}
        summary_path.write_text(json.dumps(summary))

    def typed(self, name, *, metadata=0, nbt=None, amount=1):
        return {'registry_name': name, 'metadata': metadata, 'nbt': nbt, 'amount': amount}

    def item_projection(self, name, *, nbt=None, native_tag=None, metadata=0):
        stack = {'strId': name, 'Damage': metadata, 'Count': 1}
        if native_tag is not None:
            stack['tag'] = native_tag
        return {'registry_name': name, 'metadata': metadata, 'nbt': nbt, 'status': 'ok', 'native_stack': stack,
                'serializer_class': 'codechicken.nei.recipe.stackinfo.DefaultStackStringifyHandler', 'count_semantics': 'item_stack_size', 'failure': None}

    def native_item_capture(self):
        charge = {'type': 'compound', 'value': {'charge': {'type': 'double', 'value': 10000000}}}
        directory, reference = self.capture(resources=[resource('in', registry_name='test:input', nbt=charge), resource('alt'), resource('out', registry_name='test:output')])
        canonical = self.read_records(directory, 'processes.jsonl.gz')[0]
        canonical['outputs'][0]['amount'] = 30
        self.replace_records(directory, 'processes.jsonl.gz', [canonical], 'manifest.json')
        view = self.read_records(reference, 'handler-views.jsonl.gz')[0]
        view['ingredients'][0]['alternatives'][0]['native_stack']['tag'] = {'charge': '1.0E7D'}
        view['other_stacks'][0]['real_stack_size'] = 30
        view['other_stacks'][0]['alternatives'][0]['native_stack']['Count'] = 30
        self.replace_records(reference, 'handler-views.jsonl.gz', [view], 'summary.json')
        aliases = self.read_records(reference, 'gt-display-aliases.jsonl.gz')
        projections = [self.item_projection('test:input', nbt=charge, native_tag={'charge': '1.0E7D'}), self.item_projection('test:output')]
        self.context(directory, reference, aliases=aliases, projections=projections)
        return directory, reference, aliases, projections

    def lossless_views(self, directory, reference, facts):
        views = self.read_records(reference, 'handler-views.jsonl.gz')
        for view in views:
            positioned = view['ingredients'] + view['other_stacks'] + ([view['result']] if view['result'] else [])
            for stack, item in zip((alternative for value in positioned for alternative in value['alternatives']), facts):
                stack.update(item_facts=item, item_facts_failure=None, serializer_class='codechicken.nei.recipe.stackinfo.DefaultStackStringifyHandler',
                             count_semantics='item_stack_size')
        self.replace_records(reference, 'handler-views.jsonl.gz', views, 'summary.json')
        path = reference / 'summary.json'
        summary = json.loads(path.read_text())
        summary.update(schema_version=2, failed_item_facts=0, handler_item_facts={
            'version': 1, 'stage': 'before_native_serialization', 'identity': 'registry_metadata_typed_nbt',
            'quantity': 'positioned_item_stack_size', 'native_input': 'detached_positioned_copy',
            'native_api': 'StackInfo.stackStringifyHandlers.reverse.convertItemStackToNBT(stack,true)->NBTJson.toJsonObject',
            'count_classification': 'selected_default_at_observed_quantity'})
        path.write_text(json.dumps(summary))

    def test_lossless_view_facts_distinguish_null_and_empty_tags_and_compare_native_payload(self):
        directory, reference = self.capture()
        empty = {'type': 'compound', 'value': {}}
        resources = self.read_records(directory, 'resources.jsonl.gz')
        resources.append(resource('empty', registry_name='test:input', nbt=empty))
        self.replace_records(directory, 'resources.jsonl.gz', resources, 'manifest.json')
        aliases = self.read_records(reference, 'gt-display-aliases.jsonl.gz')
        aliases.append({'resource_id': 'empty', 'status': 'ok', 'alternatives': [self.typed('test:input', nbt=empty)], 'failure': None})
        self.context(directory, reference, aliases=aliases, projection_version=3, projections=[
            self.item_projection('test:input'), self.item_projection('test:input', nbt=empty), self.item_projection('test:output')])
        self.lossless_views(directory, reference, [self.typed('test:input', amount=2), self.typed('test:output')])
        report = comparison.compare(directory, reference)
        self.assertEqual(report['counts']['matched'], 1)
        view = self.read_records(reference, 'handler-views.jsonl.gz')[0]
        view['ingredients'][0]['alternatives'][0]['item_facts']['nbt'] = empty
        self.replace_records(reference, 'handler-views.jsonl.gz', [view], 'summary.json')
        report = comparison.compare(directory, reference)
        self.assertEqual(report['counts']['matched'], 0)
        self.assertEqual(report['counts']['differences'], 1)
        canonical = self.read_records(directory, 'processes.jsonl.gz')[0]
        canonical['inputs'][0]['choices'][0]['resource_id'] = 'empty'
        self.replace_records(directory, 'processes.jsonl.gz', [canonical], 'manifest.json')
        self.assertEqual(comparison.compare(directory, reference)['counts']['matched'], 1)
        view['ingredients'][0]['alternatives'][0]['native_stack']['tag'] = {'unexpected': 1}
        self.replace_records(reference, 'handler-views.jsonl.gz', [view], 'summary.json')
        self.assertEqual(comparison.compare(directory, reference)['counts']['differences'], 1)

    def test_lossless_double_and_display_quantity_keep_native_amounts_and_real_size(self):
        directory, reference, aliases, projections = self.native_item_capture()
        self.context(directory, reference, aliases=aliases, projections=projections, projection_version=3)
        charge = projections[0]['nbt']
        self.lossless_views(directory, reference, [self.typed('test:input', nbt=charge, amount=2), self.typed('test:output', amount=30)])
        self.assertEqual(comparison.compare(directory, reference)['counts']['matched'], 1)
        canonical = self.read_records(directory, 'processes.jsonl.gz')[0]
        canonical['inputs'][0]['choices'][0].update(amount=7, native_amount=7)
        self.replace_records(directory, 'processes.jsonl.gz', [canonical], 'manifest.json')
        view = self.read_records(reference, 'handler-views.jsonl.gz')[0]
        view['displayed_fields']['render_real_stack_sizes'] = False
        view['ingredients'][0]['real_stack_size'] = 7
        for positioned in view['ingredients'] + view['other_stacks']:
            positioned['alternatives'][0]['native_stack']['Count'] = 1
            positioned['alternatives'][0]['item_facts']['amount'] = 1
        self.replace_records(reference, 'handler-views.jsonl.gz', [view], 'summary.json')
        self.assertEqual(comparison.compare(directory, reference)['counts']['matched'], 1)
        view['ingredients'][0]['real_stack_size'] = 1
        self.replace_records(reference, 'handler-views.jsonl.gz', [view], 'summary.json')
        self.assertEqual(comparison.compare(directory, reference)['counts']['differences'], 1)

    def test_lossless_fact_failures_and_custom_quantity_changes_are_not_promoted(self):
        directory, reference, aliases, projections = self.native_item_capture()
        self.context(directory, reference, aliases=aliases, projections=projections, projection_version=3)
        self.lossless_views(directory, reference, [self.typed('test:input', nbt=projections[0]['nbt'], amount=2), self.typed('test:output', amount=30)])
        original = self.read_records(reference, 'handler-views.jsonl.gz')[0]
        for case in ('failed_facts', 'custom', 'quantity_change'):
            with self.subTest(case=case):
                view = json.loads(json.dumps(original))
                alternative = view['ingredients'][0]['alternatives'][0]
                if case == 'failed_facts':
                    alternative.update(item_facts=None, item_facts_failure={'message': 'facts failed'})
                elif case == 'custom':
                    alternative.update(serializer_class='custom.Writer', count_semantics='unknown')
                else:
                    alternative['native_stack']['Count'] = 99
                self.replace_records(reference, 'handler-views.jsonl.gz', [view], 'summary.json')
                report = comparison.compare(directory, reference)
                self.assertEqual(report['counts']['matched'], 0)
                self.assertGreater(report['counts']['unsupported'], 0)
                self.assertEqual(report['counts']['missing_canonical'], 0)
                self.assertEqual(report['counts']['missing_nei'], 0)
                if case == 'failed_facts':
                    self.assertEqual(report['capture_failures'], 1)

    def test_lossless_reference_capability_is_required_and_old_references_remain_ambiguous(self):
        directory, reference = self.capture()
        empty = {'type': 'compound', 'value': {}}
        projections = [self.item_projection('test:input'), self.item_projection('test:input', nbt=empty), self.item_projection('test:output')]
        aliases = self.read_records(reference, 'gt-display-aliases.jsonl.gz')
        self.context(directory, reference, aliases=aliases, projections=projections, projection_version=3)
        self.assertEqual(comparison.compare(directory, reference)['counts']['matched'], 0)
        self.lossless_views(directory, reference, [self.typed('test:input', amount=2), self.typed('test:output')])
        self.assertEqual(comparison.compare(directory, reference)['counts']['matched'], 1)
        path = reference / 'summary.json'
        summary = json.loads(path.read_text())
        summary['handler_item_facts'].pop('native_input')
        path.write_text(json.dumps(summary))
        with self.assertRaisesRegex(comparison.ComparisonError, 'capability'):
            comparison.compare(directory, reference)

    def test_lossless_fluid_wrapper_uses_native_volume_and_rejects_custom_writer(self):
        directory, reference = self.capture()
        resources = self.read_records(directory, 'resources.jsonl.gz')
        resources[0].update(kind='fluid', registry_name='water', metadata=None)
        self.replace_records(directory, 'resources.jsonl.gz', resources, 'manifest.json')
        canonical = self.read_records(directory, 'processes.jsonl.gz')[0]
        canonical['inputs'][0]['choices'] = [dict(choice('in', amount=1000), native_amount=1000)]
        self.replace_records(directory, 'processes.jsonl.gz', [canonical], 'manifest.json')
        self.context(directory, reference, projections=[self.item_projection('test:output')], projection_version=3)
        view = self.read_records(reference, 'handler-views.jsonl.gz')[0]
        view['ingredients'][0]['alternatives'][0]['native_stack'] = {'neiFluidName': 'water', 'Count': '1000L'}
        self.replace_records(reference, 'handler-views.jsonl.gz', [view], 'summary.json')
        self.lossless_views(directory, reference, [self.typed('nei:fluid_display', amount=1), self.typed('test:output')])
        view = self.read_records(reference, 'handler-views.jsonl.gz')[0]
        alternative = view['ingredients'][0]['alternatives'][0]
        alternative.update(serializer_class='codechicken.nei.recipe.stackinfo.FluidDisplayStackStringifyHandler', count_semantics='native_conversion')
        self.replace_records(reference, 'handler-views.jsonl.gz', [view], 'summary.json')
        self.assertEqual(comparison.compare(directory, reference)['counts']['matched'], 1)
        alternative['serializer_class'] = 'custom.FluidWriter'
        self.replace_records(reference, 'handler-views.jsonl.gz', [view], 'summary.json')
        report = comparison.compare(directory, reference)
        self.assertEqual(report['counts']['matched'], 0)
        self.assertGreater(report['counts']['unsupported'], 0)

    def test_native_item_projection_compares_lapotron_double_and_preserves_thirty_outputs(self):
        directory, reference, _, _ = self.native_item_capture()
        report = comparison.compare(directory, reference)
        self.assertEqual(report['counts']['matched'], 1)
        self.assertEqual(report['counts']['differences'], 0)
        self.assertEqual(report['counts']['unsupported'], 0)

    def test_native_projection_double_string_collision_remains_ambiguous(self):
        directory, reference, aliases, projections = self.native_item_capture()
        string_tag = {'type': 'compound', 'value': {'charge': {'type': 'string', 'value': '1.0E7D'}}}
        projections.append(self.item_projection('test:input', nbt=string_tag, native_tag={'charge': '1.0E7D'}))
        self.context(directory, reference, aliases=aliases, projections=projections)
        report = comparison.compare(directory, reference)
        self.assertEqual(report['counts']['matched'], 0)
        self.assertGreater(report['ambiguous_resource_projections'], 0)
        self.assertTrue(any('Ambiguous identity' in reason for reason in report['unsupported_reasons']))

    def test_missing_failed_and_converted_native_projections_stay_unsupported(self):
        directory, reference, aliases, originals = self.native_item_capture()
        cases = []
        cases.append(('missing', originals[1:], True))
        failed = dict(originals[0], status='failed', native_stack=None, serializer_class=None, count_semantics='unknown', failure={'message': 'native serializer failed'})
        cases.append(('failed', [failed, originals[1]], False))
        unknown = dict(originals[0], serializer_class=None, count_semantics='unknown')
        cases.append(('unknown_count', [unknown, originals[1]], True))
        converted = dict(originals[0], serializer_class=None, count_semantics='native_conversion', native_stack={'neiFluidName': 'water', 'Count': '1000L'})
        cases.append(('fluid_conversion', [converted, originals[1]], True))
        original_view = self.read_records(reference, 'handler-views.jsonl.gz')[0]
        for name, projections, complete in cases:
            with self.subTest(name=name):
                view = json.loads(json.dumps(original_view))
                if name == 'fluid_conversion':
                    view['ingredients'][0]['alternatives'][0]['native_stack'] = converted['native_stack']
                self.replace_records(reference, 'handler-views.jsonl.gz', [view], 'summary.json')
                self.context(directory, reference, aliases=aliases, projections=projections, complete=complete)
                report = comparison.compare(directory, reference)
                self.assertEqual(report['counts']['matched'], 0)
                self.assertGreater(report['counts']['unsupported'], 0)
                self.assertEqual(report['counts']['missing_canonical'], 0)

    def test_native_projection_registry_classification_and_stream_integrity_are_required(self):
        directory, reference, aliases, projections = self.native_item_capture()
        context_path = reference / 'presentation-context.json'
        original = json.loads(context_path.read_text())
        for field, value in (('canonical_snapshot_id', 'other'), ('canonical_pack', {}), ('canonical_files', {})):
            with self.subTest(field=field):
                context_path.write_text(json.dumps(dict(original, **{field: value})))
                self.bind_context_pointer(reference)
                with self.assertRaises(comparison.ComparisonError):
                    comparison.compare(directory, reference)
        context_path.write_text(json.dumps(original))
        self.bind_context_pointer(reference)
        stream = reference / 'item-projections.jsonl.gz'
        captured = stream.read_bytes()
        stream.write_bytes(b'changed')
        with self.assertRaisesRegex(comparison.ComparisonError, 'checksum'):
            comparison.compare(directory, reference)
        stream.write_bytes(captured)
        metadata = json.loads(json.dumps(original))
        metadata['files']['item-projections.jsonl.gz']['records'] += 1
        context_path.write_text(json.dumps(metadata))
        self.bind_context_pointer(reference)
        with self.assertRaisesRegex(comparison.ComparisonError, 'record count'):
            comparison.compare(directory, reference)
        self.context(directory, reference, aliases=aliases, projections=projections + [projections[0]])
        with self.assertRaisesRegex(comparison.ComparisonError, 'duplicate typed identity'):
            comparison.compare(directory, reference)
        self.context(directory, reference, aliases=aliases, projections=projections)
        metadata = json.loads(context_path.read_text())
        metadata['item_projection']['serializer_classes'].append('unknown.CustomSerializer')
        context_path.write_text(json.dumps(metadata))
        self.bind_context_pointer(reference)
        report = comparison.compare(directory, reference)
        self.assertEqual(report['counts']['matched'], 0)
        self.assertGreater(report['counts']['unsupported'], 0)

    def test_historical_version_one_does_not_guess_java_float_projection(self):
        directory, reference, aliases, _ = self.native_item_capture()
        self.context(directory, reference, aliases=aliases)
        report = comparison.compare(directory, reference)
        self.assertEqual(report['counts']['matched'], 0)
        self.assertTrue(any('floating-point Java formatting' in reason for reason in report['unsupported_reasons']))

    def test_historical_four_map_scope_remains_bounded_when_solidifier_views_exist(self):
        directory, reference = self.capture()
        context_path = reference / 'presentation-context.json'
        metadata = json.loads(context_path.read_text())
        metadata['scope']['gt_families'] = ['gregtech:gt.recipe.alloysmelter', 'gregtech:gt.recipe.metalbender',
                                          'gregtech:gt.recipe.macerator', 'gregtech:gt.recipe.orewasher']
        context_path.write_text(json.dumps(metadata))
        self.bind_context_pointer(reference)
        handler = self.read_records(reference, 'handlers.jsonl.gz')[0]
        extra = dict(handler, handler_key='solidifier', gt_recipe_map_id='gregtech:gt.recipe.fluidsolidifier')
        self.replace_records(reference, 'handlers.jsonl.gz', [handler, extra], 'summary.json')
        view = self.read_records(reference, 'handler-views.jsonl.gz')[0]
        self.replace_records(reference, 'handler-views.jsonl.gz', [view, dict(view, handler_key='solidifier')], 'summary.json')
        signature = self.read_records(reference, 'signatures.jsonl.gz')[0]
        self.replace_records(reference, 'signatures.jsonl.gz', [signature, dict(signature, handler_key='solidifier')], 'summary.json')
        summary_path = reference / 'summary.json'
        summary = json.loads(summary_path.read_text())
        summary['counts'] = {'handlers': 2, 'signatures': 2, 'handler_views': 2}
        summary_path.write_text(json.dumps(summary))
        report = comparison.compare(directory, reference)
        self.assertEqual(report['counts']['matched'], 1)
        self.assertEqual(report['counts']['missing_canonical'], 0)
        self.assertEqual(report['counts']['differences'], 0)
        self.assertFalse(any(profile[0] == 'gregtech:gt.recipe.fluidsolidifier' for profile in report['mapped_profiles']))
        self.assertTrue(any('captured' in reason and 'scope' in reason for reason in report['unsupported_reasons']))
        metadata['scope']['gt_families'].append('gregtech:gt.recipe.unknown')
        context_path.write_text(json.dumps(metadata))
        self.bind_context_pointer(reference)
        with self.assertRaisesRegex(comparison.ComparisonError, 'scope'):
            comparison.compare(directory, reference)

    def test_selected_default_serializer_is_supported_in_schema_three_with_actual_five_class_registry(self):
        directory, reference, aliases, projections = self.native_item_capture()
        self.context(directory, reference, aliases=aliases, projections=projections, projection_version=3)
        context_path = reference / 'presentation-context.json'
        metadata = json.loads(context_path.read_text())
        metadata['item_projection']['serializer_classes'].extend([
            'com.gtnewhorizons.aspectrecipeindex.nei.TCAspectStringifyHandler', 'codechicken.enderstorage.internal.StorageStackStringifyHandler'])
        context_path.write_text(json.dumps(metadata))
        self.bind_context_pointer(reference)
        report = comparison.compare(directory, reference)
        self.assertEqual(report['counts']['matched'], 1)
        self.assertEqual(report['counts']['unsupported'], 0)
        metadata['schema_version'] = 2
        metadata['item_projection']['api'] = 'StackInfo.itemStackToNBT(stack,true)->NBTJson.toJsonObject'
        metadata['item_projection']['classification'] = 'pinned_builtin_default_item_count'
        context_path.write_text(json.dumps(metadata))
        self.bind_context_pointer(reference)
        self.assertEqual(comparison.compare(directory, reference)['counts']['matched'], 0)

    def test_schema_three_custom_and_fluid_winners_are_not_promoted_to_ordinary_items(self):
        directory, reference, aliases, original = self.native_item_capture()
        custom_class = 'com.gtnewhorizons.aspectrecipeindex.nei.TCAspectStringifyHandler'
        for conversion in (False, True):
            with self.subTest(conversion=conversion):
                record = dict(original[0], serializer_class=custom_class,
                              count_semantics='native_conversion' if conversion else 'unknown')
                view = self.read_records(reference, 'handler-views.jsonl.gz')[0]
                if conversion:
                    record['native_stack'] = {'neiFluidName': 'water', 'Count': '1000L'}
                    view['ingredients'][0]['alternatives'][0]['native_stack'] = record['native_stack']
                else:
                    view['ingredients'][0]['alternatives'][0]['native_stack'] = dict(record['native_stack'], Count=2)
                self.replace_records(reference, 'handler-views.jsonl.gz', [view], 'summary.json')
                self.context(directory, reference, aliases=aliases, projections=[record, original[1]], projection_version=3)
                path = reference / 'presentation-context.json'
                metadata = json.loads(path.read_text())
                metadata['item_projection']['serializer_classes'].append(custom_class)
                path.write_text(json.dumps(metadata))
                self.bind_context_pointer(reference)
                report = comparison.compare(directory, reference)
                self.assertEqual(report['counts']['matched'], 0)
                self.assertGreater(report['counts']['unsupported'], 0)
                self.assertEqual(report['counts']['missing_canonical'], 0)

    def test_schema_three_supplementary_scope_does_not_map_generic_botania_handlers(self):
        directory, reference, aliases, projections = self.native_item_capture()
        self.context(directory, reference, aliases=aliases, projections=projections, projection_version=3)
        handlers = self.read_records(reference, 'handlers.jsonl.gz')
        handlers.append(dict(handlers[0], handler_key='botania', native_class='test.BotaniaHandler', gt_recipe_map_id=None))
        self.replace_records(reference, 'handlers.jsonl.gz', handlers, 'summary.json')
        views = self.read_records(reference, 'handler-views.jsonl.gz')
        views.append(dict(views[0], handler_key='botania'))
        self.replace_records(reference, 'handler-views.jsonl.gz', views, 'summary.json')
        signatures = self.read_records(reference, 'signatures.jsonl.gz')
        signatures.append(dict(signatures[0], handler_key='botania'))
        self.replace_records(reference, 'signatures.jsonl.gz', signatures, 'summary.json')
        path = reference / 'summary.json'
        metadata = json.loads(path.read_text())
        metadata['counts'] = {'handlers': 2, 'handler_views': 2, 'signatures': 2}
        path.write_text(json.dumps(metadata))
        report = comparison.compare(directory, reference)
        self.assertEqual(report['counts']['matched'], 1)
        self.assertEqual(report['counts']['missing_canonical'], 0)
        self.assertFalse(any(profile[0].startswith('botania:') for profile in report['mapped_profiles']))
        context_path = reference / 'presentation-context.json'
        metadata = json.loads(context_path.read_text())
        metadata['scope']['supplementary_families'] = ['botania:unknown']
        context_path.write_text(json.dumps(metadata))
        self.bind_context_pointer(reference)
        with self.assertRaisesRegex(comparison.ComparisonError, 'supplementary'):
            comparison.compare(directory, reference)

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
