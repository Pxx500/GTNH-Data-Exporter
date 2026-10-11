"""Create a small synthetic snapshot for UI and transport checks, not pack data."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path


def write_snapshot(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=False)
    names = {
        "ore": "Iron ore", "dust": "Iron dust", "dust-alt": "Alternative iron dust",
        "ingot": "Iron ingot", "plate": "Iron plate", "double": "Double iron plate",
        "mold": "Plate mold", "stone": "Stone dust", "water": "Distilled water",
        "hydrogen": "Hydrogen", "oxygen": "Oxygen",
    }
    resources = [
        {"id": key, "kind": "fluid" if key in ("water", "hydrogen", "oxygen") else "item",
         "registry_name": f"example:{key}", "metadata": 0, "nbt": None,
         "display_name": name, "provenance": {"source": "synthetic example"}}
        for key, name in names.items()
    ]

    def ingredient(resource: str, amount: int = 1, role: str = "consume") -> dict:
        return {"role": role, "choices": [
            {"resource_id": resource, "amount": amount, "match": {"mode": "exact"}}
        ]}

    def output(resource: str, amount: int = 1, numerator: int = 1, denominator: int = 1) -> dict:
        return {"resource_id": resource, "amount": amount,
                "chance": {"numerator": numerator, "denominator": denominator}}

    def process(key: str, family: str, inputs: list, outputs: list) -> dict:
        return {"id": key, "family": family, "display_name": key, "inputs": inputs,
                "outputs": outputs, "duration_ticks": 100, "eu_per_tick": 16,
                "amperage": 1, "executable": True, "conditions": {},
                "provenance": {"source": "synthetic example"}}

    dust_group = {"role": "consume", "choices": [{"resource_id": None, "amount": 1,
                  "match": {"mode": "ore_dict", "group_id": "dustIron"}}]}
    processes = [
        process("crush-ore", "Macerator", [ingredient("ore")],
                [output("dust", 2), output("stone", 1, 1, 4)]),
        process("smelt-dust", "Furnace", [dust_group], [output("ingot")]),
        process("make-plate", "Bender", [ingredient("ingot"), ingredient("mold", role="presence")],
                [output("plate")]),
        process("make-double-plate", "Assembler", [ingredient("plate", 2)], [output("double")]),
        process("split-water", "Electrolyzer", [ingredient("water", 1000)],
                [output("hydrogen", 2000), output("oxygen", 1000)]),
        process("synthesize-water", "Chemical reactor", [ingredient("hydrogen", 2000),
                ingredient("oxygen", 1000)], [output("water", 1000)]),
    ]
    sources = [{"id": "iron-vein", "kind": "ore_vein", "display_name": "Example iron vein",
                "outputs": [{"resource_id": "ore", "material_role": "primary"}],
                "environment_ids": ["moon"], "status": "conditional",
                "conditions": {"stone": "example:moon_rock"},
                "parameters": {"min_y": 10, "max_y": 40, "weight": 20},
                "provenance": {"source": "synthetic example"}}]
    collections = {
        "resources": resources,
        "groups": [{"id": "dustIron", "kind": "ore_dict", "name": "dustIron",
                    "members": ["dust", "dust-alt"], "provenance": {"source": "synthetic example"}}],
        "processes": processes,
        "sources": sources,
        "environments": [{"id": "moon", "name": "Example Moon", "dimension_id": 42,
                          "provider": "example.MoonProvider", "properties": {},
                          "provenance": {"source": "synthetic example"}}],
        "coverage": [{"id": "example-only", "domain": "acquisition", "status": "partial",
                      "records": 1, "reason": "Synthetic example, not a GTNH capture",
                      "provenance": {"source": "synthetic example"}}],
    }
    files = {}
    for kind, records in collections.items():
        path = directory / f"{kind}.jsonl.gz"
        with gzip.open(path, "wt", encoding="utf-8", newline="\n") as stream:
            for record in records:
                stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
        files[path.name] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "records": len(records)}
    manifest = {"schema_version": 1, "snapshot_id": "synthetic-example-v1",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "capture": {"kind": "synthetic", "exporter_version": "example-v1"},
                "pack": {"name": "Synthetic example, not GTNH"}, "files": files}
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return directory


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    print(write_snapshot(parser.parse_args().directory))
