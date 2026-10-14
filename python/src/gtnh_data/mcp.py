"""Official MCP SDK 2.x stdio transport over the same Dataset operations."""

from functools import partial
from importlib.resources import files

import anyio
from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.shared.exceptions import MCPError

from .dataset import Dataset, DatasetError, _json

GUIDE_URI = 'gtnh-data://guide/query-workflows'
GUIDANCE = (
    f'Read {GUIDE_URI} once for tool choices and examples. Resolve names with find_resources '
    'and a small limit, then retain exact snapshot IDs. Use lookups for declarations, '
    'trace_processes for dependency paths, plan_to_bases for complete AND-input plans, '
    'audit_energy for regenerative networks, find_loops for resource/chemical loops, '
    'and analyze_statistics for bounded candidate findings. Inspect coverage, exclusions, '
    'limits, uncertainty and startup. A verified witness is not global optimization or '
    'machine execution proof. Profiles permit external feeds, not inventory. Write profile '
    'sidecars only when changing user assumptions is intended. Use path_selection=material '
    'on trace after flow_index_status reports ready. rebuild_flow_index writes derived search '
    'data, not recipe facts. Trace/recycling/loop tools do not accept profile scopes. '
    'None and empty start_stock have different meanings. '
    'Trace defaults to view=compact: complete selected recipes and declared choices with '
    'explicit counts for omitted matching variants. Use view=full for expanded candidates. '
    'Expected yield is not guaranteed stock. Data appears once in structuredContent.'
)


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
    "flow_index_status": ('Read prepared material-flow index readiness, snapshot binding and analysis version. A missing or incompatible index requires an explicit rebuild before material route selection. This does not change captured data', _schema()),
    "rebuild_flow_index": ('Prepare material-flow search data offline for this snapshot. Writes a replaceable derived sidecar, leaving captured resources and recipes unchanged. Run when readiness reports missing or incompatible, not before every query. Preparation may take longer than a lookup', _schema()),
    "analyze_statistics": ('Describe scoped catalog distributions and comparable captured-recipe cost spreads. Findings are candidates, not bugs. max_records scans resources/groups before recipes. max_findings does not cap distributions. Read overview/search limits and inspect selected process IDs', _schema({"profile_id": OPTIONAL_STRING, "scope": SCOPE, "max_records": {"type": "integer", "minimum": 1, "maximum": 2000000, "default": 600000}, "max_findings": {"type": "integer", "minimum": 1, "maximum": 500, "default": 50}, "max_signature_buckets": {"type": "integer", "minimum": 1, "maximum": 200000, "default": 50000}, "timeout_seconds": {"type": "number", "exclusiveMinimum": 0, "maximum": 60, "default": 15}})),
    "list_boundary_profiles": ('Read existing snapshot-bound base-resource and exclusion profiles before planning or editing user assumptions', _schema()),
    "get_boundary_profile": ('Read one saved profile, external-feed assumptions, scope and revision. Reuse its revision for intentional updates or deletion', _schema({"profile_id": STRING}, ('profile_id',))),
    "save_boundary_profile": ('Write a user boundary-profile sidecar only when changing saved assumptions is intended. Basics permit external feeds, not inventory or acquisition proof. Use expected_revision. Canonical snapshot remains unchanged', _schema({"profile_id": STRING, "name": STRING, "base_resource_ids": IDS, "scope": SCOPE, "expected_revision": {"type": ["integer", "null"], "minimum": 0}}, ('profile_id', 'name', 'base_resource_ids'))),
    "delete_boundary_profile": ('Delete one user profile entry when intended, with its observed expected_revision. Canonical resources and recipes remain unchanged', _schema({"profile_id": STRING, "expected_revision": {"type": ["integer", "null"], "minimum": 0}}, ('profile_id',))),
    "find_resource_groups": ('Find captured matching groups and member counts with q and a small limit. Use get_group only when full membership matters', _schema({"q": STRING, **PAGING, "limit": {"type": "integer", "minimum": 1, "maximum": 500, "default": 20}})),
    "get_scope_catalog": ('Read literal registry namespaces and exact recipe families for scope editing. These identifiers do not infer mod ownership or acquisition', _schema()),
    "plan_to_bases": ('Expand a target through complete AND recipes using an explicit saved base-feed profile. Inspect net imports, OR selections, presence, integer-batch startup and bounds. recipe_runs is not minimum raw materials. Verified witnesses do not prove global completeness', _schema({"target_id": STRING, "objective": {"enum": ["nominal_eu", "recipe_runs"]}, **NETWORK}, ('target_id', 'profile_id'))),
    "audit_energy": ('Compare bounded regenerative networks with a selected benchmark at equal net target quantity using nominal EU. Accepted witnesses net-consume the primary feed. Profile basics are not implicit cofeeds. GT EU/t already includes amperage. Inspect startup, benchmark cofeeds and limits', _schema({"primary_feed_id": STRING, "target_id": STRING, "benchmark_process_id": STRING, "scope": SCOPE, "allowed_feed_ids": {"type": ["array", "null"], "items": STRING}, "benchmark_selections": {"type": ["object", "null"]}, **NETWORK}, ('primary_feed_id', 'target_id', 'benchmark_process_id'))),
    "inspect_chemistry": ('Inspect source-backed native material accounting vectors and unsupported reasons. Formula text is not proof of purity, composition or chemical conservation', _schema({"resource_id": STRING}, ("resource_id",))),
    "inspect_acquisition": ('Inspect unification preferences, declared sources and bounded AND-input grounding. Missing evidence or an unseeded cycle is not absolute unobtainability. Generated blocks and small-ore rule candidates do not seed inventory', _schema({"resource_id": STRING, "profile_id": OPTIONAL_STRING, "scope": SCOPE, **{key: NETWORK[key] for key in ('max_depth','max_processes','max_variants','max_resources')}}, ('resource_id',))),
    "find_loops": ('Audit bounded resource-return paths. kind classifies returned-resource gain/loss, chemical_kind separately filters chemical accounting. Inspect external consumption, startup, uncertainty and limits. Material autonomy does not prove energy autonomy', _schema({
        "start_id": STRING, "kind": {"enum": ["any", "gaining", "lossy", "conserving"]}, "chemical_kind": {"enum": ["any", "balanced", "gaining", "lossy", "mixed", "unsupported"]}, "yield_mode": {"enum": ["guaranteed", "expected"]}, "selections": {"type":["object","null"]},
        "max_depth": {"type": "integer", "minimum": 1, "maximum": 20}, "max_processes": {"type": "integer", "minimum": 1, "maximum": 1000},
        "max_paths": {"type": "integer", "minimum": 1, "maximum": 100}, "max_states": {"type": "integer", "minimum": 1, "maximum": 50000}, **TIERS}, ("start_id",))),
    "plan_recycling": ('Analyze byproduct C returning consumed D for a chosen main path. Keep complete recipe inputs and explicit OR selections. Compare net recovery, external inputs and startup. This is bounded secondary-path analysis, not a global network solver', _schema({
        "main_path": _schema({"resource_ids": {"type": "array", "items": STRING}, "process_ids": {"type": "array", "items": STRING}}, ("resource_ids", "process_ids")),
        "byproduct_id": STRING, "return_id": STRING, "main_runs": {"oneOf": [{"type": "integer"}, _schema({"numerator": {"type": "integer"}, "denominator": {"type": "integer"}}, ("numerator", "denominator"))]},
        "selections": {"type": ["object", "null"]}, "yield_mode": {"enum": ["guaranteed", "expected"]},
        "max_depth": {"type": "integer", "minimum": 1, "maximum": 64}, "max_processes": {"type": "integer", "minimum": 1, "maximum": 5000},
        "max_paths": {"type": "integer", "minimum": 1, "maximum": 100}, "max_extra_steps": {"type": "integer", "minimum": 0, "maximum": 64}, **TIERS}, ("main_path", "byproduct_id", "return_id"))),
    "status": ('Read the fixed snapshot ID, manifest, record counts and named capture coverage when identity or coverage is unknown. Counts alone do not prove whole-pack completeness', _schema()),
    "find_resources": ('Resolve names to distinct typed item/fluid IDs with q, kind and a small limit. Search tolerates prefixes, word order and modest typos. Check metadata/NBT and acquisition_analysis. Optional profile scope does not merge aliases', _schema({"q": STRING, "kind": {"enum": ["item", "fluid", None]}, "profile_id": OPTIONAL_STRING, "scope": SCOPE, **PAGING})),
    "get_resource": ('Read one exact canonical resource with typed identity, material facts and provenance. Use the selected ID, not a display name', _schema({"id": STRING}, ("id",))),
    "find_processes": ('Find recipes using input_id or producing output_id, optionally exact family and small pages. Both IDs require both filters. Inspect matching_complete/unresolved_matches on input lookup. No profile scope argument', _schema({"input_id": OPTIONAL_STRING, "output_id": OPTIONAL_STRING, "family": OPTIONAL_STRING, **PAGING})),
    "get_process": ('Read one complete captured recipe: AND input slots, OR choices, presence, all outputs/chances, conditions and provenance. Use before selecting accounting inputs or a benchmark', _schema({"id": STRING}, ("id",))),
    "get_group": ('Read one captured group and full members for predicate inspection. Groups can be large. Do not infer identity equivalence from membership alone', _schema({"id": STRING}, ("id",))),
    "find_sources": ('Find configured acquisition sources by resource/environment with small pages. These are definitions, not surveyed deposits. Rule candidates are not fixed independent yields', _schema({"resource_id": OPTIONAL_STRING, "environment_id": OPTIONAL_STRING, **PAGING})),
    "get_source": ('Read a source and follow parameters.generated_source_id directly to its generator. Keep conditions, environment links, resource semantics and provenance', _schema({"id": STRING}, ("id",))),
    "find_environments": ('Find registered generation environments with q and a small limit. Null dimension/provider mappings remain unresolved. Registration is not proof of a loaded or reachable world', _schema({"q": STRING, **PAGING})),
    "trace_processes": ('Find bounded consume dependency paths from A to B, not complete inventory or yield plans. Diverse spreads ingredient branches, shortest means steps not EU, material prioritizes native material continuity using a prepared flow index. Keep all side inputs. Compact view retains complete selected recipes and declared choices, with omitted candidate counts in presentation. Full view expands matching variants. Group exclusions use literal captured members on paths, preserve cofeeds and do not expand wildcard or NBT matching. Inspect path_details, route, paths, branches, leaves, presentation and limits. Uses its own material/tier filters, not profile scope', _schema({"start_id": STRING, "target_id": STRING, "max_depth": {"type": "integer", "minimum": 1, "maximum": 64, "default": 12}, "max_processes": {"type": "integer", "minimum": 1, "maximum": 5000, "default": 300},
                            "max_paths": {"type": "integer", "minimum": 1, "maximum": 100, "default": 8}, "max_extra_steps": {"type": "integer", "minimum": 0, "maximum": 64, "default": 6},
                            "path_selection": {"enum": ["diverse", "shortest", "material"], "default": "diverse"}, "view": {"enum": ["compact", "full"], "default": "compact"},
                            "required_resource_ids": {"type": "array", "items": STRING}, "excluded_resource_ids": {"type": "array", "items": STRING}, "excluded_group_ids": IDS, **TIERS}, ("start_id", "target_id"))),
}


def create_server(dataset: Dataset) -> Server:
    async def list_resources(context, params):
        return types.ListResourcesResult(resources=[types.Resource(uri=GUIDE_URI,
            name='query-workflows', title='GTNH query workflows for agents', mime_type='text/markdown',
            description='Read once for tool selection, small requests, identity, scopes, quantities and bounded-result interpretation')])

    async def read_resource(context, params):
        if str(params.uri) != GUIDE_URI:
            raise MCPError(types.INVALID_PARAMS, 'Unknown guide resource URI')
        guide = files('gtnh_data').joinpath('agent_guide.md').read_text(encoding='utf-8')
        return types.ReadResourceResult(contents=[types.TextResourceContents(uri=params.uri,
            mime_type='text/markdown', text=guide)])

    async def list_tools(context, params):
        return types.ListToolsResult(tools=[
            types.Tool(name=name, description=description, input_schema=schema,
                       annotations=types.ToolAnnotations(read_only_hint=name not in ('save_boundary_profile', 'delete_boundary_profile', 'rebuild_flow_index'), destructive_hint=name == 'delete_boundary_profile', open_world_hint=False))
            for name, (description, schema) in OPERATIONS.items()
        ])

    async def call_tool(context, params):
        if params.name not in OPERATIONS:
            return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text="Unknown dataset operation")])
        arguments = dict(params.arguments or {})
        if params.name == 'trace_processes':
            arguments.setdefault('view', 'compact')
        try:
            result = await anyio.to_thread.run_sync(partial(getattr(dataset, params.name), **arguments))
        except (DatasetError, TypeError) as error:
            return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text=_json({"error": str(error)}))])
        summary = f"{params.name}: snapshot {dataset.snapshot_id}. Data is in structuredContent."
        return types.CallToolResult(content=[types.TextContent(type="text", text=summary)], structured_content=result)

    return Server("gtnh-data", version="0.1.0", instructions=f"Canonical GTNH snapshot {dataset.snapshot_id} is immutable. {GUIDANCE}",
                  get_tool_input_schema=lambda name: OPERATIONS[name][1] if name in OPERATIONS else None,
                  on_list_tools=list_tools, on_call_tool=call_tool,
                  on_list_resources=list_resources, on_read_resource=read_resource)


async def run_stdio(dataset: Dataset):
    server = create_server(dataset)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
