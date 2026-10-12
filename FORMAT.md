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
EnderIO baselines retain total RF in `conditions.total_rf`, with EU/t and
duration null. Native float chance thresholds remain beside canonical
fractions. The no-ball native comparison includes equality on the 24-bit
`Random.nextFloat()` lattice, and all outputs share the same roll. These
fractions do not imply independent co-product events or grinding-ball yields.

### Source

`{id, kind, display_name, outputs, environment_ids, status, conditions,
parameters, provenance}`

Kinds include `ore_vein`, `small_ore`, `underground_fluid`, `ore_mining`, `drop`, `trade`.
Each output has `resource_id` and optional amount/chance/material-role fields.
Unknown source yields are not replaced with 1. A generated block and its
mining drops must remain distinguishable. `status` is `active`, `conditional`,
`disabled` or `unknown`. Environment IDs refer to environment records.
Preserve native generator keys, material roles, height ranges, weights,
dimension gates, stone/region conditions and depletion parameters.
Relative generator weight is not a per-chunk occurrence probability.
An output tagged `resource_semantics: generated_ore_block_not_mining_drop`
describes a world block. It remains searchable but cannot establish inventory
availability or seed a dependency cycle. This applies per output, so ordinary
inventory outputs in the same source retain their own availability semantics.
Normal GT `ore_mining` sources retain Fortune 0 plain and silk branches.
`parameters.generated_source_id` links the generator, while
`generated_resource_id` identifies its world block. Outputs tagged
`mined_item_baseline` describe native base drops with quantities and certainty
conditioned on qualifying harvest, not deposit occurrence. Conditions retain
generation, drop mode, material, stone, natural flag and harvest requirements.
Tool/event modifiers and final delivery are outside this baseline scope.

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

## Independent NEI reference

An opt-in paired capture adds `nei-reference/summary.json` and three gzip
JSONL streams: `handlers.jsonl.gz`, `signatures.jsonl.gz` and
`handler-views.jsonl.gz`. This reference is separate from the authoritative
six-stream snapshot and does not become another recipe identity model.

The summary binds `canonical_snapshot_id` and `canonical_pack` to the exact
canonical manifest. It records the native NEI version and JAR hash, readiness,
projection labels, counts, failures and compressed stream checksums. Reference
files publish before the canonical manifest. Partial handler or record errors
remain explicit through `complete: false` and failure counters.

`native_recipe_id_api` signatures invoke NEI's native RecipeId API. They are
not an invocation of `/recipeid fast-dump`, and its blacklist is not applied.
Raw views preserve `ingredients`, `result` and `other_stacks`
separately. Auxiliary stacks can be furnace fuel, so they do not universally
represent products. GT-specific views retain real quantities and native
presentation fields. Generic presentation chances are not production chances.

`presentation-context.json` schema 1 binds the same snapshot and pack, plus
the closed canonical resource/process count and hash declarations. Its pointer
in `summary.files` contains its SHA-256. The context declares two checksummed
gzip JSONL streams, `gt-display-aliases.jsonl.gz` and `item-pools.jsonl.gz`.
Direct GT aliases are keyed by canonical resource ID and queried from the
original reconstructed stack at quantity one. Item pools are keyed by registry
name. Both retain ordered `{registry_name, metadata, nbt, amount}` entries
with lossless typed NBT. Status distinguishes successful, empty and failed
queries. Unregistered canonical anchors remain explicit top-level failures.

Context capture runs before handler enumeration and reads no observed recipe
views to establish expected alternatives. Scope is the four mapped GT families
and furnace. GT aliases precede wildcard expansion, whose pool metadata and
NBT replace the declaration's while the declared quantity is retained.
Empty native pools follow the pinned metadata-zero presentation rule.
The comparator uses successful records from partial context but reports its
failures. Incomplete advertised context cannot pass validation thresholds.
Without context, dependent alias/wildcard projections remain unsupported.

The comparator validates all canonical and reference streams and the paired
cohort before applying its version-pinned adapter allowlist. It reports
matching, differing, missing and unsupported projections separately, with
bounded examples and scope limits. Default thresholds require no differences,
missing matches or capture failures. An unmapped predicate is not an exact
negative. NEI NBTJson is not injective, so ambiguous projections remain
unsupported rather than being equated by display name or lossy NBT decoding.

## Dataset operations

The same operations serve HTTP, CLI and MCP. Opening a Dataset fixes one
snapshot identity. Import verifies checksums, counts and references, builds
a replacement SQLite index, then activates it. A failed import preserves
the existing usable index. Never accept a silently lossy import.

Initial operations are `status`, `find_resources`, `get_resource`,
`find_processes`, `get_process`, `get_group`, `find_sources`,
`get_source`, `find_environments` and `trace_processes`.

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
- `/sources?resource_id=&environment_id=&offset=&limit=` and `/sources/{id}`
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
cycles, truncated, coverage, route, paths, search, limit_reasons,
duplicate_process_records}`

`route` contains `status`, `strategy`, ordered `resource_ids` and ordered
`process_ids`. The strategy is `shortest_known_dependency_path`: fewest process
steps in the discovered graph through supported positive consumed inputs,
with stable ID ordering for ties. Presence and tool inputs are requirements,
not material-flow transitions.
The statuses are `found`, `not_found`, `incomplete` and `same_resource`.
`found` establishes a dependency connection, not best yield, minimum energy,
batch feasibility or satisfaction of every machine condition.
`not_found` is scoped to the captured supported graph. An identical start and
target gives `same_resource` with one resource and no process steps.

`paths` contains ordered `{resource_ids, process_ids}` records. `route`
identifies the first qualifying path. The returned process IDs are exactly
the union of complete emitted paths. Only transitions belonging to those
paths become recipe-to-recipe connections in the GUI.

`max_paths` defaults to 8 and accepts 1..100. `max_extra_steps` defaults to 2
and accepts 0..64, relative to the shortest qualifying path. `max_depth`
accepts 1..64 and bounds total path steps. `max_processes` accepts 1..5000
and bounds the union of distinct recipes. Each path is included whole or
omitted. A path that cannot fit is never represented as a successful fragment.

`required_resource_ids` and `excluded_resource_ids` are arrays of exact
snapshot resource IDs. Every required ID must occur along the material path,
and every excluded ID must be absent. Intrinsic side ingredients, presence
requirements and co-products do not satisfy an intermediate constraint.
HTTP uses repeated singular `required_resource_id` and `excluded_resource_id`
query parameters. CLI uses repeatable `--required-resource-id` and
`--excluded-resource-id`. MCP uses the plural array arguments.

Search discovers target ancestors once per resource through indexed output
references, then enumerates simple paths in the discovered graph. A path
does not repeat a resource or process, so cycles cannot create infinite
enumeration. Bounds and incomplete capture can leave further paths unknown.
Native-unknown matches, ungrouped unified/ore-dictionary matches, disabled
recipes and definite zero outputs cannot establish material transitions.
Recipes with `conditions.dynamic_output="unresolved"` also cannot establish
transitions. Their output records may describe native display templates,
which remain inspectable without being treated as verified runtime products.
Trace coverage reports these recipes under `trace.outputs`. An unresolved
producer keeps its boundary unresolved when no captured source establishes it.
GT crafting may retain declared inherited predicates in `declared_match`
while its authoritative `match.mode` remains `native_unknown`. Those declared
predicates do not establish complete matching when inventory validators or
cross-slot NBT conditions remain uninterpreted. `declared_stack_size` retains
the original declaration beside normalized crafting input quantities.
Zero-amount and zero-chance outputs also cannot ground a dependency cycle or
count as material production. Their raw records remain available for inspection.

Included recipes retain complete AND slots, OR choices, presence/tool
requirements, co-products and conditions. These records can expose unsupplied
side ingredients. They do not automatically admit additional producers,
recycling recipes or alternatives outside an emitted A-to-B path.

`duplicate_process_records` contains `{representative_id, duplicate_ids}`.
Only identical captured recipe data is grouped, ignoring record ID and
`provenance.index`. Other provenance, classes, amounts, matching, chances,
energy and conditions remain part of equality. The raw catalog is unchanged.

`search` reports `examined_processes`/`limit` (10,000),
`examined_states`/`state_limit` (20,000), `queued_states`, `peak_queue`,
`expansion_work`/`work_limit` (100,000),
`enumeration_work`/`enumeration_limit` (100,000), and `truncated`.

`limit_reasons` distinguishes `depth`, `path_limit`, `path_process_limit`,
`search_process_limit`, `search_state_limit`, `search_work_limit` and
`search_enumeration_limit`. Top-level `truncated` is true if any applies.
Found paths can coexist with an incomplete search for further paths.
Paths and cycles are not claimed exhaustive across the whole snapshot.

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
a material source. Truncation is explicit for discovery and enumeration.
Discovery is not a whole-factory optimization or a proof of progression.

## Stack decision

Java/GTNHGradle captures the running Forge 1.7.10 pack. Python 3.11+ owns
Dataset with standard-library SQLite/FTS5, gzip and JSON. FastAPI exposes
local HTTP, Uvicorn runs it, and the official Python MCP SDK exposes stdio.
React/TypeScript/Vite provides the human UI. This gives GUI and agents one
domain implementation. A separate TypeScript query engine would duplicate
matching and acquisition semantics, so the UI remains a client. A native
desktop wrapper is not required for the local browser UI.
