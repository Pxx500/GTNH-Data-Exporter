"""Rebuildable ingredient predicates and material hints, owned by Dataset.

The canonical snapshot remains authoritative. Material names and output position
are ordering hints, never matching predicates or proof of chemical conversion.
"""

import json
import hashlib
import os
import sqlite3
import tempfile
import time
from pathlib import Path
from array import array
from collections import deque
from contextlib import closing
from functools import lru_cache
from heapq import heappop, heappush

from .balance import quantity

ANALYSIS_VERSION = 5

_RECOVERY_FAMILIES = frozenset(('gregtech:gt.recipe.macerator', 'gregtech:gt.recipe.arcfurnace',
                                'gregtech:gt.recipe.alloysmelter'))
_DUST_FORMS = frozenset(('dust', 'dustSmall', 'dustTiny'))
_SIMPLE_FORMS = frozenset(('dust', 'dustSmall', 'dustTiny', 'ingot', 'ingotHot', 'nugget',
                         'plate', 'plateDouble', 'plateDense', 'foil', 'stick', 'stickLong',
                         'gearGt', 'gearGtSmall', 'ring', 'bolt', 'screw', 'rotor', 'wireFine', 'frameGt', 'block'))
_CRAFTED_FORMS = _SIMPLE_FORMS - _DUST_FORMS - {'ingot', 'ingotHot', 'nugget'}
_RECOVERY_WEIGHT = 2


def index_path(dataset):
    return dataset.path.with_suffix('.flow.sqlite')


def material_tokens(record):
    facts = record.get('material_facts') or {}
    association = facts.get('association') or {}
    primary = association.get('primary') or {}
    material = primary.get('material')
    names = set()

    def collect(node):
        if not isinstance(node, dict):
            return
        if node.get('name'):
            names.add(node['name'])
        for component in node.get('components', []):
            collect(component.get('material'))

    collect(material)
    return names


def material_basis(record):
    association = (record.get('material_facts') or {}).get('association') or {}
    return _declaration_basis((association.get('primary') or {}).get('material'))


def _declaration_basis(node):
    if not isinstance(node, dict):
        return 'unknown'
    element, components = node.get('element'), node.get('components') or []
    if not element and not components:
        return 'opaque'
    if node.get('status') != 'complete':
        return 'partial'
    if isinstance(element, dict) and isinstance(element.get('id'), str) and element['id']:
        return 'structured_complete'
    if not isinstance(components, list) or not components:
        return 'partial'
    for component in components:
        try:
            coefficient = component['coefficient']
            if isinstance(coefficient, bool) or int(coefficient) <= 0 or str(int(coefficient)) != str(coefficient):
                return 'partial'
        except (ValueError, TypeError, KeyError):
            return 'partial'
        if _declaration_basis(component.get('material')) != 'structured_complete':
            return 'partial'
    return 'structured_complete'


def material_comparison(left, right):
    left_tokens, left_basis = left
    right_tokens, right_basis = right
    if left_tokens & right_tokens:
        return 0
    if not left_tokens or not right_tokens:
        return 1
    # Declaration completeness is evidence scope, not purity or atom provenance.
    if ((left_basis == 'structured_complete' and right_basis in ('opaque', 'partial'))
            or (right_basis == 'structured_complete' and left_basis in ('opaque', 'partial'))):
        return 1
    return 4


def match_key(choice):
    return json.dumps({'resource_id': choice.get('resource_id'), 'match': choice['match']}, sort_keys=True, separators=(',', ':'))


def status(dataset):
    path = index_path(dataset)
    result = {'database': str(path), 'snapshot_id': dataset.snapshot_id, 'analysis_version': ANALYSIS_VERSION}
    if not path.is_file():
        return dict(result, status='missing')
    try:
        with closing(sqlite3.connect(f'{path.as_uri()}?mode=ro', uri=True)) as connection:
            metadata = dict(connection.execute('SELECT key,value FROM metadata'))
        if metadata.get('manifest') != dataset._manifest_json or metadata.get('analysis_version') != str(ANALYSIS_VERSION):
            return dict(result, status='incompatible', reason='Snapshot manifest or flow analysis version differs')
        return dict(result, status='ready', size_bytes=path.stat().st_size,
                    prepared_seconds=float(metadata['prepared_seconds']), counts=json.loads(metadata['counts']))
    except (sqlite3.Error, ValueError, KeyError) as exc:
        return dict(result, status='incompatible', reason=str(exc))


def rebuild(dataset):
    before = time.perf_counter()
    path = index_path(dataset)
    descriptor, temporary = tempfile.mkstemp(prefix=f'.{path.name}.', suffix='.tmp', dir=path.parent)
    os.close(descriptor)
    temporary = Path(temporary)
    counts = {'inputs': 0, 'outputs': 0, 'resources': 0, 'processes': 0, 'unique_matches': 0, 'match_memberships': 0,
              'material_basis': {}, 'terminal_categories': {}, 'requirement_slots': 0, 'unresolved_requirement_slots': 0,
              'requirement_membership_visits': 0}
    try:
        with dataset._connect() as source, closing(sqlite3.connect(temporary)) as prepared, prepared:
            prepared.executescript('''
                CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE resources(id TEXT PRIMARY KEY,materials TEXT NOT NULL,material_basis TEXT NOT NULL,terminal_category TEXT NOT NULL);
                CREATE TABLE processes(id TEXT PRIMARY KEY,representative TEXT NOT NULL,tier INTEGER,tier_status TEXT NOT NULL,eligible INTEGER NOT NULL);
                CREATE TABLE matches(match_id INTEGER,resource_id TEXT,PRIMARY KEY(match_id,resource_id));
                CREATE TABLE inputs(process_id TEXT,slot INTEGER,match_id INTEGER,PRIMARY KEY(process_id,slot,match_id));
                CREATE TABLE requirement_classes(id INTEGER PRIMARY KEY,signature TEXT UNIQUE NOT NULL);
                CREATE TABLE input_requirements(process_id TEXT,slot INTEGER,class_id INTEGER,status TEXT NOT NULL,PRIMARY KEY(process_id,slot));
                CREATE TABLE outputs(process_id TEXT,resource_id TEXT,position INTEGER);
                CREATE TABLE graph(name TEXT PRIMARY KEY,payload BLOB NOT NULL);
            ''')
            resources = []
            for row in source.execute("SELECT id,payload FROM records WHERE collection='resources' ORDER BY id"):
                record = json.loads(row['payload'])
                basis = material_basis(record)
                counts['material_basis'][basis] = counts['material_basis'].get(basis, 0) + 1
                terminal = dataset._terminal_artifact_category(record)
                counts['terminal_categories'][terminal] = counts['terminal_categories'].get(terminal, 0) + 1
                resources.append((row['id'], json.dumps(sorted(material_tokens(record))), basis, terminal))
            prepared.executemany('INSERT INTO resources VALUES(?,?,?,?)', resources)
            counts['resources'] = len(resources)
            del resources
            matches, fingerprints = {}, {}
            unresolved_inputs, unresolved_outputs = set(), set()
            process_rows, input_rows, output_rows, match_rows = [], [], [], []
            pending_matches = {}

            def flush():
                prepared.executemany('INSERT INTO processes VALUES(?,?,?,?,?)', process_rows)
                prepared.executemany('INSERT INTO inputs VALUES(?,?,?)', input_rows)
                prepared.executemany('INSERT INTO outputs VALUES(?,?,?)', output_rows)
                prepared.executemany('INSERT INTO matches VALUES(?,?)', match_rows)
                process_rows.clear()
                input_rows.clear()
                output_rows.clear()
                match_rows.clear()
                pending_matches.clear()

            def requirement_class(slot):
                effects = {}
                for choice in slot['choices']:
                    match = choice['match']
                    if match['mode'] == 'native_unknown' or (match['mode'] in ('ore_dict', 'unified') and not match.get('group_id')):
                        return None
                    try:
                        amount = quantity(choice['amount'])
                        chance = quantity(choice.get('consumption_chance', slot.get('consumption_chance', 1)))
                    except (ValueError, TypeError):
                        return None
                    if amount <= 0 or chance <= 0:
                        continue
                    mid = matches[match_key(choice)]
                    if mid in pending_matches:
                        first, last = pending_matches[mid]
                        members = (match_rows[i][1] for i in range(first, last))
                    else:
                        members = (row[0] for row in prepared.execute('SELECT resource_id FROM matches WHERE match_id=?', (mid,)))
                    sensitive = match.get('nbt_sensitive', match['mode'] not in ('ore_dict', 'unified'))
                    effect = (amount.numerator, amount.denominator, chance.numerator, chance.denominator, bool(sensitive))
                    found = False
                    for rid in members:
                        counts['requirement_membership_visits'] += 1
                        effects.setdefault(rid, set()).add(effect)
                        found = True
                    if not found:
                        return None
                if not effects:
                    return None
                signature = json.dumps({'role': slot['role'], 'accepted_resource_effects': [
                    [rid, sorted(effects[rid])] for rid in sorted(effects)]}, sort_keys=True, separators=(',', ':'))
                prepared.execute('INSERT OR IGNORE INTO requirement_classes(signature) VALUES(?)', (signature,))
                return prepared.execute('SELECT id FROM requirement_classes WHERE signature=?', (signature,)).fetchone()[0]

            for row in source.execute("SELECT id,payload FROM records WHERE collection='processes' ORDER BY id"):
                record = json.loads(row['payload'])
                captured = {key: value for key, value in record.items() if key != 'id'}
                captured['provenance'] = {key: value for key, value in record['provenance'].items() if key != 'index'}
                fingerprint = hashlib.sha256(json.dumps(captured, sort_keys=True, separators=(',', ':')).encode()).digest()
                representative = fingerprints.setdefault(fingerprint, record['id'])
                eligible = record['executable'] is not False and record['conditions'].get('dynamic_output') != 'unresolved'
                if record['conditions'].get('dynamic_output') == 'unresolved':
                    unresolved_outputs.add(record['id'])
                if record['conditions'].get('dynamic_inputs') == 'unresolved' or any(
                        choice['match']['mode'] == 'native_unknown' or
                        choice['match']['mode'] == 'unified' and not choice['match'].get('group_id')
                        for slot in record['inputs'] for choice in slot['choices']):
                    unresolved_inputs.add(record['id'])
                declaration = dataset._recipe_tier(record)
                process_rows.append((record['id'], representative, declaration['tier'], declaration['status'], int(eligible)))
                counts['processes'] += 1
                if representative == record['id'] and eligible:
                    for si, slot in enumerate(record['inputs']):
                        if slot['role'] != 'consume':
                            continue
                        slot_matches = set()
                        for choice in slot['choices']:
                            match = choice['match']
                            if choice['amount'] <= 0 or match['mode'] == 'native_unknown' or (
                                    match['mode'] in ('ore_dict', 'unified') and not match.get('group_id')):
                                continue
                            key = match_key(choice)
                            if key not in matches:
                                mid = len(matches)
                                matches[key] = mid
                                ids = dataset._choice_resources(source, choice)
                                first = len(match_rows)
                                match_rows.extend((mid, rid) for rid in ids)
                                pending_matches[mid] = first, len(match_rows)
                                counts['match_memberships'] += len(ids)
                            slot_matches.add(matches[key])
                        input_rows.extend((record['id'], si, mid) for mid in sorted(slot_matches))
                        counts['inputs'] += len(slot_matches)
                        class_id = requirement_class(slot)
                        prepared.execute('INSERT INTO input_requirements VALUES(?,?,?,?)',
                            (record['id'], si, class_id, 'complete' if class_id is not None else 'unresolved'))
                        counts['requirement_slots'] += 1
                        counts['unresolved_requirement_slots'] += int(class_id is None)
                    for oi, output in enumerate(record['outputs']):
                        if dataset._positive_output(output):
                            output_rows.append((record['id'], output['resource_id'], oi))
                            counts['outputs'] += 1
                if len(process_rows) >= 2000:
                    flush()
            flush()
            counts['unique_matches'] = len(matches)
            counts['requirement_classes'] = prepared.execute('SELECT COUNT(*) FROM requirement_classes').fetchone()[0]
            prepared.executescript('''
                CREATE INDEX input_process ON inputs(process_id,slot);
                CREATE INDEX output_resource ON outputs(resource_id,process_id);
                CREATE INDEX output_process ON outputs(process_id);
                CREATE INDEX match_resource ON matches(resource_id,match_id);
                CREATE INDEX process_representative ON processes(representative,id);
            ''')
            resource_nodes = {rid: i for i, (rid,) in enumerate(prepared.execute('SELECT id FROM resources ORDER BY id'))}
            process_nodes = {pid: len(resource_nodes) + len(matches) + i for i, (pid,) in
                             enumerate(prepared.execute('SELECT id FROM processes WHERE id=representative ORDER BY id'))}
            node_count = len(resource_nodes) + len(matches) + len(process_nodes)
            links = []
            links.extend((resource_nodes[rid], len(resource_nodes) + mid, 0)
                         for mid, rid in prepared.execute('SELECT match_id,resource_id FROM matches'))
            links.extend((len(resource_nodes) + mid, process_nodes[pid], 1)
                         for pid, mid in prepared.execute('SELECT DISTINCT process_id,match_id FROM inputs'))
            links.extend((process_nodes[pid], resource_nodes[rid], 0)
                         for pid, rid in prepared.execute('SELECT DISTINCT process_id,resource_id FROM outputs'))
            offsets = array('I', [0]) * (node_count + 1)
            for src, _, _ in links:
                offsets[src + 1] += 1
            for i in range(node_count):
                offsets[i + 1] += offsets[i]
            positions = array('I', offsets)
            destinations, costs = array('I', [0]) * len(links), bytearray(len(links))
            for src, dest, cost in links:
                i = positions[src]
                destinations[i], costs[i] = dest, cost
                positions[src] += 1
            prepared.executemany('INSERT INTO graph VALUES(?,?)', [('offsets', offsets.tobytes()),
                ('destinations', destinations.tobytes()), ('costs', bytes(costs)),
                ('resource_nodes', json.dumps(resource_nodes).encode()),
                ('process_nodes', json.dumps(process_nodes).encode())])
            counts.update(graph_nodes=node_count, graph_arcs=len(links),
                          unresolved_inputs=len(unresolved_inputs), unresolved_outputs=len(unresolved_outputs))
            elapsed = time.perf_counter() - before
            prepared.executemany('INSERT INTO metadata VALUES(?,?)', [('manifest', dataset._manifest_json),
                ('analysis_version', str(ANALYSIS_VERSION)), ('prepared_seconds', str(elapsed)),
                ('counts', json.dumps(counts))])
        os.replace(temporary, path)
        dataset._flow_distances = None
    finally:
        temporary.unlink(missing_ok=True)
    return dict(status(dataset), prepared_seconds=time.perf_counter() - before)


def _source_distances(dataset, connection, start_id, tier_filter, excluded):
    """Relaxed process-count distances preserve every consumed OR alternative.

    AND slots and required waypoints are relaxed only for this lower bound.
    Tiers and exclusions apply here as well as in concrete branch search.
    """
    cached = getattr(dataset, '_flow_distances', None)
    cache_key = start_id, tier_filter['min_tier'], tier_filter['max_tier'], tier_filter['unknown_tier_policy'], tuple(sorted(excluded))
    if cached is not None and cached[0] == cache_key:
        return cached[1], cached[2], 0, True
    blobs = dict(connection.execute('SELECT name,payload FROM graph'))
    offsets, destinations = array('I'), array('I')
    offsets.frombytes(blobs['offsets'])
    destinations.frombytes(blobs['destinations'])
    costs = blobs['costs']
    nodes = json.loads(blobs['resource_nodes'])
    blocked = {nodes[rid] for rid in excluded}
    if tier_filter['active']:
        process_nodes = json.loads(blobs['process_nodes'])
        for pid, tier, tier_status in connection.execute('SELECT id,tier,tier_status FROM processes WHERE id=representative'):
            accepted = (tier_status == 'not_applicable' or tier is None and tier_filter['unknown_tier_policy'] == 'include' or
                        tier is not None and (tier_filter['min_tier'] is None or tier >= tier_filter['min_tier'])
                        and (tier_filter['max_tier'] is None or tier <= tier_filter['max_tier']))
            if not accepted:
                blocked.add(process_nodes[pid])
    distances = array('I', [0xffffffff]) * (len(offsets) - 1)
    source = nodes[start_id]
    distances[source] = 0
    queue = deque([source])
    work = 0
    while queue:
        node = queue.popleft()
        if node in blocked:
            continue
        depth = distances[node]
        for i in range(offsets[node], offsets[node + 1]):
            work += 1
            dest, cost = destinations[i], costs[i]
            next_depth = depth + cost
            if next_depth < distances[dest]:
                distances[dest] = next_depth
                if cost:
                    queue.append(dest)
                else:
                    queue.appendleft(dest)
    dataset._flow_distances = cache_key, distances, nodes
    return distances, nodes, work, False


def find_paths(dataset, canonical, start_id, target_id, max_depth, max_processes, max_paths,
               required, excluded, max_extra_steps, tier_filter, terminal_artifact_policy='allow'):
    from .dataset import DatasetError
    prepared_status = status(dataset)
    if prepared_status['status'] != 'ready':
        raise DatasetError('Prepared flow index is missing or incompatible. Run rebuild_flow_index to rebuild it')
    route = {'status': 'not_found', 'strategy': 'material_relevant_dependency_paths', 'resource_ids': [], 'process_ids': []}
    search = {'examined_processes': 0, 'limit': 10000, 'examined_states': 0, 'state_limit': 20000,
              'expansion_work': 0, 'work_limit': 100000, 'enumeration_work': 0, 'enumeration_limit': 100000,
              'queued_states': 0, 'peak_queue': 0, 'truncated': False, 'prepared_index': prepared_status,
              'prepared_lookup_hits': 0, 'distance_pruned_states': 0, 'loaded_process_records': 0}
    partial = {'created_cursors': 0, 'cursor_admissions': 0, 'cursor_resumes': 0, 'cursor_pops': 0,
               'released_cursors': 0, 'candidate_validations': 0, 'sorted_candidates': 0,
               'deferred_candidates': 0, 'peak_deferred_candidates': 0,
               'retained_candidates': 0, 'peak_retained_candidates': 0}
    search['partial_expansion'] = partial
    recovery = {'policy': 'native_recycling_association_hint', 'weight': _RECOVERY_WEIGHT,
                'recipe_family_lookups': 0, 'recipe_family_cache_hits': 0,
                'resource_fact_lookups': 0, 'resource_fact_cache_hits': 0,
                'penalty_evaluations': 0, 'penalized_evaluations': 0}
    search['recovery_preference'] = recovery
    classes = {'policy': 'snapshot_accepted_resource_effect_equivalence', 'prepared_slot_lookups': 0,
               'prepared_slot_rows': 0, 'class_assignment_work': 0, 'known_classes': 0, 'unresolved_jobs': 0,
               'target_jobs': 0, 'represented_classes': 0, 'represented_unresolved_jobs': 0, 'scheduler_job_decisions': 0,
               'scheduled_turn_decisions': 0, 'completion_coverage_decisions': 0,
               'unrepresented_class_rounds': 0, 'remaining_endpoint_rounds': 0, 'actual_job_turns': 0,
               'completed_witnesses_admitted_or_reused': 0, 'charged_work': 0}
    search['requirement_classes'] = classes
    material_evidence = {'policy': 'native_declaration_basis', 'prepared_resource_lookups': 0,
                         'comparisons': 0, 'uncertain_disjoint_comparisons': 0}
    search['material_evidence'] = material_evidence
    families, resource_facts = {}, {}
    paths, reasons, branches = [], set(), []
    terminal_categories = {}
    search['terminal_artifacts'] = dataset._terminal_artifact_search(terminal_artifact_policy)

    def class_charge(counter, units=1):
        if search['expansion_work'] + units > search['work_limit']:
            reasons.add('search_work_limit')
            return False
        search['expansion_work'] += units
        classes['charged_work'] += units
        classes[counter] += units
        return True
    if required & excluded or start_id in excluded or target_id in excluded:
        return route, paths, search, [], [], branches
    if start_id == target_id:
        if required <= {start_id}:
            paths.append({'resource_ids': [start_id], 'process_ids': []})
            route.update(status='same_resource', **paths[0])
        return route, paths, search, [], [], branches
    with closing(sqlite3.connect(f'{index_path(dataset).as_uri()}?mode=ro', uri=True)) as connection:
        before = time.perf_counter()
        distances, nodes, distance_work, reused = _source_distances(dataset, connection, start_id, tier_filter, excluded)
        search.update(distance_work=distance_work, distance_seconds=time.perf_counter() - before, distance_cache_hit=reused)
        @lru_cache(maxsize=None)
        def material_hint_for(rid):
            material_evidence['prepared_resource_lookups'] += 1
            tokens, basis = connection.execute('SELECT materials,material_basis FROM resources WHERE id=?', (rid,)).fetchone()
            return frozenset(json.loads(tokens)), basis

        def material_for(rid):
            return material_hint_for(rid)[0]

        source_materials = material_for(start_id)
        examined, reverse, checked_tiers = set(), {}, set()
        connection.execute('CREATE TEMP TABLE distance(resource_id TEXT PRIMARY KEY,depth INTEGER)')
        connection.executemany('INSERT INTO distance VALUES(?,?)',
                               ((rid, distances[node]) for rid, node in nodes.items() if distances[node] != 0xffffffff))

        def allowed(pid, tier, tier_status):
            if not tier_filter['active'] or tier_status == 'not_applicable':
                return True
            known = tier is not None
            accepted = ((known and (tier_filter['min_tier'] is None or tier >= tier_filter['min_tier'])
                         and (tier_filter['max_tier'] is None or tier <= tier_filter['max_tier']))
                        or not known and tier_filter['unknown_tier_policy'] == 'include')
            if not accepted and pid not in checked_tiers:
                tier_filter['excluded_out_of_range' if known else 'excluded_unknown'] += 1
                checked_tiers.add(pid)
            return accepted

        def predecessors(rid, remaining=max_depth):
            key = rid, remaining
            if key in reverse:
                search['prepared_lookup_hits'] += 1
                return reverse[key]
            entries = []
            rows = connection.execute('''SELECT DISTINCT o.process_id,i.slot,m.resource_id,o.position,p.tier,p.tier_status
                FROM outputs o JOIN processes p ON p.id=o.process_id
                JOIN inputs i ON i.process_id=o.process_id JOIN matches m ON m.match_id=i.match_id
                JOIN distance d ON d.resource_id=m.resource_id
                WHERE o.resource_id=? AND d.depth<? ORDER BY o.process_id,i.slot,m.resource_id''', (rid, remaining))
            for pid, si, input_id, position, tier, tier_status in rows:
                if pid not in examined:
                    if len(examined) >= search['limit']:
                        reasons.add('search_process_limit')
                        break
                    examined.add(pid)
                if not allowed(pid, tier, tier_status) or input_id in excluded:
                    continue
                search['expansion_work'] += 1
                if search['expansion_work'] > search['work_limit']:
                    reasons.add('search_work_limit')
                    break
                if not dataset._terminal_edge_allowed(connection, input_id, rid, terminal_categories, search, reasons, prepared=True):
                    if 'search_work_limit' in reasons:
                        break
                    continue
                entries.append((pid, si, input_id, position))
            reverse[key] = entries
            return entries

        def recipe_family(pid):
            if pid in families:
                recovery['recipe_family_cache_hits'] += 1
                return families[pid]
            recovery['recipe_family_lookups'] += 1
            families[pid] = canonical.execute("SELECT json_extract(payload,'$.family') FROM records WHERE collection='processes' AND id=?", (pid,)).fetchone()[0]
            return families[pid]

        def resource_role(rid):
            if rid in resource_facts:
                recovery['resource_fact_cache_hits'] += 1
                return resource_facts[rid]
            recovery['resource_fact_lookups'] += 1
            resource_facts[rid] = tuple(canonical.execute('''SELECT json_extract(payload,'$.kind'),
                json_extract(payload,'$.material_facts.association.primary.material.name'),
                json_extract(payload,'$.material_facts.association.prefix'),
                json_extract(payload,'$.material_facts.association.has_explicit_composition')
                FROM records WHERE collection='resources' AND id=?''', (rid,)).fetchone())
            return resource_facts[rid]

        def recovery_penalty(pid, source, dest):
            recovery['penalty_evaluations'] += 1
            if recipe_family(pid) not in _RECOVERY_FAMILIES:
                return 0
            left_kind, left_material, left_form, explicit = resource_role(source)
            right_kind, right_material, right_form, _ = resource_role(dest)
            if left_kind != 'item' or right_kind != 'item' or right_material is None:
                return 0
            # Recycling composition describes the item, not the selected input's atom provenance.
            composite = explicit == 1 and left_form is None and right_form in _SIMPLE_FORMS
            crafted = (left_material is not None and left_material == right_material
                       and left_form in _CRAFTED_FORMS and right_form in _DUST_FORMS)
            if composite or crafted:
                recovery['penalized_evaluations'] += 1
                return _RECOVERY_WEIGHT
            return 0

        def penalty(source, dest, position, pid):
            left, right = material_hint_for(source), material_hint_for(dest)
            discontinuity = material_comparison(left, right)
            material_evidence['comparisons'] += 1
            material_evidence['uncertain_disjoint_comparisons'] += int(
                discontinuity == 1 and bool(left[0] and right[0]))
            return discontinuity + (2 if position else 0) + recovery_penalty(pid, source, dest)

        jobs = {}
        target_entries = predecessors(target_id)
        for pid, si, input_id, position in target_entries:
            key = pid, si
            job = jobs.setdefault(key, {'pid': pid, 'slot': si, 'candidates': set(), 'heap': [], 'seen': {}, 'paths': [], 'cursors': {}})
            job['candidates'].add(input_id)
            if distances[nodes[input_id]] + 1 > max_depth:
                search['distance_pruned_states'] += 1
                continue
            score = penalty(input_id, target_id, position, pid)
            heappush(job['heap'], (score, 1 + distances[nodes[input_id]], (target_id, input_id), (pid,)))
            search['queued_states'] += 1
            search['peak_queue'] = max(search['peak_queue'], len(job['heap']))

        known_classes, represented_classes = set(), set()
        for key, job in jobs.items():
            if not class_charge('prepared_slot_lookups'):
                break
            row = connection.execute('SELECT class_id,status FROM input_requirements WHERE process_id=? AND slot=?', key).fetchone()
            if not class_charge('prepared_slot_rows') or not class_charge('class_assignment_work', 2):
                break
            if row is not None and row[1] == 'complete' and row[0] is not None:
                job['class'] = ('prepared', row[0])
                known_classes.add(row[0])
            else:
                job['class'] = ('unresolved', *key)
                classes['unresolved_jobs'] += 1
        classes.update(known_classes=len(known_classes), target_jobs=len(jobs))

        scope = max_depth
        reference_bounds = set()

        def release_cursor(job, cursor_id):
            cursor = job['cursors'].pop(cursor_id)
            partial['retained_candidates'] -= len(cursor['choices'])
            partial['deferred_candidates'] -= len(cursor['choices']) - cursor['next']
            partial['released_cursors'] += 1

        def clear_job(job):
            job['heap'].clear()
            for cursor_id in list(job['cursors']):
                release_cursor(job, cursor_id)

        def enqueue_cursor(job, cursor_id):
            if search['queued_states'] >= search['state_limit']:
                reasons.add('search_state_limit')
                return False
            cursor = job['cursors'][cursor_id]
            score, bound, pid, input_id = cursor['choices'][cursor['next']]
            if cursor['next']:
                partial['cursor_resumes'] += 1
            cursor['next'] += 1
            # One heap entry is one concrete child. Deferred choices share the parent history.
            heappush(job['heap'], (score, bound, cursor['resources'] + (input_id,),
                                  cursor['processes'] + (pid,), cursor_id))
            search['queued_states'] += 1
            partial['cursor_admissions'] += 1
            partial['deferred_candidates'] -= 1
            search['peak_queue'] = max(search['peak_queue'], len(job['heap']))
            return True

        def advance(job):
            turns = 0
            while job['heap'] and turns < 64:
                entry = heappop(job['heap'])
                score, _, rr, pp = entry[:4]
                if len(entry) == 5:
                    cursor_id = entry[4]
                    cursor = job['cursors'][cursor_id]
                    partial['cursor_pops'] += 1
                    if cursor['next'] < len(cursor['choices']):
                        enqueue_cursor(job, cursor_id)
                    else:
                        release_cursor(job, cursor_id)
                depth = len(pp)
                turns += 1
                search['examined_states'] += 1
                rid = rr[-1]
                if rid == start_id:
                    if required <= set(rr):
                        return {'resource_ids': list(reversed(rr)), 'process_ids': list(reversed(pp))}
                    continue
                key = rid, frozenset(required & set(rr)), frozenset(rr) if required else None
                frontier = job['seen'].setdefault(key, [])
                if any(old_score <= score and old_depth <= depth for old_score, old_depth in frontier):
                    continue
                frontier[:] = [(s, d) for s, d in frontier if not (score <= s and depth <= d)]
                frontier.append((score, depth))
                if depth >= scope:
                    if connection.execute('SELECT 1 FROM outputs WHERE resource_id=? LIMIT 1', (rid,)).fetchone():
                        reasons.add('depth')
                    continue
                if job.get('objective') == 'hops':
                    reference_bounds.add((rid, scope - depth))
                choices = []
                for pid, _, input_id, position in predecessors(rid, scope - depth):
                    partial['candidate_validations'] += 1
                    if input_id in rr or pid in pp:
                        continue
                    if distances[nodes[input_id]] + depth + 1 > scope:
                        search['distance_pruned_states'] += 1
                        continue
                    if job.get('objective') == 'hops':
                        next_score = depth + 1 + distances[nodes[input_id]]
                    else:
                        next_score = score + penalty(input_id, rid, position, pid)
                        # Material overlap guides ties before a branch spends its budget.
                        next_score += 0 if material_for(input_id) & source_materials else 1
                    choices.append((next_score, depth + 1 + distances[nodes[input_id]], pid, input_id))
                if choices:
                    # Repeated AND slots retain one recipe witness and the same spine continuation.
                    choices = sorted(set(choices), key=lambda child: (child[0], child[1], child[3], child[2]))
                    cursor_id = partial['created_cursors']
                    partial['created_cursors'] += 1
                    partial['sorted_candidates'] += len(choices)
                    partial['retained_candidates'] += len(choices)
                    partial['deferred_candidates'] += len(choices)
                    partial['peak_retained_candidates'] = max(partial['peak_retained_candidates'], partial['retained_candidates'])
                    partial['peak_deferred_candidates'] = max(partial['peak_deferred_candidates'], partial['deferred_candidates'])
                    job['cursors'][cursor_id] = {'resources': rr, 'processes': pp, 'choices': choices, 'next': 0}
                    enqueue_cursor(job, cursor_id)
                if reasons & {'search_process_limit', 'search_work_limit', 'search_state_limit'}:
                    return None
            return None

        reference = {'heap': [(distances[nodes[target_id]], 0, (target_id,), ())] if distances[nodes[target_id]] <= max_depth else [],
                     'seen': {}, 'objective': 'hops', 'cursors': {}}
        reference_path = None
        target_distance = distances[nodes[target_id]]
        if max_depth < target_distance < 0xffffffff:
            reasons.add('depth')
        before_reference = search['examined_states']
        while reference['heap'] and not reasons & {'search_process_limit', 'search_work_limit', 'search_state_limit'}:
            reference_path = advance(reference)
            if reference_path is not None:
                scope = min(max_depth, len(reference_path['process_ids']) + max_extra_steps)
                break
        if reference_path is None and required and 'depth' not in reasons:
            for rid, remaining in reference_bounds:
                rows = connection.execute('''SELECT DISTINCT o.process_id,p.tier,p.tier_status,m.resource_id
                    FROM outputs o JOIN processes p ON p.id=o.process_id
                    JOIN inputs i ON i.process_id=o.process_id JOIN matches m ON m.match_id=i.match_id
                    JOIN distance d ON d.resource_id=m.resource_id
                    WHERE o.resource_id=? AND d.depth>=?''', (rid, remaining))
                if any(input_id not in excluded and allowed(pid, tier, tier_status)
                       for pid, tier, tier_status, input_id in rows):
                    reasons.add('depth')
                    break
        search['hop_reference'] = {'status': 'found' if reference_path else 'bounded' if reasons else 'not_found',
                                   'hops': len(reference_path['process_ids']) if reference_path else None,
                                   'examined_states': search['examined_states'] - before_reference,
                                   'depth_limit': scope}
        if reference_path is None and not reference['heap']:
            for job in jobs.values():
                clear_job(job)
        clear_job(reference)

        ordered = sorted(jobs.values(), key=lambda job: (
            not any(material_for(rid) & source_materials for rid in job['candidates']), job['pid'], job['slot']))

        def class_round():
            selected, picked = [], set()
            for job in ordered:
                if not class_charge('scheduler_job_decisions'):
                    return [], True
                cid = job['class']
                if job['heap'] and cid not in represented_classes and cid not in picked:
                    selected.append(job)
                    picked.add(cid)
            if selected:
                classes['unrepresented_class_rounds'] += 1
                return selected, True
            classes['remaining_endpoint_rounds'] += 1
            return ordered, False

        def class_completed(path):
            if not class_charge('completion_coverage_decisions', len(ordered)):
                return False
            pid, rid = path['process_ids'][-1], path['resource_ids'][-2]
            for job in ordered:
                if job['pid'] == pid and rid in job['candidates']:
                    if job['class'] not in represented_classes:
                        counter = 'represented_classes' if job['class'][0] == 'prepared' else 'represented_unresolved_jobs'
                        classes[counter] += 1
                    represented_classes.add(job['class'])
            classes['completed_witnesses_admitted_or_reused'] += 1
            return True

        signatures, admitted = {}, set()
        while (any(job['heap'] for job in ordered) and len(paths) < max_paths
               and not reasons & {'search_process_limit', 'search_work_limit', 'search_state_limit'}):
            selected, priority_round = class_round()
            for job in selected:
                if not class_charge('scheduled_turn_decisions'):
                    break
                if priority_round and job['class'] in represented_classes:
                    continue
                classes['actual_job_turns'] += 1
                path = advance(job)
                if path is None:
                    continue
                signature = tuple(path['process_ids']), tuple(path['resource_ids'])
                if signature in signatures:
                    if not class_completed(path):
                        break
                    job['paths'].append(signatures[signature])
                    clear_job(job)
                    continue
                if len(admitted | set(path['process_ids'])) > max_processes:
                    reasons.add('path_process_limit')
                    continue
                if not class_completed(path):
                    break
                job['paths'].append(path)
                clear_job(job)
                paths.append(path)
                signatures[signature] = path
                admitted.update(path['process_ids'])
                if len(paths) >= max_paths:
                    break
            search['peak_queue'] = max(search['peak_queue'], sum(len(job['heap']) for job in ordered))
            if reasons & {'search_process_limit', 'search_work_limit', 'search_state_limit'}:
                break
        def path_score(path):
            score = 0
            for rid, dest, pid in zip(path['resource_ids'], path['resource_ids'][1:], path['process_ids']):
                position = connection.execute('SELECT MIN(position) FROM outputs WHERE process_id=? AND resource_id=?', (pid, dest)).fetchone()[0]
                score += penalty(rid, dest, position, pid)
            return score, len(path['process_ids']), tuple(path['process_ids'])
        paths.sort(key=path_score)
        if len(paths) >= max_paths:
            reasons.add('path_limit')
        if paths:
            route.update(status='found', **paths[0])
        elif reasons:
            route['status'] = 'incomplete'
        for job in ordered:
            indices = [i for i, path in enumerate(paths) if path['process_ids'][-1] == job['pid']
                       and path['resource_ids'][-2] in job['candidates']]
            branches.append({'target_process_id': job['pid'], 'slot_index': job['slot'],
                             'candidate_resources': len(job['candidates']), 'paths': len(indices), 'path_indices': indices,
                             'status': 'represented' if indices else 'not_discovered'})
        duplicates = [{'representative_id': pid, 'duplicate_ids': [row[0] for row in connection.execute(
            'SELECT id FROM processes WHERE representative=? AND id!=? ORDER BY id', (pid, pid))]} for pid in sorted(admitted)]
        duplicates = [row for row in duplicates if row['duplicate_ids']]
        search.update(examined_processes=len(examined), loaded_process_records=len(admitted), truncated=bool(reasons),
                      pending_states=sum(len(job['heap']) for job in ordered),
                      selection_policy='one_material_relevant_spine_per_target_ingredient_branch')
        partial['pending_cursors'] = sum(len(job['cursors']) for job in ordered)
        partial['pending_cursor_entries'] = sum(len(entry) == 5 for job in ordered for entry in job['heap'])
        return route, paths, search, sorted(reasons), duplicates, branches


def path_details(dataset, paths, resources, processes, branches):
    from .dataset import DatasetError
    details, categories, groups = [], {}, {}
    @lru_cache(maxsize=None)
    def material_hint_for(rid):
        return material_tokens(resources[rid]), material_basis(resources[rid])
    with dataset._connect() as connection:
        def category_groups(rid):
            if rid not in categories:
                matched, basis = [], 'native_ore_dictionary_matching_membership'
                categories[rid] = matched, basis
                resource = resources[rid]
                if 'ore_dictionary_membership' in resource:
                    membership = resource['ore_dictionary_membership']
                    if (resource['kind'] != 'item' or not isinstance(membership, dict) or membership.get('status') != 'captured'
                            or membership.get('source_api') != 'OreDictionary.getOreIDs'
                            or membership.get('matching_semantics') != 'item_and_metadata_with_wildcard_nbt_ignored'
                            or not isinstance(membership.get('group_ids'), list)
                            or any(not isinstance(gid, str) or not gid for gid in membership['group_ids'])):
                        return categories[rid]
                    candidate_ids = sorted(set(membership['group_ids']))
                else:
                    # Existing immutable captures retain their exact registered-member evidence.
                    basis = 'exact_captured_ore_dictionary_membership'
                    candidate_ids = [gid for gid, in connection.execute("SELECT group_id FROM members WHERE resource_id=? "
                        "AND group_id GLOB 'ore:craftingTool*' ORDER BY group_id", (rid,))]
                for gid in candidate_ids:
                    if gid not in groups:
                        try:
                            groups[gid] = dataset._record(connection, 'groups', gid)
                        except DatasetError:
                            groups[gid] = None
                    group = groups[gid]
                    if group is None or (basis == 'native_ore_dictionary_matching_membership'
                            and (group['kind'] != 'ore_dict' or gid != 'ore:' + group['name'])):
                        matched.clear()
                        return categories[rid]
                    if group['kind'] == 'ore_dict' and group['name'].startswith('craftingTool'):
                        matched.append(gid)
                categories[rid] = matched, basis
            return categories[rid]

        for index, path in enumerate(paths):
            if not path['process_ids']:
                continue
            missing, breaks, byproducts, input_hints = 0, 0, [], []
            for step, (source, dest, pid) in enumerate(zip(path['resource_ids'], path['resource_ids'][1:], path['process_ids'])):
                comparison = material_comparison(material_hint_for(source), material_hint_for(dest))
                missing += int(comparison == 1)
                breaks += int(comparison == 4)
                outputs = processes[pid]['outputs']
                position = next(i for i, output in enumerate(outputs) if output['resource_id'] == dest)
                if position:
                    byproducts.append({'process_id': pid, 'resource_id': dest, 'basis': 'secondary_output_position_hint'})
                group_ids, basis = category_groups(source)
                if group_ids:
                    # Category membership does not establish actual tool use or remainder behavior.
                    conditions = processes[pid]['conditions']
                    input_hints.append({'step_index': step, 'process_id': pid, 'resource_id': source,
                        'category': 'crafting_tool', 'basis': basis,
                        'group_ids': group_ids, 'input_role': 'consume',
                        'native_accounting': {key: conditions.get(key) for key in
                            ('tool_accounting', 'container_returns', 'input_accounting')},
                        'scope': 'selected_resource_category_only'})
            branch = next((row for row in branches if index in row['path_indices']), {})
            details.append({'path_index': index, 'material_continuity': 'discontinuous' if breaks else 'partial' if missing else 'supported',
                'selection_reason': 'Preserved a target ingredient branch despite a material discontinuity hint' if breaks else
                                    'Dependency branch found with incomplete material hints' if missing else
                                    'Prioritized native material continuity and target ingredient coverage',
                'byproduct_steps': byproducts, 'target_process_id': branch.get('target_process_id'),
                'target_slot_index': branch.get('slot_index'), 'scope': 'dependency_spine_with_external_inputs',
                'input_category_hints': input_hints})
    return details
