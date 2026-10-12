import asyncio
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.shared.exceptions import MCPError
from jsonschema import Draft202012Validator

from gtnh_data import Dataset
from .artifacts import resource, snapshot


class MCPGuideTests(unittest.TestCase):
    def test_fresh_stdio_discovery_serves_guide_without_changing_tool_contracts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dataset = Dataset.import_snapshot(snapshot(root / 'snapshot', resources=[resource('a')]), root / 'index.sqlite')

            async def exercise():
                parameters = StdioServerParameters(command=sys.executable,
                    args=['-m', 'gtnh_data', 'mcp', '--database', str(dataset.path)], env=dict(os.environ))
                async with stdio_client(parameters) as (read, write):
                    async with ClientSession(read, write, read_timeout_seconds=10) as session:
                        initialized = await session.initialize()
                        self.assertIsNotNone(initialized.capabilities.resources)
                        uri = 'gtnh-data://guide/query-workflows'
                        self.assertIn(uri, initialized.instructions)
                        resources = (await session.list_resources()).resources
                        self.assertEqual([str(item.uri) for item in resources], [uri])
                        guide = await session.read_resource(uri)
                        self.assertEqual(len(guide.contents), 1)
                        self.assertEqual(guide.contents[0].mime_type, 'text/markdown')
                        for term in ('trace_processes', 'audit_energy', 'start_stock', 'amperage'):
                            self.assertIn(term, guide.contents[0].text)
                        with self.assertRaises(MCPError) as error:
                            await session.read_resource('gtnh-data://guide/not-a-file')
                        self.assertEqual(error.exception.code, -32602)
                        tools = {tool.name: tool for tool in (await session.list_tools()).tools}
                        self.assertEqual(len(tools), 23)
                        examples = re.findall(r'```json\n(.*?)\n```', guide.contents[0].text, flags=re.DOTALL)
                        self.assertGreaterEqual(len(examples), 6)
                        for example in examples:
                            request = json.loads(example)
                            Draft202012Validator(tools[request['name']].input_schema).validate(request['arguments'])
                        self.assertIn('dependency paths', tools['trace_processes'].description)
                        self.assertIn('primary feed', tools['audit_energy'].description)
                        self.assertIn('nominal EU', tools['audit_energy'].description)
                        self.assertFalse(tools['save_boundary_profile'].annotations.read_only_hint)
                        self.assertTrue(tools['delete_boundary_profile'].annotations.destructive_hint)
                        self.assertTrue(all(tool.annotations.read_only_hint for name, tool in tools.items()
                            if name not in ('save_boundary_profile', 'delete_boundary_profile')))
                        answer = await session.call_tool('get_resource', {'id': 'a'})
                        self.assertEqual(answer.structured_content, dataset.get_resource('a'))
                        self.assertEqual(len(answer.content), 1)
                        self.assertLess(len(answer.content[0].text), 256)

            asyncio.run(exercise())
