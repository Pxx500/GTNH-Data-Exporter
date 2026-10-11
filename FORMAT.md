# Snapshot format and shared query contract

Schema version: 1. This is the forward-only development format.

The runtime exporter owns capture of native mechanics. The Python `Dataset`
owns validation, indexing, matching and graph queries. HTTP, CLI and MCP
call that same owner. The UI renders its results and does not interpret
native GT recipe conventions independently.

## Snapshot

A snapshot directory contains `manifest.json` and six UTF-8 gzip JSONL files:
`resources.jsonl.gz`, `groups.jsonl.gz`, `processes.jsonl.gz`,
`sources.jsonl.gz`, `environments.jsonl.gz`, `coverage.jsonl.gz`.
Each line is one JSON object. Empty collections are empty gzip streams.

The manifest has `schema_version: 1`, `snapshot_id`, `created_at`,
`capture` (exporter version and lifecycle/context), `pack` (actual mod
versions and hashes, config/script digests where captured), and `files`.
The `files` object maps each exact filename to `{sha256, records}`.
Runtime capture includes `world_seed` as a decimal string, preserving all
64 bits of the isolated world's seed.
Checksums cover the compressed bytes. Publish the manifest only after
closing all streams. Never treat an interrupted directory as a valid snapshot.

IDs are opaque strings, unique within their record collection and scoped to
the snapshot. The writer resolves resource identity and assigns references.
Readers do not recompute IDs or strip NBT. Preserve unknown extension fields.
Missing semantic knowledge is expressed through coverage and explicit unknown
statuses, rather than invented defaults.

### Resource

`{id, kind, registry_name, metadata, nbt, display_name, provenance}`

`kind` is `item` or `fluid`. Item metadata is an integer. Fluid metadata can
be null. `nbt` is null or a typed tag `{type, value}`. A compound value maps
keys to typed tags, a list value is an array of typed tags. Preserve native
numeric types and arrays. Names are presentation, registry identity is not.
Lists retain `element_type_id`, including the native type of an empty list.
NBT `long` values use decimal strings so JavaScript clients preserve all
64 bits. Other finite numeric tag values use JSON numbers.

### Group

`{id, kind, name, members, provenance}`

`members` is an array of resource IDs. Initially `kind: ore_dict` represents
membership, not a conversion process. Groups can be fetched by ID rather
than expanded in every query result.

### Process

`{id, family, display_name, inputs, outputs, duration_ticks, eu_per_tick,
amperage, executable, conditions, provenance}`

All `inputs` slots are required together. Each slot is
`{role, choices}`. Roles are `consume`, `presence` or `tool`.
Each choice is `{resource_id, amount, match}` with optional extension fields.
Choices within a slot are alternatives. `match` is an object with `mode`
(`exact`, `wildcard`, `ore_dict`, `unified`, `native_unknown`) and a
`group_id` when applicable. For a group-only ingredient, `resource_id` can
be null and membership is carried by `match.group_id`. Presence amount is
the amount required to be present, not amount consumed. Preserve native
amount zero separately if useful for provenance. Tool wear and returned
containers are explicit extensions, never silently treated as consumed items.
An unregistered native item is retained as a `native_unknown` choice with
`resource_id: null` and a `native_item` record containing its class, amount,
metadata, typed NBT and display name. It does not become a fabricated registry
resource. A missing group reference is omitted rather than emitted as null.
`match.nbt_sensitive` can explicitly specify native NBT behavior. Exact
matching compares NBT unless this field is false. Wildcard matching ignores
metadata and follows the same explicit NBT setting. A group's wildcard
members retain their native metadata predicate. `consumption_chance` on a
slot or choice uses `{numerator, denominator}` and is distinct from output
chance and presence requirements. These fields are shared Dataset semantics.

Each output is `{resource_id, amount, chance}`. `chance` is null when
unknown or `{numerator, denominator}`. A guaranteed output uses 1/1.
All co-products remain in one process. Preserve quantities per alternative.
`executable` is true, false for informational/fake records, or null when
unknown. Conditions and source-specific metadata are structured objects.
Timing or energy can be null when absent or not established. Research is
a condition rather than a consumed item in every production operation.

### Source

`{id, kind, display_name, outputs, environment_ids, status, conditions,
parameters, provenance}`

Kinds include `ore_vein`, `small_ore`, `underground_fluid`, `drop`, `trade`.
Each output has `resource_id` and optional amount/chance/material-role fields.
Unknown source yields are not replaced with 1. A generated block and its
mining drops must remain distinguishable. `status` is `active`, `conditional`,
`disabled` or `unknown`. Environment IDs refer to environment records.
Preserve native generator keys, material roles, height ranges, weights,
dimension gates, stone/region conditions and depletion parameters.
Relative generator weight is not a per-chunk occurrence probability.

### Environment

`{id, name, dimension_id, provider, properties, provenance}`

Numeric dimension ID and provider may be null when mapping is unresolved.
The catalog includes registered dimensions, not just loaded worlds.
Generation definitions describe conditional possibility, not observed deposits.
Saved-world observations are a separate future domain.

### Coverage

`{id, domain, status, records, reason, provenance}`

Status is `complete`, `partial`, `unsupported` or `error`. Completeness is
limited to the named owner/domain. A completed GT map enumeration does not
mean all recipes or all acquisition routes in the pack are understood.
Dynamic recipe behavior, unresolved matching and other-mod acquisition must
remain visible. High record counts are not evidence of complete semantics.

## Dataset operations

The same operations serve HTTP, CLI and MCP. Opening a Dataset fixes one
snapshot identity. Import verifies checksums, counts and references, builds
a replacement SQLite index, then activates it. A failed import preserves
the existing usable index. Never accept a silently lossy import.

Initial operations are `status`, `find_resources`, `get_resource`,
`find_processes`, `get_process`, `get_group`, `find_sources`,
`find_environments` and `trace_processes`.

List results are `{snapshot_id, items, total, limit, offset}`. Use explicit
pagination, default 50 and maximum 500. Exact-resource lookup includes
supported ingredient predicates, not only literal reference equality.
Unsupported matching is reported as unresolved, never as an exact negative.
No client reconstructs semantics from tooltip strings.
Single-record results are `{snapshot_id, item}`. Status returns
`{snapshot_id, manifest, counts, coverage}`, with counts per record collection
and coverage as an array of coverage records. Filtered process lists also
report `matching_complete` and `unresolved_matches` where native predicates
cannot be evaluated. These flags do not substitute for source coverage.

`find_resources(q=...)` searches display names, registry identifiers and
snapshot resource IDs. Words can be reordered or shortened to prefixes.
Alphabetic words of 3 to 64 characters also accept one insertion, deletion,
substitution or adjacent transposition, such as `iron pltae`.
Results rank exact resource IDs, exact registry identifiers, full display
names, reordered display names, exact tokens, prefixes and typo matches in
that order. Resource ID breaks ties. Pagination follows this order and
`total` counts every matching resource. Broad queries cost more because all
matching candidates are ranked. No import or schema change is required.

Search proposes concrete identities. Equally named metadata or NBT variants
remain distinct. Callers choose an ID before process lookup or tracing.
The GUI performs that selection through autocomplete. MCP and CLI callers
use `find_resources` followed by the operation on the chosen ID.
This is lexical discovery with typo tolerance, without synonym inference,
translation or embeddings. It does not change ingredient matching semantics.

HTTP routes are read-only under `/api`:

- `/status`
- `/resources?q=&kind=&offset=&limit=` and `/resources/{id}`
- `/processes?input_id=&output_id=&family=&offset=&limit=` and `/processes/{id}`
- `/groups/{id}`
- `/sources?resource_id=&environment_id=&offset=&limit=`
- `/environments?q=&offset=&limit=`
- `/trace?start_id=&target_id=&max_depth=12&max_processes=300`

The server binds to localhost. It serves the built SPA on the same origin.
The MCP transport uses stdio and does not require the HTTP server or GUI.
Successful MCP results carry the data in `structuredContent` and a brief
text summary. They do not repeat the complete JSON in both fields.
Transport code delegates operations and translates errors, without another
database model or matcher.

## Trace result

`{snapshot_id, start_id, target_id, resources, processes, edges, leaves,
cycles, truncated, coverage}`

Edges identify resource/process nodes using `{source, target, role}`.
Node references are `resource:<raw ID>` and `process:<raw ID>`.
`cycles` is an array of arrays of these node references describing strongly
connected groups, not necessarily ordered cycle paths.
A finite result keeps each process once and uses references for cycles.
The graph preserves every input slot of included processes, all outputs and
conditions. The declared start resource is an explicit supplied assumption.
Each boundary leaf records `{resource_id, status, sources}`.
`sources` is an array of source IDs, with an optional explanatory `reason`.
Leaf status is
`assumed`, `available`, `conditional`, `unresolved` or `no_known_source`.
The last status is scoped to captured data and is never a proof of global
impossibility with incomplete source coverage. Cycles alone do not establish
a material source. Truncation is explicit and includes dependency expansion.
Discovery is not a whole-factory optimization or a proof of progression.

## Stack decision

Java/GTNHGradle captures the running Forge 1.7.10 pack. Python 3.11+ owns
Dataset with standard-library SQLite/FTS5, gzip and JSON. FastAPI exposes
local HTTP, Uvicorn runs it, and the official Python MCP SDK exposes stdio.
React/TypeScript/Vite provides the human UI. This gives GUI and agents one
domain implementation. A separate TypeScript query engine would duplicate
matching and acquisition semantics, so the UI remains a client. A native
desktop wrapper is not required for the local browser UI.
