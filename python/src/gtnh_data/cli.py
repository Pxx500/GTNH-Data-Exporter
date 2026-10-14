"""Compact JSON CLI and transport launchers."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from .dataset import Dataset, DatasetError


def _json(value):
    """ASCII JSON preserves Unicode values on consoles with limited encodings."""
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True, allow_nan=False)


def parser():
    root = argparse.ArgumentParser(prog="gtnh-data", description="Query one canonical GTNH snapshot offline")
    commands = root.add_subparsers(dest="command", required=True)
    for name in ("import", "status", "flow-index", "rebuild-flow-index", "resources", "processes", "groups", "sources", "environments", "trace", "recycle", "chemistry", "loops", "boundary-profiles", "save-boundary-profile", "delete-boundary-profile", "resource-groups", "scope-catalog", "plan-to-bases", "audit-energy", "statistics", "acquisition", "serve", "mcp"):
        command = commands.add_parser(name)
        command.add_argument("--database", required=True, type=Path)
        if name == "import":
            command.add_argument("snapshot", type=Path)
        if name in ("recycle", "plan-to-bases", "audit-energy", "statistics", "save-boundary-profile"):
            command.add_argument("--request-file", type=Path, required=True, help="Structured Dataset operation JSON request")
        if name == "boundary-profiles":
            command.add_argument("profile_id", nargs="?")
        if name in ("save-boundary-profile", "delete-boundary-profile"):
            command.add_argument("profile_id")
        if name == "delete-boundary-profile":
            command.add_argument("--expected-revision", type=int)
        if name in ("chemistry", "acquisition"):
            command.add_argument("resource_id")
            if name == "acquisition":
                command.add_argument("--profile-id")
                command.add_argument("--max-depth", type=int, default=8)
                command.add_argument("--max-processes", type=int, default=200)
                command.add_argument("--max-variants", type=int, default=128)
                command.add_argument("--max-resources", type=int, default=512)
        if name == "loops":
            command.add_argument("--selections-file", type=Path)
            command.add_argument("--start-id", required=True)
            command.add_argument("--kind", choices=("any", "gaining", "lossy", "conserving"), default="any")
            command.add_argument("--chemical-kind", choices=("any", "balanced", "gaining", "lossy", "mixed", "unsupported"), default="any")
            command.add_argument("--yield-mode", choices=("guaranteed", "expected"), default="guaranteed")
            command.add_argument("--max-depth", type=int, default=6, help="Loop depth from 1 to 20")
            command.add_argument("--max-processes", type=int, default=200, help="Loop process bound from 1 to 1000")
            command.add_argument("--max-paths", type=int, default=20)
            command.add_argument("--max-states", type=int, default=5000, help="Loop state bound from 1 to 50000")
            command.add_argument("--min-tier", type=int)
            command.add_argument("--max-tier", type=int)
            command.add_argument("--unknown-tier-policy", choices=("exclude", "include"), default="exclude")
        if name in ("resources", "processes", "sources"):
            command.add_argument("id", nargs="?")
        if name == "groups":
            command.add_argument("id")
        if name in ("resources", "processes", "sources", "environments", "resource-groups"):
            command.add_argument("--offset", type=int, default=0)
            command.add_argument("--limit", type=int, default=50)
        if name in ("resources", "environments", "resource-groups"):
            command.add_argument("--q", default="")
        if name == "resources":
            command.add_argument("--kind", choices=("item", "fluid"))
            command.add_argument("--profile-id")
            command.add_argument("--scope-file", type=Path)
        if name == "processes":
            command.add_argument("--input-id")
            command.add_argument("--output-id")
            command.add_argument("--family")
        if name == "sources":
            command.add_argument("--resource-id")
            command.add_argument("--environment-id")
        if name == "trace":
            command.add_argument("--start-id", required=True)
            command.add_argument("--target-id", required=True)
            command.add_argument("--max-depth", type=int, default=12)
            command.add_argument("--max-processes", type=int, default=300)
            command.add_argument("--max-paths", type=int, default=8)
            command.add_argument("--max-extra-steps", type=int, default=6)
            command.add_argument("--path-selection", choices=("diverse", "shortest", "material"), default="diverse", help="Spread target ingredients, prefer fewest steps, or prioritize native material flow using the prepared index")
            command.add_argument("--view", choices=("full", "compact"), default="full", help="Keep every expanded match or return path anchors and declared choices with omission counts")
            command.add_argument("--required-resource-id", action="append", dest="required_resource_ids", default=[])
            command.add_argument("--excluded-resource-id", action="append", dest="excluded_resource_ids", default=[])
            command.add_argument("--exclude-group", action="append", dest="excluded_group_ids", default=[])
            command.add_argument("--min-tier", type=int)
            command.add_argument("--max-tier", type=int)
            command.add_argument("--unknown-tier-policy", choices=("exclude", "include"), default="exclude")
        if name == "serve":
            command.add_argument("--ui-dist", type=Path, default=Path(__file__).with_name("ui_dist"))
            command.add_argument("--port", type=int, default=8765)
    return root


def main(argv=None):
    arguments = vars(parser().parse_args(argv))
    command = arguments.pop("command")
    database = arguments.pop("database")
    try:
        if command == "import":
            result = Dataset.import_snapshot(arguments["snapshot"], database).status()
        else:
            dataset = Dataset(database)
            if command == "serve":
                import uvicorn
                from .http import create_app
                uvicorn.run(create_app(dataset, arguments["ui_dist"]), host="127.0.0.1", port=arguments["port"])
                return 0
            if command == "mcp":
                from .mcp import run_stdio
                asyncio.run(run_stdio(dataset))
                return 0
            if command in ("recycle", "plan-to-bases", "audit-energy", "statistics", "save-boundary-profile"):
                profile_id = arguments.get("profile_id")
                arguments = json.loads(arguments["request_file"].read_text(encoding="utf-8"))
                if not isinstance(arguments, dict):
                    raise DatasetError("Operation request must be a JSON object")
                operation = {"recycle": "plan_recycling", "plan-to-bases": "plan_to_bases", "audit-energy": "audit_energy", "statistics": "analyze_statistics", "save-boundary-profile": "save_boundary_profile"}[command]
                result = getattr(dataset, operation)(profile_id, **arguments) if command == "save-boundary-profile" else getattr(dataset, operation)(**arguments)
                print(_json(result))
                return 0
            if command == "resources":
                scope_file = arguments.pop("scope_file")
                if scope_file is not None:
                    arguments["scope"] = json.loads(scope_file.read_text(encoding='utf-8'))
            if command == "boundary-profiles":
                profile_id = arguments.pop("profile_id")
                result = dataset.list_boundary_profiles() if profile_id is None else dataset.get_boundary_profile(profile_id)
                print(_json(result))
                return 0
            if command == "delete-boundary-profile":
                print(_json(dataset.delete_boundary_profile(**arguments)))
                return 0
            if command == "loops":
                selections_file = arguments.pop("selections_file")
                if selections_file is not None:
                    arguments['selections'] = json.loads(selections_file.read_text(encoding='utf-8'))
            if command in ("resources", "processes", "sources") and arguments.get("id") is not None:
                operation = {"resources": "get_resource", "processes": "get_process", "sources": "get_source"}[command]
                arguments = {"id": arguments["id"]}
            else:
                if command in ("resources", "processes", "sources"):
                    arguments.pop("id", None)
                operation = {"status": "status", "flow-index": "flow_index_status", "rebuild-flow-index": "rebuild_flow_index", "resources": "find_resources", "processes": "find_processes", "groups": "get_group",
                             "sources": "find_sources", "environments": "find_environments", "trace": "trace_processes",
                             "chemistry": "inspect_chemistry", "acquisition": "inspect_acquisition", "loops": "find_loops", "resource-groups": "find_resource_groups", "scope-catalog": "get_scope_catalog"}[command]
            result = getattr(dataset, operation)(**arguments)
        print(_json(result))
        return 0
    except (DatasetError, OSError, json.JSONDecodeError, TypeError) as error:
        print(_json({"error": str(error)}), file=sys.stderr)
        return 2
