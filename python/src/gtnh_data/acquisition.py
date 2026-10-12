"""Snapshot evidence for acquisition hints, without claims of unobtainability."""

import json


def unification_preferences(connection, resource_ids=None):
    """Read native anchors, without treating alias membership as output replacement."""
    ids = None if resource_ids is None else tuple(dict.fromkeys(resource_ids))
    if ids == ():
        return {}
    where = '' if ids is None else ' AND member.id IN (' + ','.join('?' for _ in ids) + ')'
    rows = connection.execute("""
        SELECT member.id, anchor.id, groups.id FROM records groups
        JOIN resources anchor ON anchor.id=json_extract(groups.payload,'$.name')
        CROSS JOIN members ON members.group_id=groups.id
        CROSS JOIN resources member ON member.id=members.resource_id
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


def summarize_acquisition(connection, resource_ids, *, snapshot_id, evidence_limit=5):
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
        for row in connection.execute("SELECT DISTINCT records.id,records.payload FROM outputs JOIN records ON records.collection='processes' AND records.id=outputs.process_id WHERE outputs.resource_id IN (" + marks + ') ORDER BY records.id', ids):
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
