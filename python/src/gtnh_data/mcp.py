"""Official MCP SDK 2.x stdio transport over the same Dataset operations."""

from functools import partial

import anyio
from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from .dataset import Dataset, DatasetError, _json


def _schema(properties=None, required=()):
    return {"type": "object", "properties": properties or {}, "required": list(required), "additionalProperties": False}


STRING = {"type": "string"}
OPTIONAL_STRING = {"type": ["string", "null"]}
PAGING = {"offset": {"type": "integer", "minimum": 0, "default": 0},
          "limit": {"type": "integer", "minimum": 1, "maximum": 500, "default": 50}}
OPERATIONS = {
    "status": ("Describe the fixed snapshot, counts and capture coverage", _schema()),
    "find_resources": ("Search snapshot resources with bounded pagination", _schema({"q": STRING, "kind": {"enum": ["item", "fluid", None]}, **PAGING})),
    "get_resource": ("Read an exact canonical resource and provenance", _schema({"id": STRING}, ("id",))),
    "find_processes": ("Find producing or using processes, including supported matching and unresolved counts", _schema({"input_id": OPTIONAL_STRING, "output_id": OPTIONAL_STRING, "family": OPTIONAL_STRING, **PAGING})),
    "get_process": ("Read all input choices, co-products, conditions and provenance", _schema({"id": STRING}, ("id",))),
    "get_group": ("Read a canonical matching group and its members", _schema({"id": STRING}, ("id",))),
    "find_sources": ("Find configured acquisition sources, not observed world deposits", _schema({"resource_id": OPTIONAL_STRING, "environment_id": OPTIONAL_STRING, **PAGING})),
    "get_source": ("Read an exact acquisition source, conditions, parent links and provenance", _schema({"id": STRING}, ("id",))),
    "find_environments": ("Search the registered environment catalog", _schema({"q": STRING, **PAGING})),
    "trace_processes": ("Find complete shortest-first consume dependency paths with required or excluded materials. Full recipe inputs remain requirements. Not an inventory, yield or throughput proof", _schema({"start_id": STRING, "target_id": STRING, "max_depth": {"type": "integer", "minimum": 1, "maximum": 64, "default": 12}, "max_processes": {"type": "integer", "minimum": 1, "maximum": 5000, "default": 300},
                            "max_paths": {"type": "integer", "minimum": 1, "maximum": 100, "default": 8}, "max_extra_steps": {"type": "integer", "minimum": 0, "maximum": 64, "default": 2},
                            "required_resource_ids": {"type": "array", "items": STRING}, "excluded_resource_ids": {"type": "array", "items": STRING}}, ("start_id", "target_id"))),
}


def create_server(dataset: Dataset) -> Server:
    async def list_tools(context, params):
        return types.ListToolsResult(tools=[
            types.Tool(name=name, description=description, input_schema=schema,
                       annotations=types.ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=False))
            for name, (description, schema) in OPERATIONS.items()
        ])

    async def call_tool(context, params):
        if params.name not in OPERATIONS:
            return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text="Unknown dataset operation")])
        try:
            result = await anyio.to_thread.run_sync(partial(getattr(dataset, params.name), **(params.arguments or {})))
        except (DatasetError, TypeError) as error:
            return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text=_json({"error": str(error)}))])
        summary = f"{params.name}: snapshot {dataset.snapshot_id}. Data is in structuredContent."
        return types.CallToolResult(content=[types.TextContent(type="text", text=summary)], structured_content=result)

    return Server("gtnh-data", version="0.1.0", instructions=f"Read-only canonical GTNH dataset {dataset.snapshot_id}. Acquisition is configured possibility. Trace is discovery, not execution proof.",
                  get_tool_input_schema=lambda name: OPERATIONS[name][1] if name in OPERATIONS else None,
                  on_list_tools=list_tools, on_call_tool=call_tool)


async def run_stdio(dataset: Dataset):
    server = create_server(dataset)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
