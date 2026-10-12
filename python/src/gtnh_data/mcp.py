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
TIERS = {"min_tier": {"type": ["integer", "null"], "minimum": 0, "maximum": 15},
         "max_tier": {"type": ["integer", "null"], "minimum": 0, "maximum": 15},
         "unknown_tier_policy": {"enum": ["exclude", "include"], "default": "exclude"}}
IDS = {"type": "array", "items": STRING}
SCOPE = _schema({name: IDS for name in ('excluded_resource_ids', 'excluded_group_ids', 'excluded_namespaces', 'excluded_family_ids')})
AMOUNT = {"oneOf": [{"type": "integer", "minimum": 1}, _schema({"numerator": {"type": "integer", "minimum": 1}, "denominator": {"type": "integer", "minimum": 1}}, ('numerator', 'denominator'))]}
NETWORK = {"target_amount": AMOUNT, "profile_id": OPTIONAL_STRING, "yield_mode": {"enum": ["guaranteed", "expected"], "default": "guaranteed"},
           "max_depth": {"type": "integer", "minimum": 1, "maximum": 20, "default": 8}, "max_processes": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 200},
           "max_variants": {"type": "integer", "minimum": 1, "maximum": 512, "default": 128}, "max_resources": {"type": "integer", "minimum": 1, "maximum": 2000, "default": 512},
           "max_solutions": {"type": "integer", "minimum": 1, "maximum": 100, "default": 8}, "max_solves": {"type": "integer", "minimum": 1, "maximum": 100, "default": 24},
           "timeout_seconds": {"type": "number", "exclusiveMinimum": 0, "maximum": 30, "default": 10},
           "max_columns": {"type": "integer", "minimum": 1, "maximum": 512, "default": 128}, "max_rows": {"type": "integer", "minimum": 1, "maximum": 4096, "default": 512},
           "start_stock": {"type": ["object", "null"]}, "selections": {"type": ["object", "null"]}, **TIERS}
OPERATIONS = {
    "analyze_statistics": ("Describe bounded scoped catalog distributions and comparable captured-recipe cost differences. Candidate findings are not confirmed bugs", _schema({"profile_id": OPTIONAL_STRING, "scope": SCOPE, "max_records": {"type": "integer", "minimum": 1, "maximum": 2000000, "default": 600000}, "max_findings": {"type": "integer", "minimum": 1, "maximum": 500, "default": 50}, "max_signature_buckets": {"type": "integer", "minimum": 1, "maximum": 200000, "default": 50000}, "timeout_seconds": {"type": "number", "exclusiveMinimum": 0, "maximum": 60, "default": 15}})),
    "list_boundary_profiles": ("List user-controlled snapshot-bound basic-resource and exclusion profiles", _schema()),
    "get_boundary_profile": ("Read a saved snapshot-bound profile and revision", _schema({"profile_id": STRING}, ('profile_id',))),
    "save_boundary_profile": ("Create or update a user-controlled boundary profile sidecar without changing canonical data", _schema({"profile_id": STRING, "name": STRING, "base_resource_ids": IDS, "scope": SCOPE, "expected_revision": {"type": ["integer", "null"], "minimum": 0}}, ('profile_id', 'name', 'base_resource_ids'))),
    "delete_boundary_profile": ("Delete a user-controlled boundary profile sidecar entry", _schema({"profile_id": STRING, "expected_revision": {"type": ["integer", "null"], "minimum": 0}}, ('profile_id',))),
    "find_resource_groups": ("Search captured resource groups and member counts", _schema({"q": STRING, **PAGING, "limit": {"type": "integer", "minimum": 1, "maximum": 500, "default": 20}})),
    "get_scope_catalog": ("List captured item namespaces and exact recipe families for exclusion editing", _schema()),
    "plan_to_bases": ("Plan whole stoichiometric recipes from a user-controlled basic-resource profile within explicit bounds", _schema({"target_id": STRING, "objective": {"enum": ["nominal_eu", "recipe_runs"]}, **NETWORK}, ('target_id', 'profile_id'))),
    "audit_energy": ("Compare complete bounded recycling networks with a chosen native benchmark at equal target quantity. Profile basics are not implicit allowed feeds", _schema({"primary_feed_id": STRING, "target_id": STRING, "benchmark_process_id": STRING, "scope": SCOPE, "allowed_feed_ids": {"type": ["array", "null"], "items": STRING}, "benchmark_selections": {"type": ["object", "null"]}, **NETWORK}, ('primary_feed_id', 'target_id', 'benchmark_process_id'))),
    "inspect_chemistry": ("Inspect source-backed material accounting facts and unsupported scope. Formula text alone is not purity or balance proof", _schema({"resource_id": STRING}, ("resource_id",))),
    "inspect_acquisition": ("Inspect captured unification and acquisition evidence, with bounded profile-root grounding. Missing data is not proof of unobtainability", _schema({"resource_id": STRING, "profile_id": OPTIONAL_STRING, "scope": SCOPE, **{key: NETWORK[key] for key in ('max_depth','max_processes','max_variants','max_resources')}}, ('resource_id',))),
    "find_loops": ("Audit bounded closed resource paths for guaranteed or expected gains, losses and external consumption", _schema({
        "start_id": STRING, "kind": {"enum": ["any", "gaining", "lossy", "conserving"]}, "chemical_kind": {"enum": ["any", "balanced", "gaining", "lossy", "mixed", "unsupported"]}, "yield_mode": {"enum": ["guaranteed", "expected"]}, "selections": {"type":["object","null"]},
        "max_depth": {"type": "integer", "minimum": 1, "maximum": 20}, "max_processes": {"type": "integer", "minimum": 1, "maximum": 1000},
        "max_paths": {"type": "integer", "minimum": 1, "maximum": 100}, "max_states": {"type": "integer", "minimum": 1, "maximum": 50000}, **TIERS}, ("start_id",))),
    "plan_recycling": ("Evaluate a chosen main path and bounded byproduct return paths with explicit quantities and native limitations", _schema({
        "main_path": _schema({"resource_ids": {"type": "array", "items": STRING}, "process_ids": {"type": "array", "items": STRING}}, ("resource_ids", "process_ids")),
        "byproduct_id": STRING, "return_id": STRING, "main_runs": {"oneOf": [{"type": "integer"}, _schema({"numerator": {"type": "integer"}, "denominator": {"type": "integer"}}, ("numerator", "denominator"))]},
        "selections": {"type": ["object", "null"]}, "yield_mode": {"enum": ["guaranteed", "expected"]},
        "max_depth": {"type": "integer", "minimum": 1, "maximum": 64}, "max_processes": {"type": "integer", "minimum": 1, "maximum": 5000},
        "max_paths": {"type": "integer", "minimum": 1, "maximum": 100}, "max_extra_steps": {"type": "integer", "minimum": 0, "maximum": 64}, **TIERS}, ("main_path", "byproduct_id", "return_id"))),
    "status": ("Describe the fixed snapshot, counts and capture coverage", _schema()),
    "find_resources": ("Search snapshot resources with bounded pagination and optional user scope", _schema({"q": STRING, "kind": {"enum": ["item", "fluid", None]}, "profile_id": OPTIONAL_STRING, "scope": SCOPE, **PAGING})),
    "get_resource": ("Read an exact canonical resource and provenance", _schema({"id": STRING}, ("id",))),
    "find_processes": ("Find producing or using processes, including supported matching and unresolved counts", _schema({"input_id": OPTIONAL_STRING, "output_id": OPTIONAL_STRING, "family": OPTIONAL_STRING, **PAGING})),
    "get_process": ("Read all input choices, co-products, conditions and provenance", _schema({"id": STRING}, ("id",))),
    "get_group": ("Read a canonical matching group and its members", _schema({"id": STRING}, ("id",))),
    "find_sources": ("Find configured acquisition sources, not observed world deposits", _schema({"resource_id": OPTIONAL_STRING, "environment_id": OPTIONAL_STRING, **PAGING})),
    "get_source": ("Read an exact acquisition source, conditions, parent links and provenance", _schema({"id": STRING}, ("id",))),
    "find_environments": ("Search the registered environment catalog", _schema({"q": STRING, **PAGING})),
    "trace_processes": ("Find bounded diverse or shortest consume dependency paths with required or excluded materials. Diverse selection spreads routes across target ingredients. Full recipe inputs remain requirements. Not an inventory, yield or throughput proof", _schema({"start_id": STRING, "target_id": STRING, "max_depth": {"type": "integer", "minimum": 1, "maximum": 64, "default": 12}, "max_processes": {"type": "integer", "minimum": 1, "maximum": 5000, "default": 300},
                            "max_paths": {"type": "integer", "minimum": 1, "maximum": 100, "default": 8}, "max_extra_steps": {"type": "integer", "minimum": 0, "maximum": 64, "default": 6},
                            "path_selection": {"enum": ["diverse", "shortest"], "default": "diverse"},
                            "required_resource_ids": {"type": "array", "items": STRING}, "excluded_resource_ids": {"type": "array", "items": STRING}, **TIERS}, ("start_id", "target_id"))),
}


def create_server(dataset: Dataset) -> Server:
    async def list_tools(context, params):
        return types.ListToolsResult(tools=[
            types.Tool(name=name, description=description, input_schema=schema,
                       annotations=types.ToolAnnotations(read_only_hint=name not in ('save_boundary_profile', 'delete_boundary_profile'), destructive_hint=name == 'delete_boundary_profile', open_world_hint=False))
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

    return Server("gtnh-data", version="0.1.0", instructions=f"Canonical GTNH snapshot {dataset.snapshot_id} is immutable. Boundary profiles are user-controlled sidecars. Acquisition is configured possibility. Traces and bounded networks are not machine execution proof.",
                  get_tool_input_schema=lambda name: OPERATIONS[name][1] if name in OPERATIONS else None,
                  on_list_tools=list_tools, on_call_tool=call_tool)


async def run_stdio(dataset: Dataset):
    server = create_server(dataset)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
