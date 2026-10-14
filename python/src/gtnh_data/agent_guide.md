# GTNH query workflows for agents

Use the connected snapshot to answer a specific question. Start with a small
lookup, select exact identities, then choose the analysis that proves what the
user asked. This server has 25 tools. It shares one Dataset owner with the GUI
and CLI. Tool schemas are the authority for current arguments and bounds.

Read this guide once through the MCP resource
`gtnh-data://guide/query-workflows`. Successful tools put their data once in
`structuredContent`. The text content is a short receipt, not another result.

## Choose the operation

| Question | Tools | What the result establishes |
|---|---|---|
| Which capture is connected, and what is covered? | `status` | Snapshot identity, manifest, counts and named capture coverage. A large count is not pack-wide completeness |
| Which item or fluid does the user mean? | `find_resources`, then `get_resource` if needed | Separate registry, metadata and typed-NBT identities, with acquisition hints. Names and unification preferences do not merge identities |
| Which recipes make or use this resource? | `find_processes`, then `get_process` for selected IDs | Captured declarations, full AND input slots, OR choices, outputs, conditions and provenance. Input lookup reports unresolved matching |
| What does a group accept? | `get_group` | Captured group membership. Exact matching still depends on the choice's mode, wildcard metadata and NBT sensitivity |
| How can the item enter the system? | `inspect_acquisition`, `find_sources`, `get_source`, `find_environments` | Bounded structural evidence and configured sources, including generator links and dimension context. Missing evidence is not absolute unobtainability |
| Can A contribute to B through known recipes? | `trace_processes` | Bounded consume dependency paths with complete selected recipes. A path does not supply all its side inputs or prove quantities |
| Is material-flow search prepared for this snapshot? | `flow_index_status`, optionally `rebuild_flow_index` | Read derived-index readiness or explicitly rebuild its sidecar offline. Preparation changes search data, not captured recipe facts |
| What returns a chosen main-path byproduct? | `plan_recycling` | Bounded C-to-D alternatives, exact net recovery and external inputs, tied to a chosen main path |
| What are all required external inputs for a target? | `plan_to_bases` | Whole-recipe balanced plans under an explicit saved base-resource profile, with net imports and separate startup requirements |
| Is a regenerative network cheaper than this recipe? | `audit_energy` | Exact verified bounded network witnesses that net-consume the primary feed, compared at equal target quantity using nominal recipe EU |
| Does a resource-return loop gain or lose anything? | `find_loops`, optionally `inspect_chemistry` | Bounded loop witnesses, returned-resource ratios and separate source-backed chemical accounting. Gain is not automatically free or autonomous |
| Which catalog or recipe-cost differences merit inspection? | `analyze_statistics`, then `get_process` | Scoped descriptive distributions and comparable captured-predicate cost spreads. Findings are candidates, not confirmed bugs |
| How should the search boundary change? | `list_boundary_profiles`, `get_boundary_profile`, `get_scope_catalog`, `find_resource_groups` | Read existing user assumptions and available exclusion identifiers |
| Should those assumptions be persisted? | `save_boundary_profile`, `delete_boundary_profile` | These two tools mutate user sidecars. Use them only when a profile change is intended, with the observed revision |

There is no exposed generic SQL tool or separate `plan_network` MCP tool.
Use `plan_to_bases` or `audit_energy` for balanced network analysis. Do not
build another client-side solver by stitching trace spines together.

## Prefer a material route when the question is about a construction chain

Use `path_selection="material"` to prioritize continuity suggested by native
material facts. This mode helps investigate the material contribution to a
target, such as iron through steel into a casing. It does not prove that all
other ingredients are supplied, conserve chemical accounting by itself, or
optimize yield or energy. Inspect `path_details`, target input branches and
the full recipes. Material mode selects one representative spine per target
ingredient branch. It does not enumerate every upstream variant. Byproduct
transitions remain valid alternatives. The GUI defaults to this policy. Agent,
CLI and HTTP calls retain `diverse` as the default, so request `material`
explicitly when that is the intended question.

Material mode gives lower priority to captured recovery recipes that dismantle
an explicitly composed component, or turn a crafted form back into dust of the
same primary material. This is a soft preference. Required recovery paths and
byproduct paths remain eligible. Unknown material roles receive no extra
recovery weight. It does not certify source-atom transfer, chemical purity or
lossless recycling. Inspect `search.recovery_preference` for the weight and
candidate fact lookups. This metadata is read per query, without a new index
version or a game dump. The extra lookups can increase query time.

`path_selection="diverse"` spreads routes across target ingredient branches.
`path_selection="shortest"` prefers fewer steps. Neither means lower EU or
better ore utilization. Choose the policy explicitly when comparing results.

Material search needs a prepared index. Call `flow_index_status` if readiness
is unknown. If its status is `missing` or `incompatible`, use
`rebuild_flow_index` once. It writes replaceable derived data next to the
imported database and may take longer than a lookup. Do not rebuild before
every trace. New imports prepare this data automatically. A rebuild needs
the imported dump, not a running game. An incompatible index is not silently
used as if it belonged to the current snapshot or analysis version.

Material search uses partial successor expansion. Each admitted cursor entry
is one concrete child path and counts against `queued_states`. Its next sibling
is admitted when that entry is processed. Deferred descriptors are not already
explored paths. Inspect `search.partial_expansion` for their current and peak
counts, candidate validations and cursor lifecycle. A small heap does not mean
those descriptors or their work disappeared. `path_limit` and missing target
branches still prevent a completeness claim.

Voltage bounds restrict captured recipe voltage requirements. Verified static
GT shaped crafting-grid declarations can report tier status `not_applicable`
with a null tier. They need no machine voltage and pass those bounds. This is
an explicit native marker checked against its declaration context. Null EU by
itself does not imply that status, free energy or resolved tool returns. Other
unknown tiers continue to follow `unknown_tier_policy`.

## Interpret resource origin separately from planning boundaries

A producer in the dump is evidence of a recipe, not proof that its entire
input chain is obtainable. A world source describes origin even if recycling
recipes also exist. Keep generated ore blocks separate from actual mining
drops and rule candidates. Conditions and dimension definitions matter.

Initial-processing classifications are bounded heuristics with evidence,
not a claim that every downstream product is a basic resource. Renewable
status cannot be inferred merely from a cycle. A suggested basic resource
does not change a profile. The profile's selected basics remain explicit
external-feed assumptions, regardless of origin evidence.

## Keep calls small and preserve identity

Call `status` when the snapshot or coverage is unknown, then retain its
`snapshot_id`. Search names with `find_resources(q=..., kind=..., limit=8)`.
Search is tolerant of word order, prefixes and modest typos. Inspect registry,
metadata, NBT and `acquisition_analysis` before choosing an ID. Equally named
items can have different producers. A captured unification anchor is a useful
preference, not proof that every gameplay operation replaces its aliases.

Use `find_processes` with an input or output ID and a small limit. Both filters
together mean both must match. Follow selected records with `get_process`.
Use `get_group` only when the matching group matters, since some groups are
large. For sources, follow `parameters.generated_source_id` directly with
`get_source`, rather than enumerating the source catalog.

New captures may retain `native_source_refs` in `get_resource` records. Catalog
anchors identify an exact registered stack and its native enum symbol. Machine
references identify a registered template whose resolver ignores NBT. These
are source facts for investigating opaque components, not inferred functional
roles, atom contribution, available stock or configured machine capability.
Check capture coverage before interpreting missing references. The active
immutable snapshot may predate this collector. Do not invent references from
the resource's display name or copy IDs between captures.

Page results retain honest `total`, `offset` and `limit`. Ask for later pages
only when the question needs them. There is no server-side `fields` projection
parameter. Keep a compact working summary and retain IDs for detail calls.
Do not repeat the full manifest, every discovered resource, all group members
or the whole statistics payload in a final answer.

MCP traces default to `view="compact"`. This retains every selected recipe in
full, all declared input choices and outputs, endpoints and actual path
resources. It omits expanded matching variants from resource, edge and leaf
lists. Read `presentation.omitted_counts`, aggregate omitted leaf evidence and
`grouped_match_refs` before interpreting boundaries. Those references describe
the native matching predicate and the scope of the reported candidate counts.
A matching group is not a set of extra required inputs.

Use `view="full"` when expanded OR, wildcard or NBT-insensitive candidates
matter. `get_group` retrieves literal captured members, which may differ from
the fully expanded predicate. Full cycle references remain unchanged in compact
results and may refer to unembedded candidate IDs. Fetch selected identities
with `get_resource` when needed. Compact view reduces presentation, not search
or uncertainty. Dataset, HTTP and CLI traces retain `full` as their default.

## Executable request examples

Each JSON block is a `tools/call` params object. The MCP client supplies the
JSON-RPC envelope. **All `r...` and `p...` IDs below are examples bound only to
snapshot `779ea030-ae9c-40ea-8854-99a176f7cc42`.** Resolve names first in any other
snapshot. Profile IDs are user configuration, not captured recipe IDs.

### Resolve names, then inspect

```json
{"name":"find_resources","arguments":{"q":"iron dust","kind":"item","limit":8}}
```

```json
{"name":"find_processes","arguments":{"output_id":"r5090","limit":5}}
```

For a source question, start with `inspect_acquisition` for the selected item.
An Amber example in the named snapshot has a small-ore source. Its top-level
candidate list does not declare fixed yields or independent drop chances:

```json
{"name":"find_sources","arguments":{"resource_id":"r10572","limit":2}}
```

Follow the returned source ID and generator parent. Inspect `environment_ids`
and the matching environment record. `dimension_id: null` remains unresolved,
even when the environment has a familiar name.

### Discover dependency routes

```json
{"name":"trace_processes","arguments":{"start_id":"r5090","target_id":"r41034","max_paths":2,"max_processes":80,"max_depth":12,"max_extra_steps":6,"path_selection":"diverse"}}
```

This asks how GT Iron Dust can contribute to the Volcanus Controller. It does
not mean Iron Dust alone crafts it. Inspect the returned `paths`, `route`,
`branch_coverage`, `leaves`, `limit_reasons` and all inputs of included recipes.
Branch coverage describes target ingredient dependency spines, not alternative
complete crafting plans. `shortest` means fewest dependency steps, not minimum
materials or EU. `required_resource_ids` and `excluded_resource_ids` constrain
actual path resources. Presence tools and coproducts are not path steps.

### Analyze a selected byproduct

This snapshot's `p46285` chemical bath consumes Water and Sodium Dust and
produces Hydrogen plus Sodium Hydroxide Dust. A chosen one-step main path can
ask whether its hydroxide returns consumed sodium:

```json
{"name":"plan_recycling","arguments":{"main_path":{"resource_ids":["r31497","r32727"],"process_ids":["p46285"]},"byproduct_id":"r7416","return_id":"r7406","main_runs":1,"max_paths":2,"max_depth":6,"yield_mode":"guaranteed","selections":{"p46285":{"0":{"choice_index":0,"resource_id":"r7406"}}}}}
```

For another main path, reuse an emitted trace path and inspect its records
first. `selections` use canonical input-array slot indexes as string keys and
zero-based choice indexes. They do not use `native_slot` indexes. A selected
resource must satisfy the declared predicate. Keep every additional AND input,
presence requirement and coproduct. Read `recovery`, `external_inputs`,
`ledger` and `combined_startup`. Returned percentages measure net returned D
against D consumed by the main plan. They are not overall factory efficiency.

### Expand a target from explicit basics

Read existing profiles first. If the user intends to save Steel Ingots and a
programmed circuit as external boundaries, the following creates a new profile
in the named snapshot. `expected_revision: 0` prevents overwriting an existing
profile. For an update or deletion, pass the revision returned by the getter.

```json
{"name":"save_boundary_profile","arguments":{"profile_id":"example-lv-steel","name":"LV casing from steel ingots","base_resource_ids":["r11342","r32557"],"scope":{"excluded_namespaces":["TConstruct","TGregworks"]},"expected_revision":0}}
```

```json
{"name":"plan_to_bases","arguments":{"target_id":"r37874","profile_id":"example-lv-steel","target_amount":1,"objective":"recipe_runs","max_solutions":2,"max_variants":128,"timeout_seconds":10,"yield_mode":"guaranteed"}}
```

Here the target is the LV Machine Casing. `recipe_runs` minimizes normalized
recipe executions within searched candidates, not raw-material consumption.
Compare each solution's `net_imports`. A target already tagged as base returns
`boundary` and `base_requirements` with no invented recipe. Otherwise inspect
`base_boundary.unresolved_startup`, presence and integer-batch startup before
calling the plan fully grounded. A base tag permits an external feed. It does
not prove inventory, a mineable deposit or dimensional access.

### Audit nominal energy

```json
{"name":"audit_energy","arguments":{"primary_feed_id":"r31497","target_id":"r32727","benchmark_process_id":"p60127","target_amount":2000,"allowed_feed_ids":["r31497"],"max_solutions":2,"max_variants":128,"max_columns":128,"max_rows":512,"timeout_seconds":10,"yield_mode":"guaranteed"}}
```

This compares Water-to-Hydrogen networks with a selected electrolyzer recipe.
Inspect the benchmark record first. This benchmark consumes an Empty Cell and
produces an Oxygen Cell, so its `cofeeds` and `coproducts` remain relevant.
There is no implicit container credit. GT nominal EU is captured EU/t times
ticks. **Captured GT EU/t already includes amperage. Do not multiply again.**
Unknown, nonpositive or non-EU energy cannot certify a cheap conversion.

An accepted network must net-consume `primary_feed_id`. With omitted
`allowed_feed_ids`, only that primary feed is allowed. A profile contributes
scope, not its base list as implicit cofeeds. Other consumed resources must
regenerate in the steady-state ledger or be explicitly allowed feeds. A
regenerating reagent can still require startup stock. Savings are relative to
equal net target quantity and nominal recipe energy, without proving machine
efficiency, overclock behavior or a global optimum.

### Audit loops and candidate anomalies

```json
{"name":"find_loops","arguments":{"start_id":"r5090","kind":"lossy","chemical_kind":"any","yield_mode":"guaranteed","max_depth":4,"max_processes":100,"max_paths":3,"max_states":1000}}
```

`kind` classifies the returned starting resource. `chemical_kind` separately
filters native chemical accounting. A gain can consume external reagents.
`autonomous` concerns material closure with startup conditions, not self-powered
machines. Unknown material facts stay unsupported. Formula display text alone
does not establish composition, purity or chemical conservation.

Material-path `path_details` can include `input_category_hints`. A
`crafting_tool` hint means the exact selected resource ID is a captured member
of the listed native OreDictionary groups. It does not establish actual tool
use, unchanged stock, wear, source-atom contribution or every OR alternative's
category. The selected input retains its `consume` role. Inspect the full
recipe and copied `native_accounting` conditions for unresolved tool damage
and container returns. An empty or absent hint list is not proof that an input
cannot function as a tool. These are output explanations, not search filters
or penalties, and they preserve the selected recipe witnesses.

The native quantity profile explicitly supports GT `5.09.54.221` and
`5.09.54.223`, with the same `.221` interpretation profile. Read the actual
snapshot and resource accounting status. A supported runtime version alone
does not resolve persisted unknown facts, GT++ declarations, fluid-phase
ambiguity or unsupported quantity bases. Use `inspect_chemistry` for the
shared accounting decision rather than parsing display formulas yourself.

```json
{"name":"analyze_statistics","arguments":{"scope":{"excluded_namespaces":["TConstruct","TGregworks"]},"max_findings":5,"max_signature_buckets":50000,"timeout_seconds":15}}
```

Begin with a scoped overview and a few findings. A small `max_records` can stop
before recipes are scanned because resources and groups are scanned first.
Read `overview_complete` separately from comparison completeness. `max_findings`
limits findings, not distribution rows. Save large statistics results through
the existing CLI to a local file and project the relevant overview, family/tier
rows and finding IDs before presenting them to an agent. Cost spreads
compare identical captured predicates and conditions after batch normalization.
They do not prove that concrete alternatives are obtainable or semantically
equivalent in execution. Keep finding kind, ratio, process IDs and bounds, then
inspect only relevant original records. Statistics has no per-family request
filter beyond `scope.excluded_family_ids`. Filter returned distribution rows
locally rather than inventing an unsupported argument.

## Interpret quantities and incomplete results

- Exact quantities are integers or `{numerator, denominator}` rationals. Items
  use counts and Forge fluids use captured volume units. Keep typed NBT and
  metadata distinct. Do not compare names as identity or convert exact values
  through binary floats when doing accounting
- Every AND slot is required. OR slots choose one valid concrete alternative.
  Presence includes nonconsumed circuits and tools. It is a stock requirement,
  not a material-flow edge or zero-cost permission to start a cycle
- `guaranteed` debits possible consumption and credits certain captured outputs.
  `expected` gives a labeled average scenario. Expected outputs are not guaranteed
  inventory or startup stock. Unknown quantities or chances are not replaced
  with certainty
- `start_stock: null` or omission means no stock declaration. `start_stock: {}`
  declares empty stock. `startup.feasible` can be null for undeclared stock,
  expected yields or fractional runs. Read `start_stock_declared` and
  `final_stock_semantics`. Without declared stock, `final_stock` is batch net
  change and may be negative. It is not an observed remaining inventory
- Normalized fractional executions describe scaling. Inspect
  `integer_batch_scale`, scaled target quantity and startup for native batches.
  The ordered stock witness is conservative, not a minimum scheduling-stock
  solution. Material feasibility does not certify machine conditions, research,
  permissions, temperature, tier capacity or runtime execution
- Trace `found` means at least one complete known dependency path. `not_found`
  describes only exhausted supported search within its scope. `incomplete`
  can mean a bound stopped discovery. `same_resource` is an identity case, not
  a production loop
- Network `complete` means verified witnesses were returned. It does not imply
  complete candidate coverage or global optimization. Check
  `discovery.coverage_complete`, discovery exclusions and limits, solver
  `search.complete` and `search.limit_reasons`. `incomplete` without solutions
  must not become an impossibility claim. `unsupported` requires inspecting the
  reasons rather than silently substituting another identity or predicate

For a small question, start with two paths or solutions and current defaults.
If a relevant limit is hit, increase that bound deliberately. Network defaults
are depth 8, 200 processes, 128 variants, 512 resources, 128 solver columns,
512 rows and a 10-second solver timeout. Raising only solver columns cannot
recover recipes omitted by discovery. Increasing everything at once wastes
work and can still leave coverage partial.

## Scope and acquisition limits

Profiles are snapshot-bound sidecars. They never remove canonical records.
The GUI calls a boundary profile a **basic input set**. Both mean declared
permitted external feeds, not inventory or source proof. MCP retains the
`*_boundary_profile` tool names and explicit profile IDs.
Pass `scope` or `profile_id` where supported, not both. Scope arrays contain
`excluded_resource_ids`, `excluded_group_ids`, literal `excluded_namespaces`
and exact `excluded_family_ids`. Use `get_scope_catalog` and
`find_resource_groups` to discover these identifiers instead of inventing
taxonomy or mod ownership. Unqualified fluid names have no inferred namespace.

Resource search, acquisition inspection, network analysis and statistics use
these profile scopes. Trace, recycling and loop tools retain their own
material/tier filters. `find_processes` supports its explicit `family` filter,
not a profile. Do not assume a scoped autocomplete implicitly scopes another
tool. Network scope excludes a whole producer with an excluded coproduct.
Statistics scopes resource/group membership, recipe families and captured
outputs while retaining raw input predicates. This is not concrete matcher
coverage. GT tier filters are nominal recipe-voltage classes, not machine
capability proofs. Unknown tiers follow the explicit policy when a tier filter
is active. RF and crafting are not guessed into GT voltage classes.

Source records describe configured possibility, not surveyed chunks. Read
conditions, status, environment links, native parameters and provenance.
Generated ore blocks tagged `generated_ore_block_not_mining_drop` do not seed
inventory. Normal mining outputs preserve their harvest assumptions. Small-ore
`mined_item_rule_candidate` outputs require the joint weighted/exclusive rule,
not independent fixed yields. These candidates do not automatically ground a
recipe cycle. Acquisition hints and bounded grounding cannot prove absolute
unobtainability when capture or discovery is incomplete.

Use [FORMAT.md](../../../FORMAT.md) for the detailed record contract when
working in the repository. The server and this guide operate offline. They do
not run Minecraft, search current wiki recipes or repair missing native facts.
