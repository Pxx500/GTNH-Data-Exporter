"""Compare persisted canonical recipes with a deliberately scoped NEI presentation reference.

The canonical side comes exclusively from checksummed snapshot streams. Native
RecipeId API records are inventoried separately, never used as canonical recipes.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sys
import time
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

GT_HANDLER = 'gregtech.nei.GTNEIDefaultHandler'
FURNACE_HANDLER = 'codechicken.nei.recipe.FurnaceRecipeHandler'
GT_FRONTEND = 'gregtech.api.recipe.RecipeMapFrontend'
GT_FAMILIES = frozenset('gregtech:gt.recipe.' + name for name in ('alloysmelter', 'metalbender', 'macerator', 'orewasher'))
PINNED_MODS = {
    'NotEnoughItems': ('2.8.159-GTNH', '050b2440952adc930e871586f496607959344aa2d7c3be781fd922a5b253a3af'),
    'gregtech': ('5.09.54.221', '60ceb229cd894dd28393efb6d0013de2835289eeef6fcf84ad3e17a6475baf5b'),
}
SOURCE_SCOPE = {
    'nei_commit': '550e85c456ff2a2ac92c47af4235ad3aa46beecb',
    'gt_source_cache_sha256': 'de60b02fc35b9bf535123920eecfc1e7b67ea9692dc518daa49a5eea34131302',
    'gt_families': sorted(GT_FAMILIES),
    'sources': [
        'https://github.com/GTNewHorizons/NotEnoughItems/blob/550e85c456ff2a2ac92c47af4235ad3aa46beecb/src/main/java/codechicken/nei/util/NBTJson.java',
        'https://github.com/GTNewHorizons/NotEnoughItems/blob/550e85c456ff2a2ac92c47af4235ad3aa46beecb/src/main/java/codechicken/nei/recipe/FurnaceRecipeHandler.java',
        'gregtech/nei/GTNEIDefaultHandler.java:610-934',
        'gregtech/api/recipe/RecipeMaps.java:138,589,1229,1239',
        'gregtech/api/recipe/NEIRecipePropertiesBuilder.java:35-46',
    ],
}


class ComparisonError(ValueError):
    """The reference cannot be bound to the pinned canonical cohort."""


class Unsupported(ValueError):
    """A presentation rule or identity cannot be established by this adapter."""


def _json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def _records(directory, filename, files):
    expected = files.get(filename)
    if not isinstance(expected, dict) or type(expected.get('records')) is not int or expected['records'] < 0:
        raise ComparisonError(f'Missing count/hash declaration for {filename}')
    path = directory / filename
    with path.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != expected.get('sha256'):
            raise ComparisonError(f'{filename}: checksum mismatch')
    count = 0
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        for count, line in enumerate(stream, 1):
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ComparisonError(f'{filename}:{count}: expected object')
            yield value
    if count != expected['records']:
        raise ComparisonError(f'{filename}: record count mismatch')


def _presentation_context(reference, summary, manifest, resources):
    pointer = summary['files'].get('presentation-context.json')
    if pointer is None:
        return None, {'available': False, 'complete': False, 'failure_count': 0,
                      'reason': 'Independent item presentation context was not captured'}
    if not isinstance(pointer, dict) or not isinstance(pointer.get('sha256'), str):
        raise ComparisonError('Invalid presentation-context.json pointer')
    path = reference / 'presentation-context.json'
    with path.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != pointer['sha256']:
            raise ComparisonError('presentation-context.json: checksum mismatch')
    metadata = json.loads(path.read_text(encoding='utf-8'))
    if type(metadata.get('schema_version')) is not int or metadata['schema_version'] != 1:
        raise ComparisonError('Only presentation context schema version 1 is mapped')
    if metadata.get('canonical_snapshot_id') != manifest['snapshot_id'] or metadata.get('canonical_pack') != manifest['pack']:
        raise ComparisonError('Presentation context snapshot identity or pack/config cohort does not match')
    expected_files = {name: manifest['files'][name] for name in ('resources.jsonl.gz', 'processes.jsonl.gz')}
    if metadata.get('canonical_files') != expected_files:
        raise ComparisonError('Presentation context canonical file binding does not match')
    scope = metadata.get('scope') or {}
    if (sorted(scope.get('gt_families', [])) != sorted(GT_FAMILIES)
            or scope.get('furnace_family') != 'minecraft:smelting'
            or type(scope.get('alias_template_amount')) is not int or scope['alias_template_amount'] != 1):
        raise ComparisonError('Presentation context scope is not the pinned item adapter scope')
    if type(metadata.get('complete')) is not bool or not isinstance(metadata.get('failures'), list):
        raise ComparisonError('Presentation context completeness/failures were not captured')
    aliases, pools = {}, {}
    counts = Counter()
    for filename, target, key, field in (
            ('gt-display-aliases.jsonl.gz', aliases, 'resource_id', 'alternatives'),
            ('item-pools.jsonl.gz', pools, 'registry_name', 'entries')):
        for record in _records(reference, filename, metadata.get('files', {})):
            id = record.get(key)
            if not isinstance(id, str) or not id or id in target:
                raise ComparisonError(f'{filename}: null, invalid or duplicate {key}')
            if key == 'resource_id' and (id not in resources or resources[id]['kind'] != 'item'):
                raise ComparisonError(f'{filename}: unresolved canonical item resource_id {id}')
            status = record.get('status')
            if status not in ('ok', 'empty', 'failed') or not isinstance(record.get(field), list):
                raise ComparisonError(f'{filename}: invalid status or stack collection')
            stacks = record[field]
            if (status == 'ok' and not stacks) or (status != 'ok' and stacks):
                raise ComparisonError(f'{filename}: status disagrees with stack collection')
            if status == 'failed' and not record.get('failure'):
                raise ComparisonError(f'{filename}: failed entry has no failure evidence')
            if status != 'failed' and record.get('failure'):
                raise ComparisonError(f'{filename}: successful entry has failure evidence')
            for stack in stacks:
                if (not isinstance(stack, dict) or not isinstance(stack.get('registry_name'), str)
                        or not stack['registry_name'] or type(stack.get('metadata')) is not int
                        or type(stack.get('amount')) is not int or 'nbt' not in stack):
                    raise ComparisonError(f'{filename}: invalid typed item stack')
                if key == 'resource_id' and stack['amount'] != 1:
                    raise ComparisonError(f'{filename}: alias is not a quantity-one template')
            target[id] = record
            counts[filename + ':' + status] += 1
    entry_failures = [{'stream': name, key: id, 'failure': record['failure']}
                      for name, mapping, key in (('gt-display-aliases.jsonl.gz', aliases, 'resource_id'),
                                                 ('item-pools.jsonl.gz', pools, 'registry_name'))
                      for id, record in mapping.items() if record['status'] == 'failed']
    failures = len(metadata['failures']) + len(entry_failures)
    if failures and metadata['complete']:
        raise ComparisonError('Presentation context claims complete despite captured failures')
    return {'aliases': aliases, 'pools': pools, 'failures': metadata['failures']}, {
        'available': True, 'complete': metadata['complete'], 'failure_count': failures,
        'failures': metadata['failures'], 'entry_failures': entry_failures, 'failure_unit': 'events, not distinct affected recipes',
        'entry_counts': dict(counts), 'readiness': metadata.get('readiness')}


def _context_items(context):
    if context is not None:
        for mapping, field in ((context['aliases'], 'alternatives'), (context['pools'], 'entries')):
            for record in mapping.values():
                for stack in record[field]:
                    yield dict(stack, kind='item')


def _item_presentation(resource_id, resource, amount, unify, context):
    declared = [dict(resource, amount=amount)]
    if unify:
        if context is None:
            raise Unsupported('Independent GT display alias context was not captured')
        record = context['aliases'].get(resource_id)
        if record is None:
            raise Unsupported(f'GT display alias context is missing for {resource_id}')
        if record['status'] != 'ok':
            raise Unsupported(f'GT display alias context is {record["status"]} for {resource_id}: {_json(record.get("failure"))}')
        declared = [dict(stack, kind='item', amount=amount) for stack in record['alternatives']]
    expanded = []
    for stack in declared:
        if stack['metadata'] != 32767:
            expanded.append(stack)
            continue
        if context is None:
            raise Unsupported('Independent NEI wildcard item pool was not captured')
        pool = context['pools'].get(stack['registry_name'])
        if pool is None:
            raise Unsupported(f'NEI wildcard item pool is missing for {stack["registry_name"]}')
        if pool['status'] == 'failed':
            raise Unsupported(f'NEI wildcard item pool failed for {stack["registry_name"]}: {_json(pool["failure"])}')
        if pool['status'] == 'empty':
            expanded.append(dict(stack, metadata=0))
        else:
            expanded.extend(dict(entry, kind='item', amount=amount) for entry in pool['entries'])
    return expanded


def _typed_nbt(tag):
    if tag is None:
        return None
    kind, value = tag['type'], tag['value']
    if kind == 'compound':
        return {key: _typed_nbt(child) for key, child in value.items()}
    if kind in ('int', 'string'):
        return value
    if kind in ('byte', 'short', 'long'):
        return str(value) + {'byte': 'B', 'short': 'S', 'long': 'L'}[kind]
    if kind in ('float', 'double'):
        raise Unsupported('NBT floating-point Java formatting is not independently mapped')
    if kind == 'list':
        if not value:
            raise Unsupported('Empty NBT list loses its element type in NBTJson')
        return [_typed_nbt(child) for child in value]
    if kind in ('byte_array', 'int_array') and value:
        return [str(item) + 'B' for item in value] if kind == 'byte_array' else value
    raise Unsupported(f'NBT projection not mapped: {kind}')


def _resource_identity(resource):
    nbt = _typed_nbt(resource.get('nbt'))
    if resource['kind'] == 'fluid' and nbt not in (None, {}):
        raise Unsupported('Fluid display serializers omit fluid NBT')
    return _json([resource['kind'], resource['registry_name'], resource['metadata'] if resource['kind'] == 'item' else None, nbt or None])


def _chance(value):
    if not isinstance(value, dict):
        raise Unsupported('Chance is unknown in the canonical record')
    fraction = Fraction(value['numerator'], value['denominator'])
    return [fraction.numerator, fraction.denominator]


def _slot(alternatives, chance, real_amount=None):
    # Duplicate entries within an OR set do not create another required slot.
    return {'alternatives': sorted({_json(entry) for entry in alternatives}), 'chance': chance, 'real_amount': real_amount}


def _projection(inputs, outputs):
    return {'inputs': sorted(inputs, key=_json), 'outputs': sorted(outputs, key=_json)}


def _native_identity(stack):
    if not isinstance(stack, dict):
        raise Unsupported('Null or unsupported native stack serialization')
    if 'neiFluidName' in stack and set(stack) <= {'neiFluidName', 'Count'}:
        count = stack.get('Count')
        if isinstance(count, str) and re.fullmatch(r'-?\d+L', count):
            count = int(count[:-1])
        identity = _json(['fluid', stack['neiFluidName'], None, None])
    elif 'strId' in stack and set(stack) <= {'strId', 'Count', 'Damage', 'tag'}:
        if type(stack.get('Damage')) is not int:
            raise Unsupported('Item metadata is not the pinned DefaultStackStringifyHandler integer')
        count = stack.get('Count')
        identity = _json(['item', stack['strId'], stack['Damage'], stack.get('tag') or None])
    else:
        raise Unsupported('Native stack serializer is outside the pinned item/fluid mapping')
    if type(count) is not int:
        raise Unsupported('Native Count is not a supported integer/long projection')
    return identity, count


def _profile(handler, view):
    if handler['native_class'] == FURNACE_HANDLER:
        return ('minecraft:smelting', 'furnace', True, False)
    family = handler.get('gt_recipe_map_id')
    fields = view.get('displayed_fields') or {}
    if handler['native_class'] != GT_HANDLER or family not in GT_FAMILIES:
        raise Unsupported('Handler/map is outside the source-proven adapter allowlist')
    if fields.get('frontend_class') != GT_FRONTEND:
        raise Unsupported('Custom or unknown GT frontend transformations are not mapped')
    if type(fields.get('render_real_stack_sizes')) is not bool or type(fields.get('unificate_output')) is not bool:
        raise Unsupported('GT display normalization properties were not captured')
    return (family, 'gt', fields['render_real_stack_sizes'], fields['unificate_output'])


def _view_projection(view, profile, ambiguous):
    if view.get('failure') or view.get('failures'):
        raise Unsupported('Handler getter failed during reference capture')
    family, adapter, _, _ = profile
    if not isinstance(view.get('ingredients'), list) or not isinstance(view.get('other_stacks'), list):
        raise Unsupported('A handler category was not captured')
    outputs = view['other_stacks'] if adapter == 'gt' else [view['result']] if view.get('result') else []
    if adapter == 'gt' and view.get('result') is not None:
        raise Unsupported('GT default handler unexpectedly has a primary result')
    if not outputs:
        raise Unsupported('No displayed output identity')

    def positioned(value):
        alternatives = []
        kinds = set()
        for alternative in value['alternatives']:
            if alternative.get('failure'):
                raise Unsupported('Stack serialization failed during reference capture')
            identity, count = _native_identity(alternative.get('native_stack'))
            if identity in ambiguous:
                raise Unsupported('Ambiguous identity: different typed NBT resources have the same NBTJson projection')
            alternatives.append([identity, count])
            kinds.add(json.loads(identity)[0])
        if not alternatives:
            raise Unsupported('Empty displayed alternative set')
        probability = None
        if adapter == 'gt':
            if value.get('native_class') != GT_HANDLER + '$FixedPositionedStack':
                raise Unsupported('Positioned stack is outside the source-proven GT chance mapping')
            if type(value.get('chance')) is not int:
                raise Unsupported('GT positioned chance was not captured')
            probability = _chance({'numerator': value['chance'], 'denominator': 10000})
        real_amount = value.get('real_stack_size') if adapter == 'gt' and kinds == {'item'} else None
        if adapter == 'gt' and kinds == {'item'} and type(real_amount) is not int:
            raise Unsupported('GT real stack size was not captured')
        return _slot(alternatives, probability, real_amount)

    return _projection([positioned(value) for value in view['ingredients']], [positioned(value) for value in outputs])


def _canonical_projection(process, profile, resources, ambiguous, context):
    _, adapter, render_real, unify_output = profile
    conditions = process.get('conditions', {})
    if conditions.get('dynamic_output') == 'unresolved':
        raise Unsupported('Declared outputs are unresolved native display templates')
    if adapter == 'gt' and conditions.get('special_items') is not None:
        raise Unsupported('GT special-slot presentation is not mapped')

    def alternatives(resource_id, amount, unify, *, is_input=False):
        if resource_id is None:
            raise Unsupported('Declared native item has no registered canonical resource anchor')
        resource = resources[resource_id]
        stacks = _item_presentation(resource_id, resource, amount, unify, context) if resource['kind'] == 'item' else [dict(resource, amount=amount)]
        entries = []
        for stack in stacks:
            identity = _resource_identity(stack)
            if identity in ambiguous:
                raise Unsupported('Ambiguous identity: different typed NBT resources have the same NBTJson projection')
            display_amount = 1 if (adapter == 'furnace' and is_input) or (stack['kind'] == 'item' and not render_real) else stack['amount']
            entries.append([identity, display_amount])
        return entries, stacks[0]['amount'] if resource['kind'] == 'item' and stacks else None

    outputs = []
    for output in process['outputs']:
        entries, first_amount = alternatives(output['resource_id'], output['amount'], adapter == 'gt' and unify_output)
        kind = resources[output['resource_id']]['kind']
        outputs.append(_slot(entries, _chance(output['chance']) if adapter == 'gt' else None, first_amount if adapter == 'gt' and kind == 'item' else None))
    try:
        inputs = []
        for slot in process['inputs']:
            entries, kinds, first_amount = [], set(), None
            for choice in slot['choices']:
                if choice['match']['mode'] not in ('exact', 'unified', 'ore_dict', 'wildcard'):
                    if choice.get('resource_id') is None:
                        raise Unsupported('Declared native item has no registered canonical resource anchor')
                    raise Unsupported('Ingredient display predicate/declared alternatives are not mapped')
                amount = choice.get('native_amount', choice['amount'])
                choices, representative = alternatives(choice.get('resource_id'), amount, adapter == 'gt', is_input=True)
                if not entries:
                    first_amount = representative
                entries.extend(choices)
                kinds.add(resources[choice['resource_id']]['kind'])
            probability = _chance(slot.get('consumption_chance')) if adapter == 'gt' else None
            inputs.append(_slot(entries, probability, first_amount if adapter == 'gt' and kinds == {'item'} else None))
    except Unsupported as error:
        # Known outputs bind an unresolved input projection to its reference case.
        error.output_key = _output_key({'outputs': outputs})
        raise
    return _projection(inputs, outputs)


def _output_key(projection):
    return _json(sorted(sorted(json.loads(entry)[0] for entry in slot['alternatives']) for slot in projection['outputs']))


def _differences(left, right):
    fields = []
    for name in ('inputs', 'outputs'):
        identities = lambda slots: sorted(sorted(json.loads(entry)[0] for entry in slot['alternatives']) for slot in slots)
        amounts = lambda slots: sorted(_json([slot['alternatives'], slot['real_amount']]) for slot in slots)
        chances = lambda slots: sorted(_json([sorted(json.loads(entry)[0] for entry in slot['alternatives']), slot['chance']]) for slot in slots)
        if identities(left[name]) != identities(right[name]):
            fields.append('alternatives')
            continue
        if amounts(left[name]) != amounts(right[name]):
            fields.append('amounts')
        if chances(left[name]) != chances(right[name]):
            fields.append('chances')
    return sorted(set(fields))


def compare(snapshot, reference, *, example_limit=20):
    started = time.perf_counter()
    phase_started = started
    timings = {}

    def finish_phase(name):
        nonlocal phase_started
        now = time.perf_counter()
        timings[name] = round(now - phase_started, 3)
        phase_started = now

    if type(example_limit) is not int or not 0 <= example_limit <= 1000:
        raise ComparisonError('example_limit must be between 0 and 1000')
    snapshot, reference = Path(snapshot), Path(reference)
    manifest = json.loads((snapshot / 'manifest.json').read_text(encoding='utf-8'))
    summary = json.loads((reference / 'summary.json').read_text(encoding='utf-8'))
    if manifest.get('schema_version') != 1 or summary.get('schema_version') != 1:
        raise ComparisonError('Only canonical and reference schema version 1 are mapped')
    if summary.get('canonical_snapshot_id') != manifest['snapshot_id'] or summary.get('canonical_pack') != manifest['pack']:
        raise ComparisonError('Reference snapshot identity or pack/config cohort does not match')
    mods = {mod['id']: mod for mod in manifest['pack']['mods']}
    for id, (version, checksum) in PINNED_MODS.items():
        if id not in mods or (mods[id].get('version'), mods[id].get('sha256')) != (version, checksum):
            raise ComparisonError(f'Unmapped runtime version/hash for {id}')
    handler_records = list(_records(reference, 'handlers.jsonl.gz', summary['files']))
    handlers = {record['handler_key']: record for record in handler_records}
    if len(handlers) != len(handler_records):
        raise ComparisonError('Duplicate handler_key in reference inventory')
    finish_phase('cohort_and_handlers')

    def validate_reference(record, seen_indexes):
        if record['handler_key'] not in handlers:
            raise ComparisonError('Reference record has an unresolved handler_key')
        if type(record.get('recipe_index')) is not int or record['recipe_index'] < 0:
            raise ComparisonError('Invalid reference recipe_index')
        key = (record['handler_key'], record['recipe_index'])
        if key in seen_indexes:
            raise ComparisonError('Duplicate reference handler/recipe index')
        seen_indexes.add(key)

    signature_indexes = set()
    observed_failures = sum(bool(handler.get('failure')) or handler.get('enumeration_status') == 'failed' for handler in handlers.values())
    for signature in _records(reference, 'signatures.jsonl.gz', summary['files']):
        validate_reference(signature, signature_indexes)
        if signature.get('projection') != 'native_recipe_id_api':
            raise ComparisonError('Signature projection label is not the pinned native RecipeId API')
        observed_failures += bool(signature.get('failure'))
    signature_count = len(signature_indexes)
    del signature_indexes
    finish_phase('reference_signatures')
    resources = {record['id']: record for record in _records(snapshot, 'resources.jsonl.gz', manifest['files'])}
    for _ in _records(snapshot, 'groups.jsonl.gz', manifest['files']):
        pass
    context, context_report = _presentation_context(reference, summary, manifest, resources)
    typed_identities = defaultdict(set)
    for resource in resources.values():
        try:
            identity = _resource_identity(resource)
            typed_identities[identity].add(_json([resource['kind'], resource['registry_name'], resource['metadata'], resource['nbt']]))
        except Unsupported:
            pass
    for resource in _context_items(context):
        try:
            identity = _resource_identity(resource)
            typed_identities[identity].add(_json(['item', resource['registry_name'], resource['metadata'], resource['nbt']]))
        except Unsupported:
            pass
    ambiguous = {identity for identity, typed in typed_identities.items() if len(typed) > 1}
    del typed_identities
    finish_phase('canonical_resources_and_groups')
    counts = Counter(matched=0, differences=0, missing_canonical=0, missing_nei=0, unsupported=0, excluded_hidden=0,
                     canonical_records=0, canonical_outside_mapped_profiles=0, reference_handlers=len(handlers), reference_views=0)
    examples = {name: [] for name in ('differences', 'missing_canonical', 'missing_nei', 'unsupported')}
    reasons = Counter()

    def unsupported(reason, detail):
        counts['unsupported'] += 1
        reasons[reason] += 1
        if len(examples['unsupported']) < example_limit:
            examples['unsupported'].append({'reason': reason, **detail})

    profiles, normalized_views = set(), []
    handlers_with_views, view_indexes = set(), set()
    for view in _records(reference, 'handler-views.jsonl.gz', summary['files']):
        validate_reference(view, view_indexes)
        counts['reference_views'] += 1
        handlers_with_views.add(view['handler_key'])
        observed_failures += bool(view.get('failure') or view.get('failures'))
        positions = (view.get('ingredients') or []) + (view.get('other_stacks') or []) + ([view['result']] if view.get('result') else [])
        observed_failures += sum(bool(alternative.get('failure')) for positioned in positions for alternative in positioned.get('alternatives', []))
        handler = handlers[view['handler_key']]
        try:
            profile = _profile(handler, view)
            profiles.add(profile)
            normalized_views.append(({'handler_key': view['handler_key'], 'recipe_index': view['recipe_index']}, profile,
                                     _view_projection(view, profile, ambiguous)))
        except Unsupported as error:
            unsupported(str(error), {'side': 'nei', 'handler_key': view['handler_key'], 'recipe_index': view['recipe_index']})
    del view_indexes
    for handler in handlers.values():
        if handler['handler_key'] not in handlers_with_views:
            unsupported('Handler has no captured views. Its recipe coverage is unverified', {'side': 'nei', 'handler_key': handler['handler_key'],
                        'enumeration_status': handler['enumeration_status'], 'recipe_count': handler.get('recipe_count')})
    if summary.get('counts') != {'handlers': len(handlers), 'signatures': signature_count, 'handler_views': counts['reference_views']}:
        raise ComparisonError('Reference summary counts do not match the streams')
    finish_phase('reference_views_projection')
    catalog = defaultdict(dict)
    output_index = defaultdict(set)
    unresolved_outputs = defaultdict(list)
    unresolved_anchors = defaultdict(list)
    for process in _records(snapshot, 'processes.jsonl.gz', manifest['files']):
        counts['canonical_records'] += 1
        applicable = [profile for profile in profiles if profile[0] == process['family']]
        if not applicable:
            counts['canonical_outside_mapped_profiles'] += 1
            continue
        if process.get('conditions', {}).get('hidden') is True:
            counts['excluded_hidden'] += 1
            continue
        for profile in applicable:
            try:
                projection = _canonical_projection(process, profile, resources, ambiguous, context)
                key = _json(projection)
                catalog[profile].setdefault(key, {'projection': projection, 'process_ids': []})['process_ids'].append(process['id'])
                output_index[(profile, _output_key(projection))].add(key)
            except Unsupported as error:
                unsupported(str(error), {'side': 'canonical', 'process_id': process['id'], 'family': process['family']})
                unresolved = {'process_id': process['id'], 'reason': str(error)}
                if hasattr(error, 'output_key'):
                    unresolved_outputs[(profile, error.output_key)].append(unresolved)
                else:
                    try:
                        anchors = {_resource_identity(resources[output['resource_id']]) for output in process['outputs']}
                        if anchors and not anchors.intersection(ambiguous) and all(json.loads(identity)[2] != 32767 for identity in anchors):
                            unresolved['anchors'] = anchors
                            for identity in anchors:
                                unresolved_anchors[(profile, identity)].append(unresolved)
                    except (Unsupported, KeyError):
                        pass
    finish_phase('canonical_recipe_projection')
    seen, uncertain = set(), set()
    for view, profile, projection in normalized_views:
        exact = _json(projection)
        detail = {'handler_key': view['handler_key'], 'recipe_index': view['recipe_index'], 'family': profile[0]}
        if exact in catalog[profile]:
            counts['matched'] += 1
            seen.add((profile, exact))
            continue
        output_key = _output_key(projection)
        candidates = output_index.get((profile, output_key), set())
        unresolved = list(unresolved_outputs.get((profile, output_key), []))
        output_identities = {json.loads(entry)[0] for slot in projection['outputs'] for entry in slot['alternatives']}
        # Direct canonical output anchors only identify unresolved boundaries.
        # They never establish expected alternatives or a successful match.
        unresolved.extend(item for identity in output_identities for item in unresolved_anchors.get((profile, identity), [])
                          if item['anchors'] <= output_identities)
        if unresolved:
            unsupported('Canonical presentation dependencies are unresolved: ' + ' | '.join(sorted({item['reason'] for item in unresolved})),
                        {'side': 'nei', **detail, 'canonical_process_ids': sorted({item['process_id'] for item in unresolved})[:example_limit]})
            uncertain.update((profile, key) for key in candidates)
        elif len(candidates) == 1:
            key = next(iter(candidates))
            candidate = catalog[profile][key]
            counts['differences'] += 1
            seen.add((profile, key))
            if len(examples['differences']) < example_limit:
                examples['differences'].append({**detail, 'process_ids': candidate['process_ids'][:example_limit],
                    'fields': _differences(candidate['projection'], projection), 'canonical': candidate['projection'], 'nei': projection})
        elif candidates:
            unsupported('Ambiguous recipe identity: multiple canonical candidates share displayed output identities', detail)
            uncertain.update((profile, key) for key in candidates)
        else:
            counts['missing_canonical'] += 1
            if len(examples['missing_canonical']) < example_limit:
                examples['missing_canonical'].append({**detail, 'nei': projection})
    accounted = seen | uncertain
    for profile, records in catalog.items():
        for key, candidate in records.items():
            if (profile, key) not in accounted:
                counts['missing_nei'] += 1
                if len(examples['missing_nei']) < example_limit:
                    examples['missing_nei'].append({'family': profile[0], 'process_ids': candidate['process_ids'][:example_limit], 'canonical': candidate['projection'],
                        'reason': 'Not displayed by captured mapped handlers. Category enable/merge settings may limit NEI presentation'})
    finish_phase('semantic_matching')
    # Verify the remaining canonical streams too, without inventing recipe semantics for them.
    for filename in ('sources.jsonl.gz', 'environments.jsonl.gz', 'coverage.jsonl.gz'):
        for _ in _records(snapshot, filename, manifest['files']):
            pass
    capture_failures = max(observed_failures, sum(summary.get(name, 0) for name in ('failed_handlers', 'failed_signatures', 'failed_views', 'failed_stacks')))
    finish_phase('remaining_stream_validation')
    timings['total'] = round(time.perf_counter() - started, 3)
    return {'schema_version': 1, 'canonical_snapshot_id': manifest['snapshot_id'], 'scope': SOURCE_SCOPE, 'counts': dict(counts),
            'unsupported_reasons': dict(reasons), 'examples': examples, 'example_limit': example_limit,
            'reference_complete': summary.get('complete') is True, 'capture_failures': capture_failures,
            'presentation_context': context_report,
            'capture_failure_unit': 'events, not distinct affected recipes',
            'mapped_profiles': [list(profile) for profile in sorted(profiles)], 'ambiguous_resource_projections': len(ambiguous),
            'ambiguous_canonical_candidates': len(uncertain - seen),
            'timings_seconds': timings,
            'native_signatures': {'records': signature_count, 'comparison_to_canonical': False, 'scope': 'Capture integrity and native API projection label only'},
            'limitations': ['No pack-wide equivalence claim', 'Display agreement does not prove execution, yields or native machine predicates',
                            'NBTJson is not injective. Typed NBT agreement is not proven', 'Generic handler chances are not production probability',
                            'Unmapped handlers, recipe maps, frontends and crafting layouts remain unverified',
                            'Hidden GT recipes excluded. Disabled/fake recipes are retained for display comparison',
                            'Furnace auxiliary fuel is not an output. Fuel, time, EU and XP are unverified',
                            'Counts compare unique canonical presentation projections, not duplicate registration multiplicities']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--example-limit', type=int, default=20)
    parser.add_argument('--max-missing', type=int, default=0)
    parser.add_argument('--max-differences', type=int, default=0)
    parser.add_argument('--max-capture-failures', type=int, default=0)
    parser.add_argument('--max-unsupported', type=int)
    args = parser.parse_args(argv)
    try:
        for value in (args.max_missing, args.max_differences, args.max_capture_failures, args.max_unsupported):
            if value is not None and value < 0:
                raise ComparisonError('Thresholds must be nonnegative')
        report = compare(args.snapshot, args.reference or args.snapshot / 'nei-reference', example_limit=args.example_limit)
        counts = report['counts']
        passed = (counts['matched'] + counts['differences'] > 0
                  and counts['missing_canonical'] + counts['missing_nei'] <= args.max_missing and counts['differences'] <= args.max_differences
                  and report['capture_failures'] <= args.max_capture_failures and report['reference_complete']
                  and (not report['presentation_context']['available'] or report['presentation_context']['complete'])
                  and (args.max_unsupported is None or counts['unsupported'] <= args.max_unsupported))
        report['thresholds'] = {'max_missing': args.max_missing, 'max_differences': args.max_differences,
                                'max_capture_failures': args.max_capture_failures, 'max_unsupported': args.max_unsupported, 'passed': passed}
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(_json(report) + '\n', encoding='utf-8')
        print(_json({'scope': 'Mapped NEI presentation only', 'counts': counts, 'capture_failures': report['capture_failures'],
                     'reference_complete': report['reference_complete'],
                     'presentation_context': {key: report['presentation_context'][key] for key in ('available', 'complete', 'failure_count')},
                     'thresholds_passed': passed, 'report': str(args.report)}))
        return 0 if passed else 1
    except (ComparisonError, OSError, ValueError, KeyError, TypeError, EOFError) as error:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(_json({'status': 'invalid_reference_or_canonical_artifact', 'error': str(error)}) + '\n', encoding='utf-8')
        print(_json({'error': str(error), 'report': str(args.report)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
