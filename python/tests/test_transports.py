import asyncio
import json
import os
import sys
import tempfile
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


class TransportTests(unittest.TestCase):
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

    def test_http_rejects_unknown_path_selection_instead_of_ignoring_it(self):
        with TestClient(create_app(self.dataset)) as client:
            response = client.get('/api/trace', params={'start_id': 'a', 'target_id': 'b', 'path_selection': 'unknown'})
            self.assertEqual(response.status_code, 400)

    def test_http_and_cli_share_explicit_path_selection_and_defaults(self):
        for selection in ('diverse', 'shortest'):
            with self.subTest(selection=selection):
                arguments = dict(start_id='a', target_id='b', path_selection=selection)
                expected = self.dataset.trace_processes(**arguments)
                with TestClient(create_app(self.dataset)) as client:
                    self.assertEqual(client.get('/api/trace', params=arguments).json(), expected)
                output = StringIO()
                with redirect_stdout(output):
                    result = main(['trace', '--database', str(self.database), '--start-id', 'a', '--target-id', 'b',
                                   '--path-selection', selection])
                self.assertEqual(result, 0)
                self.assertEqual(json.loads(output.getvalue()), expected)

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
                    self.assertEqual(trace_schema['properties']['path_selection'], {'enum': ['diverse', 'shortest'], 'default': 'diverse'})
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
                    self.assertEqual(result.structured_content, self.dataset.trace_processes(start_id="a", target_id="b"))
                    for selection in ('diverse', 'shortest'):
                        selection_arguments = {'start_id': 'a', 'target_id': 'b', 'path_selection': selection}
                        result = await session.call_tool('trace_processes', selection_arguments)
                        self.assertFalse(result.is_error)
                        self.assertEqual(result.structured_content, self.dataset.trace_processes(**selection_arguments))
                    arguments = {'start_id': 'a', 'target_id': 'b', 'required_resource_ids': ['a', 'middle'],
                                 'excluded_resource_ids': ['excluded'], 'max_paths': 2, 'max_extra_steps': 0}
                    result = await session.call_tool('trace_processes', arguments)
                    self.assertFalse(result.is_error)
                    self.assertEqual(result.structured_content, self.dataset.trace_processes(**arguments))
                    tier_arguments = dict(start_id='a', target_id='b', min_tier=0, max_tier=3, unknown_tier_policy='exclude')
                    result = await session.call_tool('trace_processes', tier_arguments)
                    self.assertFalse(result.is_error)
                    self.assertEqual(result.structured_content, self.dataset.trace_processes(**tier_arguments))
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
