import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from fastapi.testclient import TestClient
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from gtnh_data import Dataset, DatasetError
from gtnh_data.http import create_app
from gtnh_data.cli import main
from .artifacts import choice, process, resource, slot, snapshot

def network_semantics(result):
    copied = json.loads(json.dumps(result))
    for field in ('elapsed_seconds', 'distance_work', 'distance_seconds', 'distance_cache_hit'):
        copied.get('search', {}).pop(field, None)
    return copied


class TransportTests(unittest.TestCase):
    def test_cli_json_preserves_unicode_on_cp1250_stdout_and_stderr(self):
        display_name = '\ue00e GT Iron Dust'
        recipe = process('make', [slot(choice('start'))], ['target'], family='gregtech:assembler')
        recipe['provenance']['owner'] = 'GTRecipe'
        database = self.root / 'unicode.sqlite'
        dataset = Dataset.import_snapshot(snapshot(self.root / 'unicode-capture',
            resources=[dict(resource('start'), display_name=display_name), resource('target')], processes=[recipe]), database)
        environment = dict(os.environ, PYTHONIOENCODING='cp1250',
                           PYTHONPATH=str(Path(__file__).resolve().parents[1] / 'src'))

        def run(*arguments):
            return subprocess.run([sys.executable, '-m', 'gtnh_data', *arguments, '--database', str(database)],
                                  env=environment, capture_output=True, timeout=15)

        traced = run('trace', '--start-id', 'start', '--target-id', 'target', '--max-tier', '1',
                     '--path-selection', 'material', '--view', 'compact')
        self.assertEqual(traced.returncode, 0, traced.stderr.decode('cp1250', errors='replace'))
        self.assertTrue(traced.stdout.isascii())
        answer = json.loads(traced.stdout)
        self.assertEqual(next(row for row in answer['resources'] if row['id'] == 'start')['display_name'], display_name)
        self.assertEqual(answer['paths'][0]['resource_ids'], ['start', 'target'])
        request = self.root / 'unicode-request.json'
        request.write_text(json.dumps({'name': display_name, 'base_resource_ids': ['start']}, ensure_ascii=False), encoding='utf-8')
        saved = run('save-boundary-profile', 'unicode', '--request-file', str(request))
        self.assertEqual(saved.returncode, 0, saved.stderr.decode('cp1250', errors='replace'))
        self.assertTrue(saved.stdout.isascii())
        self.assertEqual(json.loads(saved.stdout), dataset.get_boundary_profile('unicode'))
        listed = run('boundary-profiles', 'unicode')
        self.assertEqual(listed.returncode, 0, listed.stderr.decode('cp1250', errors='replace'))
        self.assertTrue(listed.stdout.isascii())
        self.assertEqual(json.loads(listed.stdout), dataset.get_boundary_profile('unicode'))
        missing = run('resources', 'missing\ue00e')
        self.assertEqual(missing.returncode, 2)
        self.assertEqual(missing.stdout, b'')
        self.assertTrue(missing.stderr.isascii())
        self.assertEqual(json.loads(missing.stderr), {'error': 'Unknown resources ID: missing\ue00e'})

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.database = self.root / "dataset.sqlite"
        self.generation_source = {"id": "generation:iron", "kind": "ore_generation", "display_name": "Iron vein",
                                  "outputs": [{"resource_id": "a", "amount": 1, "resource_semantics": "generated_ore_block_not_mining_drop"}],
                                  "environment_ids": [], "status": "conditional", "conditions": {"dimension": 0},
                                  "parameters": {"weight": 10}, "provenance": {"owner": "fixture"}}
        self.mining_source = {"id": "mining:iron/fortune0", "kind": "ore_mining", "display_name": "Iron mining drop",
                              "outputs": [{"resource_id": "b", "amount": 1, "resource_semantics": "mined_item_baseline"}],
                              "environment_ids": [], "status": "conditional", "conditions": {"fortune": 0, "silk_touch": False},
                              "parameters": {"generated_source_id": self.generation_source["id"], "generated_resource_id": "a"},
                              "provenance": {"owner": "fixture"}}
        self.dataset = Dataset.import_snapshot(snapshot(self.root / "capture", resources=[dict(resource("a"), display_name="Iron Plate"), resource("b"), resource('middle'), resource('excluded')],
                                                       processes=[process("convert", [slot(choice("a"))], ["b"]),
                                                                  process('detour-first', [slot(choice('a'))], ['middle']),
                                                                  process('detour-finish', [slot(choice('middle'))], ['b'])],
                                                       sources=[self.generation_source, self.mining_source]), self.database)

    def test_http_trace_jobs_share_trace_body_validation_and_revision_polling(self):
        args = dict(start_id='a', target_id='b', path_selection='material', view='concise',
                    required_resource_ids=['a'], excluded_resource_ids=['excluded'], excluded_group_ids=[])
        expected = self.dataset.trace_processes(**args)
        with TestClient(create_app(self.dataset)) as client:
            response = client.post('/api/trace-jobs', json=args)
            self.assertEqual(response.status_code, 200, response.text)
            job = response.json()
            deadline = time.monotonic() + 5
            while job['status'] == 'running' and time.monotonic() < deadline:
                time.sleep(.01)
                job = client.get('/api/trace-jobs/' + job['job_id']).json()
            self.assertEqual(job['status'], 'finished', job)
            for field in ('paths', 'resources', 'processes', 'edges', 'leaves', 'path_details', 'presentation'):
                self.assertEqual(job['result'][field], expected[field], field)
            route = '/api/trace-jobs/' + job['job_id']
            self.assertNotIn('result', client.get(route, params={'after_revision': job['revision']}).json())
            self.assertEqual(client.post(route + '/continue', json={}).status_code, 400)
            self.assertEqual(client.post(route + '/pause').json()['status'], 'finished')
            self.assertEqual(client.delete(route).json()['status'], 'closed')
            self.assertEqual(client.delete(route).json()['status'], 'closed')
            for change in ({'max_depth': 0}, {'required_resource_ids': 'a'}, {'view': 'bad'},
                           {'budget_multiplier': 11}, {'time_budget_seconds': 0}, {'path_selection': 'shortest'}):
                self.assertEqual(client.post('/api/trace-jobs', json=dict(args, **change)).status_code, 400)
            self.assertEqual(client.get('/api/trace-jobs/missing').status_code, 404)

    def test_official_mcp_trace_jobs_share_domain_results_and_process_local_handles(self):
        async def exercise():
            parameters = StdioServerParameters(command=sys.executable,
                args=['-m', 'gtnh_data', 'mcp', '--database', str(self.database)])
            async with stdio_client(parameters) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream, read_timeout_seconds=15) as session:
                    await session.initialize()
                    tools = {tool.name: tool for tool in (await session.list_tools()).tools}
                    self.assertEqual(tools['start_trace_search'].input_schema['properties']['path_selection']['enum'], ['material'])
                    started = await session.call_tool('start_trace_search', {'start_id': 'a', 'target_id': 'b'})
                    self.assertFalse(started.is_error, started.content)
                    job = started.structured_content
                    deadline = time.monotonic() + 5
                    while job['status'] == 'running' and time.monotonic() < deadline:
                        await asyncio.sleep(.01)
                        polled = await session.call_tool('get_trace_search', {'job_id': job['job_id']})
                        self.assertFalse(polled.is_error, polled.content)
                        job = polled.structured_content
                    self.assertEqual(job['status'], 'finished', job)
                    expected = self.dataset.trace_processes(start_id='a', target_id='b', path_selection='material', view='compact')
                    for field in ('paths', 'resources', 'processes', 'edges', 'leaves', 'path_details', 'presentation'):
                        self.assertEqual(job['result'][field], expected[field], field)
                    unchanged = await session.call_tool('get_trace_search', {'job_id': job['job_id'], 'after_revision': job['revision']})
                    self.assertNotIn('result', unchanged.structured_content)
                    invalid = await session.call_tool('start_trace_search', {'start_id': 'a', 'target_id': 'b', 'path_selection': 'shortest'})
                    self.assertTrue(invalid.is_error)
                    closed = await session.call_tool('close_trace_search', {'job_id': job['job_id']})
                    self.assertEqual(closed.structured_content['status'], 'closed')
                    invalid = await session.call_tool('continue_trace_search', {'job_id': job['job_id']})
                    self.assertTrue(invalid.is_error)
        asyncio.run(exercise())

    def test_prepared_flow_index_is_inspectable_and_rebuildable_without_changing_capture(self):
        captured_before = self.database.read_bytes()
        with TestClient(create_app(self.dataset)) as client:
            answer = client.get('/api/flow-index')
            self.assertEqual(answer.status_code, 200)
            self.assertEqual(answer.json(), self.dataset.flow_index_status())
            rebuilt = client.post('/api/flow-index/rebuild')
            self.assertEqual(rebuilt.status_code, 200)
            self.assertEqual(rebuilt.json()['snapshot_id'], self.dataset.snapshot_id)
            self.assertEqual(client.get('/api/flow-index').json()['status'], 'ready')
        output = StringIO()
        with redirect_stdout(output):
            code = main(['flow-index', '--database', str(self.database)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue()), self.dataset.flow_index_status())
        output = StringIO()
        with redirect_stdout(output):
            code = main(['rebuild-flow-index', '--database', str(self.database)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())['snapshot_id'], self.dataset.snapshot_id)
        self.assertEqual(self.database.read_bytes(), captured_before)

    def test_source_parent_links_are_followable_with_exact_records_and_errors(self):
        expected = {"snapshot_id": self.dataset.snapshot_id, "item": self.mining_source}
        with TestClient(create_app(self.dataset)) as client:
            response = client.get("/api/sources/" + self.mining_source["id"])
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), expected)
            parent_id = response.json()["item"]["parameters"]["generated_source_id"]
            self.assertEqual(client.get("/api/sources/" + parent_id).json()["item"], self.generation_source)
            error = client.get("/api/sources/missing")
            self.assertEqual(error.status_code, 404)
            self.assertEqual(error.json(), {"error": "Unknown sources ID: missing"})
            self.assertEqual(client.get("/api/sources", params={"resource_id": "b"}).json(), self.dataset.find_sources(resource_id="b"))
        self.assertEqual(self.dataset.get_source(self.mining_source["id"]), expected)
        with self.assertRaisesRegex(DatasetError, "Unknown sources ID: missing"):
            self.dataset.get_source("missing")
        output = StringIO()
        with redirect_stdout(output):
            result = main(["sources", self.mining_source["id"], "--database", str(self.database)])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output.getvalue()), expected)
        output = StringIO()
        with redirect_stdout(output):
            result = main(["sources", "--resource-id", "b", "--database", str(self.database)])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output.getvalue()), self.dataset.find_sources(resource_id="b"))
        error_output = StringIO()
        with redirect_stderr(error_output):
            result = main(["sources", "missing", "--database", str(self.database)])
        self.assertEqual(result, 2)
        self.assertEqual(json.loads(error_output.getvalue()), {"error": "Unknown sources ID: missing"})

    def test_resource_acquisition_results_are_independent_across_repeated_searches(self):
        first = self.dataset.find_resources(q='Iron', limit=8)
        expected = json.loads(json.dumps(first))
        first['items'][0]['acquisition_analysis']['acquisition']['status'] = 'caller_edit'
        first['items'][0]['acquisition_analysis']['provenance']['world_source']['evidence'].clear()
        self.assertEqual(self.dataset.find_resources(q='Iron', limit=8), expected)

    def test_boundary_profiles_http_and_cli_share_snapshot_bound_owner(self):
        with TestClient(create_app(self.dataset)) as client:
            listed = client.get('/api/boundary-profiles')
            self.assertEqual(listed.status_code, 200)
            self.assertEqual(listed.json(), self.dataset.list_boundary_profiles())
            saved = client.post('/api/boundary-profiles/developer', json={'name': 'Developer basics', 'base_resource_ids': ['a'], 'scope': {'excluded_resource_ids': ['excluded']}})
            self.assertEqual(saved.status_code, 200)
            expected = self.dataset.get_boundary_profile('developer')
            self.assertEqual(saved.json(), expected)
            self.assertEqual(client.get('/api/boundary-profiles/developer').json(), expected)
        output = StringIO()
        with redirect_stdout(output):
            result = main(['boundary-profiles', 'developer', '--database', str(self.database)])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output.getvalue()), expected)

    def test_network_http_and_cli_forward_profiles_benchmark_feeds_and_exact_accounting(self):
        self.dataset.save_boundary_profile('basics', name='Basics', base_resource_ids=['a'])
        common = dict(target_id='b', target_amount=2, max_depth=3, max_processes=20, max_variants=20, max_resources=32,
                      max_solutions=1, max_solves=2, timeout_seconds=5)
        operations = [('plan-to-bases', 'plan_to_bases', dict(common, profile_id='basics')),
                      ('audit-energy', 'audit_energy', dict(common, primary_feed_id='a', benchmark_process_id='convert', profile_id='basics', allowed_feed_ids=['a']))]
        for command, operation, arguments in operations:
            expected = getattr(self.dataset, operation)(**arguments)
            self.assertEqual(expected['status'], 'complete')
            self.assertTrue(expected['solutions'][0]['witness_verified'])
            with TestClient(create_app(self.dataset)) as client:
                answer = client.post('/api/' + ('energy-audit' if command == 'audit-energy' else command), json=arguments)
                self.assertEqual(answer.status_code, 200)
                self.assertEqual(network_semantics(answer.json()), network_semantics(expected))
            request = self.root / (command + '.json')
            request.write_text(json.dumps(arguments), encoding='utf-8')
            output = StringIO()
            with redirect_stdout(output):
                code = main([command, '--database', str(self.database), '--request-file', str(request)])
            self.assertEqual(code, 0)
            self.assertEqual(network_semantics(json.loads(output.getvalue())), network_semantics(expected))

    def test_official_mcp_networks_and_profile_mutations_keep_typed_results_and_honest_annotations(self):
        self.dataset.save_boundary_profile('basics', name='Basics', base_resource_ids=['a'])
        common = dict(target_id='b', max_depth=3, max_processes=20, max_variants=20, max_resources=32,
                      max_solutions=1, max_solves=2, timeout_seconds=5)
        operations = [('plan_to_bases', dict(common, profile_id='basics')),
                      ('audit_energy', dict(common, primary_feed_id='a', benchmark_process_id='convert', allowed_feed_ids=['a']))]
        expected = {operation: getattr(self.dataset, operation)(**arguments) for operation, arguments in operations}
        async def exercise():
            parameters = StdioServerParameters(command=sys.executable, args=['-m', 'gtnh_data', 'mcp', '--database', str(self.database)], env=dict(os.environ))
            async with stdio_client(parameters) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream, read_timeout_seconds=15) as session:
                    await session.initialize()
                    tools = {tool.name: tool for tool in (await session.list_tools()).tools}
                    self.assertFalse(tools['save_boundary_profile'].annotations.read_only_hint)
                    self.assertTrue(tools['delete_boundary_profile'].annotations.destructive_hint)
                    for name, maximum in [('max_depth',20), ('max_processes',1000), ('max_variants',512), ('max_resources',2000), ('timeout_seconds',30)]:
                        self.assertEqual(tools['audit_energy'].input_schema['properties'][name]['maximum'], maximum)
                    for operation, arguments in operations:
                        answer = await session.call_tool(operation, arguments)
                        self.assertFalse(answer.is_error, answer.content)
                        self.assertEqual(network_semantics(answer.structured_content), network_semantics(expected[operation]))
                        self.assertEqual(len(answer.content), 1)
                        self.assertLess(len(answer.content[0].text), 256)
                        self.assertNotIn('executions', answer.content[0].text)
                    statistics_arguments = dict(max_records=30, max_findings=5, max_signature_buckets=20, timeout_seconds=5)
                    statistics = await session.call_tool('analyze_statistics', statistics_arguments)
                    self.assertFalse(statistics.is_error, statistics.content)
                    self.assertEqual(network_semantics(statistics.structured_content), network_semantics(self.dataset.analyze_statistics(**statistics_arguments)))
                    acquisition = await session.call_tool('inspect_acquisition', {'resource_id':'a', 'max_depth':2, 'max_processes':10, 'max_variants':10, 'max_resources':20})
                    self.assertFalse(acquisition.is_error, acquisition.content)
                    self.assertEqual(acquisition.structured_content, self.dataset.inspect_acquisition('a', max_depth=2, max_processes=10, max_variants=10, max_resources=20))
                    for name, maximum in [('max_records',2000000), ('max_findings',500), ('max_signature_buckets',200000), ('timeout_seconds',60)]:
                        self.assertEqual(tools['analyze_statistics'].input_schema['properties'][name]['maximum'], maximum)
                    answer = await session.call_tool('save_boundary_profile', {'profile_id':'mcp-profile', 'name':'Explicit user basics', 'base_resource_ids':['a'], 'expected_revision':0})
                    self.assertFalse(answer.is_error)
                    self.assertEqual(answer.structured_content, self.dataset.get_boundary_profile('mcp-profile'))
                    revision = answer.structured_content['item']['revision']
                    deleted = await session.call_tool('delete_boundary_profile', {'profile_id':'mcp-profile', 'expected_revision':revision})
                    self.assertFalse(deleted.is_error)
                    self.assertEqual(deleted.structured_content, {'snapshot_id':self.dataset.snapshot_id, 'item':None})
        asyncio.run(exercise())

    def test_statistics_preserves_rational_distributions_through_http_and_cli(self):
        arguments = dict(max_records=30, max_findings=5, max_signature_buckets=20, timeout_seconds=5)
        expected = self.dataset.analyze_statistics(**arguments)
        with TestClient(create_app(self.dataset)) as client:
            answer = client.post('/api/statistics', json=arguments)
            self.assertEqual(answer.status_code, 200)
            self.assertEqual(network_semantics(answer.json()), network_semantics(expected))
        request = self.root / 'statistics.json'
        request.write_text(json.dumps(arguments), encoding='utf-8')
        output = StringIO()
        with redirect_stdout(output):
            code = main(['statistics', '--database', str(self.database), '--request-file', str(request)])
        self.assertEqual(code, 0)
        self.assertEqual(network_semantics(json.loads(output.getvalue())), network_semantics(expected))

    def test_http_is_same_owner_with_pagination_spa_and_errors(self):
        ui = self.root / "ui"
        ui.mkdir()
        (ui / "index.html").write_text("<!doctype html><title>fixture SPA</title>")
        with TestClient(create_app(self.dataset, ui)) as client:
            response = client.get("/api/processes", params={"input_id": "a"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), self.dataset.find_processes(input_id="a"))
            self.assertEqual(client.get("/api/resources?limit=1&offset=1").json(), self.dataset.find_resources(limit=1, offset=1))
            search = client.get("/api/resources", params={"q": "iron pltae", "limit": 8}).json()
            self.assertEqual(search, self.dataset.find_resources(q="iron pltae", limit=8))
            self.assertEqual([item["id"] for item in search["items"]], ["a"])
            self.assertEqual(client.get("/api/resources/a").json(), self.dataset.get_resource("a"))
            self.assertEqual(client.get("/api/trace?start_id=a&target_id=b").json(), self.dataset.trace_processes(start_id="a", target_id="b"))
            parameters = [('start_id', 'a'), ('target_id', 'b'), ('required_resource_id', 'a'), ('required_resource_id', 'middle'),
                          ('excluded_resource_id', 'excluded'), ('max_paths', '2'), ('max_extra_steps', '0')]
            filtered = client.get('/api/trace', params=parameters)
            self.assertEqual(filtered.status_code, 200)
            self.assertEqual(filtered.json(), self.dataset.trace_processes(start_id='a', target_id='b', required_resource_ids=['a', 'middle'],
                                                                           excluded_resource_ids=['excluded'], max_paths=2, max_extra_steps=0))
            self.assertEqual(filtered.json()['paths'][0]['resource_ids'], ['a', 'middle', 'b'])
            self.assertEqual(client.get('/api/trace?start_id=a&target_id=b&max_paths=0').status_code, 400)
            self.assertEqual(client.get("/api/resources?limit=501").status_code, 400)
            self.assertEqual(client.get("/api/resources/missing").status_code, 404)
            self.assertEqual(client.get("/api/unknown").status_code, 404)
            self.assertIn("fixture SPA", client.get("/deep/link").text)

    def declared_lookup_fixture(self):
        recipe = process('informational', [], ['product'], executable=None,
            conditions={'native_inputs': [slot(choice('feed', 'native_unknown'))],
                        'dynamic_inputs': 'uninterpreted_native_subclass'})
        database = self.root / 'declared.sqlite'
        return Dataset.import_snapshot(snapshot(self.root / 'declared-capture',
            resources=[resource('feed'), resource('product')], processes=[recipe]), database), database

    def test_http_and_cli_expose_declared_input_references_without_changing_matched_default(self):
        dataset, database = self.declared_lookup_fixture()
        arguments = dict(input_id='feed', output_id='product', family='assembler', input_mode='declared', limit=1)
        expected = dataset.find_processes(**arguments)
        with TestClient(create_app(dataset)) as client:
            response = client.get('/api/processes', params=arguments)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), expected)
            self.assertEqual(client.get('/api/processes', params={'input_id': 'feed'}).json(),
                             dataset.find_processes(input_id='feed'))
            for params in ({'input_mode': 'declared'}, {'input_id': 'feed', 'input_mode': 'unknown'}):
                self.assertEqual(client.get('/api/processes', params=params).status_code, 400)
        output = StringIO()
        with redirect_stdout(output):
            code = main(['processes', '--database', str(database), '--input-id', 'feed', '--output-id', 'product',
                         '--family', 'assembler', '--input-mode', 'declared', '--limit', '1'])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue()), expected)
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(['processes', '--database', str(database), '--input-id', 'feed']), 0)
        self.assertEqual(json.loads(output.getvalue()), dataset.find_processes(input_id='feed'))
        errors = StringIO()
        with redirect_stderr(errors):
            self.assertEqual(main(['processes', '--database', str(database), '--input-mode', 'declared']), 2)
        self.assertIn('requires input_id', errors.getvalue())
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as invalid:
            main(['processes', '--database', str(database), '--input-mode', 'unknown'])
        self.assertEqual(invalid.exception.code, 2)

    def test_official_mcp_declared_input_lookup_keeps_explicit_evidence_and_validation(self):
        dataset, database = self.declared_lookup_fixture()
        async def exercise():
            parameters = StdioServerParameters(command=sys.executable,
                args=['-m', 'gtnh_data', 'mcp', '--database', str(database)], env=dict(os.environ))
            async with stdio_client(parameters) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream, read_timeout_seconds=15) as session:
                    await session.initialize()
                    tools = {tool.name: tool for tool in (await session.list_tools()).tools}
                    option = tools['find_processes'].input_schema['properties']['input_mode']
                    self.assertEqual(option['enum'], ['matched', 'declared'])
                    self.assertEqual(option['default'], 'matched')
                    for arguments in ({'input_id': 'feed'},
                                      {'input_id': 'feed', 'input_mode': 'declared', 'output_id': 'product', 'limit': 1}):
                        result = await session.call_tool('find_processes', arguments)
                        self.assertFalse(result.is_error, result.content)
                        self.assertEqual(result.structured_content, dataset.find_processes(**arguments))
                    for arguments in ({'input_mode': 'declared'}, {'input_id': 'feed', 'input_mode': 'unknown'}):
                        result = await session.call_tool('find_processes', arguments)
                        self.assertTrue(result.is_error, result.content)
        asyncio.run(exercise())

    def test_http_rejects_unknown_path_selection_instead_of_ignoring_it(self):
        with TestClient(create_app(self.dataset)) as client:
            response = client.get('/api/trace', params={'start_id': 'a', 'target_id': 'b', 'path_selection': 'unknown'})
            self.assertEqual(response.status_code, 400)

    def test_http_and_cli_forward_terminal_artifact_policy_and_reject_invalid_options(self):
        for policy in ('allow', 'direct_targets_only'):
            with self.subTest(policy=policy):
                arguments = dict(start_id='a', target_id='b', terminal_artifact_policy=policy, view='compact')
                with TestClient(create_app(self.dataset)) as client:
                    answer = client.get('/api/trace', params=arguments)
                    self.assertEqual(answer.status_code, 200)
                    self.assertEqual(answer.json()['search']['terminal_artifacts']['policy'], policy)
                    self.assertEqual(network_semantics(answer.json()), network_semantics(self.dataset.trace_processes(**arguments)))
                output = StringIO()
                with redirect_stdout(output):
                    code = main(['trace', '--database', str(self.database), '--start-id', 'a', '--target-id', 'b',
                                 '--terminal-artifact-policy', policy, '--view', 'compact'])
                self.assertEqual(code, 0)
                self.assertEqual(network_semantics(json.loads(output.getvalue())), network_semantics(self.dataset.trace_processes(**arguments)))
        with TestClient(create_app(self.dataset)) as client:
            self.assertEqual(client.get('/api/trace', params={'start_id': 'a', 'target_id': 'b'}).json()['search']['terminal_artifacts']['policy'], 'allow')
            invalid = client.get('/api/trace', params={'start_id': 'a', 'target_id': 'b', 'terminal_artifact_policy': 'unknown'})
            self.assertEqual(invalid.status_code, 400)
        errors = StringIO()
        with redirect_stderr(errors), self.assertRaises(SystemExit) as invalid:
            main(['trace', '--database', str(self.database), '--start-id', 'a', '--target-id', 'b', '--terminal-artifact-policy', 'unknown'])
        self.assertEqual(invalid.exception.code, 2)
        self.assertIn('invalid choice', errors.getvalue())

    def test_official_mcp_trace_terminal_artifact_policy_validation_and_forwarding(self):
        async def exercise():
            parameters = StdioServerParameters(command=sys.executable,
                args=['-m', 'gtnh_data', 'mcp', '--database', str(self.database)], env=dict(os.environ))
            async with stdio_client(parameters) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream, read_timeout_seconds=15) as session:
                    await session.initialize()
                    tools = {tool.name: tool for tool in (await session.list_tools()).tools}
                    self.assertIn('terminal_artifact_policy', tools['trace_processes'].input_schema['properties'])
                    option = tools['trace_processes'].input_schema['properties']['terminal_artifact_policy']
                    self.assertEqual(option['enum'], ['allow', 'direct_targets_only'])
                    self.assertEqual(option['default'], 'allow')
                    for policy in ('allow', 'direct_targets_only'):
                        arguments = {'start_id': 'a', 'target_id': 'b', 'terminal_artifact_policy': policy}
                        answer = await session.call_tool('trace_processes', arguments)
                        self.assertFalse(answer.is_error, answer.content)
                        self.assertEqual(answer.structured_content['search']['terminal_artifacts']['policy'], policy)
                        self.assertEqual(network_semantics(answer.structured_content), network_semantics(self.dataset.trace_processes(**arguments, view='compact')))
                    invalid = await session.call_tool('trace_processes', {'start_id': 'a', 'target_id': 'b', 'terminal_artifact_policy': 'unknown'})
                    self.assertTrue(invalid.is_error, invalid.content)
        asyncio.run(exercise())

    def test_http_and_cli_forward_repeated_trace_group_exclusions(self):
        groups = [{'id': 'ore:starts', 'kind': 'ore_dict', 'name': 'starts', 'members': ['a'], 'provenance': {}},
                  {'id': 'unified:middle', 'kind': 'unified', 'name': 'middle', 'members': ['middle'], 'provenance': {}}]
        dataset = Dataset.import_snapshot(snapshot(self.root / 'group-transport',
            resources=[resource(id) for id in ('a', 'b', 'middle', 'excluded')], groups=groups,
            processes=[process('make', [slot(choice('a'))], ['b'])]), self.root / 'groups.sqlite')
        expected_summaries = [{'group_id': 'ore:starts', 'name': 'starts', 'kind': 'ore_dict', 'member_count': 1},
                              {'group_id': 'unified:middle', 'name': 'middle', 'kind': 'unified', 'member_count': 1}]
        with TestClient(create_app(dataset)) as client:
            response = client.get('/api/trace', params=[('start_id', 'a'), ('target_id', 'b'),
                ('excluded_group_id', 'unified:middle'), ('excluded_group_id', 'ore:starts'), ('excluded_resource_id', 'excluded')])
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['paths'], [])
            self.assertEqual(response.json()['group_exclusions'], expected_summaries)
            self.assertEqual(client.get('/api/trace', params={'start_id': 'a', 'target_id': 'b',
                'excluded_group_id': 'missing'}).status_code, 404)
            self.assertEqual(client.get('/api/trace', params={'start_id': 'a', 'target_id': 'b',
                'excluded_group_id': ''}).status_code, 400)
        output = StringIO()
        with redirect_stdout(output):
            result = main(['trace', '--database', str(self.root / 'groups.sqlite'), '--start-id', 'a', '--target-id', 'b',
                           '--exclude-group', 'unified:middle', '--exclude-group', 'ore:starts', '--excluded-resource-id', 'excluded'])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output.getvalue())['paths'], [])
        self.assertEqual(json.loads(output.getvalue())['group_exclusions'], expected_summaries)

    def test_official_mcp_trace_accepts_literal_groups_and_reports_unknown_ids(self):
        groups = [{'id': 'ore:middle', 'kind': 'ore_dict', 'name': 'middle', 'members': ['middle'], 'provenance': {}}]
        database = self.root / 'mcp-groups.sqlite'
        dataset = Dataset.import_snapshot(snapshot(self.root / 'mcp-groups', resources=[resource(id) for id in ('a', 'b', 'middle')],
            groups=groups, processes=[process('first', [slot(choice('a'))], ['middle']),
                                     process('last', [slot(choice('middle'))], ['b'])]), database)
        async def exercise():
            parameters = StdioServerParameters(command=sys.executable,
                args=['-m', 'gtnh_data', 'mcp', '--database', str(database)], env=dict(os.environ))
            async with stdio_client(parameters) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream, read_timeout_seconds=15) as session:
                    await session.initialize()
                    tools = {tool.name: tool for tool in (await session.list_tools()).tools}
                    self.assertIn('excluded_group_ids', tools['trace_processes'].input_schema['properties'])
                    arguments = {'start_id': 'a', 'target_id': 'b', 'excluded_group_ids': ['ore:middle']}
                    answer = await session.call_tool('trace_processes', arguments)
                    self.assertFalse(answer.is_error, answer.content)
                    self.assertEqual(network_semantics(answer.structured_content),
                                     network_semantics(dataset.trace_processes(**arguments, view='compact')))
                    for groups in (['missing'], [''], 'ore:middle'):
                        invalid = await session.call_tool('trace_processes', dict(arguments, excluded_group_ids=groups))
                        self.assertTrue(invalid.is_error, invalid.content)
        asyncio.run(exercise())

    def test_http_and_cli_share_explicit_path_selection_and_defaults(self):
        for selection in ('diverse', 'shortest', 'material'):
            with self.subTest(selection=selection):
                arguments = dict(start_id='a', target_id='b', path_selection=selection)
                expected = self.dataset.trace_processes(**arguments)
                with TestClient(create_app(self.dataset)) as client:
                    self.assertEqual(network_semantics(client.get('/api/trace', params=arguments).json()), network_semantics(expected))
                output = StringIO()
                with redirect_stdout(output):
                    result = main(['trace', '--database', str(self.database), '--start-id', 'a', '--target-id', 'b',
                                   '--path-selection', selection])
                self.assertEqual(result, 0)
                self.assertEqual(network_semantics(json.loads(output.getvalue())), network_semantics(expected))

    def test_official_mcp_material_trace_and_preparation_share_owner_and_annotations(self):
        async def exercise():
            parameters = StdioServerParameters(command=sys.executable,
                args=['-m', 'gtnh_data', 'mcp', '--database', str(self.database)], env=dict(os.environ))
            async with stdio_client(parameters) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream, read_timeout_seconds=15) as session:
                    await session.initialize()
                    tools = {tool.name: tool for tool in (await session.list_tools()).tools}
                    self.assertTrue(tools['flow_index_status'].annotations.read_only_hint)
                    self.assertFalse(tools['rebuild_flow_index'].annotations.read_only_hint)
                    self.assertFalse(tools['rebuild_flow_index'].annotations.destructive_hint)
                    rebuilt = await session.call_tool('rebuild_flow_index', {})
                    self.assertFalse(rebuilt.is_error, rebuilt.content)
                    self.assertEqual(rebuilt.structured_content['snapshot_id'], self.dataset.snapshot_id)
                    status = await session.call_tool('flow_index_status', {})
                    self.assertFalse(status.is_error, status.content)
                    self.assertEqual(status.structured_content, self.dataset.flow_index_status())
                    arguments = {'start_id': 'a', 'target_id': 'b', 'path_selection': 'material'}
                    answer = await session.call_tool('trace_processes', arguments)
                    self.assertFalse(answer.is_error, answer.content)
                    self.assertEqual(network_semantics(answer.structured_content), network_semantics(self.dataset.trace_processes(**arguments, view='compact')))
        asyncio.run(exercise())

    def test_http_concise_trace_is_advertised_and_preserves_compact_graph_evidence(self):
        arguments = {'start_id': 'a', 'target_id': 'b'}
        compact = self.dataset.trace_processes(**arguments, view='compact')
        with TestClient(create_app(self.dataset)) as client:
            parameters = client.get('/openapi.json').json()['paths']['/api/trace']['get']['parameters']
            view = next(row['schema'] for row in parameters if row['name'] == 'view')
            self.assertEqual(view['enum'], ['full', 'compact', 'concise'])
            self.assertEqual(view['default'], 'full')
            response = client.get('/api/trace', params={**arguments, 'view': 'concise'})
            self.assertEqual(response.status_code, 200)
            answer = response.json()
            self.assertEqual(answer['presentation']['view'], 'concise')
            for key in ('processes', 'edges', 'paths', 'coverage', 'leaves', 'cycles', 'branch_coverage', 'limit_reasons'):
                self.assertEqual(answer[key], compact[key])
            self.assertTrue(all('material_facts' not in row and 'provenance' not in row for row in answer['resources']))
            self.assertEqual(client.get('/api/resources/a').json(), self.dataset.get_resource('a'))
            self.assertEqual(client.get('/api/trace', params={**arguments, 'view': 'unknown'}).status_code, 400)

    def test_cli_concise_trace_keeps_recipes_and_reports_resource_metadata_omissions(self):
        arguments = ['trace', '--database', str(self.database), '--start-id', 'a', '--target-id', 'b']
        compact = self.dataset.trace_processes(start_id='a', target_id='b', view='compact')
        output = StringIO()
        with redirect_stdout(output):
            code = main([*arguments, '--view', 'concise'])
        self.assertEqual(code, 0)
        answer = json.loads(output.getvalue())
        self.assertEqual(answer['presentation']['view'], 'concise')
        self.assertEqual(answer['presentation']['omitted_resource_field_counts']['provenance'], len(compact['resources']))
        self.assertTrue(all('provenance' not in row and 'material_facts' not in row for row in answer['resources']))
        for key in ('processes', 'paths', 'coverage', 'leaves', 'cycles', 'branch_coverage', 'limit_reasons'):
            self.assertEqual(answer[key], compact[key])
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as invalid:
            main([*arguments, '--view', 'unknown'])
        self.assertEqual(invalid.exception.code, 2)

    def test_official_mcp_trace_defaults_to_compact_but_full_view_remains_available(self):
        arguments = {'start_id': 'a', 'target_id': 'b'}
        full = self.dataset.trace_processes(**arguments)
        async def exercise():
            parameters = StdioServerParameters(command=sys.executable,
                args=['-m', 'gtnh_data', 'mcp', '--database', str(self.database)], env=dict(os.environ))
            async with stdio_client(parameters) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream, read_timeout_seconds=15) as session:
                    await session.initialize()
                    tools = {tool.name: tool for tool in (await session.list_tools()).tools}
                    self.assertEqual(tools['trace_processes'].input_schema['properties']['view'],
                                     {'enum': ['compact', 'full', 'concise'], 'default': 'compact'})
                    compact = await session.call_tool('trace_processes', arguments)
                    self.assertFalse(compact.is_error, compact.content)
                    self.assertEqual(compact.structured_content['presentation']['view'], 'compact')
                    for key in ('processes', 'paths', 'route', 'branch_coverage', 'cycles', 'limit_reasons'):
                        self.assertEqual(compact.structured_content[key], full[key])
                    expanded = await session.call_tool('trace_processes', dict(arguments, view='full'))
                    self.assertFalse(expanded.is_error, expanded.content)
                    self.assertEqual(network_semantics(expanded.structured_content), network_semantics(full))
                    concise = await session.call_tool('trace_processes', dict(arguments, view='concise'))
                    self.assertFalse(concise.is_error, concise.content)
                    self.assertEqual(network_semantics(concise.structured_content),
                                     network_semantics(self.dataset.trace_processes(**arguments, view='concise')))
                    self.assertEqual(concise.structured_content['presentation']['resource_record_scope'],
                                     'resource_records_with_explicit_metadata_omissions')
                    restored = await session.call_tool('get_resource', {'id': 'a'})
                    self.assertEqual(restored.structured_content, self.dataset.get_resource('a'))
                    self.assertIn('provenance', restored.structured_content['item'])
                    invalid = await session.call_tool('trace_processes', dict(arguments, view='unknown'))
                    self.assertTrue(invalid.is_error)
        asyncio.run(exercise())

    def test_http_and_cli_forward_recipe_voltage_filters_without_inferring_machine_tiers(self):
        arguments = dict(start_id='a', target_id='b', min_tier=0, max_tier=3, unknown_tier_policy='exclude')
        expected = self.dataset.trace_processes(**arguments)
        with TestClient(create_app(self.dataset)) as client:
            response = client.get('/api/trace', params=arguments)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), expected)
        output = StringIO()
        with redirect_stdout(output):
            result = main(['trace', '--database', str(self.database), '--start-id', 'a', '--target-id', 'b',
                           '--min-tier', '0', '--max-tier', '3', '--unknown-tier-policy', 'exclude'])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output.getvalue()), expected)

    def test_recycling_structured_http_and_cli_requests_use_the_dataset_owner(self):
        arguments = dict(main_path={'resource_ids':['a','b'], 'process_ids':['convert']},
                         byproduct_id='b', return_id='a', main_runs=2, yield_mode='expected',
                         min_tier=0, max_tier=3, unknown_tier_policy='include', max_paths=2)
        expected = self.dataset.plan_recycling(**arguments)
        with TestClient(create_app(self.dataset)) as client:
            response = client.post('/api/recycling-plan', json=arguments)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), expected)
            self.assertEqual(client.post('/api/recycling-plan', json={'unexpected':True}).status_code, 400)
            invalid = client.post('/api/recycling-plan', json={**arguments, 'selections': {'convert': {'0': {'choice_index': 999, 'resource_id': 'a'}}}})
            self.assertEqual(invalid.status_code, 400)
            self.assertEqual(invalid.json(), {'error': 'Invalid concrete input selection'})
        request = self.root / 'recycling-request.json'
        request.write_text(json.dumps(arguments), encoding='utf-8')
        output = StringIO()
        with redirect_stdout(output):
            result = main(['recycle', '--database', str(self.database), '--request-file', str(request)])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output.getvalue()), expected)

    def test_chemical_facts_and_bounded_loop_filters_are_shared_across_http_and_cli(self):
        arguments = dict(start_id='a', kind='any', chemical_kind='unsupported', yield_mode='expected',
                         max_depth=3, max_processes=20, max_paths=4, max_states=100,
                         min_tier=0, max_tier=3, unknown_tier_policy='include')
        expected = self.dataset.find_loops(**arguments)
        facts = self.dataset.inspect_chemistry(resource_id='a')
        with TestClient(create_app(self.dataset)) as client:
            self.assertEqual(client.get('/api/chemistry/a').json(), facts)
            self.assertEqual(client.get('/api/loops', params=arguments).json(), expected)
            self.assertEqual(client.post('/api/loops', json=arguments).json(), expected)
            self.assertEqual(client.post('/api/loops', json={'unexpected':True}).status_code, 400)
        output = StringIO()
        with redirect_stdout(output):
            result = main(['chemistry', 'a', '--database', str(self.database)])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output.getvalue()), facts)
        output = StringIO()
        with redirect_stdout(output):
            result = main(['loops', '--database', str(self.database), '--start-id', 'a', '--kind', 'any',
                           '--chemical-kind', 'unsupported', '--yield-mode', 'expected', '--max-depth', '3',
                           '--max-processes', '20', '--max-paths', '4', '--max-states', '100',
                           '--min-tier', '0', '--max-tier', '3', '--unknown-tier-policy', 'include'])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output.getvalue()), expected)

    def test_loop_advertised_http_bounds_and_cli_limits_match_the_owner(self):
        with TestClient(create_app(self.dataset)) as client:
            advertised = {item['name']: item['schema'] for item in client.get('/openapi.json').json()['paths']['/api/loops']['get']['parameters']}
            for parameter, maximum in [('max_depth', 20), ('max_processes', 1000), ('max_states', 50000)]:
                self.assertEqual(advertised[parameter]['maximum'], maximum)
                self.assertEqual(client.get('/api/loops', params={'start_id': 'a', parameter: maximum + 1}).status_code, 422)
                self.assertEqual(client.post('/api/loops', json={'start_id': 'a', parameter: maximum + 1}).status_code, 400)
                error_output = StringIO()
                with redirect_stderr(error_output):
                    result = main(['loops', '--database', str(self.database), '--start-id', 'a', '--' + parameter.replace('_', '-'), str(maximum + 1)])
                self.assertEqual(result, 2)
                self.assertEqual(json.loads(error_output.getvalue()), {'error': f'{parameter} must be between 1 and {maximum}'})

    def test_official_mcp_stdio_matches_dataset_operations(self):
        async def exercise():
            parameters = StdioServerParameters(command=sys.executable, args=["-m", "gtnh_data", "mcp", "--database", str(self.database)], env=dict(os.environ))
            async with stdio_client(parameters) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream, read_timeout_seconds=10) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    trace_schema = next(tool.input_schema for tool in tools.tools if tool.name == 'trace_processes')
                    self.assertEqual(trace_schema['properties']['path_selection'], {'enum': ['diverse', 'shortest', 'material'], 'default': 'diverse'})
                    self.assertEqual(trace_schema['properties']['max_extra_steps']['default'], 6)
                    loop_schema = next(tool.input_schema for tool in tools.tools if tool.name == 'find_loops')
                    for parameter, maximum in [('max_depth', 20), ('max_processes', 1000), ('max_states', 50000)]:
                        self.assertEqual(loop_schema['properties'][parameter]['maximum'], maximum)
                    self.assertTrue({"status", "find_resources", "get_resource", "find_processes", "get_process", "get_group", "find_sources", "get_source", "find_environments", "trace_processes", "plan_recycling"} <= {tool.name for tool in tools.tools})
                    result = await session.call_tool("get_source", {"id": self.mining_source["id"]})
                    self.assertFalse(result.is_error)
                    self.assertEqual(result.structured_content, self.dataset.get_source(self.mining_source["id"]))
                    self.assertEqual(len(result.content), 1)
                    self.assertIn("get_source", result.content[0].text)
                    self.assertIn(self.dataset.snapshot_id, result.content[0].text)
                    self.assertLess(len(result.content[0].text), 256)
                    self.assertNotIn("generated_source_id", result.content[0].text)
                    error = await session.call_tool("get_source", {"id": "missing"})
                    self.assertTrue(error.is_error)
                    self.assertEqual(json.loads(error.content[0].text), {"error": "Unknown sources ID: missing"})
                    result = await session.call_tool("find_processes", {"input_id": "a"})
                    self.assertFalse(result.is_error)
                    self.assertEqual(result.structured_content, self.dataset.find_processes(input_id="a"))
                    result = await session.call_tool("find_resources", {"q": "iron pltae", "limit": 8})
                    self.assertFalse(result.is_error)
                    self.assertEqual(result.structured_content, self.dataset.find_resources(q="iron pltae", limit=8))
                    self.assertEqual([item["id"] for item in result.structured_content["items"]], ["a"])
                    result = await session.call_tool("trace_processes", {"start_id": "a", "target_id": "b"})
                    self.assertEqual(result.structured_content, self.dataset.trace_processes(start_id="a", target_id="b", view='compact'))
                    for selection in ('diverse', 'shortest'):
                        selection_arguments = {'start_id': 'a', 'target_id': 'b', 'path_selection': selection}
                        result = await session.call_tool('trace_processes', selection_arguments)
                        self.assertFalse(result.is_error)
                        self.assertEqual(result.structured_content, self.dataset.trace_processes(**selection_arguments, view='compact'))
                    arguments = {'start_id': 'a', 'target_id': 'b', 'required_resource_ids': ['a', 'middle'],
                                 'excluded_resource_ids': ['excluded'], 'max_paths': 2, 'max_extra_steps': 0}
                    result = await session.call_tool('trace_processes', arguments)
                    self.assertFalse(result.is_error)
                    self.assertEqual(result.structured_content, self.dataset.trace_processes(**arguments, view='compact'))
                    tier_arguments = dict(start_id='a', target_id='b', min_tier=0, max_tier=3, unknown_tier_policy='exclude')
                    result = await session.call_tool('trace_processes', tier_arguments)
                    self.assertFalse(result.is_error)
                    self.assertEqual(result.structured_content, self.dataset.trace_processes(**tier_arguments, view='compact'))
                    recycling = dict(main_path={'resource_ids':['a','b'],'process_ids':['convert']}, byproduct_id='b', return_id='a', main_runs=2, yield_mode='expected')
                    result = await session.call_tool('plan_recycling', recycling)
                    self.assertFalse(result.is_error)
                    self.assertEqual(result.structured_content, self.dataset.plan_recycling(**recycling))
                    self.assertEqual(len(result.content), 1)
                    self.assertLess(len(result.content[0].text), 256)
                    self.assertNotIn('main_path', result.content[0].text)
                    loop_arguments = dict(start_id='a', kind='any', chemical_kind='unsupported', yield_mode='expected',
                                          max_depth=3, max_processes=20, max_paths=4, max_states=100,
                                          min_tier=0, max_tier=3, unknown_tier_policy='include')
                    result = await session.call_tool('find_loops', loop_arguments)
                    self.assertFalse(result.is_error)
                    self.assertEqual(result.structured_content, self.dataset.find_loops(**loop_arguments))
                    result = await session.call_tool('inspect_chemistry', {'resource_id':'a'})
                    self.assertFalse(result.is_error)
                    self.assertEqual(result.structured_content, self.dataset.inspect_chemistry(resource_id='a'))
                    self.assertLess(len(result.content[0].text), 256)
                    error = await session.call_tool("get_resource", {"id": "missing"})
                    self.assertTrue(error.is_error)
        asyncio.run(exercise())

    def test_cli_repeated_material_constraints_use_the_same_owner(self):
        output = StringIO()
        with redirect_stdout(output):
            result = main(['trace', '--database', str(self.database), '--start-id', 'a', '--target-id', 'b',
                           '--required-resource-id', 'a', '--required-resource-id', 'middle', '--excluded-resource-id', 'excluded',
                           '--max-paths', '2', '--max-extra-steps', '0'])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output.getvalue()), self.dataset.trace_processes(start_id='a', target_id='b',
                          required_resource_ids=['a', 'middle'], excluded_resource_ids=['excluded'], max_paths=2, max_extra_steps=0))


if __name__ == "__main__":
    unittest.main()
