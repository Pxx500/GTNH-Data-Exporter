import tempfile
import unittest
from pathlib import Path

from gtnh_data import Dataset, DatasetError
from .artifacts import choice, process, resource, slot, snapshot


def typed_item(id, class_name='net.minecraft.item.Item', *, superclasses=(), interfaces=(), **identity):
    row = resource(id, **identity)
    row['item_type'] = {'status': 'captured', 'basis': 'runtime_item_class_hierarchy',
        'scope': 'item_object_not_configured_stack', 'class_name': class_name,
        'superclasses': list(superclasses), 'interfaces': list(interfaces)}
    return row


class TerminalPolicyTests(unittest.TestCase):
    def test_direct_part_tool_suffix_keeps_exact_nbt_and_all_cofeeds(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rows = [typed_item('start'), typed_item('target'),
                typed_item('part', 'tconstruct.library.tools.DynamicToolPart', interfaces=['tconstruct.library.util.IToolPart']),
                typed_item('tool', 'gregtech.common.items.MetaGeneratedTool01', superclasses=['gregtech.api.items.MetaGeneratedTool']),
                typed_item('cofeed'), typed_item('presence', 'tconstruct.library.tools.ToolCore')]
            rows[3].update(registry_name='test:tool', metadata=12, nbt={'type': 'int', 'value': 1})
            variant = typed_item('wrong-nbt', 'gregtech.common.items.MetaGeneratedTool01',
                superclasses=['gregtech.api.items.MetaGeneratedTool'], registry_name='test:tool', metadata=12,
                nbt={'type': 'int', 'value': 2})
            rows.append(variant)
            matched = choice('tool')
            matched['match']['nbt_sensitive'] = True
            recipes = [process('part-maker', [slot(choice('start'))], ['part']),
                process('tool-maker', [slot(choice('part', amount=2)), slot(choice('cofeed', amount=3)),
                    slot(choice('presence'), role='presence')], ['tool']),
                process('salvage', [slot(matched)], ['target']),
                process('cofeed-maker', [slot(choice('start')), slot(choice('presence'))], ['target'])]
            dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=rows, processes=recipes), root / 'index.sqlite')
            for selection in ('shortest', 'diverse', 'material'):
                with self.subTest(selection=selection):
                    args = {'start_id': 'start', 'path_selection': selection, 'terminal_artifact_policy': 'direct_targets_only'}
                    target = dataset.trace_processes(target_id='tool', **args)
                    self.assertEqual(target['paths'], [{'resource_ids': ['start', 'part', 'tool'],
                        'process_ids': ['part-maker', 'tool-maker']}])
                    self.assertEqual(next(row for row in target['processes'] if row['id'] == 'tool-maker'), recipes[1])
                    part = dataset.trace_processes(target_id='part', **args)
                    self.assertEqual(part['paths'][0]['process_ids'], ['part-maker'])
                    product = dataset.trace_processes(target_id='target', **args)
                    self.assertEqual(product['paths'], [{'resource_ids': ['start', 'target'], 'process_ids': ['cofeed-maker']}])
                    self.assertEqual(next(row for row in product['processes'] if row['id'] == 'cofeed-maker'), recipes[-1])
                    constrained = dataset.trace_processes(target_id='target', required_resource_ids=['tool'], **args)
                    self.assertEqual(constrained['paths'], [])
                    wrong = dataset.trace_processes(start_id='wrong-nbt', target_id='target', path_selection=selection,
                        terminal_artifact_policy='allow')
                    self.assertEqual(wrong['paths'], [])
                    self.assertEqual(next(row for row in target['resources'] if row['id'] == 'tool')['nbt'], rows[3]['nbt'])

    def test_recycling_and_accounting_keep_terminal_byproducts_and_external_supplies(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rows = [typed_item(id) for id in ('a', 'b', 'd', 'external')]
            rows += [typed_item('terminal', 'tconstruct.library.tools.ToolCore'),
                typed_item('presence', 'gregtech.api.items.MetaGeneratedTool')]
            main = process('main', [slot(choice('a')), slot(choice('d', amount=4))], ['b', 'terminal'])
            main['outputs'][1]['amount'] = 2
            recovery = process('recovery', [slot(choice('terminal')), slot(choice('external')),
                slot(choice('presence'), role='presence')], ['d'])
            dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=rows, processes=[main, recovery]), root / 'index.sqlite')
            restricted = dataset.trace_processes(start_id='terminal', target_id='d', terminal_artifact_policy='direct_targets_only')
            self.assertEqual(restricted['paths'], [])
            result = dataset.plan_recycling(main_path={'resource_ids': ['a', 'b'], 'process_ids': ['main']},
                byproduct_id='terminal', return_id='d')
            self.assertEqual(result['secondary_trace']['search']['terminal_artifacts']['policy'], 'allow')
            alternative = result['alternatives'][0]
            self.assertEqual(alternative['status'], 'complete')
            self.assertEqual(alternative['recovery']['net_returned'], {'numerator': 2, 'denominator': 1})
            self.assertEqual(alternative['external_inputs'], [{'resource_id': 'external', 'amount': {'numerator': 2, 'denominator': 1}}])
            self.assertEqual(alternative['ledger']['presence']['presence'], {'numerator': 1, 'denominator': 1})

    def test_unapproved_items_and_unknown_evidence_are_not_inferred_from_names_or_registry(self):
        examples = [typed_item('input', 'ggfab.items.SingleUseItem'), typed_item('input', 'tconstruct.tools.items.Pattern'),
            typed_item('input', 'net.minecraft.item.ItemArmor'),
            typed_item('input', registry_name='gregtech:gt.metatool.01', metadata=170),
            typed_item('input', 'test.ToolCoreLookalike'), resource('input')]
        rotor = typed_item('input', 'gregtech.api.items.MetaGeneratedItem')
        rotor['material_facts'] = {'association': {'prefix': 'rotor'}}
        examples.append(rotor)
        failed = typed_item('input', 'tconstruct.library.tools.ToolCore')
        failed['item_type']['status'] = 'failed'
        examples.append(failed)
        for field, value in (('basis', 'guessed'), ('scope', 'configured_stack'), ('class_name', None),
                             ('superclasses', None), ('interfaces', ['tconstruct.library.util.IToolPart', 1])):
            row = typed_item('input', 'tconstruct.library.tools.ToolCore')
            row['item_type'][field] = value
            examples.append(row)
        scalar = resource('input')
        scalar['item_type'] = 'tconstruct.library.tools.ToolCore'
        examples.append(scalar)
        for row in examples:
            with self.subTest(row=row), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                recipe = process('use', [slot(choice('input'))], ['target'])
                dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=[row, typed_item('target')],
                    processes=[recipe]), root / 'index.sqlite')
                for selection in ('shortest', 'diverse', 'material'):
                    result = dataset.trace_processes(start_id='input', target_id='target', path_selection=selection,
                        terminal_artifact_policy='direct_targets_only')
                    self.assertEqual(result['paths'][0]['process_ids'], ['use'])
                    self.assertEqual(next(item for item in result['resources'] if item['id'] == 'input'), row)
                    metric = result['search']['terminal_artifacts']
                    unknown = not isinstance(row.get('item_type'), dict) or row is failed or row not in examples[:7]
                    self.assertEqual(metric['unknown_resources'], int(unknown))
                    self.assertEqual(metric['recognition_status'], 'partial' if unknown else 'captured_for_checked_resources')

    def test_fluid_evidence_is_not_applicable_and_policy_values_are_validated(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fluid = resource('fluid')
            fluid.update(kind='fluid', metadata=None)
            dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=[fluid, typed_item('target')],
                processes=[process('make', [slot(choice('fluid'))], ['target'])]), root / 'index.sqlite')
            for selection in ('shortest', 'diverse', 'material'):
                result = dataset.trace_processes(start_id='fluid', target_id='target', path_selection=selection,
                    terminal_artifact_policy='direct_targets_only')
                metric = result['search']['terminal_artifacts']
                self.assertEqual(metric['unknown_resources'], 0)
                self.assertEqual(metric['not_applicable_resources'], 1)
                self.assertEqual(result['paths'][0]['process_ids'], ['make'])
            with self.assertRaisesRegex(DatasetError, 'terminal_artifact_policy must be allow or direct_targets_only'):
                dataset.trace_processes(start_id='fluid', target_id='target', terminal_artifact_policy='tool_names')

    def test_approved_native_families_cannot_carry_unrelated_products_but_allow_restores(self):
        families = [
            typed_item('terminal', 'tconstruct.tools.tools.Pickaxe', superclasses=['tconstruct.library.tools.ToolCore']),
            typed_item('terminal', 'tconstruct.weaponry.items.ArrowAmmo',
                superclasses=['tconstruct.library.weaponry.AmmoItem', 'tconstruct.library.tools.ToolCore']),
            typed_item('terminal', 'vexatos.tgregworks.item.ItemTGregPart', interfaces=['tconstruct.library.util.IToolPart']),
            typed_item('terminal', 'gregtech.common.items.MetaGeneratedTool01',
                registry_name='gregtech:gt.metatool.01', metadata=170,
                superclasses=['gregtech.api.items.MetaGeneratedTool']),
            typed_item('terminal', 'detrav.items.DetravMetaGeneratedTool01',
                superclasses=['gregtech.api.items.MetaGeneratedTool']),
        ]
        for row in families:
            with self.subTest(item_type=row['item_type']), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                recipe = process('salvage', [slot(choice('terminal'))], ['target'])
                dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=[row, typed_item('target')],
                    processes=[recipe]), root / 'index.sqlite')
                for selection in ('shortest', 'diverse', 'material'):
                    with self.subTest(selection=selection):
                        allowed = dataset.trace_processes(start_id='terminal', target_id='target', path_selection=selection)
                        self.assertEqual(allowed['paths'], [{'resource_ids': ['terminal', 'target'], 'process_ids': ['salvage']}])
                        restricted = dataset.trace_processes(start_id='terminal', target_id='target', path_selection=selection,
                            terminal_artifact_policy='direct_targets_only')
                        self.assertEqual(restricted['paths'], [])
                        self.assertGreater(restricted['search']['terminal_artifacts']['blocked_edges'], 0)
                        self.assertLessEqual(restricted['search']['terminal_artifacts']['charged_work'], restricted['search']['expansion_work'])
                        restored = dataset.trace_processes(start_id='terminal', target_id='target', path_selection=selection,
                            terminal_artifact_policy='allow')
                        self.assertEqual(restored['paths'], allowed['paths'])
                self.assertEqual(dataset.get_process('salvage')['item'], recipe)
                self.assertEqual(dataset.find_processes(input_id='terminal', output_id='target')['items'], [recipe])
