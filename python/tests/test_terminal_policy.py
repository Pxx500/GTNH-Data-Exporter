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
    def test_native_single_use_subtypes_are_terminal_without_item_hierarchy(self):
        # GT .221 SingleUseTool declares these tool IDs separately from its molds.
        for metadata in (0, 1, 2, 3, 4, 6, 7, 5):
            with self.subTest(metadata=metadata), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                tool = resource('tool', registry_name='ggfab:gt.ggfab.d1', metadata=metadata,
                    nbt={'type': 'compound', 'value': {'custom': {'type': 'int', 'value': 1}}})
                tool['display_name'] = 'Unrelated label'
                recipes = [process('make', [slot(choice('start'))], ['tool']),
                    process('use', [slot(choice('tool'))], ['target'])]
                dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=[resource('start'), tool,
                    resource('target')], processes=recipes), root / 'index.sqlite')
                for selection in ('shortest', 'diverse', 'material'):
                    args = {'path_selection': selection, 'terminal_artifact_policy': 'direct_targets_only'}
                    restricted = dataset.trace_processes(start_id='start', target_id='target', **args)
                    self.assertEqual(restricted['paths'], [])
                    direct = dataset.trace_processes(start_id='start', target_id='tool', **args)
                    self.assertEqual(direct['paths'], [{'resource_ids': ['start', 'tool'], 'process_ids': ['make']}])
                    self.assertEqual(next(row for row in direct['resources'] if row['id'] == 'tool'), tool)
                    self.assertEqual(dataset.trace_processes(start_id='tool', target_id='target', **args)['paths'], [])
                    allowed = dataset.trace_processes(start_id='start', target_id='target', path_selection=selection)
                    self.assertEqual(allowed['paths'][0]['process_ids'], ['make', 'use'])
                self.assertEqual(dataset.get_process('use')['item'], recipes[1])

    def test_single_use_molds_and_native_tool_cofeeds_keep_their_roles(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rows = [resource('start'), resource('target'),
                resource('tool', registry_name='ggfab:gt.ggfab.d1', metadata=4)]
            molds = [resource(f'mold-{metadata}', registry_name='ggfab:gt.ggfab.d1', metadata=metadata)
                for metadata in (30, 31, 32, 33, 34, 36, 37, 35)]
            # Neither a matching label nor the shared namespace establishes a tool subtype.
            molds += [resource('other-subtype', registry_name='ggfab:gt.ggfab.d1', metadata=8),
                resource('other-registry', registry_name='ggfab:other', metadata=4)]
            for row in molds:
                row['display_name'] = 'Single Use Hard Hammer'
            recipes = [process(f'make-{row["id"]}', [slot(choice('start'))], [row['id']]) for row in molds]
            recipes += [process(f'use-{row["id"]}', [slot(choice(row['id'])), slot(choice('tool', amount=3)),
                slot(choice('tool'), role='presence')], ['target']) for row in molds]
            dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=rows + molds, processes=recipes), root / 'index.sqlite')
            for selection in ('shortest', 'diverse', 'material'):
                chain = dataset.trace_processes(start_id='start', target_id='target', path_selection=selection,
                    required_resource_ids=['mold-34'], terminal_artifact_policy='direct_targets_only')
                self.assertEqual(chain['paths'][0]['process_ids'], ['make-mold-34', 'use-mold-34'])
                for row in molds:
                    result = dataset.trace_processes(start_id=row['id'], target_id='target', path_selection=selection,
                        terminal_artifact_policy='direct_targets_only')
                    self.assertEqual(result['paths'][0]['process_ids'], [f'use-{row["id"]}'])
                    self.assertEqual(result['processes'], [next(p for p in recipes if p['id'] == f'use-{row["id"]}')])
                    self.assertEqual(next(r for r in result['resources'] if r['id'] == 'tool'), rows[2])

    def test_incompatible_terminal_endpoints_stop_before_recipe_graph_discovery(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rows = [typed_item('start', 'tconstruct.library.tools.ToolCore'),
                typed_item('intermediate', 'gregtech.api.items.MetaGeneratedTool'),
                typed_item('ordinary'), resource('unknown')]
            recipes = [process('upgrade', [slot(choice('start'))], ['intermediate']),
                process('recover', [slot(choice('intermediate'))], ['ordinary', 'unknown'])]
            dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=rows, processes=recipes), root / 'index.sqlite')
            for selection in ('shortest', 'diverse', 'material'):
                terminal = dataset.trace_processes(start_id='start', target_id='intermediate', path_selection=selection,
                    terminal_artifact_policy='direct_targets_only')
                self.assertEqual(terminal['paths'], [{'resource_ids': ['start', 'intermediate'], 'process_ids': ['upgrade']}])
                self.assertEqual(terminal['processes'], [recipes[0]])
                for target in ('ordinary', 'unknown'):
                    with self.subTest(selection=selection, target=target):
                        result = dataset.trace_processes(start_id='start', target_id=target, path_selection=selection,
                            terminal_artifact_policy='direct_targets_only')
                        self.assertEqual(result['paths'], [])
                        self.assertEqual(result['processes'], [])
                        self.assertEqual(result['limit_reasons'], [])
                        search = result['search']
                        self.assertEqual(search['examined_processes'], 0)
                        self.assertEqual(search['examined_states'], 0)
                        self.assertEqual(search['queued_states'], 0)
                        self.assertEqual(search.get('distance_work', 0), 0)
                        metric = search['terminal_artifacts']
                        self.assertEqual(metric['endpoint_compatibility'], 'incompatible')
                        self.assertEqual(metric['endpoint_checks'], 1)
                        self.assertEqual(metric['checked_edges'], 0)
                        self.assertEqual(metric['blocked_edges'], 0)
                        self.assertEqual(metric['resource_lookups'], 2)
                        self.assertGreater(metric['charged_work'], 0)
                        self.assertEqual(metric['charged_work'], search['expansion_work'])
                        self.assertEqual(metric['unknown_resources'], int(target == 'unknown'))

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
                        self.assertEqual(restricted['search']['terminal_artifacts']['endpoint_compatibility'], 'incompatible')
                        self.assertEqual(restricted['search']['terminal_artifacts']['blocked_edges'], 0)
                        self.assertLessEqual(restricted['search']['terminal_artifacts']['charged_work'], restricted['search']['expansion_work'])
                        restored = dataset.trace_processes(start_id='terminal', target_id='target', path_selection=selection,
                            terminal_artifact_policy='allow')
                        self.assertEqual(restored['paths'], allowed['paths'])
                self.assertEqual(dataset.get_process('salvage')['item'], recipe)
                self.assertEqual(dataset.find_processes(input_id='terminal', output_id='target')['items'], [recipe])
