"""Compact JSON CLI and transport launchers."""

import argparse
import asyncio
import sys
from pathlib import Path

from .dataset import Dataset, DatasetError, _json


def parser():
    root = argparse.ArgumentParser(prog="gtnh-data", description="Query one canonical GTNH snapshot offline")
    commands = root.add_subparsers(dest="command", required=True)
    for name in ("import", "status", "resources", "processes", "groups", "sources", "environments", "trace", "serve", "mcp"):
        command = commands.add_parser(name)
        command.add_argument("--database", required=True, type=Path)
        if name == "import":
            command.add_argument("snapshot", type=Path)
        if name in ("resources", "processes"):
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
            if command in ("resources", "processes") and arguments.get("id") is not None:
                operation = "get_resource" if command == "resources" else "get_process"
                arguments = {"id": arguments["id"]}
            else:
                if command in ("resources", "processes"):
                    arguments.pop("id", None)
                operation = {"status": "status", "resources": "find_resources", "processes": "find_processes", "groups": "get_group",
                             "sources": "find_sources", "environments": "find_environments", "trace": "trace_processes"}[command]
            result = getattr(dataset, operation)(**arguments)
        print(_json(result))
        return 0
    except (DatasetError, OSError) as error:
        print(_json({"error": str(error)}), file=sys.stderr)
        return 2
