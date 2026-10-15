"""Compare persisted canonical recipes with a deliberately scoped NEI presentation reference.

The canonical side comes exclusively from checksummed snapshot streams. Native
RecipeId API records are inventoried separately, never used as canonical recipes.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import re
import sys
import time
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

GT_HANDLER = 'gregtech.nei.GTNEIDefaultHandler'
FURNACE_HANDLER = 'codechicken.nei.recipe.FurnaceRecipeHandler'
GT_FRONTEND = 'gregtech.api.recipe.RecipeMapFrontend'
DEFAULT_SERIALIZER = 'codechicken.nei.recipe.stackinfo.DefaultStackStringifyHandler'
BUILTIN_SERIALIZERS = frozenset((DEFAULT_SERIALIZER, 'codechicken.nei.recipe.stackinfo.FluidDisplayStackStringifyHandler',
                                'codechicken.nei.recipe.stackinfo.GTFluidStackStringifyHandler'))
ITEM_PROJECTION_API = 'StackInfo.itemStackToNBT(stack,true)->NBTJson.toJsonObject'
ITEM_DISPATCH_API = 'StackInfo.stackStringifyHandlers.reverse.convertItemStackToNBT(stack,true)->NBTJson.toJsonObject'
HANDLER_ITEM_FACTS = {'version': 1, 'stage': 'before_native_serialization', 'identity': 'registry_metadata_typed_nbt',
                      'quantity': 'positioned_item_stack_size', 'native_input': 'detached_positioned_copy',
                      'native_api': ITEM_DISPATCH_API, 'count_classification': 'selected_default_at_observed_quantity'}
GT_FAMILIES = frozenset('gregtech:gt.recipe.' + name for name in ('alloysmelter', 'metalbender', 'macerator', 'orewasher', 'fluidsolidifier'))
HISTORICAL_GT_FAMILIES = frozenset(('gregtech:gt.recipe.alloysmelter', 'gregtech:gt.recipe.metalbender',
                                   'gregtech:gt.recipe.macerator', 'gregtech:gt.recipe.orewasher'))
PINNED_MODS = {
    'NotEnoughItems': ('2.8.159-GTNH', '050b2440952adc930e871586f496607959344aa2d7c3be781fd922a5b253a3af'),
    'gregtech': ('5.09.54.221', '60ceb229cd894dd28393efb6d0013de2835289eeef6fcf84ad3e17a6475baf5b'),
}
STILL_HANDLER = 'forestry.factory.recipes.nei.NEIHandlerStill'
STILL_CACHED_RECIPE = STILL_HANDLER + '$CachedStillRecipe'
STILL_PROFILE = ('forestry:still', 'forestry_still')
STILL_PINNED_MODS = {
    'Forestry': ('4.11.39', 'f3cacea1f523a5b94bf3f7bcc811c49dd5224d5024ac3d98fb6ac3b26a51547f'),
    'NotEnoughItems': ('2.8.160-GTNH', '723984da9883980f1b13a71e3e500ed52ea3c059141ef931078a8ea511a1ae17'),
}
STILL_SOURCE_SCOPE = {
    'forestry_commit': 'f2e85073d33f50f9eec874cdabef41e1a85b297f',
    'components': {name: {'version': version, 'sha256': checksum} for name, (version, checksum) in STILL_PINNED_MODS.items()},
    'family': 'forestry:still', 'projection': 'unscaled_per_unit_templates',
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
    if type(metadata.get('schema_version')) is not int or metadata['schema_version'] not in (1, 2, 3):
        raise ComparisonError('Only presentation context schema versions 1, 2 and 3 are mapped')
    if metadata.get('canonical_snapshot_id') != manifest['snapshot_id'] or metadata.get('canonical_pack') != manifest['pack']:
        raise ComparisonError('Presentation context snapshot identity or pack/config cohort does not match')
    expected_files = {name: manifest['files'][name] for name in ('resources.jsonl.gz', 'processes.jsonl.gz')}
    if metadata.get('canonical_files') != expected_files:
        raise ComparisonError('Presentation context canonical file binding does not match')
    scope = metadata.get('scope') or {}
    advertised = scope.get('gt_families')
    if not isinstance(advertised, list) or any(not isinstance(family, str) for family in advertised):
        raise ComparisonError('Invalid presentation context GT scope')
    captured_families = frozenset(advertised)
    if (captured_families not in (HISTORICAL_GT_FAMILIES, GT_FAMILIES) or len(advertised) != len(captured_families)
            or scope.get('furnace_family') != 'minecraft:smelting'
            or type(scope.get('alias_template_amount')) is not int or scope['alias_template_amount'] != 1):
        raise ComparisonError('Presentation context scope is not the pinned item adapter scope')
    if metadata['schema_version'] == 3 and scope.get('supplementary_families') != ['botania:mana_infusion']:
        raise ComparisonError('Invalid supplementary declaration scope')
    if type(metadata.get('complete')) is not bool or not isinstance(metadata.get('failures'), list):
        raise ComparisonError('Presentation context completeness/failures were not captured')
    aliases, pools, projections = {}, {}, {}
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
    registry_supported = False
    if metadata['schema_version'] >= 2:
        capability = metadata.get('item_projection')
        expected_api = ITEM_DISPATCH_API if metadata['schema_version'] == 3 else ITEM_PROJECTION_API
        expected_classification = 'selected_pinned_default_item_count' if metadata['schema_version'] == 3 else 'pinned_builtin_default_item_count'
        if (not isinstance(capability, dict) or capability.get('api') != expected_api
                or type(capability.get('template_item_amount')) is not int or capability['template_item_amount'] != 1
                or capability.get('classification') != expected_classification
                or not isinstance(capability.get('serializer_classes'), list)
                or any(not isinstance(name, str) or not name for name in capability['serializer_classes'])):
            raise ComparisonError('Invalid native item projection capability/serializer registry')
        classes = capability['serializer_classes']
        registry_supported = bool(classes) and DEFAULT_SERIALIZER in classes and set(classes) <= BUILTIN_SERIALIZERS
        for record in _records(reference, 'item-projections.jsonl.gz', metadata['files']):
            if (not isinstance(record.get('registry_name'), str) or not record['registry_name']
                    or type(record.get('metadata')) is not int or 'nbt' not in record):
                raise ComparisonError('item-projections.jsonl.gz: invalid typed identity')
            key = _typed_item_key(record)
            if key in projections:
                raise ComparisonError('item-projections.jsonl.gz: duplicate typed identity')
            status = record.get('status')
            if (status not in ('ok', 'failed') or (status == 'ok' and not isinstance(record.get('native_stack'), dict))
                    or (status == 'failed' and (record.get('native_stack') is not None or not record.get('failure')))
                    or (status == 'ok' and record.get('failure'))
                    or record.get('count_semantics') not in ('item_stack_size', 'native_conversion', 'unknown')
                    or (record.get('serializer_class') is not None and not isinstance(record['serializer_class'], str))):
                raise ComparisonError('item-projections.jsonl.gz: invalid projection status/payload/classification')
            if metadata['schema_version'] == 3 and status == 'ok' and (not isinstance(record.get('serializer_class'), str)
                    or not record['serializer_class'] or record['serializer_class'] not in classes):
                raise ComparisonError('item-projections.jsonl.gz: selected serializer is absent from the declared registry')
            projections[key] = record
            counts['item-projections.jsonl.gz:' + status] += 1
    entry_failures = [{'stream': name, key: id, 'failure': record['failure']}
                      for name, mapping, key in (('gt-display-aliases.jsonl.gz', aliases, 'resource_id'),
                                                 ('item-pools.jsonl.gz', pools, 'registry_name'))
                      for id, record in mapping.items() if record['status'] == 'failed']
    entry_failures.extend({'stream': 'item-projections.jsonl.gz', 'identity': key, 'failure': record['failure']}
                          for key, record in projections.items() if record['status'] == 'failed')
    failures = len(metadata['failures']) + len(entry_failures)
    if failures and metadata['complete']:
        raise ComparisonError('Presentation context claims complete despite captured failures')
    return {'aliases': aliases, 'pools': pools, 'failures': metadata['failures'], 'version': metadata['schema_version'],
            'projections': projections, 'registry_supported': registry_supported, 'gt_families': captured_families}, {
        'available': True, 'complete': metadata['complete'], 'failure_count': failures,
        'failures': metadata['failures'], 'entry_failures': entry_failures, 'failure_unit': 'events, not distinct affected recipes',
        'entry_counts': dict(counts), 'readiness': metadata.get('readiness')}


def _context_items(context):
    if context is not None:
        for mapping, field in ((context['aliases'], 'alternatives'), (context['pools'], 'entries')):
            for record in mapping.values():
                for stack in record[field]:
                    yield dict(stack, kind='item')
        for record in context.get('projections', {}).values():
            yield dict(record, kind='item')


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


def _typed_item_key(resource):
    return _json([resource['registry_name'], resource['metadata'], resource['nbt']])


def _exact_typed_nbt(tag):
    """Validate native typed evidence without converting it through NBTJson."""
    if tag is None:
        return
    if not isinstance(tag, dict) or 'type' not in tag or 'value' not in tag:
        raise Unsupported('Malformed typed fluid NBT')
    kind, value = tag['type'], tag['value']
    names = ('end', 'byte', 'short', 'int', 'long', 'float', 'double', 'byte_array', 'string', 'list', 'compound', 'int_array')
    if kind not in names or set(tag) != ({'type', 'value', 'element_type_id'} if kind == 'list' else {'type', 'value'}):
        raise Unsupported('Malformed typed fluid NBT fields/type')
    if kind == 'compound':
        valid = isinstance(value, dict)
        if valid:
            for child in value.values():
                _exact_typed_nbt(child)
                if child is None or child['type'] == 'end':
                    valid = False
    elif kind == 'list':
        element = tag['element_type_id']
        valid = type(element) is int and 0 <= element < len(names) and isinstance(value, list)
        if valid:
            for child in value:
                _exact_typed_nbt(child)
                if child is None or child['type'] == 'end' or child['type'] != names[element]:
                    valid = False
    elif kind in ('byte', 'short', 'int'):
        bits = {'byte': 8, 'short': 16, 'int': 32}[kind]
        valid = type(value) is int and -(2 ** (bits - 1)) <= value < 2 ** (bits - 1)
    elif kind in ('byte_array', 'int_array'):
        bits = 8 if kind == 'byte_array' else 32
        valid = isinstance(value, list) and all(type(entry) is int and -(2 ** (bits - 1)) <= entry < 2 ** (bits - 1) for entry in value)
    elif kind == 'long':
        valid = isinstance(value, str) and re.fullmatch(r'-?(0|[1-9][0-9]*)', value) is not None and -(2 ** 63) <= int(value) < 2 ** 63
    elif kind in ('float', 'double'):
        valid = type(value) in (int, float) and math.isfinite(value) and (kind != 'float' or abs(value) <= 3.4028235e38)
    elif kind == 'string':
        valid = isinstance(value, str)
    else:
        valid = value is None
    if not valid:
        raise Unsupported('Malformed typed fluid NBT value')


def _still_fluid(template, resources=None):
    if (not isinstance(template, dict) or not isinstance(template.get('registry_name'), str) or not template['registry_name']
            or type(template.get('amount')) is not int or not 0 < template['amount'] <= 2147483647 or 'nbt' not in template):
        raise Unsupported('Still fluid template requires a registered identity, positive int32 amount and typed NBT')
    _exact_typed_nbt(template['nbt'])
    identity = _json(['fluid', template['registry_name'], None, template['nbt']])
    if resources is not None:
        if template.get('status') != 'registered' or not isinstance(template.get('native_fluid_class'), str) or not template['native_fluid_class']:
            raise Unsupported('Still canonical fluid template is not a captured registered fluid')
        if 'resource_id' in template:
            resource = resources.get(template['resource_id']) if isinstance(template['resource_id'], str) else None
            if (resource is None or resource.get('kind') != 'fluid' or resource.get('metadata') is not None
                    or resource.get('registry_name') != template['registry_name'] or 'nbt' not in resource
                    or _json(resource['nbt']) != _json(template['nbt'])):
                raise Unsupported('Still canonical fluid template resource link does not preserve exact identity/NBT')
    return _slot([[identity, template['amount']]], None)


def _still_view_projection(handler, view):
    if (handler.get('native_class') != STILL_HANDLER or handler.get('queried_native_class') != STILL_HANDLER
            or handler.get('handler_id') != STILL_HANDLER or handler.get('native_recipe_id') != 'forestry.still'):
        raise Unsupported('Still handler identity is outside the verified exact native class/ID')
    facts = view.get('forestry_still_tanks')
    if (not isinstance(facts, dict) or facts.get('status') != 'captured' or facts.get('reason') is not None
            or facts.get('failure') is not None or view.get('failure') or view.get('failures')):
        raise Unsupported('Still typed tank observation is missing, unsupported or failed')
    if (view.get('ingredients') != [] or view.get('other_stacks') != [] or 'result' not in view or view['result'] is not None
            or facts.get('quantity_scope') != 'unscaled_per_unit_templates' or facts.get('cached_recipe_class') != STILL_CACHED_RECIPE
            or facts.get('getter_declaring_class') != STILL_CACHED_RECIPE or facts.get('source_api') != STILL_CACHED_RECIPE + '.getFluidTanks'):
        raise Unsupported('Still view capability or generic item shape is outside the verified tank projection')
    tanks = facts.get('tanks')
    if not isinstance(tanks, list) or len(tanks) != 2:
        raise Unsupported('Still view requires exactly two ordered tank positions')
    slots = []
    for ordinal, (tank, x) in enumerate(zip(tanks, (30, 120))):
        if (not isinstance(tank, dict) or type(tank.get('ordinal')) is not int or tank['ordinal'] != ordinal
                or tank.get('native_class') != 'forestry.core.recipes.nei.PositionedFluidTank'
                or tank.get('position') != {'x': x, 'y': 4, 'width': 16, 'height': 58}
                or tank.get('show_amount') is not True or tank.get('per_tick') is not False
                or not isinstance(tank.get('alternatives'), list) or len(tank['alternatives']) != 1):
            raise Unsupported('Still positioned tank shape/order is outside the verified handler')
        alternative = tank['alternatives'][0]
        if (not isinstance(alternative, dict) or type(alternative.get('ordinal')) is not int or alternative['ordinal'] != 0
                or alternative.get('native_class') != 'net.minecraftforge.fluids.FluidTank'
                or type(alternative.get('capacity')) is not int or alternative['capacity'] != 10000):
            raise Unsupported('Still tank alternative class, ordinal or capacity is unsupported')
        slots.append(_still_fluid(alternative.get('fluid')))
    return _projection([slots[0]], [slots[1]])


def _still_canonical_projection(process, resources):
    facts = process.get('conditions') or {}
    if (facts.get('native_class') != 'forestry.factory.recipes.StillRecipe' or facts.get('native_version') != '4.11.39'
            or facts.get('declaration_status') != 'captured_exact_native_class'):
        raise Unsupported('Still canonical declaration is outside the verified exact recipe class/version')
    return _projection([_still_fluid(facts.get('native_input_template'), resources)],
                       [_still_fluid(facts.get('native_output_template'), resources)])


def _ordinary_item_projection(context, record):
    return (record['serializer_class'] == DEFAULT_SERIALIZER and record['count_semantics'] == 'item_stack_size'
            and (context['version'] == 3 or context['registry_supported']))


def _resource_identity(resource, context=None):
    if resource['kind'] == 'item' and context is not None and context['version'] >= 2:
        record = context['projections'].get(_typed_item_key(resource))
        if record is None:
            raise Unsupported('Exact native item projection is missing for this typed identity')
        if record['status'] == 'failed':
            raise Unsupported('Exact native item projection failed: ' + _json(record['failure']))
        if not _ordinary_item_projection(context, record):
            raise Unsupported('Native item projection serializer/conversion does not establish ordinary item count semantics')
        identity, count = _native_identity(record['native_stack'])
        native = json.loads(identity)
        if count != 1 or native[:3] != ['item', resource['registry_name'], resource['metadata']]:
            raise Unsupported('Native item projection does not preserve the declared ordinary item identity/template count')
        if not context.get('handler_item_facts') and (resource['registry_name'], resource['metadata']) in context.get('uncertain_buckets', set()):
            raise Unsupported('A typed variant in this item identity bucket has an unresolved native projection')
        if context.get('handler_item_facts'):
            return _lossless_item_identity(resource, record['native_stack'])
        return identity
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


def _lossless_item_identity(facts, native_stack):
    return _json(['item', facts['registry_name'], facts['metadata'], facts['nbt'],
                  {key: value for key, value in native_stack.items() if key != 'Count'}])


def _profile(handler, view, context=None):
    if handler['native_class'] == FURNACE_HANDLER:
        return ('minecraft:smelting', 'furnace', True, False)
    family = handler.get('gt_recipe_map_id')
    fields = view.get('displayed_fields') or {}
    if handler['native_class'] != GT_HANDLER or family not in GT_FAMILIES:
        raise Unsupported('Handler/map is outside the source-proven adapter allowlist')
    if context is not None and family not in context['gt_families']:
        raise Unsupported('Handler/map is outside the captured presentation context scope')
    if fields.get('frontend_class') != GT_FRONTEND:
        raise Unsupported('Custom or unknown GT frontend transformations are not mapped')
    if type(fields.get('render_real_stack_sizes')) is not bool or type(fields.get('unificate_output')) is not bool:
        raise Unsupported('GT display normalization properties were not captured')
    return (family, 'gt', fields['render_real_stack_sizes'], fields['unificate_output'])


def _view_projection(view, profile, ambiguous, context=None):
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
            native = json.loads(identity)
            lossless = context is not None and context.get('handler_item_facts')
            if lossless:
                if alternative.get('item_facts_failure'):
                    raise Unsupported('Original handler item facts failed during reference capture')
                facts = alternative.get('item_facts')
                if (not isinstance(facts, dict) or not isinstance(facts.get('registry_name'), str) or not facts['registry_name']
                        or type(facts.get('metadata')) is not int or type(facts.get('amount')) is not int or 'nbt' not in facts
                        or (facts['nbt'] is not None and (not isinstance(facts['nbt'], dict) or facts['nbt'].get('type') != 'compound'
                            or not isinstance(facts['nbt'].get('value'), dict)))):
                    raise Unsupported('Original handler item facts are missing or invalid')
                if native[0] == 'item':
                    if (alternative.get('serializer_class') != DEFAULT_SERIALIZER or alternative.get('count_semantics') != 'item_stack_size'
                            or native[1:3] != [facts['registry_name'], facts['metadata']] or count != facts['amount']):
                        raise Unsupported('Observed item writer does not establish ordinary identity/count semantics')
                    identity = _lossless_item_identity(facts, alternative['native_stack'])
                elif (alternative.get('serializer_class') not in BUILTIN_SERIALIZERS - {DEFAULT_SERIALIZER}
                      or alternative.get('count_semantics') != 'native_conversion'):
                    raise Unsupported('Observed fluid wrapper writer/volume semantics are not source-proven')
            if context is not None and context['version'] >= 2:
                if not (lossless and native[0] == 'item') and (identity in context.get('uncertain_native_identities', set())
                        or (native[0] == 'item' and ((context['version'] == 2 and not context['registry_supported'])
                            or (native[1], native[2]) in context.get('uncertain_buckets', set())))):
                    raise Unsupported('Independent native item projection coverage/count semantics are unresolved for this identity')
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
            identity = _resource_identity(stack, context)
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
    def anchor(entry):
        identity = json.loads(entry)[0]
        value = json.loads(identity)
        if value[0] == 'item' and len(value) == 5:
            identity = _native_identity(dict(value[4], Count=1))[0]
        return identity
    return _json(sorted(sorted(anchor(entry) for entry in slot['alternatives']) for slot in projection['outputs']))


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


def compare(snapshot, reference, *, example_limit=20, profile='default'):
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
    if profile not in ('default', 'forestry_still'):
        raise ComparisonError('profile must be default or forestry_still')
    selected_profile = profile
    still = profile == 'forestry_still'
    snapshot, reference = Path(snapshot), Path(reference)
    manifest = json.loads((snapshot / 'manifest.json').read_text(encoding='utf-8'))
    summary = json.loads((reference / 'summary.json').read_text(encoding='utf-8'))
    if manifest.get('schema_version') != 1 or type(summary.get('schema_version')) is not int or summary['schema_version'] not in ((3,) if still else (1, 2)):
        raise ComparisonError('Profile requires canonical schema 1 and reference schema ' + ('3' if still else '1/2'))
    if still:
        if (summary.get('profile') != 'forestry_still' or summary.get('view_projection') != 'forestry_still_fluid_tanks_v1'
                or summary.get('signature_projection') != 'not_applicable_fluid_tank_profile'
                or summary.get('canonical_files') != manifest['files']
                or summary.get('item_presentation_context') != {'status': 'not_applicable', 'reason': 'fluid_only_profile'}
                or 'handler_item_facts' in summary
                or set(summary.get('files', {})) != {'handlers.jsonl.gz', 'signatures.jsonl.gz', 'handler-views.jsonl.gz'}
                or (reference / 'presentation-context.json').exists()):
            raise ComparisonError('Still reference capability, canonical file binding or item-context scope is invalid')
        selection = summary.get('selection')
        observations = summary.get('tank_observations')
        if (not isinstance(selection, dict) or set(selection) != {'selected_handlers', 'excluded_handlers', 'failure'}
                or any(type(selection.get(name)) is not int or selection[name] < 0 for name in ('selected_handlers', 'excluded_handlers'))
                or (selection['failure'] is not None and (not isinstance(selection['failure'], dict)
                    or not isinstance(selection['failure'].get('reason'), str) or not selection['failure']['reason'].strip()))
                or not isinstance(observations, dict) or set(observations) != {'captured', 'unsupported', 'failed'}
                or any(type(value) is not int or value < 0 for value in observations.values())
                or not isinstance(summary.get('counts'), dict)
                or any(type(value) is not int or value < 0 for value in summary['counts'].values())
                or any(type(summary.get(name)) is not int or summary[name] < 0
                       for name in ('failed_handlers', 'failed_signatures', 'failed_views', 'failed_stacks'))):
            raise ComparisonError('Still selection, observation or failure counters are invalid')
    lossless = summary['schema_version'] == 2
    if lossless and summary.get('handler_item_facts') != HANDLER_ITEM_FACTS:
        raise ComparisonError('Reference handler item-facts capability is missing or unmapped')
    if lossless and (type(summary.get('failed_item_facts')) is not int or summary['failed_item_facts'] < 0):
        raise ComparisonError('Reference failed_item_facts event count is missing or invalid')
    if summary.get('canonical_snapshot_id') != manifest['snapshot_id'] or summary.get('canonical_pack') != manifest['pack']:
        raise ComparisonError('Reference snapshot identity or pack/config cohort does not match')
    mods = {mod['id']: mod for mod in manifest['pack']['mods']}
    for id, (version, checksum) in (STILL_PINNED_MODS if still else PINNED_MODS).items():
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
    if still:
        observed_failures += bool(selection['failure'])
    for signature in _records(reference, 'signatures.jsonl.gz', summary['files']):
        validate_reference(signature, signature_indexes)
        if signature.get('projection') != 'native_recipe_id_api':
            raise ComparisonError('Signature projection label is not the pinned native RecipeId API')
        observed_failures += bool(signature.get('failure'))
    signature_count = len(signature_indexes)
    if still and signature_count:
        raise ComparisonError('Still reference signatures must be empty and explicitly not applicable')
    del signature_indexes
    finish_phase('reference_signatures')
    resources = {record['id']: record for record in _records(snapshot, 'resources.jsonl.gz', manifest['files'])}
    for _ in _records(snapshot, 'groups.jsonl.gz', manifest['files']):
        pass
    if still:
        context = None
        context_report = {'available': False, 'complete': None, 'failure_count': 0,
                          'status': 'not_applicable', 'reason': 'fluid_only_profile'}
    else:
        context, context_report = _presentation_context(reference, summary, manifest, resources)
    if lossless:
        if context is None or context['version'] != 3:
            raise ComparisonError('Lossless handler item facts require independent context schema 3')
        context['handler_item_facts'] = True
    typed_identities = defaultdict(set)
    uncertain_buckets = set()
    for resource in (() if still else resources.values()):
        try:
            identity = _resource_identity(resource, context)
            typed_identities[identity].add(_json([resource['kind'], resource['registry_name'], resource['metadata'], resource['nbt']]))
        except Unsupported:
            if resource['kind'] == 'item':
                uncertain_buckets.add((resource['registry_name'], resource['metadata']))
    for resource in _context_items(context):
        try:
            identity = _resource_identity(resource, context)
            typed_identities[identity].add(_json(['item', resource['registry_name'], resource['metadata'], resource['nbt']]))
        except Unsupported:
            uncertain_buckets.add((resource['registry_name'], resource['metadata']))
    if context is not None and context['version'] >= 2:
        context['uncertain_buckets'] = uncertain_buckets
        context['uncertain_native_identities'] = set()
        for record in context['projections'].values():
            if record['status'] == 'ok' and not _ordinary_item_projection(context, record):
                try:
                    context['uncertain_native_identities'].add(_native_identity(record['native_stack'])[0])
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

    profiles, normalized_views = ({STILL_PROFILE} if still else set()), []
    tank_observations = Counter(captured=0, unsupported=0, failed=0)
    unresolved_reference_outputs = set()
    handlers_with_views, view_indexes = set(), set()
    for view in _records(reference, 'handler-views.jsonl.gz', summary['files']):
        validate_reference(view, view_indexes)
        counts['reference_views'] += 1
        handlers_with_views.add(view['handler_key'])
        observed_failures += bool(view.get('failure') or view.get('failures'))
        if still:
            facts = view.get('forestry_still_tanks')
            status = facts.get('status') if isinstance(facts, dict) else None
            if status not in tank_observations:
                raise ComparisonError('Still view has no valid tank observation status')
            tank_observations[status] += 1
            observed_failures += status == 'failed' and not (view.get('failure') or view.get('failures'))
        positions = [] if still else (view.get('ingredients') or []) + (view.get('other_stacks') or []) + ([view['result']] if view.get('result') else [])
        observed_failures += sum(bool(alternative.get('failure')) + (bool(alternative.get('item_facts_failure')) if lossless else 0)
                                 for positioned in positions for alternative in positioned.get('alternatives', []))
        handler = handlers[view['handler_key']]
        profile = None
        try:
            profile = STILL_PROFILE if still else _profile(handler, view, context)
            profiles.add(profile)
            normalized_views.append(({'handler_key': view['handler_key'], 'recipe_index': view['recipe_index']}, profile,
                                     _still_view_projection(handler, view) if still else _view_projection(view, profile, ambiguous, context)))
        except Unsupported as error:
            unsupported(str(error), {'side': 'nei', 'handler_key': view['handler_key'], 'recipe_index': view['recipe_index']})
            if lossless and profile is not None:
                # Observed output anchors mark uncertainty, never expected alternatives or a successful match.
                try:
                    outputs = view['other_stacks'] if profile[1] == 'gt' else [view['result']] if view.get('result') else []
                    anchors = [[_native_identity(alternative.get('native_stack'))[0] for alternative in value['alternatives']] for value in outputs]
                    if anchors and all(anchors):
                        unresolved_reference_outputs.add((profile, _json(sorted(sorted(slot) for slot in anchors))))
                except (Unsupported, KeyError, TypeError):
                    pass
    for handler in handlers.values():
        if handler['handler_key'] not in handlers_with_views:
            unsupported('Handler has no captured views. Its recipe coverage is unverified', {'side': 'nei', 'handler_key': handler['handler_key'],
                        'enumeration_status': handler['enumeration_status'], 'recipe_count': handler.get('recipe_count')})
    if summary.get('counts') != {'handlers': len(handlers), 'signatures': signature_count, 'handler_views': counts['reference_views']}:
        raise ComparisonError('Reference summary counts do not match the streams')
    if still and observations != dict(tank_observations):
        raise ComparisonError('Still tank observation counters do not match the views')
    reference_complete = summary.get('complete') is True
    if still:
        reference_complete = (reference_complete and selection['selected_handlers'] == 1 and selection['failure'] is None
                              and len(handlers) == 1 and counts['reference_views'] > 0 and counts['unsupported'] == 0
                              and tank_observations['captured'] == counts['reference_views'] and not observed_failures)
        if len(handlers) == 1:
            handler = next(iter(handlers.values()))
            reference_complete = (reference_complete and handler.get('enumeration_status') == 'ok'
                                  and type(handler.get('recipe_count')) is int and handler['recipe_count'] == counts['reference_views']
                                  and {index for key, index in view_indexes} == set(range(counts['reference_views'])))
    del view_indexes
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
        if not still and process.get('conditions', {}).get('hidden') is True:
            counts['excluded_hidden'] += 1
            continue
        for profile in applicable:
            try:
                projection = _still_canonical_projection(process, resources) if still else _canonical_projection(process, profile, resources, ambiguous, context)
                key = _json(projection)
                catalog[profile].setdefault(key, {'projection': projection, 'process_ids': []})['process_ids'].append(process['id'])
                output_index[(profile, _output_key(projection))].add(key)
            except Unsupported as error:
                unsupported(str(error), {'side': 'canonical', 'process_id': process['id'], 'family': process['family']})
                unresolved = {'process_id': process['id'], 'reason': str(error)}
                if hasattr(error, 'output_key'):
                    unresolved_outputs[(profile, error.output_key)].append(unresolved)
                elif not still:
                    try:
                        anchors = {_resource_identity(resources[output['resource_id']], context) for output in process['outputs']}
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
                if (profile, _output_key(candidate['projection'])) in unresolved_reference_outputs:
                    unsupported('A captured reference view with these outputs has unresolved item facts or writer semantics',
                                {'side': 'canonical', 'family': profile[0], 'process_ids': candidate['process_ids'][:example_limit]})
                    continue
                counts['missing_nei'] += 1
                if len(examples['missing_nei']) < example_limit:
                    examples['missing_nei'].append({'family': profile[0], 'process_ids': candidate['process_ids'][:example_limit], 'canonical': candidate['projection'],
                        'reason': 'Not displayed by captured mapped handlers. Category enable/merge settings may limit NEI presentation'})
    finish_phase('semantic_matching')
    # Verify the remaining canonical streams too, without inventing recipe semantics for them.
    for filename in ('sources.jsonl.gz', 'environments.jsonl.gz', 'coverage.jsonl.gz'):
        for _ in _records(snapshot, filename, manifest['files']):
            pass
    failure_fields = ('failed_handlers', 'failed_signatures', 'failed_views', 'failed_stacks') + (('failed_item_facts',) if lossless else ())
    capture_failures = max(observed_failures, sum(summary.get(name, 0) for name in failure_fields))
    finish_phase('remaining_stream_validation')
    timings['total'] = round(time.perf_counter() - started, 3)
    report = {'schema_version': 1, 'canonical_snapshot_id': manifest['snapshot_id'], 'scope': STILL_SOURCE_SCOPE if still else SOURCE_SCOPE, 'counts': dict(counts),
            'unsupported_reasons': dict(reasons), 'examples': examples, 'example_limit': example_limit,
            'reference_complete': reference_complete and (not still or (counts['unsupported'] == 0 and capture_failures == 0)), 'capture_failures': capture_failures,
            'presentation_context': context_report,
            'handler_item_facts': summary.get('handler_item_facts') if lossless else None,
            'capture_failure_unit': 'events, not distinct affected recipes',
            'mapped_profiles': [list(profile) for profile in sorted(profiles)], 'ambiguous_resource_projections': len(ambiguous),
            'ambiguous_canonical_candidates': len(uncertain - seen),
            'timings_seconds': timings,
            'native_signatures': {'records': signature_count, 'comparison_to_canonical': False, 'scope': 'Capture integrity and native API projection label only'},
            'limitations': ['No pack-wide equivalence claim', 'Display agreement does not prove execution, yields or native machine predicates',
                            'Exact typed ordinary item facts and native projections compared' if lossless else 'NBTJson is not injective. Typed NBT agreement is not proven',
                            'Fluid NBT and custom writer semantics remain unverified', 'Generic handler chances are not production probability',
                            'Unmapped handlers, recipe maps, frontends and crafting layouts remain unverified',
                            'Hidden GT recipes excluded. Disabled/fake recipes are retained for display comparison',
                            'Furnace auxiliary fuel is not an output. Fuel, time, EU and XP are unverified',
                            'Counts compare unique canonical presentation projections, not duplicate registration multiplicities']}
    if still:
        report['profile'] = selected_profile
        report['native_signatures']['scope'] = 'Not applicable to the fluid-tank profile. The signatures stream must be empty'
        view_occurrences = defaultdict(list)
        for view, _, projection in normalized_views:
            view_occurrences[_json(projection)].append(view)
        occurrences = [{'projection': json.loads(key), 'canonical_process_ids': catalog[STILL_PROFILE].get(key, {}).get('process_ids', []),
                        'nei_views': view_occurrences.get(key, [])}
                       for key in dict.fromkeys([*catalog[STILL_PROFILE], *view_occurrences])]
        report['duplicate_occurrences'] = {'canonical': sum(len(value['process_ids']) - 1 for value in catalog[STILL_PROFILE].values()),
                                           'nei': sum(len(views) - 1 for views in view_occurrences.values())}
        report['projection_occurrences'] = occurrences
        report['catalog_occurrence_counts_equal'] = (counts['unsupported'] == 0 and counts['differences'] == 0
            and counts['missing_canonical'] == 0 and counts['missing_nei'] == 0
            and report['reference_complete']
            and all(len(candidate['process_ids']) == len(view_occurrences[key]) for key, candidate in catalog[STILL_PROFILE].items()))
        report['limitations'] = ['Only source-verified Still per-unit fluid templates are compared, including exact typed NBT and tank order',
                                'Template agreement does not prove batch yield, accepted output, execution, matching, timing or energy',
                                'Unique projection equality does not prove catalog occurrence equality. Occurrences are reported separately',
                                'No authority or equivalence claim for GT maps or other NEI handlers']
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--profile', choices=('default', 'forestry_still'), default='default')
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
        report = compare(args.snapshot, args.reference or args.snapshot / 'nei-reference', example_limit=args.example_limit, profile=args.profile)
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
