"""Canonical snapshot import and the one shared offline query owner."""

from __future__ import annotations

import gzip
import hashlib
import json
import math
import os
import re
import sqlite3
import tempfile
import threading
import unicodedata
from collections import deque
from contextlib import contextmanager
from functools import lru_cache
from fractions import Fraction
from heapq import heappop, heappush
from itertools import product
from pathlib import Path

COLLECTIONS = ("resources", "groups", "processes", "sources", "environments", "coverage")


class DatasetError(ValueError):
    """An invalid artifact, query or snapshot reference."""


def _json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True, allow_nan=False)


@lru_cache(maxsize=16384)
def _search_text(value):
    return "".join(char for char in unicodedata.normalize("NFD", value.lower()) if not unicodedata.combining(char))


@lru_cache(maxsize=16384)
def _search_words(value):
    return tuple(re.findall(r"[^\W_]+", _search_text(value)))


def _deletions(word):
    return {word, *(word[:index] + word[index + 1:] for index in range(len(word)))}


def _one_edit(left, right):
    if abs(len(left) - len(right)) > 1:
        return False
    if len(left) == len(right):
        mismatches = [index for index, pair in enumerate(zip(left, right)) if pair[0] != pair[1]]
        return len(mismatches) <= 1 or (len(mismatches) == 2 and mismatches[1] == mismatches[0] + 1
            and left[mismatches[0]] == right[mismatches[1]] and left[mismatches[1]] == right[mismatches[0]])
    shorter, longer = sorted((left, right), key=len)
    index = next((index for index, pair in enumerate(zip(shorter, longer)) if pair[0] != pair[1]), len(shorter))
    return shorter[index:] == longer[index + 1:]


class Dataset:
    """One snapshot, with a fresh read-only connection for every operation."""

    def __init__(self, database: str | Path):
        self.path = Path(database).resolve()
        self._search_vocabulary = None
        self._unification_preferences = None
        self._search_lock = threading.Lock()
        if not self.path.is_file():
            raise DatasetError(f"No imported dataset at {self.path}")
        with self._connect() as connection:
            row = connection.execute("SELECT value FROM metadata WHERE key='manifest'").fetchone()
            if row is None:
                raise DatasetError("Database has no snapshot manifest")
            self._manifest_json = row[0]
            self.snapshot_id = json.loads(row[0])["snapshot_id"]

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(f"{self.path.as_uri()}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        try:
            if hasattr(self, "snapshot_id"):
                row = connection.execute("SELECT value FROM metadata WHERE key='manifest'").fetchone()
                if row is None or row[0] != self._manifest_json:
                    raise DatasetError("Dataset was replaced. Open a new handle for its snapshot")
            yield connection
        except sqlite3.Error as exc:
            raise DatasetError(f"Cannot read dataset: {exc}") from exc
        finally:
            connection.close()

    @classmethod
    def import_snapshot(cls, source: str | Path, database: str | Path) -> Dataset:
        source, database = Path(source).resolve(), Path(database).resolve()
        try:
            manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"), parse_constant=cls._invalid_constant)
            cls._validate_manifest(manifest)
        except (OSError, ValueError, TypeError) as exc:
            raise DatasetError(f"Invalid manifest: {exc}") from exc
        database.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=f".{database.name}.", suffix=".tmp", dir=database.parent)
        os.close(descriptor)
        temporary = Path(temporary)
        connection = sqlite3.connect(temporary)
        try:
            cls._create_schema(connection)
            connection.execute("INSERT INTO metadata VALUES('manifest',?)", (_json(manifest),))
            for collection in COLLECTIONS:
                filename = f"{collection}.jsonl.gz"
                file = source / filename
                expected = manifest["files"][filename]
                with file.open("rb") as stream:
                    if hashlib.file_digest(stream, "sha256").hexdigest() != expected["sha256"]:
                        raise DatasetError(f"{filename}: checksum mismatch")
                count = 0
                with gzip.open(file, "rt", encoding="utf-8") as stream:
                    for count, line in enumerate(stream, 1):
                        try:
                            record = json.loads(line, parse_constant=cls._invalid_constant)
                            cls._validate_record(collection, record)
                            cls._insert_record(connection, collection, record)
                        except (ValueError, TypeError, KeyError, sqlite3.Error) as exc:
                            raise DatasetError(f"{filename}:{count}: {exc}") from exc
                if count != expected["records"]:
                    raise DatasetError(f"{filename}: record count mismatch ({count} != {expected['records']})")
            cls._validate_references(connection)
            connection.commit()
            connection.close()
            os.replace(temporary, database)
        except (OSError, ValueError, TypeError, sqlite3.Error, EOFError) as exc:
            raise DatasetError(f"Invalid snapshot: {exc}") from exc
        finally:
            connection.close()
            temporary.unlink(missing_ok=True)
        return cls(database)

    @staticmethod
    def _invalid_constant(value):
        raise DatasetError(f"Non-finite JSON number: {value}")

    @staticmethod
    def _validate_manifest(manifest):
        if not isinstance(manifest, dict) or type(manifest.get("schema_version")) is not int or manifest["schema_version"] != 1:
            raise DatasetError("schema_version must be 1")
        for key in ("snapshot_id", "created_at"):
            if not isinstance(manifest.get(key), str) or not manifest[key]:
                raise DatasetError(f"{key} must be a nonempty string")
        for key in ("capture", "pack", "files"):
            if not isinstance(manifest.get(key), dict):
                raise DatasetError(f"{key} must be an object")
        filenames = {f"{collection}.jsonl.gz" for collection in COLLECTIONS}
        if set(manifest["files"]) != filenames:
            raise DatasetError("files must describe exactly the six canonical gzip JSONL files")
        for filename, descriptor in manifest["files"].items():
            if not isinstance(descriptor, dict) or not re.fullmatch(r"[0-9a-f]{64}", str(descriptor.get("sha256", ""))):
                raise DatasetError(f"{filename}: invalid sha256")
            count = descriptor.get("records")
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise DatasetError(f"{filename}: records must be a nonnegative integer")

    @staticmethod
    def _number(value, name, *, nullable=False, integer=False):
        if value is None and nullable:
            return
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 or (integer and not isinstance(value, int)):
            raise DatasetError(f"{name} must be a nonnegative {'integer' if integer else 'number'}")

    @classmethod
    def _chance(cls, value, name):
        if value is None:
            return
        if not isinstance(value, dict) or "numerator" not in value or "denominator" not in value:
            raise DatasetError(f"{name} must be a rational chance or null")
        cls._number(value["numerator"], name, integer=True)
        cls._number(value["denominator"], name, integer=True)
        if value["denominator"] <= 0 or value["numerator"] > value["denominator"]:
            raise DatasetError(f"{name} must be between zero and one")

    @classmethod
    def _nbt(cls, tag):
        if tag is None:
            return
        if not isinstance(tag, dict) or "type" not in tag or "value" not in tag:
            raise DatasetError("NBT must be a typed tag or null")
        type, value = tag["type"], tag["value"]
        if type == "compound":
            if not isinstance(value, dict):
                raise DatasetError("NBT compound value must be an object")
            for child in value.values():
                if child is None:
                    raise DatasetError("NBT compound children must be typed tags")
                cls._nbt(child)
        elif type == "list":
            if not isinstance(value, list):
                raise DatasetError("NBT list value must be an array")
            for child in value:
                if child is None:
                    raise DatasetError("NBT list children must be typed tags")
                cls._nbt(child)
        elif type in ("byte_array", "int_array", "long_array"):
            if not isinstance(value, list) or any(isinstance(v, bool) or not isinstance(v, int) for v in value):
                raise DatasetError("NBT numeric arrays must contain integers")
        elif type == "string":
            if not isinstance(value, str):
                raise DatasetError("NBT string value must be a string")
        elif type == "long":
            if not isinstance(value, str) or not re.fullmatch(r"-?\d+", value):
                raise DatasetError("NBT long value must be a decimal string")
        elif type in ("byte", "short", "int"):
            if isinstance(value, bool) or not isinstance(value, int):
                raise DatasetError("NBT integer tag value must be an integer")
        elif type in ("float", "double"):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise DatasetError("NBT floating tag value must be finite")
        else:
            raise DatasetError(f"Unsupported typed NBT tag: {type}")

    @classmethod
    def _validate_record(cls, collection, record):
        fields = {
            "resources": ("kind", "registry_name", "metadata", "nbt", "display_name", "provenance"),
            "groups": ("kind", "name", "members", "provenance"),
            "processes": ("family", "display_name", "inputs", "outputs", "duration_ticks", "eu_per_tick", "amperage", "executable", "conditions", "provenance"),
            "sources": ("kind", "display_name", "outputs", "environment_ids", "status", "conditions", "parameters", "provenance"),
            "environments": ("name", "dimension_id", "provider", "properties", "provenance"),
            "coverage": ("domain", "status", "records", "reason", "provenance"),
        }
        if not isinstance(record, dict) or not isinstance(record.get("id"), str) or not record["id"]:
            raise DatasetError("record id must be a nonempty string")
        missing = [field for field in fields[collection] if field not in record]
        if missing:
            raise DatasetError(f"missing fields: {', '.join(missing)}")
        if not isinstance(record["provenance"], dict):
            raise DatasetError("provenance must be an object")
        if collection == "resources":
            if record["kind"] not in ("item", "fluid") or not isinstance(record["registry_name"], str) or not record["registry_name"]:
                raise DatasetError("resource kind and registry_name are required")
            metadata = record["metadata"]
            if metadata is not None and (isinstance(metadata, bool) or not isinstance(metadata, int)):
                raise DatasetError("metadata must be an integer or null")
            if record["kind"] == "item" and metadata is None:
                raise DatasetError("item metadata must be an integer")
            cls._nbt(record["nbt"])
        elif collection == "groups":
            if not isinstance(record["members"], list) or any(not isinstance(id, str) or not id for id in record["members"]):
                raise DatasetError("members must be resource IDs")
        elif collection == "processes":
            if record["executable"] not in (True, False, None) or (record["executable"] is not None and not isinstance(record["executable"], bool)):
                raise DatasetError("executable must be boolean or null")
            if not isinstance(record["conditions"], dict) or not isinstance(record["inputs"], list):
                raise DatasetError("conditions must be an object and inputs must be an array")
            for field in ("duration_ticks", "eu_per_tick", "amperage"):
                cls._number(record[field], field, nullable=True)
            for slot in record["inputs"]:
                if not isinstance(slot, dict) or slot.get("role") not in ("consume", "presence", "tool") or not isinstance(slot.get("choices"), list) or not slot["choices"]:
                    raise DatasetError("each input requires a role and nonempty choices")
                cls._chance(slot.get("consumption_chance"), "consumption_chance")
                for choice in slot["choices"]:
                    if not isinstance(choice, dict) or not isinstance(choice.get("match"), dict):
                        raise DatasetError("choice match must be an object")
                    if "resource_id" not in choice or (choice["resource_id"] is not None and (not isinstance(choice["resource_id"], str) or not choice["resource_id"])):
                        raise DatasetError("choice resource_id must be a nonempty ID or null")
                    cls._number(choice.get("amount"), "choice amount")
                    cls._chance(choice.get("consumption_chance"), "consumption_chance")
                    match = choice["match"]
                    if match.get("mode") not in ("exact", "wildcard", "ore_dict", "unified", "native_unknown"):
                        raise DatasetError("unsupported match mode")
                    if "group_id" in match and (not isinstance(match["group_id"], str) or not match["group_id"]):
                        raise DatasetError("group_id must be a nonempty ID")
                    if "nbt_sensitive" in match and not isinstance(match["nbt_sensitive"], bool):
                        raise DatasetError("nbt_sensitive must be boolean")
                    if match["mode"] in ("exact", "wildcard") and not isinstance(choice.get("resource_id"), str):
                        raise DatasetError("exact/wildcard choices require resource_id")
                    if match["mode"] == "ore_dict" and not isinstance(match.get("group_id"), str):
                        raise DatasetError("ore_dict choices require group_id")
        elif collection == "sources":
            if record["status"] not in ("active", "conditional", "disabled", "unknown"):
                raise DatasetError("invalid acquisition status")
            if not isinstance(record["environment_ids"], list) or any(not isinstance(id, str) for id in record["environment_ids"]):
                raise DatasetError("environment_ids must be an array of IDs")
            if not isinstance(record["conditions"], dict) or not isinstance(record["parameters"], dict):
                raise DatasetError("source conditions/parameters must be objects")
        elif collection == "environments":
            if record["dimension_id"] is not None and (isinstance(record["dimension_id"], bool) or not isinstance(record["dimension_id"], int)):
                raise DatasetError("dimension_id must be an integer or null")
            if record["provider"] is not None and not isinstance(record["provider"], str):
                raise DatasetError("provider must be a string or null")
            if not isinstance(record["properties"], dict):
                raise DatasetError("environment properties must be an object")
        elif collection == "coverage":
            if record["status"] not in ("complete", "partial", "unsupported", "error"):
                raise DatasetError("invalid coverage status")
            cls._number(record["records"], "records", integer=True)
        if collection in ("processes", "sources"):
            if not isinstance(record["outputs"], list):
                raise DatasetError("outputs must be an array")
            for output in record["outputs"]:
                if not isinstance(output, dict) or not isinstance(output.get("resource_id"), str):
                    raise DatasetError("outputs require resource_id")
                if collection == "processes" or "amount" in output:
                    cls._number(output.get("amount"), "output amount", nullable=collection == "sources")
                if collection == "processes" and "chance" not in output:
                    raise DatasetError("process output chance is required, use null when unknown")
                cls._chance(output.get("chance"), "output chance")
        if collection == 'sources':
            cls._validate_source_rule(record)

    @classmethod
    def _validate_source_rule(cls, source):
        rule = source['parameters'].get('output_rule')
        marked = any(output.get('resource_semantics') == 'mined_item_rule_candidate' for output in source['outputs'])
        if 'output_rule' not in source['parameters']:
            if marked:
                raise DatasetError('Rule candidates require output_rule')
            return
        if not isinstance(rule, dict) or rule.get('kind') != 'gt_small_ore_fortune0' or type(rule.get('version')) is not int or rule['version'] != 1:
            raise DatasetError('Unsupported source output_rule kind/version')
        if source['kind'] != 'ore_mining' or source['status'] != 'conditional' or not source['conditions']:
            raise DatasetError('Small ore rule requires a conditional ore_mining source with harvest conditions')
        if rule.get('scope') != 'per_qualifying_native_base_harvest' or rule.get('evaluation_order') != ['primary', 'host']:
            raise DatasetError('Invalid small ore rule scope/evaluation order')
        for field in ('generated_source_id', 'generated_resource_id'):
            if not isinstance(source['parameters'].get(field), str) or not source['parameters'][field]:
                raise DatasetError(f'Small ore rule requires {field}')
        primary = rule.get('primary')
        if not isinstance(primary, dict) or primary.get('kind') != 'weighted_draws_with_replacement' or primary.get('empty_pool_behavior') != 'emit_nothing':
            raise DatasetError('Invalid small ore primary draw rule')
        for field in ('draw_count', 'total_weight'):
            cls._number(primary.get(field), field, integer=True)
        if primary['draw_count'] < 1 or type(primary.get('amount_per_draw')) is not int or primary['amount_per_draw'] != 1:
            raise DatasetError('Small ore draws require positive draw_count and amount_per_draw 1')
        candidates = primary.get('candidates')
        if not isinstance(candidates, list):
            raise DatasetError('Small ore primary candidates must be an array')
        support, weight = set(), 0
        for candidate in candidates:
            if not isinstance(candidate, dict) or not isinstance(candidate.get('resource_id'), str) or not candidate['resource_id']:
                raise DatasetError('Small ore candidates require resource IDs')
            cls._number(candidate.get('weight'), 'candidate weight', integer=True)
            if candidate['weight'] < 1 or candidate['resource_id'] in support:
                raise DatasetError('Candidate weights must be positive, with distinct resolved resource IDs')
            support.add(candidate['resource_id'])
            weight += candidate['weight']
        if weight != primary['total_weight']:
            raise DatasetError('Small ore candidate weights must sum to total_weight')
        host = rule.get('host')
        if not isinstance(host, dict) or host.get('kind') != 'exclusive_choice' or not isinstance(host.get('outcomes'), list) or not host['outcomes']:
            raise DatasetError('Invalid small ore exclusive host rule')

        def probability(value):
            if not isinstance(value, dict):
                raise DatasetError('Host probability must be a rational chance')
            cls._chance(value, 'host probability')
            return Fraction(value['numerator'], value['denominator'])

        expected = {'none': Fraction(2, 3), 'pure': Fraction(1, 9), 'impure': Fraction(2, 9)}
        seen_cases, host_resources, total_probability = set(), set(), Fraction(0)
        for outcome in host['outcomes']:
            if not isinstance(outcome, dict) or not isinstance(outcome.get('native_cases'), list) or not outcome['native_cases']:
                raise DatasetError('Host outcomes require native_cases')
            cases, combined = set(), Fraction(0)
            for native_case in outcome['native_cases']:
                if not isinstance(native_case, dict) or not isinstance(native_case.get('case'), str) or native_case['case'] not in expected:
                    raise DatasetError('Unknown small ore host case')
                name = native_case['case']
                if name in seen_cases or probability(native_case.get('probability')) != expected[name]:
                    raise DatasetError('Host cases must appear once with their exact native probabilities')
                seen_cases.add(name)
                cases.add(name)
                combined += expected[name]
            outer = probability(outcome.get('probability'))
            if outer != combined:
                raise DatasetError('Host outcome probability must equal its native case probabilities')
            total_probability += outer
            outputs = outcome.get('outputs')
            if not isinstance(outputs, list):
                raise DatasetError('Host outcome outputs must be an array')
            if 'none' in cases:
                if cases != {'none'} or outputs:
                    raise DatasetError('The no-dust host case must emit nothing')
            else:
                if len(outputs) != 1 or not isinstance(outputs[0], dict) or not isinstance(outputs[0].get('resource_id'), str) or not outputs[0]['resource_id']:
                    raise DatasetError('Each dust host outcome requires one resource')
                output = outputs[0]
                if type(output.get('amount')) is not int or output['amount'] != 1 or output['resource_id'] in host_resources:
                    raise DatasetError('Host dust amount must be 1 and equal dust identities must be grouped')
                host_resources.add(output['resource_id'])
                support.add(output['resource_id'])
        if seen_cases != set(expected) or total_probability != 1:
            raise DatasetError('Host outcomes must cover all native cases with total probability 1')
        declared = [output['resource_id'] for output in source['outputs']]
        if len(declared) != len(set(declared)) or set(declared) != support:
            raise DatasetError('Small ore candidate outputs must exactly match the rule resource support')
        if any(output.get('resource_semantics') != 'mined_item_rule_candidate' or 'amount' in output or 'chance' in output for output in source['outputs']):
            raise DatasetError('Small ore candidate outputs require the rule marker without independent amount/chance')

    @staticmethod
    def _validate_references(connection):
        checks = (
            ("members", "resource_id", "resources"), ("inputs", "resource_id", "resources"),
            ("inputs", "group_id", "groups"), ("outputs", "resource_id", "resources"),
            ("source_outputs", "resource_id", "resources"), ("source_environments", "environment_id", "environments"),
        )
        for table, column, collection in checks:
            row = connection.execute(f"SELECT {column} FROM {table} WHERE {column} IS NOT NULL AND NOT EXISTS (SELECT 1 FROM records WHERE collection=? AND id={table}.{column}) LIMIT 1", (collection,)).fetchone()
            if row is not None:
                raise DatasetError(f"Unresolved {collection} reference: {row[0]}")
        for row in connection.execute("SELECT payload FROM records WHERE collection='sources' AND json_extract(payload,'$.parameters.output_rule.kind')='gt_small_ore_fortune0'"):
            source = json.loads(row[0])
            for field, collection in (('generated_source_id', 'sources'), ('generated_resource_id', 'resources')):
                id = source['parameters'][field]
                if connection.execute('SELECT 1 FROM records WHERE collection=? AND id=?', (collection, id)).fetchone() is None:
                    raise DatasetError(f'Unresolved {collection} reference: {id}')
            for output in source['outputs']:
                if connection.execute('SELECT kind FROM resources WHERE id=?', (output['resource_id'],)).fetchone()[0] != 'item':
                    raise DatasetError('Small ore rule candidates must reference item resources')

    @staticmethod
    def _create_schema(connection):
        connection.executescript("""
            CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE records(collection TEXT NOT NULL, id TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(collection,id));
            CREATE TABLE resources(id TEXT PRIMARY KEY, kind TEXT, registry_name TEXT, metadata INTEGER, nbt TEXT);
            CREATE INDEX resource_identity ON resources(kind,registry_name,metadata,nbt);
            CREATE TABLE members(group_id TEXT, resource_id TEXT, PRIMARY KEY(group_id,resource_id));
            CREATE INDEX member_resource ON members(resource_id,group_id);
            CREATE TABLE inputs(process_id TEXT, slot INTEGER, choice INTEGER, resource_id TEXT, mode TEXT, group_id TEXT, role TEXT, nbt_sensitive INTEGER);
            CREATE INDEX input_resource ON inputs(resource_id,process_id);
            CREATE INDEX input_group ON inputs(group_id,process_id);
            CREATE INDEX input_process ON inputs(process_id);
            CREATE TABLE outputs(process_id TEXT, resource_id TEXT);
            CREATE INDEX output_resource ON outputs(resource_id,process_id);
            CREATE TABLE source_outputs(source_id TEXT, resource_id TEXT);
            CREATE INDEX source_resource ON source_outputs(resource_id,source_id);
            CREATE TABLE source_environments(source_id TEXT, environment_id TEXT);
            CREATE INDEX source_environment ON source_environments(environment_id,source_id);
            CREATE VIRTUAL TABLE search USING fts5(collection UNINDEXED, id UNINDEXED, text);
        """)

    @staticmethod
    def _insert_record(connection, collection, record):
        id = record["id"]
        connection.execute("INSERT INTO records VALUES(?,?,?)", (collection, id, _json(record)))
        if collection == "resources":
            connection.execute("INSERT INTO resources VALUES(?,?,?,?,?)", (id, record["kind"], record["registry_name"], record.get("metadata"), _json(record.get("nbt"))))
        elif collection == "groups":
            connection.executemany("INSERT INTO members VALUES(?,?)", ((id, member) for member in record["members"]))
        elif collection == "processes":
            for slot, input in enumerate(record["inputs"]):
                for choice, entry in enumerate(input["choices"]):
                    match = entry["match"]
                    nbt_sensitive = match.get("nbt_sensitive", True if match["mode"] in ("exact", "wildcard") else None)
                    connection.execute("INSERT INTO inputs VALUES(?,?,?,?,?,?,?,?)", (id, slot, choice, entry.get("resource_id"), match["mode"], match.get("group_id"), input["role"], nbt_sensitive))
            connection.executemany("INSERT INTO outputs VALUES(?,?)", ((id, entry["resource_id"]) for entry in record["outputs"]))
        elif collection == "sources":
            connection.executemany("INSERT INTO source_outputs VALUES(?,?)", ((id, entry["resource_id"]) for entry in record["outputs"]))
            connection.executemany("INSERT INTO source_environments VALUES(?,?)", ((id, entry) for entry in record["environment_ids"]))
        if collection in ("resources", "processes", "environments"):
            text = " ".join(str(record.get(key) or "") for key in ("id", "display_name", "registry_name", "name", "family", "provider"))
            connection.execute("INSERT INTO search VALUES(?,?,?)", (collection, id, text))

    @staticmethod
    def _pagination(offset, limit):
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            raise DatasetError("offset must be a nonnegative integer")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
            raise DatasetError("limit must be between 1 and 500")

    def _record(self, connection, collection, id):
        row = connection.execute("SELECT payload FROM records WHERE collection=? AND id=?", (collection, id)).fetchone()
        if row is None:
            raise DatasetError(f"Unknown {collection} ID: {id}")
        return json.loads(row[0])

    def _get(self, collection, id):
        with self._connect() as connection:
            return {"snapshot_id": self.snapshot_id, "item": self._record(connection, collection, id)}

    def get_resource(self, id):
        return self._get("resources", id)

    def get_process(self, id):
        return self._get("processes", id)

    def get_group(self, id):
        return self._get("groups", id)

    def get_source(self, id):
        return self._get("sources", id)

    def _page(self, connection, collection, where="1", parameters=(), *, offset=0, limit=50):
        self._pagination(offset, limit)
        clause = f"collection=? AND ({where})"
        values = (collection, *parameters)
        total = connection.execute(f"SELECT COUNT(*) FROM records WHERE {clause}", values).fetchone()[0]
        rows = connection.execute(f"SELECT payload FROM records WHERE {clause} ORDER BY id LIMIT ? OFFSET ?", (*values, limit, offset))
        return {"snapshot_id": self.snapshot_id, "items": [json.loads(row[0]) for row in rows], "total": total, "offset": offset, "limit": limit}

    @staticmethod
    def _search_clause(q):
        tokens = re.findall(r"\w+", q, flags=re.UNICODE)
        if not tokens:
            return "1", ()
        expression = " AND ".join('"' + token + '"*' for token in tokens)
        return "id IN (SELECT id FROM search WHERE collection=records.collection AND search MATCH ?)", (expression,)

    def status(self):
        with self._connect() as connection:
            counts = {collection: connection.execute("SELECT COUNT(*) FROM records WHERE collection=?", (collection,)).fetchone()[0] for collection in COLLECTIONS}
            coverage = [json.loads(row[0]) for row in connection.execute("SELECT payload FROM records WHERE collection='coverage' ORDER BY id")]
            return {"snapshot_id": self.snapshot_id, "manifest": json.loads(self._manifest_json), "counts": counts, "coverage": coverage}

    def find_resources(self, *, q="", kind=None, offset=0, limit=50, scope=None, profile_id=None):
        if kind not in (None, "item", "fluid"):
            raise DatasetError("kind must be item or fluid")
        self._pagination(offset, limit)
        tokens = _search_words(q)
        scope = self._profile_scope(scope, profile_id)
        with self._connect() as connection:
            scoped_clause, scoped_values = self._scope_clause(connection, scope)
            if not tokens:
                clause = "json_extract(payload,'$.kind')=?" if kind else "1"
                page = self._page(connection, "resources", clause + ' AND ' + scoped_clause,
                    ((kind,) if kind else ()) + scoped_values, offset=offset, limit=limit)
                return self._acquisition_page(connection, page)
            alternatives = self._resource_search_terms(connection, tokens)
            expression = " AND ".join("(" + " OR ".join(f'"{word}"*' for word in sorted(words)) + ")" for words in alternatives)
            clause = "search MATCH ? AND search.collection='resources'"
            parameters = (expression,)
            if kind:
                clause += " AND resources.kind=?"
                parameters += (kind,)
            tables = "search JOIN resources ON resources.id=search.id JOIN records ON records.collection='resources' AND records.id=search.id"
            clause += ' AND ' + re.sub(r'\bid\b', 'records.id', scoped_clause).replace('payload', 'records.payload')
            parameters += scoped_values
            total = connection.execute(f"SELECT COUNT(*) FROM {tables} WHERE {clause}", parameters).fetchone()[0]
            connection.create_function("resource_search_rank", 4, self._resource_search_rank(q, tokens, alternatives), deterministic=True)
            from .acquisition import acquisition_rank, unification_preferences
            with self._search_lock:
                if self._unification_preferences is None:
                    self._unification_preferences = unification_preferences(connection)
            connection.create_function('resource_acquisition_rank', 1,
                lambda id: acquisition_rank(self._unification_preferences.get(id, {})), deterministic=True)
            rows = connection.execute(f"""SELECT records.payload FROM {tables} WHERE {clause}
                ORDER BY resource_search_rank(resources.id,resources.registry_name,json_extract(records.payload,'$.display_name'),search.text),resource_acquisition_rank(resources.id),resources.id
                LIMIT ? OFFSET ?""", (*parameters, limit, offset))
            return self._acquisition_page(connection, {"snapshot_id": self.snapshot_id, "items": [json.loads(row[0]) for row in rows], "total": total, "offset": offset, "limit": limit})

    def _acquisition_page(self, connection, page):
        from .acquisition import summarize_acquisition
        analysis = summarize_acquisition(connection, [r['id'] for r in page['items']], snapshot_id=self.snapshot_id)
        for item in page['items']:
            item['acquisition_analysis'] = analysis['resources'][item['id']]
        return page

    def _profile_scope(self, scope, profile_id):
        if profile_id is not None:
            if scope is not None:
                raise DatasetError('Specify scope or profile_id, not both')
            scope = self.get_boundary_profile(profile_id)['item']['scope']
        return scope

    def _scope_clause(self, connection, scope):
        keys = ('excluded_resource_ids', 'excluded_group_ids', 'excluded_namespaces', 'excluded_family_ids')
        if scope is None:
            scope = {}
        if not isinstance(scope, dict) or set(scope) - set(keys):
            raise DatasetError('Invalid analysis scope')
        clauses, values = ['1'], ()
        for key in keys:
            entries = scope.get(key, [])
            if not isinstance(entries, list) or any(not isinstance(v, str) or not v for v in entries):
                raise DatasetError(f'{key} must be an array of nonempty strings')
            if len(entries) > 1000:
                raise DatasetError(f'{key} exceeds 1000 entries')
            for entry in sorted(set(entries)):
                if key == 'excluded_resource_ids':
                    self._record(connection, 'resources', entry)
                    clauses.append('id != ?')
                    values += (entry,)
                elif key == 'excluded_group_ids':
                    self._record(connection, 'groups', entry)
                    clauses.append('id NOT IN (SELECT resource_id FROM members WHERE group_id=?)')
                    values += (entry,)
                elif key == 'excluded_namespaces':
                    clauses.append("substr(json_extract(payload,'$.registry_name'),1,instr(json_extract(payload,'$.registry_name'),':')-1) != ?")
                    values += (entry,)
        return ' AND '.join(clauses), values

    def find_resource_groups(self, *, q='', limit=20, offset=0):
        if not isinstance(q, str):
            raise DatasetError('q must be a string')
        escaped = q.strip().replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        where = "(id LIKE ? ESCAPE '\\' OR json_extract(payload,'$.name') LIKE ? ESCAPE '\\')" if escaped else '1'
        values = ('%' + escaped + '%',) * 2 if escaped else ()
        with self._connect() as connection:
            result = self._page(connection, 'groups', where, values, offset=offset, limit=limit)
            for item in result['items']:
                item['member_count'] = connection.execute('SELECT COUNT(*) FROM members WHERE group_id=?', (item['id'],)).fetchone()[0]
            return result

    def get_scope_catalog(self):
        with self._connect() as connection:
            namespaces = [{'id': row[0], 'resources': row[1]} for row in connection.execute("SELECT substr(registry_name,1,instr(registry_name,':')-1) AS ns,COUNT(*) FROM resources WHERE instr(registry_name,':')>0 GROUP BY ns ORDER BY ns")]
            families = [{'id': row[0], 'processes': row[1]} for row in connection.execute("SELECT json_extract(payload,'$.family') AS family,COUNT(*) FROM records WHERE collection='processes' GROUP BY family ORDER BY family")]
            fluid_unknown = connection.execute("SELECT COUNT(*) FROM resources WHERE instr(registry_name,':')=0").fetchone()[0]
            return {'snapshot_id': self.snapshot_id, 'namespaces': namespaces, 'families': families,
                    'unknown_namespace_count': fluid_unknown}

    def _profiles(self):
        path = self.path.with_name(self.path.name + '.boundary-profiles.json')
        with self._connect():
            pass
        if not path.exists():
            return {'schema_version': 1, 'snapshot_id': self.snapshot_id, 'profiles': []}
        try:
            value = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc:
            raise DatasetError(f'Cannot read boundary profiles: {exc}') from exc
        if value.get('schema_version') != 1 or value.get('snapshot_id') != self.snapshot_id or not isinstance(value.get('profiles'), list):
            raise DatasetError('Boundary profiles belong to another snapshot or have an unsupported format')
        return value

    def list_boundary_profiles(self):
        return {'snapshot_id': self.snapshot_id, 'items': self._profiles()['profiles']}

    def get_boundary_profile(self, profile_id):
        for profile in self._profiles()['profiles']:
            if profile['id'] == profile_id:
                return {'snapshot_id': self.snapshot_id, 'item': profile}
        raise DatasetError(f'Unknown boundary profile: {profile_id}')

    def _write_profile(self, profile_id, profile, expected_revision):
        path = self.path.with_name(self.path.name + '.boundary-profiles.json')
        lock = path.with_suffix(path.suffix + '.lock')
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise DatasetError('Boundary profiles are being edited by another request') from exc
        os.close(fd)
        temporary = None
        try:
            value = self._profiles()
            old = next((p for p in value['profiles'] if p['id'] == profile_id), None)
            revision = old['revision'] if old else 0
            if expected_revision is not None and (type(expected_revision) is not int or expected_revision != revision):
                raise DatasetError('Boundary profile revision changed')
            value['profiles'] = [p for p in value['profiles'] if p['id'] != profile_id]
            if profile is not None:
                profile['revision'] = revision + 1
                value['profiles'].append(profile)
                value['profiles'].sort(key=lambda p: p['id'])
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as stream:
                temporary = stream.name
                stream.write(_json(value))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
            temporary = None
            return {'snapshot_id': self.snapshot_id, 'item': profile}
        finally:
            if temporary is not None:
                Path(temporary).unlink(missing_ok=True)
            lock.unlink(missing_ok=True)

    def save_boundary_profile(self, profile_id, *, name, base_resource_ids, scope=None, expected_revision=None):
        if not isinstance(profile_id, str) or not profile_id or len(profile_id) > 100 or not isinstance(name, str) or not name.strip():
            raise DatasetError('Profile ID and name must be nonempty strings')
        with self._connect() as connection:
            feeds = self._resource_ids(connection, base_resource_ids, 'base_resource_ids')
            clause, values = self._scope_clause(connection, scope)
            scoped = {row[0] for row in connection.execute("SELECT id FROM records WHERE collection='resources' AND " + clause, values)}
            if not feeds <= scoped:
                raise DatasetError('Base resources must be inside the profile scope')
        return self._write_profile(profile_id, {'id': profile_id, 'name': name.strip(),
            'base_resource_ids': sorted(feeds), 'scope': scope or {},
            'semantics': 'assumed_external_feed_not_inventory_or_generation'}, expected_revision)

    def delete_boundary_profile(self, profile_id, *, expected_revision=None):
        self.get_boundary_profile(profile_id)
        return self._write_profile(profile_id, None, expected_revision)

    def _resource_ids(self, connection, ids, name):
        if not isinstance(ids, (list, set, tuple)) or len(ids) > 1000 or any(not isinstance(id, str) for id in ids):
            raise DatasetError(f'{name} must contain at most 1000 resource IDs')
        for id in ids:
            self._record(connection, 'resources', id)
        return set(ids)

    def discover_network(self, target_id, *, allowed_feed_ids, selections=None, scope=None, max_depth=8,
                         max_processes=200, max_variants=128, max_resources=512,
                         min_tier=None, max_tier=None, unknown_tier_policy='exclude', preferred_process_ids=None):
        for key, value, maximum in (('max_depth', max_depth, 20), ('max_processes', max_processes, 1000),
                                    ('max_variants', max_variants, 512), ('max_resources', max_resources, 2000)):
            if type(value) is not int or not 1 <= value <= maximum:
                raise DatasetError(f'{key} must be between 1 and {maximum}')
        if selections is not None and (not isinstance(selections, dict) or any(not isinstance(v, dict) for v in selections.values())):
            raise DatasetError('selections must map process IDs to slot selections')
        selections = selections or {}
        tiers = self._tier_filter(min_tier, max_tier, unknown_tier_policy)
        variants, records, resources, groups = [], {}, {}, {}
        counts, examples, reasons = {}, [], set()
        work, work_limit, examined = 0, 50000, 0
        def exclude(reason, id):
            counts[reason] = counts.get(reason, 0) + 1
            if len(examples) < 50:
                examples.append({'reason': reason, 'id': id})
        with self._connect() as connection:
            self._record(connection, 'resources', target_id)
            feeds = self._resource_ids(connection, allowed_feed_ids, 'allowed_feed_ids')
            if len(feeds | {target_id}) > max_resources:
                raise DatasetError('max_resources must accommodate the target and all allowed feeds')
            clause, values = self._scope_clause(connection, scope)
            allowed = {r[0] for r in connection.execute("SELECT id FROM records WHERE collection='resources' AND " + clause, values)}
            if target_id not in allowed or not feeds <= allowed:
                raise DatasetError('Target and allowed feeds must be inside the analysis scope')
            for pid in selections:
                self._record(connection, 'processes', pid)
            preferred = list(preferred_process_ids or [])
            for pid in preferred:
                self._record(connection, 'processes', pid)
            queue, seen, choice_cache = deque([(target_id, 0, None)]), {target_id}, {}
            included = {target_id} | feeds
            deferred = deque()
            coproducts = set()
            checked = set()
            while queue and not reasons & {'candidate_process_limit', 'candidate_variant_limit', 'candidate_work_limit', 'candidate_resource_limit'}:
                rid, depth, rows = queue.popleft()
                resources[rid] = self._record(connection, 'resources', rid)
                if rid in feeds:
                    continue
                if depth >= max_depth:
                    reasons.add('candidate_depth')
                    continue
                if rows is None:
                    priority = 'CASE id ' + ''.join('WHEN ? THEN 0 ' for _ in preferred) + 'ELSE 1 END,' if preferred else ''
                    feed_priority = "CASE WHEN id IN (SELECT process_id FROM inputs WHERE resource_id IN (" + ','.join('?' for _ in feeds) + ")) THEN 0 ELSE 1 END," if feeds else ''
                    closure = "CASE WHEN id IN (SELECT process_id FROM inputs WHERE resource_id IN (" + ','.join('?' for _ in coproducts) + ")) THEN 0 ELSE 1 END," if coproducts else ''
                    ranks = feed_priority + closure if rid == target_id else closure + feed_priority
                    ranked_ids = (*sorted(feeds), *sorted(coproducts)) if rid == target_id else (*sorted(coproducts), *sorted(feeds))
                    rows = iter(connection.execute("SELECT id,payload FROM records WHERE collection='processes' AND id IN (SELECT process_id FROM outputs WHERE resource_id=?) ORDER BY " + priority + ranks + "json_array_length(payload,'$.inputs'),id", (rid, *preferred, *ranked_ids)))
                row = next(rows, None)
                if row is None:
                    continue
                queue.append((rid, depth, rows))
                for row in (row,):
                    pid = row['id']
                    if pid in checked:
                        continue
                    checked.add(pid)
                    examined += 1
                    work += 1
                    if work > work_limit:
                        reasons.add('candidate_work_limit')
                        break
                    p = json.loads(row['payload'])
                    if not any(o['resource_id'] == rid and self._positive_output(o) for o in p['outputs']):
                        continue
                    if any(o['resource_id'] not in allowed for o in p['outputs']):
                        exclude('output_resource_scope', pid)
                        continue
                    if p['executable'] is not True or p['conditions'].get('dynamic_inputs') == 'unresolved' or p['conditions'].get('dynamic_output') == 'unresolved' or p['conditions'].get('enabled') is False or p['conditions'].get('fake') is True:
                        exclude('unsupported_process', pid)
                        continue
                    if p['family'] in (scope or {}).get('excluded_family_ids', []):
                        exclude('family_scope', pid)
                        continue
                    if not self._tier_allowed(p, tiers):
                        exclude('tier', pid)
                        continue
                    options, invalid = [], False
                    if set(selections.get(pid, {})) - {str(si) for si in range(len(p['inputs']))}:
                        raise DatasetError('Unknown network input slot')
                    for si, slot in enumerate(p['inputs']):
                        available = []
                        requested = selections.get(pid, {}).get(str(si))
                        if requested is not None and (not isinstance(requested, dict) or set(requested) != {'choice_index', 'resource_id'} or type(requested['choice_index']) is not int or not isinstance(requested['resource_id'], str)):
                            raise DatasetError('Invalid network input selection')
                        for ci, c in enumerate(slot['choices']):
                            if requested is not None and ci != requested['choice_index']:
                                continue
                            key = _json({'id': c.get('resource_id'), 'match': c['match']})
                            if key not in choice_cache:
                                m = c['match']
                                choice_cache[key] = self._choice_resources(connection, c) if m['mode'] != 'native_unknown' and (m['mode'] not in ('unified', 'ore_dict') or m.get('group_id')) else []
                                work += len(choice_cache[key])
                            for concrete in choice_cache[key]:
                                if requested is not None and concrete != requested['resource_id']:
                                    continue
                                if concrete not in allowed:
                                    exclude('resource_scope', concrete)
                                    continue
                                available.append({'choice_index': ci, 'resource_id': concrete})
                        if requested is not None and not available:
                            raise DatasetError('Selected network input does not match its declared predicate or scope')
                        if not available:
                            invalid = True
                            exclude('unresolved_input', pid)
                            break
                        options.append(available)
                    if work > work_limit:
                        reasons.add('candidate_work_limit')
                        break
                    if invalid:
                        continue
                    if len(records) >= max_processes:
                        reasons.add('candidate_process_limit')
                        break
                    # First admit one complete producer variant. Defer its remaining OR
                    # variants so one ore group cannot consume the whole closure budget.
                    for si, option in enumerate(options):
                        option.sort(key=lambda c: (c['resource_id'] != p['inputs'][si]['choices'][c['choice_index']].get('resource_id'), c['choice_index'], c['resource_id']))
                    combinations = iter(product(*options))
                    first = next(combinations)
                    deferred.append((p, combinations, depth))
                    for selected in (first,):
                        if len(variants) >= max_variants:
                            reasons.add('candidate_variant_limit')
                            break
                        candidate_resources = {c['resource_id'] for c in selected} | {o['resource_id'] for o in p['outputs']}
                        if len(included | candidate_resources) > max_resources:
                            reasons.add('candidate_resource_limit')
                            break
                        included.update(candidate_resources)
                        accounting = json.loads(_json(p))
                        for si, c in enumerate(selected):
                            accounting['inputs'][si]['choices'][c['choice_index']].update(resource_id=c['resource_id'], match={'mode': 'exact', 'nbt_sensitive': True})
                        variant = {'variant_id': f'{pid}:v0', 'process_id': pid,
                            'process': accounting, 'selections': {str(si): c for si, c in enumerate(selected)}}
                        variants.append(variant)
                        records[pid] = p
                        coproducts.update(o['resource_id'] for o in p['outputs'] if self._positive_output(o))
                        for si, c in enumerate(selected):
                            child = c['resource_id']
                            if child not in seen:
                                seen.add(child)
                                queue.append((child, depth + 1, None))
                        if 'candidate_resource_limit' in reasons:
                            break
                    if reasons & {'candidate_variant_limit', 'candidate_resource_limit'}:
                        break
                    break
            while deferred and len(variants) < max_variants and not reasons & {'candidate_process_limit', 'candidate_work_limit', 'candidate_resource_limit'}:
                p, combinations, depth = deferred.popleft()
                selected = next(combinations, None)
                if selected is None:
                    continue
                candidate_resources = {c['resource_id'] for c in selected}
                if len(included | candidate_resources) > max_resources:
                    reasons.add('candidate_resource_limit')
                    break
                included.update(candidate_resources)
                accounting = json.loads(_json(p))
                for si, c in enumerate(selected):
                    accounting['inputs'][si]['choices'][c['choice_index']].update(resource_id=c['resource_id'], match={'mode': 'exact', 'nbt_sensitive': True})
                    # Undiscovered alternatives are real bounded-closure omissions.
                    if c['resource_id'] not in seen and c['resource_id'] not in feeds:
                        reasons.add('candidate_alternative_closure')
                pid = p['id']
                variants.append({'variant_id': f'{pid}:v{sum(v["process_id"] == pid for v in variants)}',
                                 'process_id': pid, 'process': accounting,
                                 'selections': {str(si): c for si, c in enumerate(selected)}})
                deferred.append((p, combinations, depth))
            if deferred and len(variants) >= max_variants:
                # Only a remaining concrete combination proves this bound truncated.
                if any(next(combinations, None) is not None for _, combinations, _ in deferred):
                    reasons.add('candidate_variant_limit')
            used = included
            resources = {id: self._record(connection, 'resources', id) for id in sorted(used)}
            gids = {c['match']['group_id'] for p in records.values() for s in p['inputs'] for c in s['choices'] if c['match'].get('group_id')}
            groups = {id: self._record(connection, 'groups', id) for id in sorted(gids)}
        return {'snapshot_id': self.snapshot_id, 'target_id': target_id, 'allowed_feed_ids': sorted(feeds),
                'variants': variants, 'resources': list(resources.values()), 'groups': list(groups.values()),
                'processes': records,
                'scope': scope or {}, 'tier_filter': tiers, 'exclusions': {'counts': counts, 'examples': examples,
                    'count_semantics': 'Producer exclusions count records. Resource exclusions count candidate input-reference events'},
                'search': {'examined_processes': examined, 'processes': len(records), 'variants': len(variants),
                    'resources': len(resources), 'expansion_work': work, 'work_limit': work_limit,
                    'max_depth': max_depth, 'max_processes': max_processes, 'max_variants': max_variants, 'max_resources': max_resources},
                'limit_reasons': sorted(reasons), 'coverage_complete': not reasons and not counts,
                'scope_semantics': 'bounded_required_input_neighborhood_not_global_reachability'}

    def plan_network(self, target_id, *, target_amount=1, allowed_feed_ids, primary_feed_id=None,
                     selections=None, scope=None, objective='nominal_eu', yield_mode='guaranteed',
                     max_depth=8, max_processes=200, max_variants=128, max_resources=512,
                     min_tier=None, max_tier=None, unknown_tier_policy='exclude',
                     max_solutions=8, max_solves=24, max_columns=128, max_rows=512,
                     timeout_seconds=10, start_stock=None, preferred_process_ids=None):
        from .balance import ledger_json, quantity
        from .network import solve_network
        with self._connect() as connection:
            if primary_feed_id is not None:
                self._record(connection, 'resources', primary_feed_id)
            if start_stock is not None:
                if not isinstance(start_stock, dict):
                    raise DatasetError('start_stock must map resource IDs to quantities')
                self._resource_ids(connection, list(start_stock), 'start_stock')
        discovery = self.discover_network(target_id, allowed_feed_ids=allowed_feed_ids, selections=selections,
            scope=scope, max_depth=max_depth, max_processes=max_processes, max_variants=max_variants,
            max_resources=max_resources, min_tier=min_tier, max_tier=max_tier,
            unknown_tier_policy=unknown_tier_policy, preferred_process_ids=preferred_process_ids)
        try:
            result = solve_network(discovery['variants'], target_id=target_id, target_amount=target_amount,
                allowed_feed_ids=set(discovery['allowed_feed_ids']), primary_feed_id=primary_feed_id,
                objective=objective, yield_mode=yield_mode, max_solutions=max_solutions, max_solves=max_solves,
                max_columns=max_columns, max_rows=max_rows, timeout_seconds=timeout_seconds, start_stock=start_stock)
            amount = quantity(target_amount)
        except (ValueError, TypeError) as exc:
            raise DatasetError(str(exc)) from exc
        result.update(snapshot_id=self.snapshot_id, target_id=target_id, target_amount=amount,
                      allowed_feed_ids=discovery['allowed_feed_ids'], primary_feed_id=primary_feed_id,
                      discovery=discovery, coverage_complete=discovery['coverage_complete'] and result.get('search', {}).get('complete', False),
                      execution_scope='stoichiometric_witness_not_machine_or_condition_certification')
        if not discovery['coverage_complete'] and result['status'] == 'infeasible':
            result['status'] = 'incomplete'
        return ledger_json(result)

    def plan_to_bases(self, target_id, *, profile_id, target_amount=1, selections=None,
                      objective='recipe_runs', yield_mode='guaranteed', max_depth=8,
                      max_processes=200, max_variants=128, max_resources=512,
                      min_tier=None, max_tier=None, unknown_tier_policy='exclude',
                      max_solutions=8, max_solves=24, max_columns=128, max_rows=512,
                      timeout_seconds=10, start_stock=None):
        profile = self.get_boundary_profile(profile_id)['item']
        from .balance import quantity, ledger_json
        if target_id in profile['base_resource_ids']:
            try:
                amount = quantity(target_amount)
                if amount <= 0:
                    raise ValueError('target_amount must be positive')
            except ValueError as exc:
                raise DatasetError(str(exc)) from exc
            with self._connect() as connection:
                self._record(connection, 'resources', target_id)
            return ledger_json({'snapshot_id': self.snapshot_id, 'target_id': target_id, 'target_amount': amount,
                'status': 'complete', 'boundary': {'resource_id': target_id, 'amount': amount},
                'base_requirements': {target_id: amount}, 'solutions': [], 'profile': profile,
                'execution_scope': 'assumed_external_feed_boundary', 'coverage_complete': True})
        result = self.plan_network(target_id, target_amount=target_amount,
            allowed_feed_ids=profile['base_resource_ids'], scope=profile['scope'], selections=selections,
            objective=objective, yield_mode=yield_mode, max_depth=max_depth, max_processes=max_processes,
            max_variants=max_variants, max_resources=max_resources, min_tier=min_tier, max_tier=max_tier,
            unknown_tier_policy=unknown_tier_policy, max_solutions=max_solutions, max_solves=max_solves,
            max_columns=max_columns, max_rows=max_rows, timeout_seconds=timeout_seconds, start_stock=start_stock)
        result['profile'] = profile
        bases = set(profile['base_resource_ids'])
        for solution in result['solutions']:
            stock = solution['startup']['required_start_stock']
            unresolved = {id: amount for id, amount in stock.items() if id not in bases
                          and quantity((start_stock or {}).get(id, 0)) < quantity(amount)}
            solution['base_boundary'] = {'status': 'requires_startup' if unresolved else 'net_expanded',
                'unresolved_startup': unresolved,
                'semantics': 'Declared base feeds are assumptions. Ordered startup and presence remain separate'}
        return result

    def audit_energy(self, primary_feed_id, target_id, *, benchmark_process_id, target_amount=1,
                     profile_id=None, allowed_feed_ids=None, benchmark_selections=None,
                     selections=None, scope=None, yield_mode='guaranteed', max_depth=8,
                     max_processes=200, max_variants=128, max_resources=512,
                     min_tier=None, max_tier=None, unknown_tier_policy='exclude',
                     max_solutions=8, max_solves=24, max_columns=128, max_rows=512,
                     timeout_seconds=10, start_stock=None):
        from .balance import ledger_json, net_ledger, quantity
        from .network import nominal_energy
        scope = self._profile_scope(scope, profile_id)
        benchmark_selections = benchmark_selections or {}
        if not isinstance(benchmark_selections, dict):
            raise DatasetError('benchmark_selections must map input slots to selections')
        benchmark_discovery = self.discover_network(target_id, allowed_feed_ids=[primary_feed_id] if allowed_feed_ids is None else allowed_feed_ids,
            scope=scope, selections={benchmark_process_id: benchmark_selections},
            max_depth=1, max_processes=1, max_variants=1, preferred_process_ids=[benchmark_process_id])
        variant = next((v for v in benchmark_discovery['variants'] if v['process_id'] == benchmark_process_id), None)
        if variant is None:
            raise DatasetError('Benchmark is not an executable target producer inside this scope')
        try:
            base = net_ledger({benchmark_process_id: variant['process']}, {benchmark_process_id: 1},
                selections={benchmark_process_id: variant['selections']}, yield_mode=yield_mode)
            energy, energy_reason = nominal_energy(variant['process'])
            produced = base['net'].get(target_id, Fraction())
            if base['status'] != 'complete' or produced <= 0 or energy is None or base['net'].get(primary_feed_id, Fraction()) >= 0:
                raise DatasetError('Benchmark has no known positive net target, primary-feed consumption or nominal EU')
            amount = quantity(target_amount)
            runs = amount / produced
            scaled = net_ledger({benchmark_process_id: variant['process']}, {benchmark_process_id: runs},
                selections={benchmark_process_id: variant['selections']}, yield_mode=yield_mode)
        except (ValueError, TypeError) as exc:
            raise DatasetError(str(exc)) from exc
        result = self.plan_network(target_id, target_amount=target_amount,
            allowed_feed_ids=[primary_feed_id] if allowed_feed_ids is None else allowed_feed_ids,
            primary_feed_id=primary_feed_id, scope=scope, selections=selections, objective='nominal_eu',
            yield_mode=yield_mode, max_depth=max_depth, max_processes=max_processes, max_variants=max_variants,
            max_resources=max_resources, min_tier=min_tier, max_tier=max_tier, unknown_tier_policy=unknown_tier_policy,
            max_solutions=max_solutions, max_solves=max_solves, max_columns=max_columns, max_rows=max_rows,
            timeout_seconds=timeout_seconds, start_stock=start_stock, preferred_process_ids=[benchmark_process_id])
        baseline = energy * runs
        result['benchmark'] = ledger_json({'process': benchmark_discovery['processes'][benchmark_process_id],
            'selections': variant['selections'], 'runs': runs, 'ledger': scaled,
            'energy': {'total_eu': baseline, 'eu_per_target': baseline / amount},
            'cofeeds': {id: -v for id, v in scaled['net'].items() if v < 0 and id != primary_feed_id},
            'coproducts': {id: v for id, v in scaled['net'].items() if v > 0 and id != target_id},
            'comparison_scope': 'nominal_recipe_energy_without_container_or_coproduct_credit'})
        for solution in result['solutions']:
            total = solution['nominal_energy']['total_eu']
            if total is None:
                solution['savings'] = {'status': 'unknown'}
            else:
                delta = baseline - quantity(total)
                solution['savings'] = ledger_json({'status': 'known', 'eu': delta,
                    'fraction': delta / baseline, 'percent': 100 * delta / baseline})
        return result

    @staticmethod
    def _inventory_source_output(output):
        return output.get('resource_semantics') not in ('generated_ore_block_not_mining_drop', 'mined_item_rule_candidate')

    def inspect_acquisition(self, resource_id, *, profile_id=None, scope=None, max_depth=8,
                            max_processes=200, max_variants=128, max_resources=512):
        from .acquisition import summarize_acquisition, analyze_grounding
        profile = self.get_boundary_profile(profile_id)['item'] if profile_id is not None else None
        scope = self._profile_scope(scope, profile_id)
        bases = profile['base_resource_ids'] if profile else []
        discovery = self.discover_network(resource_id, allowed_feed_ids=bases, scope=scope, max_depth=max_depth,
            max_processes=max_processes, max_variants=max_variants, max_resources=max_resources)
        ids = [r['id'] for r in discovery['resources']]
        known = set()
        with self._connect() as connection:
            summary = summarize_acquisition(connection, [resource_id], snapshot_id=self.snapshot_id)
            for offset in range(0, len(ids), 500):
                batch = ids[offset:offset + 500]
                rows = connection.execute("SELECT DISTINCT payload FROM records WHERE collection='sources' AND id IN (SELECT source_id FROM source_outputs WHERE resource_id IN (" + ','.join('?' for _ in batch) + '))', batch)
                for row in rows:
                    source = json.loads(row[0])
                    if source['status'] in ('active', 'conditional'):
                        known.update(o['resource_id'] for o in source['outputs'] if self._inventory_source_output(o) and o['resource_id'] in ids)
        grounding = analyze_grounding(discovery['variants'], known, bases, discovery['coverage_complete'],
            resource_ids=ids, limit_reasons=discovery['limit_reasons'])
        return {'snapshot_id': self.snapshot_id, 'resource_id': resource_id,
            'item': summary['resources'][resource_id], 'grounding': grounding,
            'discovery': {k: discovery[k] for k in ('search', 'exclusions', 'scope', 'limit_reasons', 'coverage_complete')},
            'seed_semantics': 'conditional_declared_item_sources_and_assumed_base_feeds_not_inventory_stock'}

    def analyze_statistics(self, *, scope=None, profile_id=None, max_records=600000,
                           max_findings=50, max_signature_buckets=50000, timeout_seconds=15):
        from .statistics import analyze_statistics
        from .balance import ledger_json
        scope = self._profile_scope(scope, profile_id)
        with self._connect() as connection:
            clause, values = self._scope_clause(connection, scope)
            resource_rows = connection.execute("SELECT id,payload FROM records WHERE collection='resources' AND " + clause + ' ORDER BY id', values)
            allowed = {row[0] for row in connection.execute("SELECT id FROM records WHERE collection='resources' AND " + clause, values)}
            excluded_groups = set((scope or {}).get('excluded_group_ids', []))
            families = (scope or {}).get('excluded_family_ids', [])
            family_clause = " AND json_extract(payload,'$.family') NOT IN (" + ','.join('?' for _ in families) + ')' if families else ''
            process_rows = connection.execute("SELECT payload FROM records WHERE collection='processes'" + family_clause
                + " AND id NOT IN (SELECT process_id FROM outputs WHERE resource_id NOT IN (SELECT id FROM records WHERE collection='resources' AND "
                + clause + ')) ORDER BY id', (*families, *values))
            def groups():
                for row in connection.execute("SELECT id,payload FROM records WHERE collection='groups' ORDER BY id"):
                    if row['id'] in excluded_groups:
                        continue
                    group = json.loads(row['payload'])
                    group['members'] = [id for id in group['members'] if id in allowed]
                    group['membership_scope'] = 'analysis_resource_scope'
                    yield group
            try:
                result = analyze_statistics((json.loads(row['payload']) for row in resource_rows), groups(),
                    ({'process': p, 'recipe_tier': self._recipe_tier(p)} for p in (json.loads(row[0]) for row in process_rows)),
                    max_records=max_records, max_findings=max_findings,
                    max_signature_buckets=max_signature_buckets, timeout_seconds=timeout_seconds)
            except (ValueError, TypeError) as exc:
                raise DatasetError(str(exc)) from exc
            ids = {id for finding in result['findings'] for id in finding['process_ids']}
            result['processes'] = {id: self._record(connection, 'processes', id) for id in sorted(ids)}
        result.update(snapshot_id=self.snapshot_id, scope=scope or {})
        result['search']['scope_semantics'] = 'Resource catalog and group membership are scoped. Recipe families and all captured outputs are scoped. Raw input predicates remain unchanged'
        return ledger_json(result)

    def _resource_search_terms(self, connection, tokens):
        # The existing FTS index is authoritative. This temporary view leaves the imported database unchanged.
        with self._search_lock:
            if self._search_vocabulary is None:
                connection.execute("CREATE VIRTUAL TABLE temp.resource_terms USING fts5vocab(main,search,row)")
                vocabulary = {}
                for row in connection.execute("SELECT term FROM temp.resource_terms"):
                    word = row[0]
                    if 3 <= len(word) <= 64 and word.isalpha():
                        for deletion in _deletions(word):
                            vocabulary.setdefault(deletion, set()).add(word)
                self._search_vocabulary = vocabulary
        alternatives = []
        for token in tokens:
            words = {token}
            if 3 <= len(token) <= 64 and token.isalpha():
                candidates = set().union(*(self._search_vocabulary.get(deletion, ()) for deletion in _deletions(token)))
                words.update(word for word in candidates if _one_edit(token, word))
            alternatives.append(words)
        return alternatives

    @staticmethod
    def _resource_search_rank(q, tokens, alternatives):
        literal = _search_text(q.strip())

        def rank(id, registry, display, text):
            display = display or ""
            display_words = _search_words(display)
            if literal == _search_text(id):
                return 0
            if literal == _search_text(registry):
                return 1
            if tokens == display_words:
                return 2
            if sorted(tokens) == sorted(display_words):
                return 3
            words = _search_words(text)
            costs = [min((0 if word == token else 1 if word.startswith(token) else 2
                for word in words if any(word.startswith(alternative) for alternative in choices)), default=3)
                for token, choices in zip(tokens, alternatives)]
            tier = 4 if max(costs) == 0 else 5 if max(costs) == 1 else 6
            in_display = all(any(word.startswith(alternative) for word in display_words for alternative in choices) for choices in alternatives)
            return tier * 1000000 + costs.count(2) * 10000 + (0 if in_display else 1000) + costs.count(1) * 100 + min(len(display_words), 99)

        return rank

    def _using_clause(self, connection, resource_id):
        self._record(connection, "resources", resource_id)
        return """id IN (
            WITH requested AS (SELECT * FROM resources WHERE id=?)
            SELECT inputs.process_id FROM requested JOIN inputs ON inputs.resource_id=requested.id
                WHERE inputs.mode='exact'
            UNION
            SELECT inputs.process_id FROM requested
                JOIN resources anchor ON anchor.kind=requested.kind AND anchor.registry_name=requested.registry_name
                    AND anchor.metadata IS requested.metadata
                JOIN inputs ON inputs.resource_id=anchor.id
                WHERE inputs.mode='exact' AND inputs.nbt_sensitive=0
            UNION
            SELECT inputs.process_id FROM requested
                JOIN resources member ON member.kind=requested.kind AND member.registry_name=requested.registry_name
                    AND (member.metadata IS requested.metadata OR member.metadata=32767)
                JOIN members ON members.resource_id=member.id
                JOIN inputs ON inputs.group_id=members.group_id
                LEFT JOIN resources anchor ON anchor.id=inputs.resource_id
                WHERE inputs.mode IN ('ore_dict','unified')
                    AND (inputs.nbt_sensitive IS NOT 1 OR requested.nbt=COALESCE(anchor.nbt,member.nbt))
            UNION
            SELECT inputs.process_id FROM requested
                JOIN resources anchor ON anchor.kind=requested.kind AND anchor.registry_name=requested.registry_name
                JOIN inputs ON inputs.resource_id=anchor.id
                WHERE inputs.mode='wildcard' AND (inputs.nbt_sensitive=0 OR anchor.nbt=requested.nbt)
        )""", (resource_id,)

    @staticmethod
    def _unresolved_input_clause():
        return """(
            json_extract(payload,'$.conditions.dynamic_inputs')='unresolved' OR
            id IN (SELECT process_id FROM inputs WHERE mode='native_unknown' OR (mode='unified' AND group_id IS NULL))
        )"""

    def find_processes(self, *, input_id=None, output_id=None, family=None, offset=0, limit=50):
        clauses, parameters = ["1"], ()
        with self._connect() as connection:
            if input_id is not None:
                clause, values = self._using_clause(connection, input_id)
                clauses.append(clause)
                parameters += values
            if output_id is not None:
                self._record(connection, "resources", output_id)
                clauses.append("id IN (SELECT process_id FROM outputs WHERE resource_id=?)")
                parameters += (output_id,)
            if family is not None:
                clauses.append("json_extract(payload,'$.family')=?")
                parameters += (family,)
            result = self._page(connection, "processes", " AND ".join(clauses), parameters, offset=offset, limit=limit)
            unresolved = 0
            if input_id is not None:
                extra_clauses = [self._unresolved_input_clause()]
                extra_values = ()
                if output_id is not None:
                    extra_clauses.append("id IN (SELECT process_id FROM outputs WHERE resource_id=?)")
                    extra_values += (output_id,)
                if family is not None:
                    extra_clauses.append("json_extract(payload,'$.family')=?")
                    extra_values += (family,)
                unresolved = connection.execute("SELECT COUNT(*) FROM records WHERE collection='processes' AND " + " AND ".join(extra_clauses), extra_values).fetchone()[0]
            result.update(matching_complete=unresolved == 0, unresolved_matches=unresolved)
            return result

    def find_sources(self, *, resource_id=None, environment_id=None, offset=0, limit=50):
        clauses, values = ["1"], ()
        with self._connect() as connection:
            if resource_id is not None:
                self._record(connection, "resources", resource_id)
                clauses.append("id IN (SELECT source_id FROM source_outputs WHERE resource_id=?)")
                values += (resource_id,)
            if environment_id is not None:
                self._record(connection, "environments", environment_id)
                clauses.append("id IN (SELECT source_id FROM source_environments WHERE environment_id=?)")
                values += (environment_id,)
            return self._page(connection, "sources", " AND ".join(clauses), values, offset=offset, limit=limit)

    def find_environments(self, *, q="", offset=0, limit=50):
        where, values = self._search_clause(q)
        with self._connect() as connection:
            return self._page(connection, "environments", where, values, offset=offset, limit=limit)

    @staticmethod
    def _positive_output(output):
        return output['amount'] > 0 and (output['chance'] is None or output['chance']['numerator'] > 0)

    @staticmethod
    def _recipe_tier(record):
        voltage = record.get('eu_per_tick')
        result = {'process_id': record['id'], 'status': 'unknown', 'tier': None, 'name': None,
                  'scope': 'recipe_voltage_not_machine_capability'}
        native_owner = record['provenance'].get('owner') in ('GTRecipe', 'RecipeAssemblyLine.sAssemblylineRecipes')
        captured_source = record['conditions'].get('recipe_voltage_tier_source') == 'GTUtility.getTier(mEUt)'
        if (not record['family'].startswith('gregtech:') or not (native_owner or captured_source)
                or type(voltage) is not int or voltage < 0):
            result['reason'] = 'No supported GT native recipe-voltage declaration'
            return result
        # GT5 .221 GTUtility.getTier(long), including its nominal zero-EU tier.
        thresholds = (8, 32, 128, 512, 2048, 8192, 32768, 131072, 524288, 2097152,
                      8388608, 33554432, 134217728, 536870912, 2147483640)
        names = ('ULV', 'LV', 'MV', 'HV', 'EV', 'IV', 'LuV', 'ZPM', 'UV', 'UHV', 'UEV', 'UIV', 'UMV', 'UXV', 'MAX', 'MAX+')
        tier = next((tier for tier, maximum in enumerate(thresholds) if voltage <= maximum), 15)
        if captured_source and record['conditions'].get('recipe_voltage_tier') != tier:
            result['reason'] = 'Captured native recipe tier disagrees with its voltage declaration'
            return result
        result.update(status='known', tier=tier, name=names[tier])
        return result

    @staticmethod
    def _tier_filter(min_tier, max_tier, unknown_tier_policy):
        for name, value in (('min_tier', min_tier), ('max_tier', max_tier)):
            if value is not None and (type(value) is not int or not 0 <= value <= 15):
                raise DatasetError(f'{name} must be an integer between 0 and 15')
        if min_tier is not None and max_tier is not None and min_tier > max_tier:
            raise DatasetError('min_tier must not exceed max_tier')
        if unknown_tier_policy not in ('exclude', 'include'):
            raise DatasetError('unknown_tier_policy must be exclude or include')
        return {'min_tier': min_tier, 'max_tier': max_tier, 'unknown_tier_policy': unknown_tier_policy,
                'active': min_tier is not None or max_tier is not None, 'excluded_unknown': 0, 'excluded_out_of_range': 0}

    def _tier_allowed(self, record, filters):
        if not filters['active']:
            return True
        tier = self._recipe_tier(record)['tier']
        if tier is None:
            return filters['unknown_tier_policy'] == 'include'
        return ((filters['min_tier'] is None or tier >= filters['min_tier'])
                and (filters['max_tier'] is None or tier <= filters['max_tier']))

    def _find_paths_shortest(self, connection, start_id, target_id, max_depth, max_processes, max_paths, required, excluded, max_extra_steps, tier_filter=None):
        search = {"examined_processes": 0, "limit": 10000, "examined_states": 0, "state_limit": 20000,
                  "expansion_work": 0, "work_limit": 100000, "enumeration_work": 0, "enumeration_limit": 100000,
                  "queued_states": 0, "peak_queue": 0, "truncated": False}
        route = {"status": "not_found", "strategy": "shortest_known_dependency_path", "resource_ids": [], "process_ids": []}
        paths, records, choices, adjacency = [], {}, {}, {}
        fingerprints, duplicate_ids = {}, {}
        reasons, admitted, tier_checked = set(), set(), set()
        if required & excluded or start_id in excluded or target_id in excluded:
            return route, paths, search, [], []
        if start_id == target_id:
            if required <= {start_id}:
                path = {"resource_ids": [start_id], "process_ids": []}
                route.update(status="same_resource", **path)
                paths.append(path)
            return route, paths, search, [], []

        def predecessors(resource_id):
            if resource_id in adjacency:
                return adjacency[resource_id]
            entries = []
            for row in connection.execute("SELECT DISTINCT process_id FROM outputs WHERE resource_id=? ORDER BY process_id", (resource_id,)):
                process_id = row[0]
                if process_id not in records:
                    if len(records) >= search["limit"]:
                        reasons.add("search_process_limit")
                        break
                    records[process_id] = self._record(connection, "processes", process_id)
                record = records[process_id]
                if tier_filter is not None and not self._tier_allowed(record, tier_filter):
                    if process_id not in tier_checked:
                        key = 'excluded_unknown' if self._recipe_tier(record)['tier'] is None else 'excluded_out_of_range'
                        tier_filter[key] += 1
                        tier_checked.add(process_id)
                    continue
                if (record["executable"] is False or record["conditions"].get("dynamic_output") == "unresolved"
                        or not any(output["resource_id"] == resource_id and self._positive_output(output) for output in record["outputs"])):
                    continue
                captured = {key: value for key, value in record.items() if key != "id"}
                captured["provenance"] = {key: value for key, value in record["provenance"].items() if key != "index"}
                fingerprint = _json(captured)
                representative = fingerprints.setdefault(fingerprint, process_id)
                if representative != process_id:
                    duplicate_ids.setdefault(representative, set()).add(process_id)
                    continue
                input_ids = set()
                for slot in record["inputs"]:
                    if slot["role"] != "consume":
                        continue
                    for choice in slot["choices"]:
                        match = choice["match"]
                        if choice["amount"] <= 0 or match["mode"] == "native_unknown":
                            continue
                        if match["mode"] in ("ore_dict", "unified") and not match.get("group_id"):
                            continue
                        key = _json({"resource_id": choice.get("resource_id"), "match": match})
                        if key not in choices:
                            candidates = self._choice_resources(connection, choice)
                            search["expansion_work"] += len(candidates)
                            if search["expansion_work"] > search["work_limit"]:
                                reasons.add("search_work_limit")
                                return []
                            choices[key] = candidates
                        input_ids.update(choices[key])
                entries.extend((process_id, input_id) for input_id in sorted(input_ids - excluded))
            adjacency[resource_id] = entries
            return entries

        # Discover each target ancestor once, then enumerate paths inside that graph.
        # Recipe variants cannot multiply the discovery queue into a path tree.
        queue = deque([(target_id, 0)])
        discovered = {target_id}
        search.update(queued_states=1, peak_queue=1)
        nearest_start = None
        forward = {}
        halted = False
        while queue and not halted:
            resource_id, depth = queue.popleft()
            search["examined_states"] += 1
            scope = min(max_depth, nearest_start + max_extra_steps) if nearest_start is not None and not required else max_depth
            if depth >= scope:
                if scope == max_depth and connection.execute("SELECT 1 FROM outputs WHERE resource_id=? LIMIT 1", (resource_id,)).fetchone():
                    reasons.add("depth")
                continue
            entries = predecessors(resource_id)
            for process_id, input_id in entries:
                search["expansion_work"] += 1
                if search["expansion_work"] > search["work_limit"]:
                    reasons.add("search_work_limit")
                    halted = True
                    break
                forward.setdefault(input_id, set()).add((process_id, resource_id))
                if input_id == start_id:
                    nearest_start = depth + 1 if nearest_start is None else nearest_start
                elif input_id not in discovered:
                    if search["queued_states"] >= search["state_limit"]:
                        reasons.add("search_state_limit")
                        halted = True
                        break
                    discovered.add(input_id)
                    queue.append((input_id, depth + 1))
                    search["queued_states"] += 1
                    search["peak_queue"] = max(search["peak_queue"], len(queue))
            if reasons & {"search_process_limit", "search_work_limit"}:
                break

        # A reverse distance in the discovered graph prunes branches that cannot
        # finish within the current shortest qualifying path's detour allowance.
        distances = {target_id: 0}
        queue = deque([target_id])
        while queue:
            resource_id = queue.popleft()
            for _, input_id in adjacency.get(resource_id, ()):
                if input_id not in distances:
                    distances[input_id] = distances[resource_id] + 1
                    queue.append(input_id)
        queue = deque()
        if start_id in distances:
            if search["queued_states"] < search["state_limit"]:
                queue.append(((start_id,), ()))
                search["queued_states"] += 1
            else:
                reasons.add("search_state_limit")
        shortest = None
        halted = False
        while queue and not halted:
            resource_ids, process_ids = queue.popleft()
            search["examined_states"] += 1
            scope = min(max_depth, shortest + max_extra_steps) if shortest is not None else max_depth
            depth = len(process_ids)
            if depth >= scope:
                continue
            for process_id, output_id in sorted(forward.get(resource_ids[-1], ())):
                search["enumeration_work"] += 1
                if search["enumeration_work"] > search["enumeration_limit"]:
                    reasons.add("search_enumeration_limit")
                    halted = True
                    break
                if output_id in resource_ids or process_id in process_ids or depth + 1 + distances.get(output_id, max_depth + 1) > scope:
                    continue
                next_resources = resource_ids + (output_id,)
                next_processes = process_ids + (process_id,)
                if output_id == target_id:
                    if not required <= set(next_resources):
                        continue
                    shortest = depth + 1 if shortest is None else shortest
                    additions = set(next_processes) - admitted
                    if len(admitted) + len(additions) > max_processes:
                        reasons.add("path_process_limit")
                        if not paths:
                            halted = True
                            break
                        continue
                    paths.append({"resource_ids": list(next_resources), "process_ids": list(next_processes)})
                    admitted.update(additions)
                    if len(paths) >= max_paths:
                        reasons.add("path_limit")
                        halted = True
                        break
                else:
                    if search["queued_states"] >= search["state_limit"]:
                        reasons.add("search_state_limit")
                        halted = True
                        break
                    queue.append((next_resources, next_processes))
                    search["queued_states"] += 1
                    search["peak_queue"] = max(search["peak_queue"], len(queue))
        search["examined_processes"] = len(records)
        search["truncated"] = bool(reasons)
        if paths:
            route.update(status="found", **paths[0])
        elif reasons:
            route["status"] = "incomplete"
        duplicates = [{"representative_id": id, "duplicate_ids": sorted(duplicate_ids[id])} for id in sorted(admitted & duplicate_ids.keys())]
        return route, paths, search, sorted(reasons), duplicates

    def _find_paths(self, connection, start_id, target_id, max_depth, max_processes, max_paths,
                    required, excluded, max_extra_steps, tier_filter, path_selection):
        if path_selection == 'shortest':
            return (*self._find_paths_shortest(connection, start_id, target_id, max_depth, max_processes,
                max_paths, required, excluded, max_extra_steps, tier_filter), [])
        primary = self._find_paths_shortest(connection, start_id, target_id, max_depth, max_processes,
            1, required, excluded, 0, dict(tier_filter))
        route, paths, primary_search, primary_reasons, primary_duplicates = primary
        if start_id == target_id or required & excluded or start_id in excluded or target_id in excluded:
            return (*primary, [])
        primary_limit_reasons = set(primary_reasons) - {'path_limit'}
        reasons = set()
        scope = min(max_depth, len(paths[0]['process_ids']) + max_extra_steps) if paths else max_depth
        records, choices, fingerprints, duplicate_ids, graph, reverse_cache = {}, {}, {}, {}, {}, {}
        seen_tiers = set()
        search = {'examined_processes': 0, 'limit': 10000, 'examined_states': 0, 'state_limit': 40000,
                  'expansion_work': 0, 'work_limit': 100000, 'enumeration_work': 0, 'enumeration_limit': 100000,
                  'queued_states': 0, 'peak_queue': 0, 'truncated': False, 'primary': primary_search,
                  'source': {'depth_limit': 2, 'process_limit': 2000, 'examined_resources': 0, 'examined_processes': 0,
                             'scope': 'forward_seed_only_reverse_discovery_continues', 'process_limit_reached': False},
                  'discovery': {'queued_states': 0, 'examined_states': 0, 'state_limit': 20000, 'pending_states': 0},
                  'enumeration': {'queued_states': 0, 'examined_states': 0, 'state_limit': 20000, 'work': 0, 'work_limit': 100000,
                                  'pending_states': 0, 'variant_pool_limit': 1000, 'deferred_variants': 0, 'peak_deferred_variants': 0}}

        def read(row):
            pid = row['id']
            if pid not in records:
                if len(records) >= search['limit']:
                    reasons.add('search_process_limit')
                    return None
                records[pid] = json.loads(row['payload'])
            record = records[pid]
            if not self._tier_allowed(record, tier_filter):
                if pid not in seen_tiers:
                    key = 'excluded_unknown' if self._recipe_tier(record)['tier'] is None else 'excluded_out_of_range'
                    tier_filter[key] += 1
                    seen_tiers.add(pid)
                return None
            if record['executable'] is False or record['conditions'].get('dynamic_output') == 'unresolved':
                return None
            captured = {k: v for k, v in record.items() if k != 'id'}
            captured['provenance'] = {k: v for k, v in record['provenance'].items() if k != 'index'}
            representative = fingerprints.setdefault(_json(captured), pid)
            if representative != pid:
                duplicate_ids.setdefault(representative, set()).add(pid)
            return records[representative]

        for path in paths:
            for pid in path['process_ids']:
                read({'id': pid, 'payload': _json(self._record(connection, 'processes', pid))})

        def inputs(slot):
            ids = set()
            if slot['role'] != 'consume':
                return ids
            for choice in slot['choices']:
                match = choice['match']
                if (choice['amount'] <= 0 or match['mode'] == 'native_unknown'
                        or match['mode'] in ('unified', 'ore_dict') and not match.get('group_id')):
                    continue
                key = _json({'resource_id': choice.get('resource_id'), 'match': match})
                if key not in choices:
                    choices[key] = set(self._choice_resources(connection, choice)) - excluded
                    search['expansion_work'] += len(choices[key])
                if search['expansion_work'] > search['work_limit']:
                    reasons.add('search_work_limit')
                    return set()
                ids.update(choices[key])
            return ids

        def edge(source, pid, output):
            graph.setdefault(source, set()).add((pid, output))
            search['expansion_work'] += 1
            if search['expansion_work'] > search['work_limit']:
                reasons.add('search_work_limit')

        jobs = []
        rows = connection.execute("SELECT id,payload FROM records WHERE collection='processes' AND id IN "
                                  '(SELECT process_id FROM outputs WHERE resource_id=?) ORDER BY id', (target_id,))
        job_keys = set()
        for row in rows:
            record = read(row)
            if record is None or not any(o['resource_id'] == target_id and self._positive_output(o) for o in record['outputs']):
                continue
            for si, slot in enumerate(record['inputs']):
                candidates = inputs(slot)
                key = record['id'], si
                if not candidates or key in job_keys:
                    continue
                job_keys.add(key)
                jobs.append({'pid': record['id'], 'slot': si, 'candidates': candidates,
                             'queue': deque((id, 1) for id in sorted(candidates)), 'seen': set(candidates)})
                for id in candidates:
                    edge(id, record['id'], target_id)
                search['discovery']['queued_states'] += len(candidates)
        search['discovery']['pending_states'] = search['discovery']['queued_states']
        search['peak_queue'] = search['discovery']['pending_states']
        if len(paths) < max_paths:
            source_queue, source_seen = deque([(start_id, 0)]), {start_id}
            while source_queue and len(records) < search['source']['process_limit']:
                rid, depth = source_queue.popleft()
                if depth >= min(2, scope):
                    continue
                search['source']['examined_resources'] += 1
                clause, values = self._using_clause(connection, rid)
                rows = connection.execute("SELECT id,payload FROM records WHERE collection='processes' AND " + clause + ' ORDER BY id', values)
                for row in rows:
                    if len(records) >= search['source']['process_limit']:
                        break
                    record = read(row)
                    if record is None or not any(rid in inputs(slot) for slot in record['inputs']):
                        continue
                    for output in record['outputs']:
                        dest = output['resource_id']
                        if not self._positive_output(output) or dest in excluded:
                            continue
                        edge(rid, record['id'], dest)
                        if dest not in source_seen:
                            source_seen.add(dest)
                            source_queue.append((dest, depth + 1))
                if 'search_work_limit' in reasons:
                    break
            search['source']['examined_processes'] = len(records)
            search['source']['process_limit_reached'] = bool(source_queue and len(records) >= search['source']['process_limit'])
            while any(job['queue'] for job in jobs):
                for job in jobs:
                    if not job['queue']:
                        continue
                    rid, depth = job['queue'].popleft()
                    search['discovery']['pending_states'] -= 1
                    search['discovery']['examined_states'] += 1
                    if depth >= scope:
                        if scope == max_depth and connection.execute('SELECT 1 FROM outputs WHERE resource_id=? LIMIT 1', (rid,)).fetchone():
                            reasons.add('depth')
                        continue
                    if rid not in reverse_cache:
                        entries = set()
                        rows = connection.execute("SELECT id,payload FROM records WHERE collection='processes' AND id IN "
                                                  '(SELECT process_id FROM outputs WHERE resource_id=?) ORDER BY id', (rid,))
                        for row in rows:
                            record = read(row)
                            if record is None or not any(o['resource_id'] == rid and self._positive_output(o) for o in record['outputs']):
                                continue
                            for slot in record['inputs']:
                                entries.update((record['id'], id) for id in inputs(slot))
                            if reasons & {'search_process_limit', 'search_work_limit'}:
                                break
                        reverse_cache[rid] = entries
                    for pid, input_id in sorted(reverse_cache[rid]):
                        edge(input_id, pid, rid)
                        if input_id not in job['seen']:
                            if search['discovery']['queued_states'] >= search['discovery']['state_limit']:
                                reasons.add('search_state_limit')
                                continue
                            job['seen'].add(input_id)
                            job['queue'].append((input_id, depth + 1))
                            search['discovery']['queued_states'] += 1
                            search['discovery']['pending_states'] += 1
                            search['peak_queue'] = max(search['peak_queue'], search['discovery']['pending_states'])
                    if reasons & {'search_process_limit', 'search_work_limit'}:
                        break
                if reasons & {'search_process_limit', 'search_work_limit'}:
                    break

        def candidates(job):
            adjacency, backwards = {}, {}
            for source, entries in graph.items():
                allowed = [(pid, dest) for pid, dest in sorted(entries) if dest != target_id
                           or job['pid'] is None or pid == job['pid'] and source in job['candidates']]
                adjacency[source] = allowed
                for _, dest in allowed:
                    backwards.setdefault(dest, set()).add(source)
            distance = {target_id: 0}
            queue = deque([target_id])
            while queue:
                dest = queue.popleft()
                for source in backwards.get(dest, ()):
                    if source not in distance:
                        distance[source] = distance[dest] + 1
                        queue.append(source)
            if start_id not in distance:
                return
            if search['enumeration']['queued_states'] >= search['enumeration']['state_limit']:
                reasons.add('search_state_limit')
                return
            heap = [(distance[start_id], 0, (start_id,), ())]
            search['enumeration']['queued_states'] += 1
            search['enumeration']['pending_states'] += 1
            turn_work = 0
            while heap:
                _, depth, resource_ids, process_ids = heappop(heap)
                search['enumeration']['pending_states'] -= 1
                search['enumeration']['examined_states'] += 1
                for pid, dest in adjacency.get(resource_ids[-1], ()):
                    search['enumeration']['work'] += 1
                    turn_work += 1
                    if turn_work >= 128:
                        turn_work = 0
                        yield None
                    if search['enumeration']['work'] > search['enumeration']['work_limit']:
                        reasons.add('search_enumeration_limit')
                        return
                    if dest in resource_ids or pid in process_ids or depth + 1 + distance.get(dest, scope + 1) > scope:
                        continue
                    rr, pp = resource_ids + (dest,), process_ids + (pid,)
                    if dest == target_id:
                        if required <= set(rr):
                            yield {'resource_ids': list(rr), 'process_ids': list(pp)}
                    else:
                        if search['enumeration']['queued_states'] >= search['enumeration']['state_limit']:
                            reasons.add('search_state_limit')
                            continue
                        heappush(heap, (depth + 1 + distance[dest], depth + 1, rr, pp))
                        search['enumeration']['queued_states'] += 1
                        search['enumeration']['pending_states'] += 1
                        search['peak_queue'] = max(search['peak_queue'], search['enumeration']['pending_states'])

        if not paths:
            for path in candidates({'pid': None, 'candidates': set()}):
                if path is not None:
                    if len(path['process_ids']) <= max_processes:
                        paths.append(path)
                        scope = min(max_depth, len(path['process_ids']) + max_extra_steps)
                    else:
                        reasons.add('path_process_limit')
                    break
        admitted = {id for path in paths for id in path['process_ids']}
        signatures = {_json(path) for path in paths}
        spines = {tuple(path['resource_ids']) for path in paths}
        def covered(job):
            return [i for i, path in enumerate(paths) if path['process_ids'] and path['process_ids'][-1] == job['pid']
                    and path['resource_ids'][-2] in job['candidates']]
        for job in jobs:
            job['iterator'] = candidates(job)
            job['finished'] = False
            job['deferred'] = deque()
        def admit(path):
            nonlocal scope, admitted, signatures, spines
            next_scope = min(scope, len(path['process_ids']) + max_extra_steps)
            kept = [p for p in paths if len(p['process_ids']) <= next_scope]
            if paths and len(path['process_ids']) < min(len(p['process_ids']) for p in paths):
                included, retained = set(path['process_ids']), [path]
                for previous in sorted(kept, key=lambda p: len(p['process_ids'])):
                    union = included | set(previous['process_ids'])
                    if len(union) <= max_processes:
                        included = union
                        retained.append(previous)
                    else:
                        reasons.add('path_process_limit')
                kept = retained
            else:
                included = {id for p in kept for id in p['process_ids']} | set(path['process_ids'])
                kept.append(path)
            if len(included) > max_processes:
                reasons.add('path_process_limit')
                return False
            if len(path['process_ids']) > next_scope:
                return False
            paths[:] = kept
            scope, admitted = next_scope, included
            signatures = {_json(p) for p in paths}
            spines = {tuple(p['resource_ids']) for p in paths}
            return True
        while len(paths) < max_paths and any(not job['finished'] or job['deferred'] for job in jobs):
            progress, active_work = False, False
            unrepresented = [job for job in jobs if not covered(job) and not job['finished']]
            for job in sorted(unrepresented or jobs, key=lambda job: (len(covered(job)), job['pid'], job['slot'])):
                if job['finished']:
                    continue
                for path in job['iterator']:
                    if path is None:
                        active_work = True
                        break
                    signature = _json(path)
                    if signature in signatures:
                        continue
                    if tuple(path['resource_ids']) in spines and covered(job):
                        if search['enumeration']['deferred_variants'] < search['enumeration']['variant_pool_limit']:
                            job['deferred'].append(path)
                            search['enumeration']['deferred_variants'] += 1
                            search['enumeration']['peak_deferred_variants'] = max(search['enumeration']['peak_deferred_variants'], search['enumeration']['deferred_variants'])
                        else:
                            reasons.add('search_variant_limit')
                        continue
                    if admit(path):
                        progress = True
                        break
                else:
                    job['finished'] = True
                if len(paths) >= max_paths:
                    break
            if not progress and not active_work:
                for job in sorted(jobs, key=lambda job: (len(covered(job)), job['pid'], job['slot'])):
                    while job['deferred']:
                        path = job['deferred'].popleft()
                        search['enumeration']['deferred_variants'] -= 1
                        if _json(path) not in signatures and admit(path):
                            progress = True
                            break
                    if len(paths) >= max_paths:
                        break
                if not progress:
                    if any(not job['finished'] for job in jobs):
                        continue
                    break
        if len(paths) >= max_paths:
            reasons.add('path_limit')
        reasons.update(primary_limit_reasons)
        if paths:
            paths.sort(key=lambda path: len(path['process_ids']))
            route.update(status='found', **paths[0])
        elif reasons:
            route['status'] = 'incomplete'
        branches = [{'target_process_id': job['pid'], 'slot_index': job['slot'], 'candidate_resources': len(job['candidates']),
                     'paths': len(covered(job)), 'path_indices': covered(job),
                     'status': 'represented' if covered(job) else 'not_discovered'} for job in jobs]
        search.update(examined_processes=len(records), examined_states=search['discovery']['examined_states'] + search['enumeration']['examined_states'],
                      queued_states=search['discovery']['queued_states'] + search['enumeration']['queued_states'],
                      enumeration_work=search['enumeration']['work'], truncated=bool(reasons))
        duplicates = [{"representative_id": id, "duplicate_ids": sorted(duplicate_ids[id])} for id in sorted(admitted & duplicate_ids.keys())]
        duplicates.extend(item for item in primary_duplicates if item['representative_id'] not in duplicate_ids)
        return route, paths, search, sorted(reasons), duplicates, branches

    def trace_processes(self, *, start_id, target_id, max_depth=12, max_processes=300, max_paths=8,
                        required_resource_ids=None, excluded_resource_ids=None, max_extra_steps=6,
                        min_tier=None, max_tier=None, unknown_tier_policy='exclude', path_selection='diverse'):
        tier_filter = self._tier_filter(min_tier, max_tier, unknown_tier_policy)
        if path_selection not in ('diverse', 'shortest'):
            raise DatasetError('path_selection must be diverse or shortest')
        if isinstance(max_depth, bool) or not isinstance(max_depth, int) or not 1 <= max_depth <= 64:
            raise DatasetError("max_depth must be between 1 and 64")
        if isinstance(max_processes, bool) or not isinstance(max_processes, int) or not 1 <= max_processes <= 5000:
            raise DatasetError("max_processes must be between 1 and 5000")
        if type(max_paths) is not int or not 1 <= max_paths <= 100:
            raise DatasetError("max_paths must be between 1 and 100")
        if type(max_extra_steps) is not int or not 0 <= max_extra_steps <= 64:
            raise DatasetError("max_extra_steps must be between 0 and 64")
        for name, ids in (("required_resource_ids", required_resource_ids), ("excluded_resource_ids", excluded_resource_ids)):
            if ids is not None and (not isinstance(ids, list) or any(not isinstance(id, str) or not id for id in ids)):
                raise DatasetError(f"{name} must be an array of resource IDs")
        if any(not isinstance(id, str) or not id for id in (start_id, target_id)):
            raise DatasetError("start_id and target_id must be resource IDs")
        with self._connect() as connection:
            required, excluded = set(required_resource_ids or []), set(excluded_resource_ids or [])
            for id in sorted(required | excluded):
                self._record(connection, "resources", id)
            resources = {id: self._record(connection, "resources", id) for id in (start_id, target_id)}
            processes = {}
            edges = {}
            input_slots = {}
            route, paths, search, limit_reasons, duplicates, branches = self._find_paths(connection, start_id, target_id, max_depth, max_processes, max_paths, required, excluded, max_extra_steps, tier_filter, path_selection)
            unresolved = set()

            def admit(id):
                if id in processes:
                    return False
                record = self._record(connection, "processes", id)
                if record["executable"] is False:
                    return False
                processes[id] = record
                if connection.execute("SELECT 1 FROM records WHERE collection='processes' AND id=? AND " + self._unresolved_input_clause(), (id,)).fetchone():
                    unresolved.add(id)
                slots = []
                for slot_index, slot in enumerate(record["inputs"]):
                    candidates = set()
                    for choice_index, choice in enumerate(slot["choices"]):
                        for resource_id in self._choice_resources(connection, choice):
                            if resource_id not in resources:
                                resources[resource_id] = self._record(connection, "resources", resource_id)
                            candidates.add(resource_id)
                            edge = {"source": f"resource:{resource_id}", "target": f"process:{id}",
                                    "role": slot["role"], "slot_index": slot_index, "choice_index": choice_index}
                            edges[_json(edge)] = edge
                    slots.append(candidates)
                input_slots[id] = slots
                for output in record["outputs"]:
                    resource_id = output["resource_id"]
                    if resource_id not in resources:
                        resources[resource_id] = self._record(connection, "resources", resource_id)
                    edge = {"source": f"process:{id}", "target": f"resource:{resource_id}", "role": "output"}
                    edges[_json(edge)] = edge
                return True

            for id in sorted({id for path in paths for id in path["process_ids"]}):
                admit(id)

            coverage = [json.loads(row[0]) for row in connection.execute("SELECT payload FROM records WHERE collection='coverage' ORDER BY id")]
            unsupported_count = connection.execute("SELECT COUNT(*) FROM records WHERE collection='processes' AND " + self._unresolved_input_clause()).fetchone()[0]
            if unsupported_count:
                coverage.append({"id": "dataset:unresolved-matching", "domain": "trace.matching", "status": "partial",
                                 "records": unsupported_count, "reason": "Unsupported ingredient predicates can leave undiscovered routes in this snapshot",
                                 "provenance": {"owner": "Dataset"}})
            unresolved_output_count = connection.execute("SELECT COUNT(*) FROM records WHERE collection='processes' AND "
                                                        "json_extract(payload,'$.conditions.dynamic_output')='unresolved'").fetchone()[0]
            if unresolved_output_count:
                coverage.append({"id": "dataset:unresolved-outputs", "domain": "trace.outputs", "status": "partial",
                                 "records": unresolved_output_count, "reason": "Unresolved dynamic outputs cannot establish material paths",
                                 "provenance": {"owner": "Dataset"}})
            edges_list = sorted(edges.values(), key=lambda edge: (edge["source"], edge["target"], edge["role"], edge.get("slot_index", -1), edge.get("choice_index", -1)))
            cycles = self._cycles(edges_list)
            cyclic_resources = {node.removeprefix("resource:") for component in cycles for node in component if node.startswith("resource:")}
            unresolved_outputs = {output["resource_id"] for id in unresolved for output in processes[id]["outputs"]}
            for component in cycles:
                members = {node.removeprefix("resource:") for node in component if node.startswith("resource:")}
                if members & unresolved_outputs:
                    unresolved_outputs.update(members)
            source_coverage = [record for record in coverage if any(term in record["domain"].lower() for term in ("acquisition", "source", "worldgen", "drop", "trade"))]
            incomplete_sources = not source_coverage or any(record["status"] != "complete" for record in source_coverage)
            source_states = {}
            source_ids = {}
            generation_only = set()
            rule_only = set()
            unresolved_boundaries = set()
            for resource_id in resources:
                rows = connection.execute("SELECT DISTINCT payload FROM records JOIN source_outputs ON source_outputs.source_id=records.id WHERE collection='sources' AND resource_id=? ORDER BY records.id", (resource_id,))
                sources = [json.loads(row[0]) for row in rows]
                source_ids[resource_id] = [source["id"] for source in sources]
                inventory_sources = [source for source in sources if any(
                    output['resource_id'] == resource_id
                    and self._inventory_source_output(output)
                    for output in source['outputs'])]
                if sources and not inventory_sources:
                    if any(output['resource_id'] == resource_id and output.get('resource_semantics') == 'generated_ore_block_not_mining_drop'
                           for source in sources for output in source['outputs']):
                        generation_only.add(resource_id)
                    if any(output['resource_id'] == resource_id and output.get('resource_semantics') == 'mined_item_rule_candidate'
                           for source in sources for output in source['outputs']):
                        rule_only.add(resource_id)
                if connection.execute("SELECT 1 FROM records WHERE collection='processes' AND id IN (SELECT process_id FROM outputs WHERE resource_id=?) AND (" + self._unresolved_input_clause()
                                      + " OR json_extract(payload,'$.conditions.dynamic_output')='unresolved') LIMIT 1", (resource_id,)).fetchone():
                    unresolved_boundaries.add(resource_id)
                if resource_id == start_id:
                    source_states[resource_id] = "assumed"
                elif any(source["status"] == "active" and not source["conditions"] for source in inventory_sources):
                    source_states[resource_id] = "available"
                elif any(source["status"] in ("active", "conditional") for source in inventory_sources):
                    source_states[resource_id] = "conditional"
                elif (any(source["status"] == "unknown" for source in inventory_sources) or incomplete_sources
                      or resource_id in generation_only or resource_id in rule_only or resource_id in unresolved_outputs or resource_id in unresolved_boundaries):
                    source_states[resource_id] = "unresolved"
                else:
                    source_states[resource_id] = "no_known_source"

            grounded = {id for id, status in source_states.items() if status in ("assumed", "available", "conditional")}
            changed = True
            while changed:
                changed = False
                for process_id, record in processes.items():
                    if process_id in unresolved or not all(choices & grounded for choices in input_slots[process_id]):
                        continue
                    for output in record["outputs"]:
                        if self._positive_output(output) and output["resource_id"] not in grounded:
                            grounded.add(output["resource_id"])
                            changed = True
            produced = {output["resource_id"] for process_id, record in processes.items() if process_id not in unresolved
                        for output in record["outputs"] if self._positive_output(output)}
            needed = {id for slots in input_slots.values() for choices in slots for id in choices} | {start_id, target_id}
            leaves = []
            path_resources = {id for path in paths for id in path["resource_ids"]}
            for resource_id in sorted(needed):
                if resource_id != start_id and resource_id in path_resources and resource_id in produced and (resource_id not in cyclic_resources or resource_id in grounded):
                    continue
                leaf = {"resource_id": resource_id, "status": source_states[resource_id], "sources": source_ids[resource_id]}
                if resource_id in rule_only and leaf['status'] == 'unresolved':
                    leaf['reason'] = 'A stochastic per-harvest rule describes potential products, not a jointly available inventory or a cycle seed'
                elif resource_id in cyclic_resources and resource_id not in grounded:
                    leaf["reason"] = "A cycle needs an external acquisition source or an explicit supplied seed"
                elif resource_id in generation_only and leaf['status'] == 'unresolved':
                    leaf['reason'] = 'Configured generation describes a world block, not a captured inventory acquisition or mining drop'
                elif resource_id in unresolved_outputs | unresolved_boundaries and leaf["status"] == "unresolved":
                    leaf["reason"] = "Producer inputs, matching or outputs are unresolved"
                leaves.append(leaf)
            return {"snapshot_id": self.snapshot_id, "start_id": start_id, "target_id": target_id,
                    "resources": [resources[id] for id in sorted(resources)], "processes": [processes[id] for id in sorted(processes)],
                      "edges": edges_list, "leaves": leaves, "cycles": cycles, "truncated": bool(limit_reasons), "coverage": coverage,
                      "route": route, "paths": paths, "search": search, "limit_reasons": sorted(limit_reasons), "duplicate_process_records": duplicates,
                      'tier_filter': tier_filter, 'recipe_tiers': [self._recipe_tier(processes[id]) for id in sorted(processes)],
                      'path_selection': path_selection, 'branch_coverage': branches}

    def _choice_resources(self, connection, choice):
        match = choice["match"]
        if match["mode"] in ("ore_dict", "unified") and match.get("group_id"):
            nbt_clause, values = "", (match["group_id"],)
            if match.get("nbt_sensitive") is True:
                if choice.get("resource_id") is not None:
                    anchor = self._record(connection, "resources", choice["resource_id"])
                    nbt_clause = " AND candidate.nbt=?"
                    values += (_json(anchor["nbt"]),)
                else:
                    nbt_clause = " AND candidate.nbt=member.nbt"
            return [row[0] for row in connection.execute("""
                SELECT DISTINCT candidate.id FROM members
                JOIN resources member ON member.id=members.resource_id
                JOIN resources candidate ON candidate.kind=member.kind AND candidate.registry_name=member.registry_name
                    AND (member.metadata IS candidate.metadata OR member.metadata=32767)
                WHERE members.group_id=?
            """ + nbt_clause + " ORDER BY candidate.id", values)]
        resource_id = choice.get("resource_id")
        if resource_id is None:
            return []
        if match["mode"] == "wildcard" or (match["mode"] == "exact" and match.get("nbt_sensitive") is False):
            anchor = self._record(connection, "resources", resource_id)
            clause = "kind=? AND registry_name=?"
            values = (anchor["kind"], anchor["registry_name"])
            if match["mode"] == "exact":
                clause += " AND metadata IS ?"
                values += (anchor["metadata"],)
            if match.get("nbt_sensitive", True):
                clause += " AND nbt=?"
                values += (_json(anchor["nbt"]),)
            return [row[0] for row in connection.execute("SELECT id FROM resources WHERE " + clause + " ORDER BY id", values)]
        return [resource_id]

    def _selected_path(self, connection, path, selections, preferred_input=None):
        if not isinstance(path, dict) or set(path) != {'resource_ids', 'process_ids'}:
            raise DatasetError('main_path must contain resource_ids and process_ids')
        resource_ids, process_ids = path['resource_ids'], path['process_ids']
        if (not isinstance(resource_ids, list) or not isinstance(process_ids, list)
                or not 1 <= len(process_ids) <= 64 or len(resource_ids) != len(process_ids) + 1
                or any(not isinstance(id, str) or not id for id in resource_ids + process_ids)
                or len(set(resource_ids)) != len(resource_ids) or len(set(process_ids)) != len(process_ids)):
            raise DatasetError('A selected path must be a complete simple path of 1 to 64 processes')
        for id in resource_ids:
            self._record(connection, 'resources', id)
        records, selected, unsupported = {}, {}, []
        for index, id in enumerate(process_ids):
            raw = self._record(connection, 'processes', id)
            previous, following = resource_ids[index:index + 2]
            if (raw['executable'] is False or raw['conditions'].get('dynamic_output') == 'unresolved'
                    or not any(o['resource_id'] == following and self._positive_output(o) for o in raw['outputs'])):
                raise DatasetError(f'{id} does not establish the selected material output')
            if any(raw['conditions'].get(k) == 'unresolved' for k in ('dynamic_inputs', 'dynamic_output')):
                unsupported.append({'process_id': id, 'reason': 'Native dynamic recipe semantics are unresolved'})
            narrowed = json.loads(_json(raw))
            selected[id] = {}
            flow_slots = 0
            for slot_index, slot in enumerate(raw['inputs']):
                candidates = [set(self._choice_resources(connection, c)) if c['match']['mode'] != 'native_unknown'
                              and (c['match']['mode'] not in ('unified', 'ore_dict') or c['match'].get('group_id')) else set()
                              for c in slot['choices']]
                requested = selections.get(id, {}).get(str(slot_index), selections.get(id, {}).get(slot_index))
                flow_matches = [i for i, c in enumerate(slot['choices']) if slot['role'] == 'consume'
                                and c['amount'] > 0 and previous in candidates[i]]
                if flow_matches:
                    flow_slots += 1
                if requested is None:
                    if len(flow_matches) == 1:
                        requested = {'choice_index': flow_matches[0], 'resource_id': previous}
                    elif not flow_matches and preferred_input is not None and slot['role'] == 'consume':
                        matches = [i for i, c in enumerate(slot['choices']) if c['amount'] > 0 and preferred_input in candidates[i]]
                        if len(matches) == 1:
                            requested = {'choice_index': matches[0], 'resource_id': preferred_input}
                    if requested is None and len(slot['choices']) == 1 and slot['choices'][0]['match']['mode'] == 'exact':
                        requested = {'choice_index': 0, 'resource_id': slot['choices'][0].get('resource_id')}
                if requested is None:
                    unsupported.append({'process_id': id, 'reason': f'Input slot {slot_index} needs an explicit concrete OR/group selection'})
                    continue
                if not isinstance(requested, dict) or set(requested) != {'choice_index', 'resource_id'}:
                    raise DatasetError('Each input selection must contain choice_index and resource_id')
                ci, rid = requested['choice_index'], requested['resource_id']
                if type(ci) is not int or not 0 <= ci < len(slot['choices']) or not isinstance(rid, str):
                    raise DatasetError('Invalid concrete input selection')
                self._record(connection, 'resources', rid)
                if rid not in candidates[ci]:
                    raise DatasetError(f'{rid} does not match {id} input slot {slot_index}')
                selected[id][str(slot_index)] = dict(requested)
                narrowed_choice = dict(slot['choices'][ci], resource_id=rid,
                                       match={'mode': 'exact', 'nbt_sensitive': True})
                narrowed['inputs'][slot_index]['choices'] = [narrowed_choice]
            if not flow_slots:
                raise DatasetError(f'{id} does not consume the selected preceding resource')
            # Input matching belongs here. Accounting receives resolved concrete facts.
            records[id] = narrowed
        return records, selected, unsupported

    def _path_plan(self, connection, path, first_runs, selections, yield_mode, preferred_input=None):
        from .balance import net_ledger, witness_ledger
        records, selected, unsupported = self._selected_path(connection, path, selections, preferred_input)
        result = {'status': 'unsupported', 'executions': [], 'selected_inputs': selected,
                  'ledger': None, 'startup': None, 'unsupported': unsupported,
                  'native_executability': {id: record['executable'] for id, record in records.items()},
                  'machine_conditions': {id: record['conditions'] for id, record in records.items()},
                  'execution_scope': 'selected_material_accounting_not_machine_execution'}
        if unsupported:
            return result, records, []
        units = {id: net_ledger(records, {id: 1}, yield_mode=yield_mode) for id in path['process_ids']}
        for unit in units.values():
            unsupported.extend(unit['unsupported'])
        if unsupported:
            return result, records, []
        steps, count = [], first_runs
        for index, id in enumerate(path['process_ids']):
            incoming, outgoing = path['resource_ids'][index:index + 2]
            required = units[id]['consumed'].get(incoming, Fraction())
            produced = units[id]['produced'].get(outgoing, Fraction())
            if required <= 0 or produced <= 0:
                unsupported.append({'process_id': id, 'reason': 'Selected flow has no positive consumption or modeled output in this yield mode'})
                return result, records, []
            if index:
                count = available / required
            steps.append({'process_id': id, 'runs': count})
            available = produced * count
        result['executions'] = steps
        result['ledger'] = net_ledger(records, {step['process_id']: step['runs'] for step in steps}, yield_mode=yield_mode)
        result['startup'] = witness_ledger(records, steps, yield_mode=yield_mode)
        result['status'] = result['ledger']['status']
        result['unsupported'] = result['ledger']['unsupported']
        return result, records, steps

    def plan_recycling(self, *, main_path, byproduct_id, return_id, main_runs=1, selections=None,
                       yield_mode='guaranteed', max_depth=12, max_processes=300, max_paths=8,
                       max_extra_steps=2, min_tier=None, max_tier=None, unknown_tier_policy='exclude'):
        """Account bounded selected paths, with external supplies and startup stock explicit."""
        from .balance import quantity, witness_ledger, ledger_json
        try:
            runs = quantity(main_runs)
        except ValueError as exc:
            raise DatasetError(str(exc)) from exc
        if runs <= 0:
            raise DatasetError('main_runs must be positive')
        if yield_mode not in ('guaranteed', 'expected'):
            raise DatasetError('yield_mode must be guaranteed or expected')
        if selections is not None and (not isinstance(selections, dict)
                or any(not isinstance(pid, str) or not isinstance(slots, dict) for pid, slots in selections.items())):
            raise DatasetError('selections must map process IDs to input-slot selections')
        selections = selections or {}
        filters = self._tier_filter(min_tier, max_tier, unknown_tier_policy)
        # The same query owner supplies every secondary path and its full raw recipe records.
        secondary = self.trace_processes(start_id=byproduct_id, target_id=return_id,
            max_depth=max_depth, max_processes=max_processes, max_paths=max_paths,
            max_extra_steps=max_extra_steps, min_tier=min_tier, max_tier=max_tier,
            unknown_tier_policy=unknown_tier_policy, path_selection='shortest')
        with self._connect() as connection:
            for pid, slots in selections.items():
                record = self._record(connection, 'processes', pid)
                for index in slots:
                    if (not isinstance(index, (str, int)) or isinstance(index, bool) or str(index) not in
                            {str(i) for i in range(len(record['inputs']))}):
                        raise DatasetError(f'Invalid input slot selection for {pid}')
            main, main_records, main_steps = self._path_plan(connection, main_path, runs, selections, yield_mode, return_id)
            main.update(byproduct_available=None, return_consumed=None)
            if any(not self._tier_allowed(record, filters) for record in main_records.values()):
                raise DatasetError('The selected main path violates the recipe tier filter')
            result = {'snapshot_id': self.snapshot_id, 'status': 'unsupported', 'main_path': main_path,
                      'byproduct_id': byproduct_id, 'return_id': return_id, 'yield_mode': yield_mode,
                      'main_plan': main, 'alternatives': [], 'secondary_trace': secondary,
                      'byproduct_feed_policy': 'no_additional_byproduct_imports',
                      'ranking': {'criterion': 'net_returned_per_main_consumed',
                                  'scope': 'bounded_discovered_paths', 'global_optimum_proven': False},
                      'limitations': ['Selected dependency paths require every AND input and machine condition',
                                      'Fractional executions are per-unit accounting, not an integer batch execution proof',
                                      'Recovered material does not eliminate startup stock needed before it exists',
                                      'Expected quantities are scenarios and cannot prove available stock',
                                      'Recovery ranking covers bounded discovered paths, not a proven global maximum']}
            if main['status'] != 'complete':
                return ledger_json(result)
            surplus = max(main['ledger']['net'].get(byproduct_id, Fraction()), Fraction())
            demand = main['ledger']['consumed'].get(return_id, Fraction())
            main.update(byproduct_available=surplus, return_consumed=demand)
            if surplus <= 0 or demand <= 0 or byproduct_id == return_id:
                main['unsupported'].append({'process_id': None, 'reason': 'Choose a net surplus main output and a distinct consumed main input'})
                main['status'] = 'unsupported'
                return ledger_json(result)
            for path in secondary['paths']:
                side, side_records, side_steps = self._path_plan(connection, path, Fraction(1), selections, yield_mode)
                alternative = {'path': path, **side, 'combined_ledger': None, 'combined_startup': None,
                               'recovery': None, 'external_inputs': []}
                result['alternatives'].append(alternative)
                if side['status'] != 'complete':
                    continue
                required_feed = side['startup']['required_start_stock'][byproduct_id]
                side, side_records, side_steps = self._path_plan(connection, path, surplus / required_feed, selections, yield_mode)
                alternative.update(side)
                # Distinct occurrences may resolve the same raw recipe to different OR inputs.
                ordered_records, ordered_steps, occurrence_ids = {}, [], {}
                for phase, records, steps in (('main', main_records, main_steps), ('side', side_records, side_steps)):
                    for step in steps:
                        key = f'{phase}:{step["process_id"]}'
                        occurrence_ids[key] = (step['process_id'], phase)
                        ordered_records[key] = dict(records[step['process_id']], id=key)
                        ordered_steps.append(dict(step, process_id=key))
                combined = witness_ledger(ordered_records, ordered_steps, yield_mode=yield_mode)
                def restore_occurrences(value):
                    if isinstance(value, dict):
                        if value.get('process_id') in occurrence_ids:
                            value['process_id'], value['phase'] = occurrence_ids[value['process_id']]
                        for nested in value.values():
                            restore_occurrences(nested)
                    elif isinstance(value, list):
                        for nested in value:
                            restore_occurrences(nested)
                restore_occurrences(combined)
                alternative['combined_startup'] = combined
                alternative['combined_ledger'] = {k: v for k, v in combined.items()
                                                  if k not in ('steps', 'required_start_stock', 'final_stock', 'feasible', 'feasibility_scope')}
                produced = side['ledger']['produced'].get(return_id, Fraction())
                consumed_return = side['ledger']['consumed'].get(return_id, Fraction())
                recovered = max(produced - consumed_return, Fraction())
                alternative['recovery'] = {'resource_id': return_id, 'main_consumed': demand,
                    'side_produced': produced, 'side_consumed': consumed_return, 'net_returned': recovered,
                    'main_input_returned_percent': recovered * 100 / demand,
                    'usable_returned': min(recovered, demand), 'surplus_returned': max(recovered - demand, Fraction())}
                alternative['external_inputs'] = [{'resource_id': id, 'amount': -amount - (surplus if id == byproduct_id else 0)}
                    for id, amount in sorted(side['ledger']['net'].items())
                    if -amount > (surplus if id == byproduct_id else 0)]
            result['alternatives'].sort(key=lambda a: (a['status'] != 'complete',
                -a['recovery']['main_input_returned_percent'] if a['recovery'] is not None else Fraction()))
            if any(a['status'] == 'complete' for a in result['alternatives']):
                result['status'] = 'complete'
            elif result['alternatives']:
                result['status'] = 'unsupported'
            else:
                result['status'] = 'incomplete' if secondary['truncated'] else 'not_found'
            return ledger_json(result)

    def inspect_chemistry(self, resource_id):
        from .balance import inspect_chemistry, ledger_json
        with self._connect() as connection:
            resource = self._record(connection, 'resources', resource_id)
            facts = resource.get('material_facts')
            return ledger_json({'snapshot_id': self.snapshot_id, 'resource_id': resource_id,
                                'material_facts': facts, **inspect_chemistry(facts)})

    def find_loops(self, *, start_id, max_depth=6, max_processes=200, max_paths=20, max_states=5000,
                   min_tier=None, max_tier=None, unknown_tier_policy='exclude',
                   kind='any', chemical_kind='any', yield_mode='guaranteed', selections=None):
        """Discover finite native-matched candidates, then share exact cycle accounting."""
        from .balance import find_loops, ledger_json
        for name, value, maximum in (('max_depth', max_depth, 20), ('max_processes', max_processes, 1000),
                                     ('max_paths', max_paths, 100), ('max_states', max_states, 50000)):
            if type(value) is not int or not 1 <= value <= maximum:
                raise DatasetError(f'{name} must be between 1 and {maximum}')
        if (kind not in ('any', 'gaining', 'lossy', 'conserving') or yield_mode not in ('guaranteed', 'expected')
                or chemical_kind not in ('any', 'balanced', 'gaining', 'lossy', 'mixed', 'unsupported')):
            raise DatasetError('Unsupported loop kind or yield mode')
        if selections is not None and (not isinstance(selections, dict)
                or any(not isinstance(pid, str) or not isinstance(slots, dict) for pid, slots in selections.items())):
            raise DatasetError('selections must map process IDs to input-slot selections')
        selections = selections or {}
        filters = self._tier_filter(min_tier, max_tier, unknown_tier_policy)
        with self._connect() as connection:
            self._record(connection, 'resources', start_id)
            queue, visited, records, raw, choices = deque([(start_id, 0)]), {start_id}, {}, {}, {}
            reasons, tier_checked = set(), set()
            work, work_limit, examined = 0, 100000, 0
            while queue:
                resource_id, depth = queue.popleft()
                examined += 1
                if depth >= max_depth:
                    reasons.add('candidate_depth')
                    continue
                clause, values = self._using_clause(connection, resource_id)
                for row in connection.execute('SELECT id,payload FROM records WHERE collection=\'processes\' AND '
                                               + clause + ' ORDER BY id', values):
                    pid = row['id']
                    if pid in records:
                        continue
                    record = json.loads(row['payload'])
                    if (record['executable'] is False or record['conditions'].get('dynamic_output') == 'unresolved'):
                        continue
                    if not self._tier_allowed(record, filters):
                        if pid not in tier_checked:
                            key = 'excluded_unknown' if self._recipe_tier(record)['tier'] is None else 'excluded_out_of_range'
                            filters[key] += 1
                            tier_checked.add(pid)
                        continue
                    concrete = json.loads(_json(record))
                    carries_input = False
                    for si, slot in enumerate(record['inputs']):
                        resolved = []
                        for ci, choice in enumerate(slot['choices']):
                            match = choice['match']
                            key = _json({'resource_id': choice.get('resource_id'), 'match': match})
                            if key not in choices:
                                choices[key] = (self._choice_resources(connection, choice) if match['mode'] != 'native_unknown'
                                                and (match['mode'] not in ('unified', 'ore_dict') or match.get('group_id')) else [])
                                work += len(choices[key])
                            if work > work_limit:
                                reasons.add('candidate_work_limit')
                                break
                            for rid in choices[key]:
                                resolved.append(dict(choice, resource_id=rid, match={'mode': 'exact', 'nbt_sensitive': True},
                                                     declared_choice_index=ci))
                            if slot['role'] == 'consume' and choice['amount'] > 0 and resource_id in choices[key]:
                                carries_input = True
                        concrete['inputs'][si]['choices'] = resolved
                    if 'candidate_work_limit' in reasons:
                        break
                    if not carries_input:
                        continue
                    if len(records) >= max_processes:
                        reasons.add('candidate_process_limit')
                        break
                    records[pid], raw[pid] = concrete, record
                    for output in record['outputs']:
                        rid = output['resource_id']
                        if not self._positive_output(output) or rid in visited:
                            continue
                        if len(visited) >= max_states:
                            reasons.add('candidate_state_limit')
                            break
                        visited.add(rid)
                        queue.append((rid, depth + 1))
                if reasons & {'candidate_process_limit', 'candidate_work_limit', 'candidate_state_limit'}:
                    break
            resolved_selections = {}
            for pid, slots in selections.items():
                self._record(connection, 'processes', pid)
                if pid not in records:
                    continue
                resolved_selections[pid] = {}
                for si, requested in slots.items():
                    if (str(si) not in {str(i) for i in range(len(records[pid]['inputs']))}
                            or not isinstance(requested, dict) or set(requested) != {'choice_index', 'resource_id'}
                            or type(requested['choice_index']) is not int or not isinstance(requested['resource_id'], str)):
                        raise DatasetError('Invalid loop input selection')
                    resolved = records[pid]['inputs'][int(si)]['choices']
                    matches = [i for i, c in enumerate(resolved) if c['declared_choice_index'] == requested['choice_index']
                               and c['resource_id'] == requested['resource_id']]
                    if len(matches) != 1:
                        raise DatasetError('Selected loop input does not match the declared predicate')
                    resolved_selections[pid][str(si)] = {'choice_index': matches[0], 'resource_id': requested['resource_id']}
            used = {start_id} | {c['resource_id'] for r in records.values() for s in r['inputs'] for c in s['choices']} \
                   | {o['resource_id'] for r in records.values() for o in r['outputs']}
            facts = {}
            ids = sorted(used)
            for offset in range(0, len(ids), 500):
                batch = ids[offset:offset + 500]
                rows = connection.execute('SELECT id,payload FROM records WHERE collection=\'resources\' AND id IN ('
                                          + ','.join('?' for _ in batch) + ')', batch)
                facts.update({row['id']: json.loads(row['payload']).get('material_facts') for row in rows})
            result = find_loops(records, start_id, chemical_facts=facts, selections=resolved_selections,
                                kind=kind, chemical_kind=chemical_kind, yield_mode=yield_mode, max_depth=max_depth, max_processes=max_processes,
                                max_paths=max_paths, max_states=max_states)
            for witness in result['witnesses']:
                for step in witness['steps']:
                    for si, selection in step.get('selections', {}).items():
                        choice = records[step['process_id']]['inputs'][int(si)]['choices'][selection['choice_index']]
                        selection['choice_index'] = choice['declared_choice_index']
            result.update(snapshot_id=self.snapshot_id, start_id=start_id, tier_filter=filters,
                          recipe_tiers=[self._recipe_tier(raw[id]) for id in sorted(raw)],
                          candidate_search={'examined_resources': examined, 'discovered_resources': len(visited),
                                            'processes': len(records), 'expansion_work': work, 'work_limit': work_limit})
            result['limit_reasons'] = sorted(set(result['limit_reasons']) | reasons)
            if reasons:
                result['status'] = 'limited'
            return ledger_json(result)

    @staticmethod
    def _cycles(edges):
        """Iterative SCC discovery avoids recursion limits on long process graphs."""
        adjacency, reverse = {}, {}
        for edge in edges:
            source, target = edge["source"], edge["target"]
            adjacency.setdefault(source, set()).add(target)
            adjacency.setdefault(target, set())
            reverse.setdefault(target, set()).add(source)
            reverse.setdefault(source, set())
        visited, ordered = set(), []
        for start in sorted(adjacency):
            stack = [(start, False)]
            while stack:
                node, expanded = stack.pop()
                if expanded:
                    ordered.append(node)
                elif node not in visited:
                    visited.add(node)
                    stack.append((node, True))
                    stack.extend((next, False) for next in sorted(adjacency[node], reverse=True) if next not in visited)
        visited, components = set(), []
        for start in reversed(ordered):
            if start in visited:
                continue
            component, stack = [], [start]
            while stack:
                node = stack.pop()
                if node in visited:
                    continue
                visited.add(node)
                component.append(node)
                stack.extend(reverse[node] - visited)
            if len(component) > 1 or start in adjacency[start]:
                components.append(sorted(component))
        return sorted(components)
