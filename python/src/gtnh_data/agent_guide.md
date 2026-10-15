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

Prepared analysis gives unrepresented target requirement classes a
turn before equivalent endpoint jobs. Class equality uses the complete
snapshot-specific accepted resource sets and their declared amount, consumption
chance and NBT effects. Original endpoint recipes, AND slots and cofeeds remain
separate. Inspect `search.requirement_classes` for class coverage and charged
scheduling work.
`known_classes` and `represented_classes` count resolved classes.
`unresolved_jobs` and `represented_unresolved_jobs` are separate counts.
An unresolved job is not a proven equivalent requirement.

It also distinguishes structured native material declarations from
opaque or partial ones. A disjoint name set across these evidence bases receives
an uncertainty hint rather than a stronger discontinuity hint. Scoring and
`path_details.material_continuity` use the same comparison.
`structured_complete` describes declaration structure, not purity, chemical
validity or source-atom contribution. Display formulas are not parsed. Inspect
`search.material_evidence` for prepared lookups and comparisons.

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
used as if it belonged to the current snapshot or analysis version. Material
evidence and requirement classes were introduced in analysis version 4.
Item-type classification was introduced in version 5. The current preparation
format is version 6, which also stores the exact captured recipe family for
metadata lookups. This changes no ranking weights or recipe records.
A process reporting an earlier version has older code loaded.
Reload the MCP process after
upgrading, then explicitly rebuild if status is incompatible.
Rebuilding derived data does not reload running code.

Material presentation lists retained paths through the consumed item first
within comparable final Cutter transformations. Inspect `path_ordering`
for the applied policy, classification visits and permutation from new path
positions to original positions. Route, branch indices and path details already
follow that order. This Cutter preference does not reorder other families.
This is a declared mechanical continuity preference. Fluids can contribute
material, including recipes that consume UU-Matter, and remain required inputs.
All returned fluid paths stay available. Use required intermediates when you
want a particular fluid route. Ordering does not recover an undiscovered path
or establish best yield, atom contribution or a coolant role.

Material presentation also moves retained Space Mining acquisition paths after
other alternatives already found. This preference takes priority over the Cutter
convention. Recognition requires one of the exact source-verified `.221`, `.223`
or `.225` version and JAR cohorts. Unknown cohorts stay neutral. No path or native
recipe field is removed. Direct and sole acquisition routes remain available.
This is presentation of existing dependency paths, not improved discovery,
certified material transfer, or an optimization of ore yield or energy. For
Scheelite, it can expose a shorter QFT and Tungstensteel route before the chemical
route. Use required intermediates or tier filters when those constraints matter.
Other path selectors retain their existing order.

`path_ordering.changed` describes the final permutation. The acquisition policy
also reports whether its own partition changed the order, the exact source
cohort and affected recipes. `unchanged_material_order` means no preference
applied. Its visit counts still report presentation work. These counts are
separate from search budgets and do not establish additional coverage.

The presentation pass and batched unresolved-producer checks use the existing
imported data and keep analysis version 6. Reload running code after upgrading.
Rebuild only if `flow_index_status` reports missing or incompatible data.

Some captured catalogs are informational declarations. For example,
`forestry:squeezer` retains static native ingredients and products with unresolved
stateful matching. Inspect these with `find_processes` using the family or output,
then `get_process`. A null `executable` does not supply a supported quantity
ledger or trace transition. Generated filled-container executions are outside
that static catalog. Do not turn unknown machine timing or energy into zero.
Read the snapshot's coverage before assuming a catalog is present. New code
does not add records to an existing immutable capture. A newer dump requires
its own import and explicit selection.

For `botania:runic_altar`, native mana is a total cost, not EU/t. Full material
requirements include an extra Livingrock and retained literal Botania runes.
Read unresolved native inputs and subclass reasons before using a declaration.
Mana delivery, wand interaction and cooldown are separate runtime requirements.
An unknown voltage tier is not evidence that the recipe requires no energy.

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

Material search retains a found hop-reference witness as a provisional
candidate within the existing path and included-recipe limits. Its material
jobs can still improve it. A better candidate replaces it only when the full
covered requirement-class set agrees. Retention alone does not finish that
material exploration, including when `max_paths=1`.
Read `search.reference_candidate` for admission, final retention, replacement
and compatible-improvement turns. Its resource and process arrays identify
the admitted reference, which may later be replaced and not embedded in the
final graph. Follow exact IDs in the same snapshot when needed. Its charged
work includes candidate admission and replacement bookkeeping. Requirement
class work is reported separately. A retained witness can coexist with search
truncation. It does not prove optimality or supply the other recipe inputs.

## Keep tools and parts out of ordinary dependency spines

Request `terminal_artifact_policy="direct_targets_only"` when tools and parts
should be direct targets rather than bridges to ordinary products. Recognized
families are Tinkers ToolCore tools and ammunition, IToolPart implementations
including TGregworks parts, and GT MetaGeneratedTool descendants including
turbine metatools. Ordinary component rotors, casts, shapes, GGfab implements
and armor receive no extra rule.

A recognized tool or part can feed another recognized tool or part. It cannot
feed an ordinary or unclassified output on the selected spine. This keeps
material → part → tool routes available. Full recipe cofeeds remain visible,
and direct recipe lookup stays available. Request `"allow"` for unrestricted
dependency investigation. Recycling explicitly uses that unrestricted policy.
Loop and energy audits retain their original accounting.

An incompatible tool/part start and ordinary or unclassified target is rejected
before graph discovery. This follows the same edge rule and does not establish
general unobtainability. Inspect `search.terminal_artifacts.endpoint_compatibility`
and `endpoint_checks`. Endpoint classification is charged separately from
actual recipe-edge checks. Choose `"allow"` to investigate that resource's
recycling or other unrestricted dependencies.

Recognition uses captured `item_type` class/interface ancestry. Missing or
failed item evidence is unknown, not a negative classification. Inspect the
returned recognition diagnostics before claiming the categories were fully
recognized. Current older captures lack these facts. The public default stays
`"allow"` until the native evidence is accepted and rolled out. The current
prepared format requires analysis version 6 and the normal explicit rebuild
after loading new code.

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

Trace `max_processes` limits unique recipes included in the returned combined
graph. It does not set the internal process-search cap. Read `search.limit`,
`search.work_limit`, `search.truncated` and `limit_reasons` for search bounds.
`search_process_limit` is different from `path_process_limit`. Raising the
included-recipe limit does not raise the server search limits.

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

Opt in to `view="concise"` for route topology and complete selected recipes
without embedded resource `material_facts` and resource `provenance`. It keeps
the compact graph, exact registry/metadata/typed-NBT identities, every selected
recipe and its side inputs, coverage, source boundaries, limits and ordering.
`presentation.resource_record_scope` and `omitted_resource_field_counts`
identify the omitted evidence. Follow exact resource IDs with `get_resource`
in the same snapshot for full composition and provenance. Chemistry tasks may
prefer compact to avoid those follow-up lookups. Concise is opt-in and makes
no token-count, model-context or CPU-time guarantee. It does not reduce search
or uncertainty.

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

For underground fluids, inspect the linked environment's
`properties.dimension_blacklist` when present. It preserves GT's native numeric
exclusions with their source API and capture status. Keep empty arrays,
unresolved null and absent capture distinct. The list does not resolve a named
provider rule to actual dimensions or prove a current deposit. Acquisition
inspection includes the full linked environment properties. A conditional
source remains evidence of a native definition, with inventory availability
unproved.

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

Use `excluded_group_ids` to avoid a captured group without listing its aliases.
Discover exact group IDs through `find_resource_groups` with a small name query.
Each group is resolved to its literal captured members once in Dataset. Results
report `group_exclusions` with the group ID, name, kind and member count, without
dumping every excluded identity. It applies to every path-selection policy.

```json
{"name":"trace_processes","arguments":{"start_id":"r4010","target_id":"r24189","path_selection":"material","view":"compact","max_paths":4,"excluded_group_ids":["ore:nuggetIron"]}}
```

In the named canonical snapshot, this group has five members, including an
Iron Oreberry. The separate `unified:r12261` group has three. They are not
interchangeable, and neither means all Nuggets across materials. This exclusion
does not expand a wildcard or NBT-insensitive recipe predicate to other members.
It constrains resources on the path, including endpoints if selected. Full
recipe cofeeds, OR alternatives and outputs remain present even if some belong
to an excluded group. Use planning scope for a whole-network exclusion instead.
Unknown groups or malformed ID arrays are errors, not ignored filters.

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

Some GT recipe maps expose display projections of custom machine logic. Eye of
Harmony is one verified example. Its raw zero EU/t and one-item display outputs
do not establish an ULV recipe or free production. New captures retain exact
native base quantities and requirements under `conditions.special_items`, with
execution and voltage explicitly unresolved. Those base declarations do not
include all runtime yield conditions. Accounting and discovery reject the exact
typed projection in older supported snapshots too. Inspect its raw process for
research, but do not present it as a solvable production step.

Space Mining is another custom model. Its captured amounts and weights are
output-pool declarations. They are not a supported per-operation yield model.
Accounting and accounting discovery reject the exact typed native declaration
in both yield modes, while possible-output lookup and dependency traces remain
available. Its nominal voltage can remain known. Do not multiply a stack by its
captured weight to claim ore per mining operation, or infer material conversion
from consumed drill parts into ores.

`get_process` can return `projection_issue` beside the unchanged `item`. Read
its shared `reason` before using the process for accounting. The issue does not
mean the machine cannot run. It means this application cannot account for that
native operation model. Missing annotation does not certify executability.

New captures can also include informational Space Pumping catalog processes
under `gtnhintergalactic:space_pumping`. Their native fluid amounts describe one
selected line, one parallel and batch size one. Read the planet/gas selectors
in `conditions.native_metadata.space_pumping` as native selectors, not dimension
IDs. Environment mapping and runtime machine requirements remain unresolved.
These records have `executable: null`, so lookup does not make them eligible
production-network steps or assumed inventory sources. Use actual captured
fluid identities rather than a roster copied from another pack version.

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
`crafting_tool` hint reports the selected resource's category membership.
The `native_ore_dictionary_matching_membership` basis uses captured
`resource.ore_dictionary_membership` from `OreDictionary.getOreIDs`. Native
matching uses item and metadata, includes registered wildcards, and ignores
NBT and count. The `exact_captured_ore_dictionary_membership` basis reports
literal registered-variant membership. It remains supported for existing
immutable snapshots whose native membership field is absent. This preserves
their captured evidence without treating it as a native matching result.
A valid captured empty field produces no category hint. Failed or malformed
native evidence also produces no positive hint and does not substitute
literal membership. Inspect the resource field's status and diagnostic.
Hint absence is not negative evidence, including failed or uncaptured states.
Neither basis establishes actual tool use, unchanged stock, wear, source-atom
contribution or every OR alternative's category. The selected input retains
its `consume` role. Inspect the full recipe and copied `native_accounting`
conditions for unresolved tool damage and container returns. These are output
explanations, not search filters or penalties. Literal group exclusions and
the full selected recipe witnesses retain their existing semantics.

The native quantity profile explicitly supports GT `5.09.54.221`,
`5.09.54.223` and `5.09.54.225`, with the same `.221` interpretation profile. Read the actual
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
