"""Canonical artifact fixtures written through the documented file format."""

import gzip
import hashlib
import json
from pathlib import Path

COLLECTIONS = ("resources", "groups", "processes", "sources", "environments", "coverage")


def resource(id, *, metadata=0, nbt=None, registry_name=None):
    return {"id": id, "kind": "item", "registry_name": registry_name or f"test:{id}",
            "metadata": metadata, "nbt": nbt, "display_name": id, "provenance": {"owner": "fixture"}}


def choice(id, mode="exact", *, group=None, amount=1):
    match = {"mode": mode}
    if group is not None:
        match["group_id"] = group
    return {"resource_id": id, "amount": amount, "match": match}


def process(id, inputs, outputs, *, family="assembler", executable=True, conditions=None):
    return {"id": id, "family": family, "display_name": id, "inputs": inputs,
            "outputs": [{"resource_id": output, "amount": 1, "chance": {"numerator": 1, "denominator": 1}} for output in outputs],
            "duration_ticks": 20, "eu_per_tick": 8, "amperage": 1, "executable": executable,
            "conditions": conditions or {}, "provenance": {"owner": "fixture"}}


def slot(*choices, role="consume"):
    return {"role": role, "choices": list(choices)}


def snapshot(path, *, id="fixture", **collections):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    files = {}
    for collection in COLLECTIONS:
        rows = collections.get(collection, [])
        filename = f"{collection}.jsonl.gz"
        with gzip.open(path / filename, "wt", encoding="utf-8") as stream:
            for row in rows:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        files[filename] = {"sha256": hashlib.sha256((path / filename).read_bytes()).hexdigest(), "records": len(rows)}
    manifest = {"schema_version": 1, "snapshot_id": id, "created_at": "2026-10-11T00:00:00Z",
                "capture": {"exporter_version": "fixture"}, "pack": {"mods": []}, "files": files}
    (path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return path
