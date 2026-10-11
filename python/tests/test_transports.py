import asyncio
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from fastapi.testclient import TestClient
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from gtnh_data import Dataset
from gtnh_data.http import create_app
from gtnh_data.cli import main
from .artifacts import choice, process, resource, slot, snapshot


class TransportTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.database = self.root / "dataset.sqlite"
        self.dataset = Dataset.import_snapshot(snapshot(self.root / "capture", resources=[dict(resource("a"), display_name="Iron Plate"), resource("b"), resource('middle'), resource('excluded')],
                                                       processes=[process("convert", [slot(choice("a"))], ["b"]),
                                                                  process('detour-first', [slot(choice('a'))], ['middle']),
                                                                  process('detour-finish', [slot(choice('middle'))], ['b'])]), self.database)

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

    def test_official_mcp_stdio_matches_dataset_operations(self):
        async def exercise():
            parameters = StdioServerParameters(command=sys.executable, args=["-m", "gtnh_data", "mcp", "--database", str(self.database)], env=dict(os.environ))
            async with stdio_client(parameters) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream, read_timeout_seconds=10) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    self.assertEqual({tool.name for tool in tools.tools}, {"status", "find_resources", "get_resource", "find_processes", "get_process", "get_group", "find_sources", "find_environments", "trace_processes"})
                    result = await session.call_tool("find_processes", {"input_id": "a"})
                    self.assertFalse(result.is_error)
                    self.assertEqual(result.structured_content, self.dataset.find_processes(input_id="a"))
                    result = await session.call_tool("find_resources", {"q": "iron pltae", "limit": 8})
                    self.assertFalse(result.is_error)
                    self.assertEqual(result.structured_content, self.dataset.find_resources(q="iron pltae", limit=8))
                    self.assertEqual([item["id"] for item in result.structured_content["items"]], ["a"])
                    result = await session.call_tool("trace_processes", {"start_id": "a", "target_id": "b"})
                    self.assertEqual(result.structured_content, self.dataset.trace_processes(start_id="a", target_id="b"))
                    arguments = {'start_id': 'a', 'target_id': 'b', 'required_resource_ids': ['a', 'middle'],
                                 'excluded_resource_ids': ['excluded'], 'max_paths': 2, 'max_extra_steps': 0}
                    result = await session.call_tool('trace_processes', arguments)
                    self.assertFalse(result.is_error)
                    self.assertEqual(result.structured_content, self.dataset.trace_processes(**arguments))
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
