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
        return directory, reference

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
