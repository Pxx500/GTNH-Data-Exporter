"""Repeatable read-only route benchmark against an explicitly selected database."""

import argparse
import json
import time
import ctypes
import os
from pathlib import Path

from gtnh_data import Dataset


CASES = [('casing', 'r5090', 'r37874'), ('hull', 'r5090', 'r37926'),
         ('double_plate', 'r4010', 'r24189'), ('volcanus', 'r5090', 'r41034')]


def memory():
    if os.name != 'nt':
        return None
    class Counters(ctypes.Structure):
        _fields_ = [('cb', ctypes.c_ulong), ('PageFaultCount', ctypes.c_ulong)] + [
            (name, ctypes.c_size_t) for name in ('PeakWorkingSetSize', 'WorkingSetSize', 'QuotaPeakPagedPoolUsage',
                'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage', 'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage')]
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    ctypes.windll.kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    ctypes.windll.psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
    if not ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise OSError('GetProcessMemoryInfo failed')
    return {'working_set_bytes': counters.WorkingSetSize, 'peak_working_set_bytes': counters.PeakWorkingSetSize}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('database', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--selection', default='diverse')
    parser.add_argument('--case', choices=[case[0] for case in CASES])
    parser.add_argument('--tiers', nargs='+', choices=['LV', 'MV', 'none'], default=['LV', 'MV', 'none'])
    args = parser.parse_args()
    report = {'database': str(args.database.resolve()), 'selection': args.selection,
              'cold_definition': 'fresh Dataset handle, OS filesystem cache not flushed', 'cases': []}
    for name, start, target in CASES:
        if args.case and args.case != name:
            continue
        for tier_name in args.tiers:
            tier = None if tier_name == 'none' else tier_name
            before_open = time.perf_counter()
            dataset = Dataset(args.database)
            open_seconds = time.perf_counter() - before_open
            for run in ('cold', 'warm'):
                before = time.perf_counter()
                result = dataset.trace_processes(start_id=start, target_id=target, max_tier={'LV': 1, 'MV': 2}.get(tier),
                                                 path_selection=args.selection)
                elapsed = time.perf_counter() - before
                labels = {row['id']: row['display_name'] for row in result['resources']}
                row = {'case': name, 'run': run, 'tier': tier, 'seconds': elapsed,
                       'dataset_open_seconds': open_seconds, 'process_memory': memory(),
                       'snapshot_id': result['snapshot_id'], 'search': result['search'],
                       'limit_reasons': result['limit_reasons'], 'branch_coverage': result['branch_coverage'],
                       'paths': [dict(path, labels=[labels[id] for id in path['resource_ids']]) for path in result['paths']],
                       'steel_included': any('Steel' in labels[id] for path in result['paths'] for id in path['resource_ids']),
                       'leaves': result['leaves'], 'path_details': result.get('path_details')}
                report['cases'].append(row)
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
                print(json.dumps({key: row[key] for key in ('case', 'run', 'tier', 'seconds', 'steel_included', 'limit_reasons')}), flush=True)


if __name__ == '__main__':
    main()
