"""Snapshot evidence for acquisition hints, without claims of unobtainability."""

import json


def unification_preferences(connection, resource_ids=None):
    """Read native anchors, without treating alias membership as output replacement."""
    ids = None if resource_ids is None else tuple(dict.fromkeys(resource_ids))
    if ids == ():
        return {}
    where = '' if ids is None else ' AND member.id IN (' + ','.join('?' for _ in ids) + ')'
    rows = connection.execute("""
        SELECT member.id, anchor.id, groups.id FROM resources member
        CROSS JOIN members ON members.resource_id=member.id
        CROSS JOIN records groups ON groups.id=members.group_id AND groups.collection='groups'
        CROSS JOIN resources anchor ON anchor.id=json_extract(groups.payload,'$.name')
        WHERE groups.collection='groups' AND json_extract(groups.payload,'$.kind')='unified'
          AND json_extract(groups.payload,'$.provenance.owner')='GTOreDictUnificator.getNonUnifiedStacks'
          AND member.kind='item' AND anchor.kind='item' AND member.nbt=anchor.nbt
          AND member.metadata IS NOT 32767 AND anchor.metadata IS NOT 32767
    """ + where, () if ids is None else ids)
    facts = {}
    for rid, preferred, gid in rows:
        fact = facts.setdefault(rid, {'preferred_resource_ids': set(), 'group_ids': set()})
        fact['preferred_resource_ids'].add(preferred)
        fact['group_ids'].add(gid)
    for rid, fact in facts.items():
        preferred = fact['preferred_resource_ids']
        status = 'ambiguous' if len(preferred) != 1 else 'canonical' if rid in preferred else 'noncanonical_unification_variant'
        fact.update(status=status, preferred_resource_ids=sorted(preferred), group_ids=sorted(fact['group_ids']),
                    evidence='captured_native_unification_anchor', replacement_confirmed=False)
    return facts


def acquisition_rank(analysis):
    """Secondary search rank. Text relevance remains the primary key."""
    status = analysis.get('unification', analysis).get('status', 'unassociated')
    return {'canonical': 0, 'unassociated': 1, 'ambiguous': 2, 'noncanonical_unification_variant': 3}.get(status, 1)


def _known_process_state(process):
    conditions = process.get('conditions', {})
    return (process.get('executable') is True and conditions.get('fake') is not True
            and conditions.get('enabled') is not False
            and all(conditions.get(k) != 'unresolved' for k in ('dynamic_inputs', 'dynamic_output')))


def _interpreted(process):
    return (_known_process_state(process)
            and all(slot.get('choices') and all(c.get('resource_id') is not None or c['match'].get('group_id')
                for c in slot['choices']) and all(c['match']['mode'] != 'native_unknown'
                and (c['match']['mode'] not in ('unified', 'ore_dict') or c['match'].get('group_id'))
                for c in slot['choices']) for slot in process.get('inputs', [])))


def _positive(output):
    chance = output.get('chance')
    return output.get('amount', 0) > 0 and chance is not None and chance.get('numerator', 0) > 0


def _batches(values, size=500):
    values = tuple(values)
    for offset in range(0, len(values), size):
        yield values[offset:offset + size]


def _source_evidence(connection, resource_ids, evidence_limit, include_details=False):
    """Keep native generation, inventory baselines and stochastic support separate."""
    result = {rid: {'status': 'no_active_source_evidence', 'evidence_counts': {
        'generated_ore_block': 0, 'confirmed_mining_drop': 0, 'mined_item_rule_candidate': 0,
        'direct_world_source': 0, 'unresolved_source': 0}, 'evidence': []} for rid in resource_ids}
    seeds = {}
    for batch in _batches(resource_ids):
        marks = ','.join('?' for _ in batch)
        rows = connection.execute("""SELECT DISTINCT links.resource_id, source.id,
            json_extract(source.payload,'$.kind'), json_extract(source.payload,'$.status'),
            json_extract(output.value,'$.resource_semantics'), json_extract(output.value,'$.amount'),
            json_extract(output.value,'$.chance.numerator'), json_extract(source.payload,'$.environment_ids'),
            json_extract(source.payload,'$.parameters.generated_source_id'),
            json_extract(source.payload,'$.parameters.generated_resource_id'),
            json_extract(source.payload,'$.conditions.mining.material'),
            json_extract(source.payload,'$.provenance.owner'),
            json_extract(source.payload,'$.parameters.min_amount'),
            json_extract(source.payload,'$.parameters.max_amount'), resource.kind
            FROM source_outputs links JOIN records source ON source.collection='sources' AND source.id=links.source_id
            JOIN resources resource ON resource.id=links.resource_id
            JOIN json_each(source.payload,'$.outputs') output ON json_extract(output.value,'$.resource_id')=links.resource_id
            WHERE links.resource_id IN (""" + marks + ') ORDER BY links.resource_id,source.id', batch)
        seen = set()
        for rid, sid, kind, status, semantics, amount, chance, environments, generator, block, material, owner, minimum, maximum, resource_kind in rows:
            if (rid, sid) in seen:
                continue
            seen.add((rid, sid))
            active = status in ('active', 'conditional')
            category = ('unresolved_source' if not active else
                'generated_ore_block' if semantics == 'generated_ore_block_not_mining_drop' else
                'mined_item_rule_candidate' if semantics == 'mined_item_rule_candidate' else
                'confirmed_mining_drop' if semantics == 'mined_item_baseline' and amount and amount > 0 and chance and chance > 0 else
                'direct_world_source' if kind == 'underground_fluid' and resource_kind == 'fluid' and owner == 'GTMod.proxy.mUndergroundOil'
                    and minimum is not None and minimum > 0 and maximum is not None and maximum >= minimum else
                'direct_world_source' if semantics not in ('mined_item_baseline', 'generated_ore_block_not_mining_drop')
                    and amount and amount > 0 and (chance is None or chance > 0) else 'unresolved_source')
            world = result[rid]
            world['evidence_counts'][category] += 1
            evidence = {'source_id': sid, 'kind': kind, 'status': status, 'resource_semantics': semantics,
                'classification': category, 'confidence': 'captured_definition',
                'environment_ids': json.loads(environments or '[]'), 'generated_source_id': generator,
                'generated_resource_id': block, 'native_owner': owner}
            if len(world['evidence']) < evidence_limit:
                world['evidence'].append(evidence)
            if kind == 'ore_mining' and category in ('confirmed_mining_drop', 'mined_item_rule_candidate') and material:
                seeds.setdefault(rid, []).append((material, evidence))
    for world in result.values():
        counts = world['evidence_counts']
        world['status'] = ('captured_inventory_source' if counts['confirmed_mining_drop'] or counts['direct_world_source'] else
            'mining_rule_candidate_only' if counts['mined_item_rule_candidate'] else
            'generated_block_only' if counts['generated_ore_block'] else 'no_active_source_evidence')
        world['inventory_obtainable_proven'] = False
    if include_details:
        examples = [e for world in result.values() for e in world['evidence']]
        details = {}
        for batch in _batches({e['source_id'] for e in examples}):
            for sid, conditions, parameters in connection.execute("SELECT id,json_extract(payload,'$.conditions'),json_extract(payload,'$.parameters') FROM records WHERE collection='sources' AND id IN (" + ','.join('?' for _ in batch) + ')', batch):
                details[sid] = {'conditions': json.loads(conditions), 'parameters': json.loads(parameters)}
        environments = {}
        for batch in _batches({id for e in examples for id in e['environment_ids']}):
            for id, payload in connection.execute("SELECT id,payload FROM records WHERE collection='environments' AND id IN (" + ','.join('?' for _ in batch) + ')', batch):
                environments[id] = json.loads(payload)
        for e in examples:
            e.update(details[e['source_id']])
            e['environments'] = [environments[id] for id in e['environment_ids'] if id in environments]
    return result, seeds


# This is an explainable ore-processing heuristic, not a universal recipe taxonomy.
# Smelting, construction and recycling deliberately have no transitions here.
_ORE_PROCESSING_TRANSITIONS = {
    'hammer': {('ore', 'crushed'), ('rawOre', 'crushed'), ('crushed', 'dustImpure'),
               ('crushedPurified', 'dustPure'), ('crushedCentrifuged', 'dust')},
    'macerator': {('ore', 'crushed'), ('rawOre', 'crushed'), ('crushed', 'dustImpure'),
                  ('crushedPurified', 'dustPure'), ('crushedCentrifuged', 'dust')},
    'orewasher': {('crushed', 'crushedPurified')},
    'thermalcentrifuge': {('crushed', 'crushedCentrifuged'), ('crushedPurified', 'crushedCentrifuged')},
    'centrifuge': {('dustImpure', 'dust'), ('dustPure', 'dust')},
}
_INITIAL_PREFIXES = {'crushed', 'crushedPurified', 'crushedCentrifuged', 'dustImpure', 'dustPure', 'dust'}


def _native_materials(connection, ids):
    result = {}
    for batch in _batches(ids):
        for rid, kind, metadata, nbt, facts in connection.execute("""SELECT resources.id,resources.kind,resources.metadata,
                resources.nbt,json_extract(records.payload,'$.material_facts') FROM resources
                CROSS JOIN records ON records.id=resources.id AND records.collection='resources'
                WHERE resources.id IN (""" + ','.join('?' for _ in batch) + ')', batch):
            facts = json.loads(facts or '{}')
            association = facts.get('association') or {}
            material = (association.get('primary') or {}).get('material') or {}
            if (kind == 'item' and metadata != 32767 and nbt == 'null' and facts.get('status') == 'associated'
                    and facts.get('source_api') == 'GTOreDictUnificator.getItemData'
                    and material.get('native_class') == 'gregtech.api.enums.Materials' and material.get('name')):
                prefix = association.get('prefix')
                result[rid] = (material['name'], prefix, 'ore' if prefix and prefix.startswith('ore') else prefix)
    return result


def _initial_processing(connection, ids, source_seeds, evidence_limit):
    """At most three native early-processing steps with source and material witnesses.

    The witness establishes a possible origin for the main product. It does not
    establish all AND inputs, machine access, quantities or executable inventory.
    """
    materials = _native_materials(connection, ids)
    frontier = {rid for rid in ids if rid in materials and materials[rid][1] in _INITIAL_PREFIXES}
    seen = set(frontier)
    edges = {}
    group_members = {}
    resource_kinds = {}
    limits = set()
    process_count = 0
    for depth in range(3):
        if not frontier:
            break
        processes = {}
        families = tuple('gregtech:gt.recipe.' + family for family in _ORE_PROCESSING_TRANSITIONS)
        for batch in _batches(sorted(frontier)):
            rows = connection.execute("""SELECT DISTINCT records.id,records.payload FROM outputs
                CROSS JOIN records ON records.collection='processes' AND records.id=outputs.process_id
                WHERE outputs.resource_id IN (""" + ','.join('?' for _ in batch) + ") AND json_extract(records.payload,'$.family') IN (" + ','.join('?' for _ in families) + ') ORDER BY records.id LIMIT ?', (*batch, *families, 20001 - process_count))
            for pid, payload in rows:
                if process_count >= 20000:
                    limits.add('process_budget')
                    break
                process_count += 1
                p = json.loads(payload)
                provenance = p.get('provenance', {})
                if (_interpreted(p) and p.get('outputs') and _positive(p['outputs'][0])
                        and p['outputs'][0]['resource_id'] in frontier and provenance.get('owner') == 'GTRecipe'
                        and p['family'] == 'gregtech:' + str(provenance.get('map'))):
                    processes[pid] = p
        choices = [c for p in processes.values() for s in p['inputs'] if s['role'] == 'consume' for c in s['choices']]
        missing_groups = {c['match']['group_id'] for c in choices if c['match']['mode'] in ('unified', 'ore_dict')
                          and c['match']['group_id'] not in group_members}
        for batch in _batches(sorted(missing_groups)):
            for gid in batch:
                group_members[gid] = []
            for gid, rid in connection.execute('SELECT group_id,resource_id FROM members WHERE group_id IN (' + ','.join('?' for _ in batch) + ')', batch):
                group_members[gid].append(rid)
        candidates = {c.get('resource_id') for c in choices if c.get('resource_id')}
        candidates.update(rid for gid in missing_groups for rid in group_members[gid])
        if len(candidates | seen) > 10000:
            limits.add('resource_budget')
            break
        for batch in _batches(candidates - resource_kinds.keys()):
            resource_kinds.update(connection.execute('SELECT id,kind FROM resources WHERE id IN (' + ','.join('?' for _ in batch) + ')', batch))
        materials.update(_native_materials(connection, candidates - materials.keys()))
        next_frontier = set()
        for p in processes.values():
            output = p['outputs'][0]['resource_id']
            if output not in materials:
                continue
            material, _, output_prefix = materials[output]
            transitions = _ORE_PROCESSING_TRANSITIONS[p['family'].removeprefix('gregtech:gt.recipe.')]
            solid_slots = [s for s in p['inputs'] if s['role'] == 'consume'
                           and any(resource_kinds.get(c.get('resource_id')) == 'item'
                               or any(resource_kinds.get(rid) == 'item' for rid in group_members.get(c['match'].get('group_id'), [])) for c in s['choices'])]
            if len(solid_slots) != 1:
                continue
            for c in solid_slots[0]['choices']:
                if c.get('amount', 0) <= 0:
                    continue
                mode = c['match']['mode']
                matches = ([c['resource_id']] if mode == 'exact' and c.get('resource_id') else
                           group_members.get(c['match'].get('group_id'), []) if mode in ('unified', 'ore_dict') else [])
                for input in matches:
                    if input not in materials:
                        continue
                    input_material, _, input_prefix = materials[input]
                    if input_material == material and (input_prefix, output_prefix) in transitions:
                        edges.setdefault(output, set()).add((input, p['id']))
                        if input not in seen:
                            next_frontier.add(input)
        seen.update(next_frontier)
        frontier = next_frontier
    _, extra_seeds = _source_evidence(connection, seen - set(ids), 0)
    seeds = {**source_seeds, **extra_seeds}
    result = {}
    for rid in ids:
        evidence = []
        found = False
        pending = [(rid, [])]
        visited = set()
        while pending:
            current, backwards = pending.pop(0)
            if current in visited:
                continue
            visited.add(current)
            if backwards and current in materials and materials[current][2] in {'ore', 'rawOre', 'crushed', 'dustImpure', 'dustPure'}:
                for source_material, source in seeds.get(current, []):
                    if (source_material == materials[current][0]
                            and source['native_owner'] in ('GTOreAdapter.getOreDrops', 'GTOreAdapter.getSmallOreDrops')):
                        found = True
                        if evidence_limit:
                            chain = list(reversed(backwards))
                            evidence.append({'source_resource_id': current, 'source_id': source['source_id'],
                                'source_semantics': source['resource_semantics'], 'source_classification': source['classification'],
                                'material': source_material, 'process_ids': [pid for _, pid, _ in chain],
                                'resource_ids': [current] + [out for _, _, out in chain],
                                'prefixes': [materials[current][1]] + [materials[out][1] for _, _, out in chain]})
                        break
            if len(backwards) < 3:
                pending.extend((input, backwards + [(input, pid, current)]) for input, pid in sorted(edges.get(current, ())))
        evidence.sort(key=lambda e: (e['source_classification'] != 'confirmed_mining_drop',
            e['prefixes'][0] != 'rawOre', len(e['process_ids']), e['source_resource_id'], e['process_ids']))
        result[rid] = {'status': 'inferred' if found else 'no_bounded_evidence',
            'confidence': 'heuristic' if found else 'unknown', 'max_steps': 3, 'evidence': evidence[:evidence_limit],
            'limit_reasons': sorted(limits), 'execution_proven': False,
            'reason': 'Bounded native ore-processing families, prefix transitions and same-material main products with captured mining evidence. Other recipe inputs and machine conditions remain unproven'}
    return result


def summarize_acquisition(connection, resource_ids, *, snapshot_id, evidence_limit=5, include_source_details=False):
    ids = tuple(dict.fromkeys(resource_ids))
    if len(ids) > 1000 or not 0 <= evidence_limit <= 50:
        raise ValueError('Acquisition requests support at most 1000 IDs and 0 to 50 evidence examples')
    unification = unification_preferences(connection, ids)
    result = {'snapshot_id': snapshot_id, 'resources': {}, 'coverage': {'complete': False, 'status_counts': {}, 'unsupported': []}}
    for rid in ids:
        result['resources'][rid] = {'unification': unification.get(rid, {'status': 'unassociated',
            'preferred_resource_ids': [], 'group_ids': [], 'evidence': None, 'replacement_confirmed': False}),
            'acquisition': {'source_count': 0, 'eligible_producer_count': 0, 'unresolved_producer_count': 0,
                            'nonexecutable_producer_count': 0, 'source_ids': [], 'process_ids': [], 'unresolved_process_ids': []}}
    for row in connection.execute("SELECT payload FROM records WHERE collection='coverage'"):
        record = json.loads(row[0])
        status = record.get('status', 'unknown')
        counts = result['coverage']['status_counts']
        counts[status] = counts.get(status, 0) + 1
        if status in ('unsupported', 'unknown', 'failed'):
            result['coverage']['unsupported'].append({'id': record['id'], 'status': record.get('status'), 'reason': record.get('reason')})
    if ids:
        marks = ','.join('?' for _ in ids)
        for rid, sid in connection.execute('SELECT DISTINCT resource_id,source_id FROM source_outputs WHERE resource_id IN (' + marks + ') ORDER BY resource_id,source_id', ids):
            fact = result['resources'][rid]['acquisition']
            fact['source_count'] += 1
            if len(fact['source_ids']) < evidence_limit:
                fact['source_ids'].append(sid)
        for row in connection.execute("SELECT DISTINCT records.id,records.payload FROM outputs CROSS JOIN records ON records.collection='processes' AND records.id=outputs.process_id WHERE outputs.resource_id IN (" + marks + ') ORDER BY records.id', ids):
            p = json.loads(row[1])
            for rid in {o['resource_id'] for o in p['outputs'] if o['resource_id'] in result['resources'] and o.get('amount', 0) > 0 and (o.get('chance') is None or o['chance'].get('numerator', 0) > 0)}:
                fact = result['resources'][rid]['acquisition']
                if p.get('executable') is False or p.get('conditions', {}).get('fake') is True or p.get('conditions', {}).get('enabled') is False:
                    fact['nonexecutable_producer_count'] += 1
                elif _interpreted(p) and any(o['resource_id'] == rid and _positive(o) for o in p['outputs']):
                    fact['eligible_producer_count'] += 1
                    if len(fact['process_ids']) < evidence_limit:
                        fact['process_ids'].append(p['id'])
                else:
                    fact['unresolved_producer_count'] += 1
                    if len(fact['unresolved_process_ids']) < evidence_limit:
                        fact['unresolved_process_ids'].append(p['id'])
    for fact in result['resources'].values():
        acquisition = fact['acquisition']
        acquisition['status'] = ('known_source' if acquisition['source_count'] else 'eligible_producer'
            if acquisition['eligible_producer_count'] else 'unresolved_producer_only'
            if acquisition['unresolved_producer_count'] else 'no_known_acquisition')
        acquisition.update(coverage_complete=False, obtainable_proven=False,
            reason='Captured sources and interpreted producers are evidence only. Missing evidence does not prove unobtainability')
    sources, seeds = _source_evidence(connection, ids, evidence_limit, include_source_details)
    processing = _initial_processing(connection, ids, seeds, evidence_limit)
    for rid, fact in result['resources'].items():
        world = sources[rid]
        suggested = world['status'] in ('captured_inventory_source', 'mining_rule_candidate_only') or processing[rid]['status'] == 'inferred'
        fact['provenance'] = {'world_source': world,
            'initial_processing': processing[rid],
            'renewable': {'status': 'unknown', 'reason': 'Captured sources and recipe cycles do not prove replenishment or a self-sustaining supply'},
            'basic_suggestion': {'suggested': suggested, 'reason': 'Captured sources or bounded initial processing can inform a user-selected planning boundary',
                'requires_user_selection': True}}
    return result


def _cycles(adjacency):
    """Iterative two-pass components for the bounded discovered dependency graph."""
    seen, order = set(), []
    for start in sorted(adjacency):
        stack = [(start, False)]
        while stack:
            node, done = stack.pop()
            if done:
                order.append(node)
            elif node not in seen:
                seen.add(node)
                stack.append((node, True))
                stack.extend((child, False) for child in sorted(adjacency[node], reverse=True) if child not in seen)
    reverse = {node: set() for node in adjacency}
    for node, children in adjacency.items():
        for child in children:
            reverse[child].add(node)
    seen, components = set(), []
    for start in reversed(order):
        if start in seen:
            continue
        stack, component = [start], set()
        while stack:
            node = stack.pop()
            if node not in seen:
                seen.add(node)
                component.add(node)
                stack.extend(reverse[node] - seen)
        if len(component) > 1 or start in adjacency[start]:
            components.append(component)
    return components


def analyze_grounding(variants, known_source_ids, base_ids, discovery_complete, *, resource_ids=None, limit_reasons=()):
    """Structural possibility under explicit seeds, not quantity or execution proof."""
    known_source_ids, base_ids = set(known_source_ids), set(base_ids)
    seeds = known_source_ids | base_ids
    reachable, resources, dependencies, unsupported = set(seeds), set(resource_ids or ()) | seeds, [], []
    for variant in variants:
        p = variant['process']
        selected = variant.get('selections', {})
        required = set()
        valid = _known_process_state(p)
        for index, slot in enumerate(p.get('inputs', [])):
            selection = selected.get(str(index))
            if selection is None:
                valid = False
                continue
            ci, rid = selection['choice_index'], selection['resource_id']
            if not 0 <= ci < len(slot['choices']) or slot['choices'][ci].get('resource_id') != rid or slot['choices'][ci]['match']['mode'] != 'exact':
                valid = False
            elif slot['role'] == 'consume' and slot['choices'][ci].get('amount', 0) <= 0:
                valid = False
            required.add(rid)
        outputs = {o['resource_id'] for o in p['outputs'] if _positive(o)}
        resources.update(required | outputs)
        if valid:
            dependencies.append((required, outputs, p['id']))
        else:
            unsupported.append(p['id'])
    changed = True
    while changed:
        changed = False
        for required, outputs, _ in dependencies:
            if required <= reachable and not outputs <= reachable:
                reachable.update(outputs)
                changed = True
    adjacency = {rid: set() for rid in resources}
    for required, outputs, _ in dependencies:
        for output in outputs:
            adjacency[output].update(required)
    cycles = []
    for component in _cycles(adjacency):
        if not component & reachable:
            cycles.append({'resource_ids': sorted(component), 'status': 'unseeded_in_discovered_graph',
                           'external_dependency_ids': sorted(set().union(*(adjacency[r] for r in component)) - component)})
    complete = bool(discovery_complete) and not limit_reasons and not unsupported
    return {'scope': 'structural_possibility_in_discovered_native_variants', 'execution_proven': False,
        'discovery_complete': complete, 'base_resource_ids': sorted(set(base_ids)),
        'known_source_resource_ids': sorted(set(known_source_ids)), 'reachable_resource_ids': sorted(reachable),
        'resources': {rid: {'status': 'structural_reachable' if rid in reachable else
            'no_known_grounded_path' if complete else 'incomplete'} for rid in sorted(resources)},
        'unseeded_cycles': sorted(cycles, key=lambda c: c['resource_ids']), 'unsupported_process_ids': sorted(set(unsupported)),
        'limit_reasons': sorted(set(limit_reasons)), 'limitations': [
            'Every selected AND input including presence must be seeded or structurally produced',
            'Positive stochastic outputs express possible acquisition, not guaranteed stock',
            'Quantities, machine conditions, startup stock and incomplete pack acquisition coverage remain outside this heuristic']}
