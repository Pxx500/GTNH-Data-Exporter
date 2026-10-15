import copy
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from gtnh_data import Dataset, DatasetError, flow_index
from .artifacts import choice, process, resource, slot, snapshot
from .test_flow_index import material


def fixture(root, *, fanout=0):
    rows = [material(id, 'Base') for id in ('start', 'middle', 'feed', 'bait', 'target')]
    rows += [material('short', 'Other'), resource('external'), resource('tool')]
    recipes = [process('short-maker', [slot(choice('start'))], ['short']),
               process('middle-maker', [slot(choice('start'))], ['middle']),
               process('feed-maker', [slot(choice('middle')), slot(choice('external', amount=3)),
                   slot(choice('tool'), role='presence')], ['feed']),
               process('finish', [slot(choice('short'), choice('feed'))], ['target'])]
    if fanout:
        recipes[2]['inputs'][0] = slot(choice('bait'))
        recipes += [process(f'bait-{i:05}', [slot(choice('start'))], ['bait'],
                            conditions={'native_variant': i}) for i in range(fanout)]
    return Dataset.import_snapshot(snapshot(root / 'capture', resources=rows, processes=recipes), root / 'index.sqlite')


def arguments(dataset, canonical, **overrides):
    values = dict(dataset=dataset, canonical=canonical, start_id='start', target_id='target', max_depth=12,
                  max_processes=300, max_paths=1, required=set(), excluded=set(), max_extra_steps=6,
                  tier_filter=dataset._tier_filter(None, None, 'exclude'))
    values.update(overrides)
    return values


def without_time(raw):
    result = copy.deepcopy(raw)
    result[2].pop('distance_seconds', None)
    return result


class SearchContinuationTests(unittest.TestCase):
    def test_pause_resume_keeps_candidates_and_exact_final_domain_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            dataset = fixture(Path(temporary))
            with dataset._connect() as canonical:
                baseline = flow_index.find_paths(**arguments(dataset, canonical))
            fresh = Dataset(dataset.path)
            with fresh._connect() as canonical:
                handle = flow_index.begin_search(**arguments(fresh, canonical))
                try:
                    admitted_before_finish = False
                    previous_work = 0
                    for _ in range(1000):
                        progress = handle.advance(1e-12)
                        raw = handle.snapshot()
                        self.assertEqual(progress['search'], raw[2])
                        self.assertGreaterEqual(raw[2]['expansion_work'], previous_work)
                        previous_work = raw[2]['expansion_work']
                        if raw[1] and progress['status'] == 'paused':
                            admitted_before_finish = True
                        saved = copy.deepcopy(raw)
                        raw[1].clear()
                        raw[2]['expansion_work'] = -1
                        self.assertEqual(handle.snapshot(), saved)
                        if progress['status'] == 'finished':
                            break
                    else:
                        self.fail('finite synthetic search never finished')
                    self.assertTrue(admitted_before_finish)
                    self.assertEqual(without_time(handle.snapshot()), without_time(baseline))
                    self.assertEqual(handle.advance(0.01)['status'], 'finished')
                finally:
                    handle.close()
                self.assertEqual(handle.advance(0.01)['status'], 'closed')
                self.assertEqual(canonical.execute('SELECT 1').fetchone()[0], 1)

    def test_validates_time_and_budget_without_claiming_a_pause_as_a_limit(self):
        with tempfile.TemporaryDirectory() as temporary:
            dataset = fixture(Path(temporary))
            with dataset._connect() as canonical:
                for invalid in (True, 0, 11, 1.5, '2'):
                    with self.subTest(budget=invalid), self.assertRaises(DatasetError):
                        flow_index.begin_search(**arguments(dataset, canonical), budget_multiplier=invalid)
                handle = flow_index.begin_search(**arguments(dataset, canonical))
                try:
                    for invalid in (True, 0, -1, float('inf'), float('nan'), '1'):
                        with self.subTest(seconds=invalid), self.assertRaises(DatasetError):
                            handle.advance(invalid)
                    self.assertEqual(handle.advance(1e-12)['status'], 'paused')
                    self.assertEqual(handle.snapshot()[3], [])
                finally:
                    handle.close()
                handle.close()
                self.assertEqual(handle.advance(0.1)['status'], 'closed')
                with self.assertRaisesRegex(DatasetError, 'closed'):
                    handle.snapshot()

    def test_synchronous_owner_preserves_the_callers_tier_exclusion_counters(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            high = process('high', [slot(choice('start'))], ['target'])
            high.update(family='gregtech:gt.recipe.assembler', eu_per_tick=120)
            high['provenance']['owner'] = 'GTRecipe'
            dataset = Dataset.import_snapshot(snapshot(root / 'capture', resources=[resource('start'), resource('target')],
                processes=[high]), root / 'index.sqlite')
            tier = dataset._tier_filter(None, 1, 'exclude')
            with dataset._connect() as canonical:
                result = flow_index.find_paths(**arguments(dataset, canonical, tier_filter=tier))
            self.assertEqual(result[1], [])
            self.assertEqual(tier['excluded_out_of_range'], 1)

    def test_hard_process_cap_stays_terminal_and_larger_budget_is_cumulative(self):
        with tempfile.TemporaryDirectory() as temporary:
            dataset = fixture(Path(temporary), fanout=10001)
            results = []
            for multiplier in (1, 2):
                fresh = Dataset(dataset.path)
                with fresh._connect() as canonical:
                    handle = flow_index.begin_search(**arguments(fresh, canonical), budget_multiplier=multiplier)
                    try:
                        for _ in range(1000):
                            progress = handle.advance(0.01)
                            if progress['status'] == 'finished':
                                break
                        else:
                            self.fail('finite capped search never finished')
                        results.append(handle.snapshot())
                        finished = handle.snapshot()
                        self.assertEqual(handle.advance(0.01)['status'], 'finished')
                        self.assertEqual(handle.snapshot(), finished)
                    finally:
                        handle.close()
            small, large = results
            self.assertIn('search_process_limit', small[3])
            self.assertNotIn('search_process_limit', large[3])
            self.assertEqual(small[2]['examined_processes'], 10000)
            self.assertGreater(large[2]['examined_processes'], small[2]['examined_processes'])
            self.assertGreaterEqual(large[2]['expansion_work'], small[2]['expansion_work'])
            for key in ('limit', 'state_limit', 'work_limit'):
                self.assertEqual(large[2][key], small[2][key] * 2)
            self.assertLessEqual(len(large[1]), 1)

    def test_close_and_error_release_prepared_connections_without_closing_canonical(self):
        for corrupt in (False, True):
            with self.subTest(corrupt=corrupt), tempfile.TemporaryDirectory() as temporary:
                dataset = fixture(Path(temporary))
                if corrupt:
                    with closing(sqlite3.connect(flow_index.index_path(dataset))) as connection, connection:
                        connection.execute('DROP TABLE input_requirements')
                opened = []
                native_connect = sqlite3.connect

                def connect(*args, **kwargs):
                    connection = native_connect(*args, **kwargs)
                    opened.append(connection)
                    return connection

                with dataset._connect() as canonical, patch.object(flow_index.sqlite3, 'connect', side_effect=connect):
                    handle = flow_index.begin_search(**arguments(dataset, canonical))
                    if corrupt:
                        with self.assertRaises(sqlite3.Error):
                            handle.advance(1)
                    else:
                        for _ in range(100):
                            if handle.advance(1e-12)['phase'] == 'reference':
                                break
                        else:
                            self.fail('search never opened its concrete frontier')
                        live = 0
                        for connection in opened:
                            try:
                                connection.execute('SELECT 1')
                                live += 1
                            except sqlite3.ProgrammingError:
                                pass
                        self.assertEqual(live, 1)
                    handle.close()
                    handle.close()
                    self.assertTrue(opened)
                    for connection in opened:
                        with self.assertRaises(sqlite3.ProgrammingError):
                            connection.execute('SELECT 1')
                    self.assertEqual(canonical.execute('SELECT 1').fetchone()[0], 1)
