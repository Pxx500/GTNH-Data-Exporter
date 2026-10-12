"""Compact JSON CLI and transport launchers."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from .dataset import Dataset, DatasetError, _json


def parser():
    root = argparse.ArgumentParser(prog="gtnh-data", description="Query one canonical GTNH snapshot offline")
    commands = root.add_subparsers(dest="command", required=True)
    for name in ("import", "status", "resources", "processes", "groups", "sources", "environments", "trace", "recycle", "chemistry", "loops", "serve", "mcp"):
        command = commands.add_parser(name)
        command.add_argument("--database", required=True, type=Path)
        if name == "import":
            command.add_argument("snapshot", type=Path)
        if name == "recycle":
            command.add_argument("--request-file", type=Path, required=True, help="Structured Dataset.plan_recycling JSON request")
        if name == "chemistry":
            command.add_argument("resource_id")
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
        if name in ("resources", "processes", "sources", "environments"):
            command.add_argument("--offset", type=int, default=0)
            command.add_argument("--limit", type=int, default=50)
        if name in ("resources", "environments"):
            command.add_argument("--q", default="")
        if name == "resources":
            command.add_argument("--kind", choices=("item", "fluid"))
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
            command.add_argument("--max-extra-steps", type=int, default=2)
            command.add_argument("--required-resource-id", action="append", dest="required_resource_ids", default=[])
            command.add_argument("--excluded-resource-id", action="append", dest="excluded_resource_ids", default=[])
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
            if command == "recycle":
                arguments = json.loads(arguments["request_file"].read_text(encoding="utf-8"))
                if not isinstance(arguments, dict):
                    raise DatasetError("Recycling request must be a JSON object")
                result = dataset.plan_recycling(**arguments)
                print(_json(result))
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
                operation = {"status": "status", "resources": "find_resources", "processes": "find_processes", "groups": "get_group",
                             "sources": "find_sources", "environments": "find_environments", "trace": "trace_processes",
                             "chemistry": "inspect_chemistry", "loops": "find_loops"}[command]
            result = getattr(dataset, operation)(**arguments)
        print(_json(result))
        return 0
    except (DatasetError, OSError, json.JSONDecodeError, TypeError) as error:
        print(_json({"error": str(error)}), file=sys.stderr)
        return 2
