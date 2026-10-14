"""Bounded-output profiling of one read-only native route query."""

import argparse
import cProfile
import io
import json
import pstats
import time
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path

from gtnh_data import Dataset


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('database', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    dataset = Dataset(args.database)
    queries = defaultdict(lambda: {'calls': 0, 'seconds': 0.0, 'max_seconds': 0.0})
    original = dataset._connect

    class TimedConnection:
        def __init__(self, connection):
            self.connection = connection

        def execute(self, sql, parameters=()):
            before = time.perf_counter()
            cursor = self.connection.execute(sql, parameters)
            elapsed = time.perf_counter() - before
            row = queries[sql]
            row['calls'] += 1
            row['seconds'] += elapsed
            row['max_seconds'] = max(row['max_seconds'], elapsed)
            return cursor

    @contextmanager
    def timed_connection():
        with original() as connection:
            yield TimedConnection(connection)

    dataset._connect = timed_connection
    request = {'start_id': 'r4010', 'target_id': 'r24189', 'max_tier': 1, 'path_selection': 'material'}
    profiler = cProfile.Profile()
    before = time.perf_counter()
    result = profiler.runcall(dataset.trace_processes, **request)
    elapsed = time.perf_counter() - before
    args.output.parent.mkdir(parents=True, exist_ok=True)
    profiler.dump_stats(str(args.output.with_suffix('.pstats')))
    args.output.with_name(args.output.stem + '-result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    stream = io.StringIO()
    pstats.Stats(profiler, stream=stream).sort_stats('cumulative').print_stats(35)
    report = {'request': request, 'snapshot_id': result['snapshot_id'], 'seconds': elapsed,
              'search': result['search'], 'sizes': {key: len(result[key]) for key in ('resources', 'processes', 'edges', 'leaves')},
              'sql': [dict(sql=sql, **row) for sql, row in sorted(queries.items(), key=lambda entry: entry[1]['seconds'], reverse=True)[:12]],
              'profile': stream.getvalue()}
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('snapshot_id', 'seconds', 'sizes', 'sql')}, indent=2), flush=True)
    print(stream.getvalue(), flush=True)


if __name__ == '__main__':
    main()
