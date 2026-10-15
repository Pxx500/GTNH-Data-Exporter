"""Snapshot-bound, read-only recipe search benchmark.

The CLI accepts DATABASE MANIFEST OUTPUT_DIRECTORY. Fixed-work runs use one
unchanged synchronous request. Wall-time checkpoints continue one live material
search job and retain actual active time separately from requested budgets.
"""


import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import shutil
import statistics
import sys
import time

from gtnh_data import Dataset


DEFAULT_REQUEST = {'max_depth': 12, 'max_processes': 300, 'max_paths': 8,
                   'required_resource_ids': None, 'excluded_resource_ids': None,
                   'excluded_group_ids': None, 'max_extra_steps': 6, 'min_tier': None,
                   'max_tier': None, 'unknown_tier_policy': 'exclude',
                   'path_selection': 'diverse', 'view': 'full', 'terminal_artifact_policy': 'allow'}


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _request(request):
    if set(request) - (set(DEFAULT_REQUEST) | {'start_id', 'target_id'}):
        raise ValueError('unknown synchronous trace request setting')
    if not all(isinstance(request.get(key), str) and request[key] for key in ('start_id', 'target_id')):
        raise ValueError('exact start_id and target_id are required')
    return DEFAULT_REQUEST | request


def load_manifest(dataset, path):
    """Load hash-bound saved requests, refusing a different snapshot or cohort."""
    path = Path(path)
    manifest = _read(path)
    if manifest.get('schema_version') != 1:
        raise ValueError('unsupported benchmark manifest schema_version')
    binding = manifest['binding']
    status = dataset.status()
    if binding['snapshot_id'] != status['snapshot_id']:
        raise ValueError('snapshot binding does not match dataset')
    cohort = json.dumps(status['manifest']['pack'], sort_keys=True, separators=(',', ':')).encode()
    if binding['cohort_sha256'] != hashlib.sha256(cohort).hexdigest():
        raise ValueError('mod cohort binding does not match dataset')
    if manifest.get('regime') not in ('fixed_work', 'wall_time'):
        raise ValueError('regime must be fixed_work or wall_time')
    if manifest['regime'] == 'wall_time':
        checkpoints = manifest.get('checkpoints_seconds')
        if (not isinstance(checkpoints, list) or not checkpoints or any(
                type(value) not in (int, float) or not math.isfinite(value) or not .05 <= value <= 60
                for value in checkpoints) or checkpoints != sorted(set(checkpoints))):
            raise ValueError('wall_time checkpoints_seconds must be increasing finite budgets from 0.05 to 60')
    if binding.get('database_sha256') != sha256(dataset.path):
        raise ValueError('database hash binding does not match dataset')
    names = set()
    for case in manifest['cases']:
        name = case['name']
        if not name or name in names or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_-' for c in name):
            raise ValueError('case names must be unique lowercase filename-safe identifiers')
        names.add(name)
        source = (path.parent / case['baseline']['path']).resolve()
        if sha256(source) != case['baseline']['sha256']:
            raise ValueError(f'{name}: saved baseline hash changed')
        saved = _read(source)
        if saved['result']['snapshot_id'] != binding['snapshot_id']:
            raise ValueError(f'{name}: saved baseline snapshot differs')
        if _request(case['request']) != _request(saved['measurement']['request']):
            raise ValueError(f'{name}: saved request differs from case request')
        multiplier = case.get('budget_multiplier', 1)
        if type(multiplier) is not int or not 1 <= multiplier <= 10:
            raise ValueError(f'{name}: budget_multiplier must be an integer between 1 and 10')
        if manifest['regime'] == 'fixed_work' and multiplier != 1:
            raise ValueError(f'{name}: larger budgets require wall_time jobs')
        if manifest['regime'] == 'wall_time' and _request(case['request'])['path_selection'] != 'material':
            raise ValueError(f'{name}: wall_time requires material path selection')
    return manifest


def evaluate_result(case, result, baseline):
    """Compare returned dependency spines without calling them inventory plans."""
    def key(path):
        return tuple(path['resource_ids']), tuple(path['process_ids'])

    def indices(paths, sequence, field):
        if not sequence:
            return []
        matched = []
        for index, path in enumerate(paths):
            remaining = iter(path[field])
            if all(any(value == expected for value in remaining) for expected in sequence):
                matched.append(index)
        return matched

    paths, old_paths = result['paths'], baseline['paths']
    keys, old_keys = {key(path) for path in paths}, {key(path) for path in old_paths}
    expected, request = case.get('expected', {}), case['request']
    processes = {process['id']: process for process in result['processes']}
    families = [{'families': [processes.get(id, {}).get('family') for id in path['process_ids']]}
                for path in paths]
    represented = {(branch['target_process_id'], branch['slot_index'])
                   for branch in result['branch_coverage'] if branch.get('path_indices')}
    expected_jobs = {tuple(job) for job in expected.get('target_jobs', [])}
    witness = expected.get('witness')
    errors = []
    if len(paths) > request['max_paths']:
        errors.append('returned path count exceeds max_paths')
    union = {id for path in paths for id in path['process_ids']}
    if union != set(processes) or len(union) > request['max_processes']:
        errors.append('returned process union differs or exceeds max_processes')
    for index, path in enumerate(paths):
        resources, pids = path['resource_ids'], path['process_ids']
        if (not resources or resources[0] != request['start_id'] or resources[-1] != request['target_id']
                or len(resources) != len(pids) + 1 or len(pids) > request['max_depth']
                or len(resources) != len(set(resources)) or len(pids) != len(set(pids))):
            errors.append(f'path {index} violates endpoint, depth or simple-spine contract')
    if paths and key(result['route']) != key(paths[0]):
        errors.append('route differs from first returned path')
    for branch in result['branch_coverage']:
        if any(type(index) is not int or not 0 <= index < len(paths)
               or paths[index]['process_ids'][-1] != branch['target_process_id']
               for index in branch.get('path_indices', [])):
            errors.append('target branch contains an invalid path reference')

    def counters(value, prefix=''):
        numeric = {}
        for name, child in value.items():
            field = f'{prefix}.{name}' if prefix else name
            if isinstance(child, dict):
                numeric.update(counters(child, field))
            elif type(child) in (int, float):
                numeric[field] = child
        return numeric

    current_counters, previous_counters = counters(result['search']), counters(baseline['search'])
    story_indices = indices(paths, expected.get('resource_sequence'), 'resource_ids')
    return {
        'path_count': len(paths), 'unique_path_count': len(keys),
        'path_set': {'common': len(keys & old_keys), 'added': len(keys - old_keys),
                     'removed': len(old_keys - keys),
                     'precision': len(keys & old_keys) / len(keys) if keys else None,
                     'recall': len(keys & old_keys) / len(old_keys) if old_keys else None},
        'first_route': {'same_as_baseline': bool(paths and old_paths and key(paths[0]) == key(old_paths[0])),
                        'path': paths[0] if paths else None,
                        'seconds': None,
                        'timing_scope': 'path position only, arrival timing is reported separately by run regime'},
        'expected_witness_path_indices': [i for i, path in enumerate(paths) if witness and key(path) == key(witness)],
        'resource_sequence_path_indices': story_indices,
        'first_route_contains_resource_sequence': 0 in story_indices,
        'family_sequence_path_indices': indices(families, expected.get('family_sequence'), 'families'),
        'target_jobs': {'represented': len(represented), 'total': len(result['branch_coverage']),
                        'expected': len(expected_jobs),
                        'expected_recall': len(represented & expected_jobs) / len(expected_jobs) if expected_jobs else None,
                        'missing_expected': sorted(expected_jobs - represented)},
        'represented_classes': result['search'].get('requirement_classes', {}).get('represented_classes'),
        'search_numeric_deltas': {name: value - previous_counters[name]
                                 for name, value in current_counters.items() if name in previous_counters},
        'path_details': result.get('path_details', []),
        'search': result['search'], 'branch_coverage': result['branch_coverage'],
        'limit_reasons': result['limit_reasons'], 'structural_errors': errors}


def validate_witness(dataset, case):
    """Retain full declarations and reuse Dataset's native consumed-slot matcher.

    A witness is a conditional dependency spine. Cofeed supply, batch alignment,
    machine execution and stock feasibility are outside this proof.
    """
    started = time.perf_counter()
    witness = case.get('expected', {}).get('witness')
    receipt = {'status': 'not_declared', 'expanded_choices': 0, 'match_memberships': 0,
               'resources': [], 'processes': [], 'hops': [],
               'scope': 'dependency spine conditional on all other AND inputs and machine conditions',
               'matcher': 'Dataset._choice_resources on consume slots, Dataset source SHA256 retained in receipt'}
    if not witness:
        receipt['seconds'] = time.perf_counter() - started
        return receipt
    rr, pp = witness['resource_ids'], witness['process_ids']
    request = _request(case['request'])
    if (len(rr) != len(pp) + 1 or not pp or rr[0] != request['start_id']
            or rr[-1] != request['target_id'] or len(pp) > request['max_depth']
            or len(rr) != len(set(rr)) or len(pp) != len(set(pp))):
        raise ValueError(f"{case['name']}: invalid witness spine structure")
    if (not set(request['required_resource_ids'] or []) <= set(rr)
            or set(request['excluded_resource_ids'] or []) & set(rr)):
        raise ValueError(f"{case['name']}: witness contradicts resource constraints")
    receipt['resources'] = [dataset.get_resource(id)['item'] for id in rr]
    unknown = False
    invalid = False
    filters = dataset._tier_filter(request['min_tier'], request['max_tier'], request['unknown_tier_policy'])
    with dataset._connect() as connection:
        for group_id in request['excluded_group_ids'] or []:
            excluded = {row[0] for row in connection.execute('SELECT resource_id FROM members WHERE group_id=?', (group_id,))}
            if excluded & set(rr):
                raise ValueError(f"{case['name']}: witness contradicts excluded group")
        for start, pid, target in zip(rr, pp, rr[1:]):
            process = dataset.get_process(pid)['item']
            receipt['processes'].append(process)
            unresolved = connection.execute("SELECT 1 FROM records WHERE collection='processes' AND id=? AND "
                + dataset._unresolved_input_clause(), (pid,)).fetchone() is not None
            matched_slots = []
            if not unresolved:
                for index, slot in enumerate(process['inputs']):
                    if slot['role'] != 'consume':
                        continue
                    for choice in slot['choices']:
                        matches = dataset._choice_resources(connection, choice)
                        receipt['expanded_choices'] += 1
                        receipt['match_memberships'] += len(matches)
                        if start in matches:
                            matched_slots.append(index)
            positive = any(output['resource_id'] == target and dataset._positive_output(output)
                           for output in process['outputs'])
            output_unknown = process['conditions'].get('dynamic_output') == 'unresolved'
            valid = process['executable'] and positive and bool(matched_slots) and dataset._tier_allowed(process, filters)
            status = 'unknown' if unresolved or output_unknown else 'valid' if valid else 'invalid'
            unknown |= status == 'unknown'
            invalid |= status == 'invalid'
            receipt['hops'].append({'process_id': pid, 'input_id': start, 'output_id': target,
                                    'status': status, 'matched_consume_slots': sorted(set(matched_slots)),
                                    'tier': dataset._recipe_tier(process)})
    receipt['status'] = 'invalid' if invalid else 'unknown' if unknown else 'valid'
    receipt['seconds'] = time.perf_counter() - started
    return receipt


def run_wall_time(dataset, case, baseline, output, stem, checkpoints):
    """Observe cumulative active budgets on one job, closing it on every exit."""
    output = Path(output)
    started = time.perf_counter()
    envelope = dataset.start_trace_search(**case['request'], time_budget_seconds=checkpoints[0],
                                          budget_multiplier=case.get('budget_multiplier', 1))
    job_id = envelope['job_id']
    report = {'job_id': job_id, 'budget_multiplier': case.get('budget_multiplier', 1),
              'checkpoints': [], 'first_observed_expected_story': None,
              'first_result_scope': 'server creation to first nonempty rendered dependency result, usefulness not implied',
              'story_observation_scope': 'client-observed upper bound, active worker time and client wall time are separate'}
    latest_result = None
    latest_metrics = None
    result_revision = -1

    def observe(answer):
        nonlocal latest_result, latest_metrics, result_revision
        if answer['job_id'] != job_id:
            raise ValueError('search job identity changed during continuation')
        if answer.get('result') is not None and answer['result_revision'] > result_revision:
            latest_result = answer['result']
            latest_metrics = evaluate_result(case, latest_result, baseline)
            result_revision = answer['result_revision']
            resource_hits = set(latest_metrics['resource_sequence_path_indices'])
            family_hits = set(latest_metrics['family_sequence_path_indices'])
            expected = case.get('expected', {})
            story_hits = (resource_hits & family_hits if expected.get('resource_sequence') and expected.get('family_sequence')
                          else resource_hits | family_hits)
            if story_hits and report['first_observed_expected_story'] is None:
                report['first_observed_expected_story'] = {
                    'active_elapsed_seconds': answer['elapsed_seconds'],
                    'client_wall_seconds': time.perf_counter() - started,
                    'result_revision': result_revision, 'path_indices': sorted(story_hits),
                    'scope': 'first client-observed matching story, upper bound on availability'}

    try:
        observe(envelope)
        for index, target in enumerate(checkpoints):
            if index and envelope['status'] == 'paused' and envelope['elapsed_seconds'] < target:
                envelope = dataset.continue_trace_search(job_id,
                    time_budget_seconds=max(.05, target - envelope['elapsed_seconds']))
                observe(envelope)
            while envelope['status'] == 'running':
                time.sleep(.05)
                envelope = dataset.get_trace_search(job_id, after_revision=envelope['revision'])
                observe(envelope)
            actual = envelope['elapsed_seconds']
            terminal = envelope['status'] in ('finished', 'failed', 'closed')
            packet = dict(envelope)
            if latest_result is not None:
                packet['result'] = latest_result
            raw_path = output / f'{stem}-checkpoint-{index + 1:02d}.json'
            raw_path.write_text(json.dumps(packet, indent=2) + '\n', encoding='utf-8')
            report['checkpoints'].append({
                'requested_cumulative_seconds': target, 'actual_active_seconds': actual,
                'cooperative_overrun_seconds': max(0, actual - target),
                'early_terminal': terminal and actual < target,
                'checkpoint_reason': 'terminal' if terminal else 'time_budget_pause',
                'terminal_reason': {'status': envelope['status'], 'error': envelope.get('error'),
                                    'limit_reasons': latest_result.get('limit_reasons', []) if latest_result else []}
                                   if terminal else None,
                'client_wall_seconds': time.perf_counter() - started,
                'envelope': {key: value for key, value in envelope.items() if key != 'result'},
                'response': raw_path.name, 'response_sha256': sha256(raw_path), 'metrics': latest_metrics})
            if envelope['status'] in ('failed', 'closed'):
                break
    finally:
        try:
            report['cleanup'] = dataset.close_trace_search(job_id)
        finally:
            dataset.shutdown_trace_searches()
            (output / f'{stem}-job.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


def run_benchmark(database, manifest_path, output, *, repeats=1, preflight_only=False):
    """Write an exclusive run receipt, preserving every saved baseline and response."""
    if type(repeats) is not int or not 1 <= repeats <= 20:
        raise ValueError('repeats must be between 1 and 20')
    database, manifest_path, output = Path(database).resolve(), Path(manifest_path).resolve(), Path(output).resolve()
    dataset = Dataset(database)
    started = time.perf_counter()
    manifest = load_manifest(dataset, manifest_path)
    if not manifest['cases']:
        raise ValueError('manifest must contain at least one case')
    sidecar = database.with_suffix('.flow.sqlite')
    if not sidecar.is_file() or manifest['binding'].get('prepared_index_sha256') != sha256(sidecar):
        raise ValueError('prepared sidecar hash binding does not match')
    status = dataset.flow_index_status()
    if status['status'] != 'ready' or status['snapshot_id'] != manifest['binding']['snapshot_id']:
        raise ValueError('matching prepared index must already be ready')
    output.mkdir(parents=True, exist_ok=False)
    inputs = output / 'inputs'
    inputs.mkdir()
    shutil.copyfile(manifest_path, inputs / 'manifest.json')
    protected = {str(path): sha256(path) for path in (database, sidecar, manifest_path)}
    package = Path(sys.modules[Dataset.__module__].__file__).resolve().parent
    sources = [Path(__file__).resolve(), *sorted(package.glob('*.py'))]
    source_hashes = {str(path): sha256(path) for path in sources}
    report = {'schema_version': 1, 'status': 'preflight', 'created_at': datetime.now(timezone.utc).isoformat(),
              'regime': manifest['regime'], 'database': str(database), 'binding': manifest['binding'],
              'python': sys.version, 'platform': platform.platform(), 'source_sha256': source_hashes,
              'cold_definition': 'fresh Dataset handle per run, OS filesystem cache not flushed',
              'memory': None, 'memory_scope': 'not sampled to avoid adding observers to the trace window',
              'preflight': {'prepared_index': status, 'cases': [], 'seconds': None}, 'runs': []}

    def save():
        (output / 'receipt.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')

    baselines = {}
    for case in manifest['cases']:
        source = (manifest_path.parent / case['baseline']['path']).resolve()
        protected[str(source)] = case['baseline']['sha256']
        shutil.copyfile(source, inputs / (case['name'] + '-baseline.json'))
        baselines[case['name']] = _read(source)['result']
        try:
            proof = validate_witness(dataset, case)
        except Exception as error:
            report.update(status='failed', error=f"{case['name']}: {type(error).__name__}: {error}")
            save()
            raise
        report['preflight']['cases'].append({'name': case['name'], 'witness': proof})
        save()
        if proof['status'] in ('unknown', 'invalid'):
            report.update(status='failed', error=f"{case['name']}: witness validation {proof['status']}")
            save()
            raise ValueError(f"{case['name']}: witness validation {proof['status']}, see preflight receipt")
    report['preflight']['seconds'] = time.perf_counter() - started
    save()
    if not preflight_only:
        report['status'] = 'running'
        save()
        for case in manifest['cases']:
            for repeat in range(repeats):
                before = time.perf_counter()
                current = Dataset(database)
                open_seconds = time.perf_counter() - before
                if manifest['regime'] == 'wall_time':
                    try:
                        run = run_wall_time(current, case, baselines[case['name']], output,
                                            f"{case['name']}-{repeat + 1:02d}", manifest['checkpoints_seconds'])
                    except Exception as error:
                        report.update(status='failed', error=f"{case['name']}: {type(error).__name__}: {error}")
                        save()
                        raise
                    report['runs'].append({'case': case['name'], 'repeat': repeat + 1,
                        'request': case['request'], 'effective_request': _request(case['request']),
                        'dataset_open_seconds': open_seconds, **run})
                    save()
                    if any(row['envelope']['status'] in ('failed', 'closed') for row in run['checkpoints']):
                        report.update(status='failed', error=f"{case['name']}: search job did not finish or pause normally")
                        save()
                        raise ValueError(report['error'])
                    continue
                before = time.perf_counter()
                try:
                    result = current.trace_processes(**case['request'])
                except Exception as error:
                    report.update(status='failed', error=f"{case['name']}: {type(error).__name__}: {error}")
                    save()
                    raise
                elapsed = time.perf_counter() - before
                raw_path = output / f"{case['name']}-{repeat + 1:02d}-response.json"
                raw_path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
                if result['snapshot_id'] != manifest['binding']['snapshot_id']:
                    raise ValueError('trace returned a different snapshot')
                metrics = evaluate_result(case, result, baselines[case['name']])
                report['runs'].append({'case': case['name'], 'repeat': repeat + 1,
                    'request': case['request'], 'effective_request': _request(case['request']),
                    'dataset_open_seconds': open_seconds, 'trace_seconds': elapsed,
                    'response': raw_path.name, 'response_sha256': sha256(raw_path), 'metrics': metrics})
                save()
    report['protected_sha256_before'] = protected
    report['protected_sha256_after'] = {path: sha256(path) for path in protected}
    report['source_sha256_after'] = {str(path): sha256(path)
        for path in [Path(__file__).resolve(), *sorted(package.glob('*.py'))]}
    report['inputs_unchanged'] = report['protected_sha256_before'] == report['protected_sha256_after']
    report['sources_unchanged'] = source_hashes == report['source_sha256_after']
    report['status'] = 'complete' if report['inputs_unchanged'] and report['sources_unchanged'] else 'failed'
    report['timing_summary'] = []
    for case in manifest['cases']:
        times = [row['trace_seconds'] for row in report['runs'] if row['case'] == case['name'] and 'trace_seconds' in row]
        if times:
            report['timing_summary'].append({'case': case['name'], 'samples': len(times),
                'trace_seconds_min': min(times), 'trace_seconds_median': statistics.median(times),
                'trace_seconds_max': max(times)})
    save()
    if not report['inputs_unchanged'] or not report['sources_unchanged']:
        raise ValueError('benchmark inputs or source changed during invocation, see receipt')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('database', type=Path)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('output', type=Path, help='new directory, existing paths are never overwritten')
    parser.add_argument('--repeats', type=int, default=1)
    parser.add_argument('--preflight-only', action='store_true', help='validate and save native witness evidence without trace calls')
    args = parser.parse_args()
    try:
        report = run_benchmark(args.database, args.manifest, args.output,
                               repeats=args.repeats, preflight_only=args.preflight_only)
    except (ValueError, KeyError, OSError) as error:
        parser.exit(2, f'{error}\n')
    print(json.dumps({'receipt': str(args.output.resolve() / 'receipt.json'),
                      'regime': report['regime'], 'runs': len(report['runs'])}))


if __name__ == '__main__':
    main()
