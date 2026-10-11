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

    def find_resources(self, *, q="", kind=None, offset=0, limit=50):
        if kind not in (None, "item", "fluid"):
            raise DatasetError("kind must be item or fluid")
        self._pagination(offset, limit)
        tokens = _search_words(q)
        with self._connect() as connection:
            if not tokens:
                return self._page(connection, "resources", "json_extract(payload,'$.kind')=?" if kind else "1", (kind,) if kind else (), offset=offset, limit=limit)
            alternatives = self._resource_search_terms(connection, tokens)
            expression = " AND ".join("(" + " OR ".join(f'"{word}"*' for word in sorted(words)) + ")" for words in alternatives)
            clause = "search MATCH ? AND search.collection='resources'"
            parameters = (expression,)
            if kind:
                clause += " AND resources.kind=?"
                parameters += (kind,)
            tables = "search JOIN resources ON resources.id=search.id JOIN records ON records.collection='resources' AND records.id=search.id"
            total = connection.execute(f"SELECT COUNT(*) FROM {tables} WHERE {clause}", parameters).fetchone()[0]
            connection.create_function("resource_search_rank", 4, self._resource_search_rank(q, tokens, alternatives), deterministic=True)
            rows = connection.execute(f"""SELECT records.payload FROM {tables} WHERE {clause}
                ORDER BY resource_search_rank(resources.id,resources.registry_name,json_extract(records.payload,'$.display_name'),search.text),resources.id
                LIMIT ? OFFSET ?""", (*parameters, limit, offset))
            return {"snapshot_id": self.snapshot_id, "items": [json.loads(row[0]) for row in rows], "total": total, "offset": offset, "limit": limit}

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

    def _find_paths(self, connection, start_id, target_id, max_depth, max_processes, max_paths, required, excluded, max_extra_steps):
        search = {"examined_processes": 0, "limit": 10000, "examined_states": 0, "state_limit": 20000,
                  "expansion_work": 0, "work_limit": 100000, "enumeration_work": 0, "enumeration_limit": 100000,
                  "queued_states": 0, "peak_queue": 0, "truncated": False}
        route = {"status": "not_found", "strategy": "shortest_known_dependency_path", "resource_ids": [], "process_ids": []}
        paths, records, choices, adjacency = [], {}, {}, {}
        fingerprints, duplicate_ids = {}, {}
        reasons, admitted = set(), set()
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

    def trace_processes(self, *, start_id, target_id, max_depth=12, max_processes=300, max_paths=8,
                        required_resource_ids=None, excluded_resource_ids=None, max_extra_steps=2):
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
            route, paths, search, limit_reasons, duplicates = self._find_paths(connection, start_id, target_id, max_depth, max_processes, max_paths, required, excluded, max_extra_steps)
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
            unresolved_boundaries = set()
            for resource_id in resources:
                rows = connection.execute("SELECT DISTINCT payload FROM records JOIN source_outputs ON source_outputs.source_id=records.id WHERE collection='sources' AND resource_id=? ORDER BY records.id", (resource_id,))
                sources = [json.loads(row[0]) for row in rows]
                source_ids[resource_id] = [source["id"] for source in sources]
                if connection.execute("SELECT 1 FROM records WHERE collection='processes' AND id IN (SELECT process_id FROM outputs WHERE resource_id=?) AND (" + self._unresolved_input_clause()
                                      + " OR json_extract(payload,'$.conditions.dynamic_output')='unresolved') LIMIT 1", (resource_id,)).fetchone():
                    unresolved_boundaries.add(resource_id)
                if resource_id == start_id:
                    source_states[resource_id] = "assumed"
                elif any(source["status"] == "active" and not source["conditions"] for source in sources):
                    source_states[resource_id] = "available"
                elif any(source["status"] in ("active", "conditional") for source in sources):
                    source_states[resource_id] = "conditional"
                elif any(source["status"] == "unknown" for source in sources) or incomplete_sources or resource_id in unresolved_outputs or resource_id in unresolved_boundaries:
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
                if resource_id in cyclic_resources and resource_id not in grounded:
                    leaf["reason"] = "A cycle needs an external acquisition source or an explicit supplied seed"
                elif resource_id in unresolved_outputs | unresolved_boundaries and leaf["status"] == "unresolved":
                    leaf["reason"] = "Producer inputs, matching or outputs are unresolved"
                leaves.append(leaf)
            return {"snapshot_id": self.snapshot_id, "start_id": start_id, "target_id": target_id,
                    "resources": [resources[id] for id in sorted(resources)], "processes": [processes[id] for id in sorted(processes)],
                      "edges": edges_list, "leaves": leaves, "cycles": cycles, "truncated": bool(limit_reasons), "coverage": coverage,
                      "route": route, "paths": paths, "search": search, "limit_reasons": sorted(limit_reasons), "duplicate_process_records": duplicates}

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
