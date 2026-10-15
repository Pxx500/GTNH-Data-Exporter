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

Resources may carry `native_source_refs`, retaining native registered catalog
anchors and machine template references. A `catalog_anchor` names its native
`owner`, enum `symbol`, access `basis` and `identity_scope`. Matching uses the
exact registry, metadata and typed NBT, ignoring count. All matching symbols
are retained. Catalog preparation does not create resources by itself.

GT ItemList anchors use its raw registered-stack accessor. GT++ anchors use a
single layout-checked read of the private instance `mStack` field, retaining
`field` and `declared_type`. The public normalized getter is not used. Catalog
failures discard that catalog's partial results and emit explicit failed
coverage. Other successfully prepared catalogs remain independent.

A `machine_template` names the native template owner, `meta_id`, actual
`template_class` and `ItemMachines.getMetaTileEntity` access basis. Its scope
explicitly states that the native resolver ignores NBT. It identifies a
registered template, not the stack's configured capabilities or an observed
world machine. Neither reference kind establishes semantic use, material
composition, chemical accounting or obtainable stock. An empty list or older
snapshot without references does not establish the absence of a native role.

Item resources may carry `ore_dictionary_membership`:

```json
{
  "status": "captured",
  "source_api": "OreDictionary.getOreIDs",
  "matching_semantics": "item_and_metadata_with_wildcard_nbt_ignored",
  "group_ids": ["ore:craftingToolHardHammer"]
}
```

The field records the native lookup for this stack, using item and metadata
with registered wildcard matches and no direct NBT or count comparison.
Names are persisted as sorted unique group references. Runtime-local numeric
ore IDs are not persisted. A successful empty lookup has `group_ids: []`.
Lookup failure has `status: "failed"` and a `diagnostic` object with exception
class and message, without a successful group list. Fluids omit the field.
The lookup dispatches through the item's metadata getter. The inspected GT
metatool getter is passive, while arbitrary custom overrides are outside that
source proof.

Native matching membership differs from literal registered group members.
It can include an NBT variant absent from the group's captured `members` list.
It does not modify that list, resource identity or exclusion semantics, and
does not establish actual tool use, wear, material contribution or chemistry.
Existing snapshots without this field retain their literal-member evidence.

Item resources may carry `item_type`, captured from the registered Item object:

```json
{
  "status": "captured",
  "basis": "runtime_item_class_hierarchy",
  "scope": "item_object_not_configured_stack",
  "class_name": "example.RegisteredItem",
  "superclasses": ["net.minecraft.item.Item", "java.lang.Object"],
  "interfaces": ["example.ParentInterface", "example.ToolPartInterface"]
}
```

Superclass names run from the immediate parent through the root. Interfaces
are sorted unique names from the class, its parents and inherited interfaces.
The capture reads JDK class metadata without invoking item behavior. Variants
of the same Item object reuse the captured hierarchy. Failure records retain
the basis, scope and diagnostics, without certifying a partial hierarchy.
Fluids omit this field. Missing or failed evidence means unknown item type.
These facts do not establish stack usability, acquisition, material contribution
or native tool wear. Resource identity and recipe accounting remain unchanged.

Resources can also carry `material_facts` schema 1. These facts retain the
actual GT version, accounting profile, source API, associations, prefix/native
material amounts, component trees, density fields, element/isotope data and
display formula. Source status is `associated`, `unassociated`, `ambiguous`
or `failed`. Accounting eligibility is bounded. `chemistry_purity` remains
`not_certified` and a display formula is never parsed into authoritative facts.

Item quantities use native GT material units. Ordinary chemical fluids use
formula units per 1,000 native fluid units. Molten solids use material units
per 144. Nested components retain their own unit basis and native density.
Unknown profiles, material classes, states, phases and compositions remain
unresolved. `association.candidates` preserves every native dispatcher/public
phase-identity candidate, with its tree, phases, accounting and evidence.
Ambiguous identity is not resolved by name. Query accounting may establish a
common vector only when all candidate bases, scales and vectors agree exactly.

Item and fluid resources may additionally carry `material_facts.native_owner`.
This is independent direct item, block or fluid owner evidence. Its source class and API,
literal native material identity, form and declaration tree do not replace the
GT ItemData association or change chemical accounting eligibility.

For GT++ owners, material identity retains the native class, `gtpp` system,
internal name and default local label. These are declaration fields, not
resource IDs or authoritative GT5 material references. The form retains the
native type and an OrePrefix only when the actual owner API supplies it.
A nominal prefix amount describes that form's native declaration and does
not provide a GT++ chemical quantity conversion.

GT++ declaration edges carry `declared_parts`, an integer string from
`MaterialStack.getPartsPerOneHundred`, with its explicit API quantity basis.
These values may include native rounding or clamping and are not certified
molar coefficients. `traversal_status` describes bounded traversal of the
declaration tree. A terminal declaration is distinct from an elemental leaf.
Missing references, cycles and traversal limits remain unresolved with reasons.
Neither a completed traversal nor matching names establishes chemical identity,
purity, source-atom transfer, resource interchangeability or obtainable stock.
Existing accounting consumers continue to use the supported GT accounting
profile and preserve unresolved GT++ accounting.

Fluid native-owner evidence has scope `native_fluid_owner`. It records the
actual fluid class and every distinct material object in the native GT++
catalog whose stored fluid or plasma field references that fluid object.
Each candidate retains its owner class, actual field bindings (`mFluid` or
`mPlasma`) and bounded declaration tree. One distinct owner is associated,
multiple owners are ambiguous, and no match is unassociated. Failed catalog
traversal retains partial candidates with diagnostics and cannot establish
uniqueness. Field bindings describe native references, not certified phase,
amount, purity or GT5 identity. Item and block owner fields remain independent.
This links the fluid object, not stack-specific NBT behavior. Tagged resource
identities and native recipe predicates remain separate.

The unchanged native GT quantity profile is identified by `5.09.54.221` and
explicitly supports runtime versions `5.09.54.221`, `5.09.54.223` and `5.09.54.225`.
The relevant native source implementations and runtime classes were compared
before extending this exact allowlist. `profile_version` identifies the
interpretation, while `native_version` records the actual captured runtime.
Other versions and unknown quantity bases remain unsupported. Accepting a
runtime version does not make unresolved persisted facts eligible, certify
purity or remove prefix, NBT, composition and fluid-phase requirements.

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
Forestry Centrifuge captures one-item consumption and separate strict
`Random.nextFloat() < threshold` output rolls. Native processing time is
measured in Forestry work ticks, with a five-game-tick work interval. Effective
duration and energy stay unknown because machine state and scaling affect them.
Recipe-side wildcard metadata and asymmetric NBT matching remain explicit.
Native HashSet selection order describes the captured run, not a stable priority.

`forestry:squeezer` captures static declarations from the verified Forestry
4.11.39 manager. Each declared stack is a separate AND requirement with its
native amount. Literal predicates remain in `declared_match`, while authoritative
matching stays `native_unknown` because initial selection, cached selection and
removal have different native rules. Each record has `executable: null` and null
duration, EU/t and amperage. Actual fluid quantity and optional remnant are
preserved. Remnant probability uses the strict 24-bit float comparison, with its
raw threshold retained. Work time and machine coefficients are context, not a
fixed game duration or EU conversion. Generated container templates are counted
separately. Their offered-container-dependent outputs are not expanded into
invented fixed executions.

`forestry:carpenter` retains passive declarations from the verified Forestry
4.11.39 manager and exact recipe/grid classes. `conditions.native_pattern`
preserves width, height, row-major cells including blanks, and nested alternative
order. Matching can offset and mirror the pattern. Raw stack counts, metadata
and typed NBT remain captured facts. The selected phantom-grid stock drives
ore-aware inventory removal and container-return callbacks, so this is not a
complete fixed material transaction.

Top-level inputs stay empty. `conditions.native_inputs` provides literal
ingredient references for declaration lookup. Pattern quantities are null with
raw `declared_stack_size` retained. Separate packaging has a declared count of
one and optional fluid retains its actual amount and NBT. These requirements
do not resolve selected-stock removal or container returns. Full fixed main
outputs retain their amounts. Executability, duration, EU/t and amperage stay
null. Native Forestry work ticks and coefficients remain metadata. Unknown
outer or grid classes are diagnostic without invoking their overridden getters.

`forestry:still` retains passive per-unit FluidStack templates from the verified
Forestry 4.11.39 manager and exact base recipe. Raw input/output amounts, typed
NBT, registry status and cycles remain under `native_input_template`,
`native_output_template` and `native_cycles_per_unit` in conditions. Literal
input references also use `conditions.native_inputs`, with native template
scope and unresolved effective matching. Interpreted inputs remain empty.

For registered templates with positive, representable native scalar products,
the top-level output retains the getter's exact per-unit amount, `chance: null`
and `native_output_semantics: declared_per_unit_template_not_cycle_yield`.
Invalid or unavailable facts stay in metadata without a canonical output row.
`native_scalar_status` records the check. This does not replace native Java
signed-int multiplication with an arbitrary-precision execution model.

The controller buffers a scaled input batch and attempts a scaled output fill.
Its output-space check uses only the unscaled template and does not establish
full batch receipt. Separate container handling and machine modifiers remain
runtime context. Dynamic input/output accounting, execution, duration, EU/t and
amperage stay unresolved. An output template supports lookup without supporting
an executable ledger, guaranteed yield or a fixed energy conversion.

Eye of Harmony has a native machine declaration behind its GT display recipe.
The GT arrays remain a captured projection. They do not establish execution
quantities, guaranteed yield or recipe voltage. Its process has `executable: null`,
unresolved dynamic inputs and outputs, and unresolved recipe voltage. Raw GT
EU/t and duration remain visible without deriving a nominal voltage tier.
`conditions.special_items` retains the native type and adds
`status: captured_native_declaration`, `quantity_scope: base_not_executed_yield`
and `runtime_execution: unresolved`. Native item and fluid output lists preserve
their order and exact long quantities as `amount_decimal` strings beside resource
references and getter provenance. Native long requirements, energy and timing use
`value_decimal`. Native success chance and efficiency retain their numeric values.
Casing and rocket tiers are machine requirements, not GT recipe voltage.
Accounting and discovery also reject the exact typed Eye of Harmony projection
in supported older snapshots. Raw inspection remains available. Neither the
display outputs nor the base declaration alone certify an executable network.

Space Mining exposes weighted output-pool templates rather than a supported
per-operation quantity model. The checked GT `.221` controller selects outputs
repeatedly, with runtime plasma, parallelism and filtering effects. Captured
amounts and weights remain unchanged. Possible-output lookup and descriptive
dependency paths remain available. Ordinary operation-ledger accounting and
accounting discovery reject the exact GT map and typed `SpaceMiningData`
declaration in both yield modes. Expected `amount * chance` is not a supported
operation yield. Guaranteed mode is also unsupported operation accounting,
not a claim that its former zero-ore projection guaranteed ore. This issue
does not invalidate the captured nominal voltage tier.

Space Pumping's separate native catalog uses family
`gtnhintergalactic:space_pumping`. Each valid catalog entry is an informational
process with no material inputs, one actual native fluid output and
`executable: null`. The output amount comes from the runtime catalog stack,
not NEI's zero-size display stack. It describes one selected line, one parallel
and batch size one. Nominal duration is 20 ticks and nominal energy comes from
the native controller constant under its verified contract. Recipe voltage
and runtime execution remain unresolved.

`conditions.native_metadata.space_pumping` preserves `planet_type` and
`gas_type` selectors, source APIs and the quantity scope. These selectors are
not dimension IDs. Environment mapping and the elevator/module execution
requirements remain unresolved. The process adds no assumed inventory supply.
Ordinary ledger and network discovery reject its null executable status,
while exact process/output lookup remains available. Source-verified contracts
cover GT `.221`, `.223` and `.225`. Unsupported contracts and invalid native
entries are reported in coverage. Actual runtime fluid identity stays
authoritative across catalog differences between those versions.

Botania Mana Infusion retains one-item consumption, output quantity and typed
NBT, plus `conditions.total_mana` and `energy_unit: mana`. Catalyst predicates
in `conditions.catalyst_below` identify the required block one block below the
pool. They ignore block metadata and do not consume the catalyst. Both native
requirement flags are retained. Mana availability, native list priority,
entity-age gates and item pre-hooks remain runtime conditions. Unknown recipe
subclasses and unresolved pre-hooks do not inherit base matching or guaranteed
execution. Duration and EU rates remain unknown.

`botania:runic_altar` preserves the active native list and distinguishes exact
base declarations from custom classes. Each ordinary ingredient occurrence
requires one item, ignoring the declaration's stack count and input NBT. Direct
metadata is literal, including 32767, while OreDictionary member metadata can be
wildcard. One additional Livingrock is consumed by item identity outside the
catalog input list. Literal Botania runes are returned, so homogeneous rune
slots use presence without also creating new rune coproducts. Other ingredients,
including ordinary tools, are consumed. Choice-dependent return behavior cannot
be represented by one slot role. Such records retain the full ordered list under
`conditions.native_inputs`, clear interpreted inputs and remain unresolved.

Runic Altar mana is a total native cost. Charging, wand interaction and the
dropped Livingrock are runtime gates. The 60-tick success cooldown is separate
from recipe duration. Duration, EU/t and amperage stay null. Stateful output
subclasses such as `HeadRecipe` do not acquire a fixed output from a cached name
or an invoked matcher. Unknown class behavior remains unresolved. Interpreted
material declarations do not certify present mana or altar readiness.

`botania:petal_apothecary` retains the active `BotaniaAPI.petalRecipes` list
under the verified 1.13.39-GTNH contract. Exact base RecipePetals declarations
preserve ingredient occurrences, alternatives, raw stack counts, typed identity
and fixed full outputs. Each catalog ingredient occurrence consumes one item,
including runes. This family does not inherit Runic Altar's rune-return rule.

Interpreted inputs remain empty. `conditions.native_inputs` contains catalog
ingredient declarations, excluding the separate seed trigger and water refill
transaction. `seed_trigger` preserves the native unlocalized-name regex and its
precedence after component admission fails, without inventing a seed resource
or OreDictionary group. `component_admission` records the native callback
requirement without evaluating it. `water_state` describes consumed filled state
and separate refill paths, not a universal fluid volume or bucket debit.
Executability, duration, EU/t and amperage stay null. Unknown subclasses and
unchecked versions remain diagnostic without matcher or overridden-getter probes.

#### Optional GT registration callsites

When explicitly requested, GT-map process provenance carries
`native_registration_callsites` from `GTRecipe.stackTraces`. Its scope is
`native_registration_or_copy_calls_not_execution`. Native strings and array
order are retained. `observed_trace_count` describes the original outer list.
Each retained trace has its original `native_trace_index`,
`observed_frame_count` and ordered `frames`.

Status is `missing`, `captured`, `malformed`, `truncated` or `failed`.
Native null is missing. A non-null empty list is captured with no origins.
Captured means the observed lists were retained completely, not complete
historical provenance. Copies can replace original registration evidence.
No exporter calls `reloadOwner` to reconstruct an origin. An omitted field
means this optional metadata was not captured, not that native origins are absent.

Malformed or omitted frames retain a null position and bounded ordinal issues.
Limits are four traces per recipe, 64 frames per trace, 1024 UTF-16 units per
frame, 16 KiB retained raw UTF-8 text per recipe and 128 MiB across the GT loop.
At most 32 issue details are retained per recipe, with an omitted-detail count.
Record byte counts describe retained raw text, not total JSON size.
The separate `recipe.native_registration_callsites` coverage entry reports
status counts, issue-event counts, retained bytes/frames and all fixed limits.
These exporter limits do not bound native initialization or memory consumption.

The option `--native-recipe-callsites` forwards
`-PdataNativeRecipeCallsites=true` through the existing full-pack launcher.
It sets `gt.recipe.lookup.validate.capture_callsite=true` on the game JVM
before recipe construction. Export also requires that explicit property.
The option does not enable lookup validation or use NEI configuration as an
export activation rule. No role, chemistry or runtime execution interpretation
follows from these raw registration or copy stacks alone.

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

Small-ore Fortune 0 sources retain a joint rule in `parameters.output_rule`:
`kind: gt_small_ore_fortune0`, `version: 1` and
`scope: per_qualifying_native_base_harvest`. The `primary` component has
`kind: weighted_draws_with_replacement`, positive `draw_count`, `total_weight`,
`amount_per_draw: 1`, weighted `candidates: [{resource_id, weight}]` and
`empty_pool_behavior: emit_nothing`. It preserves native repeated draws rather
than replacing variable quantities with averages.

The `host` component is an `exclusive_choice` with outcomes containing
`native_cases: [{case, probability}]`, their combined rational `probability`
and quantity-one `outputs`. Native cases are none with probability 2/3,
pure dust with 1/9 and impure dust with 2/9. Equal resolved dust identities
share one 1/3 outcome. They do not become two simultaneous products.
`evaluation_order` is `[primary, host]`. Host selection still runs when the
primary pool is empty. Silk and normal drop-system policy do not affect this
small-ore branch. Generator links, eligibility and harvest context remain.

Top-level outputs expose distinct positive-support resource IDs with
`resource_semantics: mined_item_rule_candidate`. They omit fixed quantities
and independent chances. They are searchable potential products whose rule
does not establish joint inventory or seed a dependency cycle. Trace leaves
remain unresolved unless another captured ordinary source grounds the item.
Import validates rule weights, cases, probabilities, support and references.
Failed native rule collection keeps an unknown source with empty outputs and
failure evidence, without a malformed recognized rule.

### Environment

`{id, name, dimension_id, provider, properties, provenance}`

Numeric dimension ID and provider may be null when mapping is unresolved.
The catalog includes registered dimensions, not just loaded worlds.
Generation definitions describe conditional possibility, not observed deposits.
Saved-world observations are a separate future domain.

Underground-fluid rule environments can preserve the native global numeric
filter in `properties.dimension_blacklist`. Its `source_api` identifies
`gregtech.GTMod.proxy.mUndergroundOil.blackList`. A nonnull array has
`status: captured` and exact ordered `dimension_ids`, including duplicates.
An observed null remains null with `status: unresolved` and
`reason: native_array_is_null`. Empty and unavailable are distinct.
The scope is `native_numeric_filter_not_resolved_availability`. The field does
not resolve provider rules, change source status or establish deposit/inventory
availability. Sources reach this shared context through `environment_ids`.

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

Reference summary schema 2 declares `handler_item_facts` version 1. Every
non-null item alternative retains detached `{registry_name, metadata, nbt,
amount}` facts before native serialization, plus `item_facts_failure`, the
selected `serializer_class` and `count_semantics`. Fact capture reads no
display-name getters. Native conversion runs on a detached stack and cannot
mutate the observed alternative. `failed_item_facts` counts failed fact
observations separately from native stack and signature failures.

`native_recipe_id_api` signatures invoke NEI's native RecipeId API. They are
not an invocation of `/recipeid fast-dump`, and its blacklist is not applied.
Raw views preserve `ingredients`, `result` and `other_stacks`
separately. Auxiliary stacks can be furnace fuel, so they do not universally
represent products. GT-specific views retain real quantities and native
presentation fields. Generic presentation chances are not production chances.

`presentation-context.json` schema 3 binds the same snapshot and pack, plus
the closed canonical resource/process count and hash declarations. Its pointer
in `summary.files` contains its SHA-256. The context declares three checksummed
gzip JSONL streams, `gt-display-aliases.jsonl.gz`, `item-pools.jsonl.gz` and
`item-projections.jsonl.gz`.
Direct GT aliases are keyed by canonical resource ID and queried from the
original reconstructed stack at quantity one. Item pools are keyed by registry
name. Both retain ordered `{registry_name, metadata, nbt, amount}` entries
with lossless typed NBT. Status distinguishes successful, empty and failed
queries. Unregistered canonical anchors remain explicit top-level failures.

Context capture runs before handler enumeration and reads no observed recipe
views to establish expected alternatives. Scope is the five mapped GT families
including Fluid Solidifier, and furnace. GT aliases precede wildcard expansion, whose pool metadata and
NBT replace the declaration's while the declared quantity is retained.
Empty native pools follow the pinned metadata-zero presentation rule.
The comparator uses successful records from partial context but reports its
failures. Incomplete advertised context cannot pass validation thresholds.
Without context, dependent alias/wildcard projections remain unsupported.

Item projections map complete typed item identities to exact native stack
serialization followed by `NBTJson.toJsonObject`. Capture uses the same reverse
public `StackInfo.stackStringifyHandlers` dispatch as the pinned NEI API. It
invokes `convertItemStackToNBT(stack, true)` once per reached handler and stops
at the first non-null result, retaining the actual selected serializer class.
Each copied template has quantity one. Rows retain
`status`, `native_stack`, `failure`, `serializer_class` and `count_semantics`.
The context records the ordered native serializer classes and projection API,
with `classification: selected_pinned_default_item_count`.
Scoped declarations, aliases, pools and canonical identity collision variants
are captured independently before recipe views. Native Java floating-point
NBT formatting is preserved without a Python approximation. Supplementary
declaration scope includes `botania:mana_infusion` with no GT unification,
capturing its independent wildcard pools without mapping its NEI handler.

Only an exact default-item serializer winner with its source-proven identity
and count envelope permits applying a declared
recipe quantity. Unknown serializers and item-to-fluid conversions retain
their payloads but do not establish ordinary item quantities. Distinct typed
identities with the same native projection remain ambiguous in historical
reference summary schema 1. Reference summary schema 2 with context schema 3
compares both exact typed identity and exact native payload, with quantity,
chance and GT real stack size checked separately. Its selected default writer
must preserve the actual observed quantity. It does not normalize null and
empty compounds. Custom writers, quantity-changing projections and failed
facts remain unsupported. Historical schema
1 and 2 contexts remain readable within their captured scope and original
projection rules. Schema 1 lacks native projections. Schema 2 infers ordinary
counts only under its pinned built-in serializer registry. Missing or unknown
historical facts cannot retrospectively establish native identity agreement.

The comparator validates all canonical and reference streams and the paired
cohort before applying its version-pinned adapter allowlist. It reports
matching, differing, missing and unsupported projections separately, with
bounded examples and scope limits. Default thresholds require no differences,
missing matches or capture failures. An unmapped predicate is not an exact
negative. NEI NBTJson is not injective. Without captured lossless facts,
ambiguous projections remain unsupported rather than being equated by display
name or lossy NBT decoding.

### Forestry Still fluid reference

The explicit `forestry_still` capture scope uses reference summary schema 3.
It selects the exact registered `NEIHandlerStill` before loading recipes from
unrelated handlers. The exact native manager and recipe roster are checked
before NEI constructs its cached recipes. A missing or duplicate handler,
unsupported roster or component identity mismatch is a selection failure.
The default full capture retains reference summary schema 2.

Schema 3 declares `profile: "forestry_still"`,
`view_projection: "forestry_still_fluid_tanks_v1"` and
`signature_projection: "not_applicable_fluid_tank_profile"`.
`canonical_files` copies the closed canonical file declarations. Together with
the snapshot ID, pack manifest and verified stream hashes/counts, this binds
the reference to its paired canonical capture.
`selection` records selected/excluded handler counts and a nullable failure.
`tank_observations` counts captured, unsupported and failed observations.

Each view retains the ordinary generic fields and adds `forestry_still_tanks`.
The observation records its status, cached recipe class, getter API and
declaring class, plus `quantity_scope: "unscaled_per_unit_templates"`.
Its ordered `tanks` retain ordinal, native class, position, `show_amount`,
`per_tick` and the complete ordered alternatives. Each alternative retains
ordinal, native class, capacity and a fluid with `registry_name`, positive
`amount` and lossless typed `nbt`. Unsupported shapes remain explicit and
are not reduced to a convenient pair of fluids.

The supported view contains two ordinary fluid tanks at their source-defined
positions and no generic item ingredients/result/other stacks. The comparator
checks both unscaled templates against `conditions.native_input_template`
and `conditions.native_output_template`, including their canonical resource
links, quantities and typed NBT. It does not multiply by cycle count.
Unique projection agreement and occurrence agreement are reported separately.

The profile requires Forestry 4.11.39 and NEI 2.8.160-GTNH with their pinned
JAR hashes. It has no item presentation context. The summary explicitly sets
`item_presentation_context` to `status: "not_applicable"` with reason
`fluid_only_profile`. No context file or item-facts capability is advertised.
The signatures stream has zero records and is explicitly inapplicable.
Empty generic signatures do not establish fluid agreement. Selection failures,
missing views, unsupported tanks and failed observations prevent complete
validation. Agreement covers presentation templates, not controller execution,
batch yield, power use or output-space checks.

## Dataset operations

The same operations serve HTTP, CLI and MCP. Opening a Dataset fixes one
snapshot identity. Import verifies checksums, counts and references, builds
a replacement SQLite index, then activates it. A failed import preserves
the existing usable index. Never accept a silently lossy import.

Initial operations are `status`, `find_resources`, `get_resource`,
`find_processes`, `get_process`, `get_group`, `find_sources`,
`get_source`, `find_environments` and `trace_processes`.

Progressive material queries use `start_trace_search`, `get_trace_search`,
`pause_trace_search`, `continue_trace_search` and `close_trace_search`.
Their job envelope is `{job_id, snapshot_id, revision, status, phase,
elapsed_seconds, progress, result_revision, request}` with optional `result`,
`first_result_seconds` and `error`. A result is the existing trace payload.
Missing `result` means no new rendered snapshot for the supplied
`after_revision`, not an empty graph. Lifecycle and result revisions share a
monotonic sequence. Pause/continue acknowledgements include a retained result
when one exists. Published snapshots do not mutate the retained frontier.

States are running, paused, finished, failed and closed. A time allowance is
cooperative and pauses unfinished work. Logical limits are terminal and remain
in the trace's `limit_reasons`. Continue adds active time to the same paused
operation and keeps cumulative work. Close disposes its state at a checkpoint.
The default allowance is 5 seconds, permitted range 0.05..60. Active elapsed
time includes rendering and excludes paused intervals. First-result timing
starts at job creation and ends at the first rendered nonempty publication.
An explicit integer budget multiplier 1..10 scales process, admission and
expansion guards, with unchanged default 1 and independent output/depth limits.

Job lifetime is process-local to Dataset. HTTP and stdio MCP don't share live
handles. One job runs, at most four are retained, and idle jobs expire after
15 minutes. One worker owns each retained SQLite connection through creation,
advancement, snapshot rendering and cleanup. No job state is written to the
canonical database or prepared sidecar. Existing synchronous trace operations
retain their response contracts and material search uses the same engine.

List results are `{snapshot_id, items, total, limit, offset}`. Use explicit
pagination, default 50 and maximum 500. Exact-resource lookup includes
supported ingredient predicates, not only literal reference equality.
Unsupported matching is reported as unresolved, never as an exact negative.
No client reconstructs semantics from tooltip strings.
Single-record results are `{snapshot_id, item}`. Process inspection may also
include `projection_issue` outside the unchanged `item`. This sparse object
contains `status: unsupported_accounting`, `native_model`, `reason` and
`voltage_unresolved`. It explains a recognized native model without a supported
operation-accounting projection. Absence of this issue is not certification
of native execution. Status returns
`{snapshot_id, manifest, counts, coverage}`, with counts per record collection
and coverage as an array of coverage records. Process lists in the default
`input_mode: matched` report `matching_complete` and `unresolved_matches`
where native predicates cannot be evaluated. Unresolved counts describe the
requested family/output scope, not established matches for the input ID.
These flags do not substitute for source coverage.

`find_processes` also accepts `input_mode: declared`, requiring `input_id`.
It finds exact captured resource-ID references in `inputs[].choices[]` and
`conditions.native_inputs[].choices[]`. It does not expand groups, wildcard
metadata, NBT-insensitive identities, names or `declared_match` predicates.
This is a separate relation query. It need not be a superset of known matches.
Repeated references yield one process result while the full raw item retains
all occurrences. Output/family filters and ordinary paging still apply.

Declared pages add `input_lookup` with `mode: declared`,
`scope: literal_captured_resource_references` and `matching_evaluated: false`.
They omit `matching_complete` and `unresolved_matches` because native matching
was not evaluated. A declared reference does not establish acceptance,
executability, quantities or a valid trace transition. Ordinary item bodies
remain unchanged. The HTTP parameter is `input_mode`, the CLI flag is
`--input-mode`, and the existing MCP `find_processes` tool uses the same enum.
Both modes read existing snapshot data without migration or reimport.

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

## Selected-path accounting operations

`trace_processes` accepts optional `min_tier`, `max_tier` and
`unknown_tier_policy: exclude|include`. Tier bounds are integers 0 through 15.
With no bound, the existing search scope is retained. An active filter uses
source-backed nominal GT recipe voltage, including native Assembly Line.
`tier_filter` and `recipe_tiers` disclose exclusions and uncertainty. Other
machine requirements are not inferred from voltage.

`plan_recycling` accepts a selected `main_path` of resource/process IDs,
`byproduct_id`, `return_id`, positive `main_runs`, concrete slot `selections`,
yield mode, tier filters and secondary path bounds. It validates the path,
accounts all AND slots and discovers secondary C to D paths through the same
Dataset trace. Slot selections are keyed by process ID and zero-based slot
index, with `{choice_index, resource_id}`. UI and transports do not implement
their own ingredient matcher.

The result contains `main_plan`, `alternatives`, `secondary_trace`, exact
ledgers, startup stocks, recovery and scope metadata. The available byproduct
is the main net surplus. Side scaling uses its full ordered startup requirement
so repeated consumption cannot silently import more C. Complete alternatives
rank by exact net recovery within the bounded discovered paths. Unsupported
alternatives retain their records and reasons. Quantitative amounts are JSON
`{numerator, denominator}` with positive denominator. Native facts can retain
decimal strings, while query arithmetic uses exact rational values.

`find_loops` accepts `start_id`, returned-resource `kind`, independent
`chemical_kind`, yield mode, selections, tier bounds and finite search limits.
Maximum depth/process/state bounds are 20/1,000/50,000. Filters apply before
the accepted witness count. Limits and unsupported chemical candidates remain
explicit. Each witness contains ordered steps, exact return ratio, full ledger,
initial stock, external consumption and chemical input/output/delta vectors.
Chemical imbalance without a return witness is not a loop proof. Material
closure does not establish energy independence or machine executability.

`inspect_chemistry(resource_id)` returns native-unit accounting or explicit
unsupported reasons, bound to the snapshot. It never equates resource identities
or certifies purity. Loss can be intentional under the GTNH balancing rule.

Guaranteed mode uses certain outputs and conservative consumption. Expected
mode is labelled as a scenario and does not certify inventory availability.
Startup scope is conservative batch-prefix stock, not globally minimal
interleaved scheduling. Fractional executions expose `integer_batch_scale`
and require scaling before native batch feasibility can be claimed. The full
net ledger retains side effects on the main target and every co-product.
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
duplicate_process_records, path_selection, branch_coverage,
recipe_groups, path_groups}`

`recipe_groups` groups returned processes by their declared material
transformation. Each entry is `{id, basis, process_ids,
auxiliary_input_indices}`. The last field maps every member process ID to its
zero-based auxiliary input-slot indices. Shared material requirements include
all consumed materials, accepted alternatives, quantities and output chances.
Repeated deterministic singleton ingredients can match an equivalent combined
quantity. Independent alternative slots retain their original multiplicity.

Explicit tool and presence requirements may differ between variants. A verified
GT shaped crafting slot can also be auxiliary when its complete declared
alternatives match a captured native crafting-tool category. This projection
does not establish that the tool is unconsumed. Original slot roles and unresolved
tool damage or returns remain on the native process record. Costs, voltage,
auxiliary requirements and machine conditions always belong to each variant.

The basis is `declared_material_transformation` when supported declarations
establish equivalence, or `native_process` for a process kept separate. Unknown
material effects cannot establish equivalence. Group IDs remain stable as new
variants enter a progressive result. Groups describe returned recipes, not an
exhaustive list of equivalent machines in the snapshot.

`path_groups` entries are `{id, representative_path_index, path_indices}`.
Each groups complete original paths with the same ordered resource spine and
recipe-group sequence. The existing `paths` records remain unchanged. Selecting
one variant at each step does not establish a new witnessed path. Accounting
and recycling still require one original whole path and native process IDs.
Search limits count native witnesses and recipes, so the number of displayed
route families can be smaller than `max_paths`. Quantified network executions
keep their separate execution identities.

`trace_processes` also accepts optional `excluded_group_ids`. Dataset validates
the snapshot's groups, resolves each group's literal captured members once and
unions them with exact excluded resource IDs for every path-selection policy.
This does not expand native wildcard or NBT matching. It constrains path
resources, including endpoints, while full recipe cofeeds and OR choices remain
intact. Required groups and generic form classification are not inferred.
Unknown groups and malformed arrays are errors.

Results include `group_exclusions`, a sorted array of
`{group_id, name, kind, member_count}`. It is empty when no group is excluded.
The result does not dump the full expanded exclusion set. OreDictionary and
unification group IDs retain their distinct meanings. HTTP uses repeated
`excluded_group_id` query parameters. CLI uses repeatable `--exclude-group`.
The GUI requests compact presentation explicitly, retaining full selected
recipes with bounded matching-variant presentation.

Material search keeps a found hop-reference path as a provisional candidate
inside the existing result limits. Its material jobs remain eligible to
improve it, including at `max_paths=1`. Replacement requires the same complete
requirement-class set and a better existing material-order key. Recipe-union
limits apply to the resulting retained set. This adds no prepared format,
query option or extra candidate position.

`search.reference_candidate` has policy `provisional_material_candidate`,
booleans `reference_admitted`, `reference_retained` and `reference_replaced`,
the admitted reference `resource_ids` and `process_ids`,
`compatible_improvement_turns` and `charged_work`. The arrays can identify a
replaced witness whose records are absent from the final graph. Admission
work includes scoring, signature and replacement bookkeeping. Class scans
remain separately charged under `requirement_classes`. Retention and settled
material exploration are separate facts. Search limits and incompleteness
still apply to results that retain a reference.

Trace `view` accepts `full`, `compact` and opt-in `concise`. Dataset, HTTP and
CLI default to full. MCP defaults to compact. Concise retains the exact compact
graph and complete selected native recipes, including all input choices,
presence, quantities, outputs, chances, conditions and provenance. It omits
only `material_facts` and `provenance` keys from resource records. Resource
IDs, registry names, metadata and typed NBT remain exact. Coverage, source
boundaries, cycles, exclusions, search work, limits and path ordering remain.

Concise reports `presentation.view="concise"`,
`resource_record_scope="resource_records_with_explicit_metadata_omissions"`,
and `omitted_resource_field_counts` with the actual count of resource records
that contained each omitted key. Its `resource_detail_notice` is
`Resource material_facts and provenance are omitted. Resolve exact resource IDs in the same snapshot for full records.`
Resolve those IDs through the existing resource lookup for omitted native
evidence. Concise is suited to route topology and full recipes. Chemistry
inspection may prefer compact. It changes response presentation without a
new snapshot or prepared-index format and makes no token or CPU guarantee.

`terminal_artifact_policy` is `allow` by default, or `direct_targets_only`.
The restrictive policy uses captured item class/interface ancestry to recognize
Tinkers ToolCore tools and ammunition, IToolPart implementations including
TGregworks, and GT MetaGeneratedTool descendants including turbine metatools.
GGFab single-use tools are recognized independently by their exact registered
item and tool metadata from native `SingleUseTool` declarations. Their molds
use different metadata and remain outside this tool category. This does not
depend on display names or treat the whole GGFab namespace as tools.
A selected consumed edge from a recognized tool or part is allowed only when
its output is also recognized. This preserves material → part → tool targets
and blocks tool → ordinary product carriers. No process is removed globally.
Full cofeeds, direct recipe lookup and native accounting remain intact.
Recycling explicitly requests `allow`. Other audits retain their own accounting.
There is no extra rule for ordinary component rotors, shaping aids or armor.

`search.terminal_artifacts` reports the applied policy, recognition basis,
checked and blocked edges, cached resource lookups, terminal/unknown/not-applicable
resource counts and charged work. Classification counts cover inspected route
endpoints and selected-spine candidates, not the entire snapshot.
`endpoint_checks` and `endpoint_compatibility` report a separate preflight.
Every permitted successor of a recognized terminal is terminal, so a terminal
start cannot reach an ordinary or unclassified target under the restrictive
policy. An `incompatible` preflight skips recipe discovery and distance work,
while charging actual endpoint classification. It adds no fictional recipe edge.
Missing, failed or malformed item hierarchy
is unknown. Fluids are not applicable. A partial recognition status cannot
establish complete category enforcement. Prepared analysis version 7 stores
these facts and the exact captured process family in the existing flow sidecar.
An incompatible version requires an explicit rebuild. Captured resource
identities remain unchanged.

`path_selection` is `diverse` by default, or `shortest` or `material`. Diverse selection
spreads emitted dependency paths across consumed input-slot branches at the
target. Those branches represent different AND requirements, not complete
alternative production plans. Shortest selection prioritizes fewest steps.
For diverse and shortest selection, the primary `route` remains the shortest
qualifying witness discovered. Material selection prioritizes native material
evidence and distinct target requirements through prepared analysis. Its primary
route follows the presented material witnesses, without a yield or energy claim.
Recovery preference reads the captured family from prepared process metadata,
with the existing per-query cache. Its `recipe_family_source` is
`prepared_process_metadata`. The original process record remains complete in
canonical inspection and trace results. This changes metadata lookup storage,
not route scores, recipe eligibility or search bounds.

For comparable final Cutter transformations, material presentation lists
retained paths through the consumed item before paths through consumed fluids.
Comparison preserves ordered nonfluid input slots, outputs, conditions, EU/t
and amperage. Fluid declarations and duration remain in each complete recipe.
The preference leaves discovery, path count and fluid participation intact.
Unknown, mixed or unresolved templates stay in their original positions.
This Cutter preference does not reorder other selectors or machine families.

Material results disclose presentation work in `path_ordering`. The Cutter policy is
`cutter_consumed_item_first`, scope `comparable_retained_final_cutter_paths`,
`changed`, `eligible_paths`, `classification_visits` and `original_path_indices`.
The permutation maps each new path position to its original position. Visit
counts describe retained paths, unique inspected recipes, slots, choices and
outputs. They are presentation metadata, separate from discovery counters.
The primary route, branch path indices and path details use the presented
order. This is an explicit mechanical item-continuity preference. Fluid input
purpose and material contribution remain unknown. Required fluid waypoints
and paths entering only through fluids remain supported.

Material presentation also places retained Space Mining acquisition paths after
other retained alternatives. This stable partition has priority over the Cutter
preference. It changes neither discovery nor the set of returned paths. The
source role is recognized only for the exact verified Intergalactic version and
JAR cohorts bundled with GT `5.09.54.221`, `5.09.54.223` and `5.09.54.225`.
Unknown cohorts stay neutral. Full native operation requirements, cofeeds and
outputs remain in each recipe. The convention does not establish atom transfer,
ore yield, lower energy or better chemistry. A direct or sole acquisition route
remains available. Other path selectors retain their existing order.

The acquisition policy is `native_acquisition_after_retained_alternatives`, with
scope `retained_material_paths`. It reports `acquisition_paths`,
`unknown_role_paths`, `source_evidence`, `acquisition_process_ids`,
`acquisition_changed`, classification visits and the composed permutation.
`changed` describes the final order. `acquisition_changed` describes the stable
partition after applying any Cutter preference. When present,
`cutter_preference` reports its own evidence separately. This avoids treating
every final reorder as evidence that acquisition paths moved.

Without either relevant preference, `unchanged_material_order` reports an
identity permutation, `changed: false` and zero eligible paths. Its visits still
count the scan of retained paths and unique processes. Cutter-only results
report that scan as `acquisition_classification_visits`. No presentation visits
are included in discovery counters. A missing descriptor on a non-material
result does not imply that a material presentation pass ran.

`branch_coverage` contains `{target_process_id, slot_index,
candidate_resources, paths, path_indices, status}` for consumed target slots.
`paths` counts emitted witnesses and `path_indices` points into `paths`.
Status is `represented` or `not_discovered`. The latter does not establish
unreachability. Slots explicitly marked as presence or tool roles are not
dependency-spine transitions. A tool-category hint does not change a consumed
slot's native role.

Material-path `path_details[].input_category_hints` describes selected input
categories. Its basis is `native_ore_dictionary_matching_membership` for a
successful native field, or `exact_captured_ore_dictionary_membership` for
supported snapshots without that field. Valid native empty results and failed
or malformed native evidence do not substitute literal hints. Failed evidence
remains in the resource record. Absence of a hint does not certify absence of
a tool category. Native recipe roles and accounting remain unchanged.

Material traces include `path_details[].material_detours`, descriptive
evidence for retained two- or three-recipe windows. Step indices `start_step` and `end_step` are
zero-based and inclusive. Each entry keeps `process_ids`, `resource_ids`,
`cases_checked`, `zero_net_cases` and a concrete `witness`.

- `status: zero_net`, scope `all_concrete_choices`, means every enumerated,
  supported deterministic concrete input case compatible with the selected
  dependency spine has zero net change across the
  complete captured exact-resource vector
- `status: conditional_zero_net`, scope `concrete_selection_witness_only`,
  means fully enumerated cases include both zero and nonzero vectors. The
  witness proves only that a zero-net selection exists

The witness contains per-process input `selections`, exact rational
`executions`, `required_start_stock`, `presence` and an empty `net` map.
Even universal net-balance evidence includes only one startup-stock witness.
Other concrete selections can require different starting resources.
Starting stock includes presence requirements. Do not subtract the global
presence map to infer consumed startup stock. These are conservative batch
prefix requirements, not a declaration that stock is available.

The trace-level `material_detour_analysis` reports scope
`retained_2_3_recipe_windows`, analysis `status` (`complete` or `partial`),
`limits`, actual `work` and `counts` for `zero_net`, `conditional_zero_net`,
`nonzero` and `unknown`. Limits are 128 windows, 256 concrete cases, 4096
matching-row analysis visits and 16 cases per window. Visits operate on
already rendered matching candidates. They do not count prior rendering or
search expansion. Unknown or nonzero windows have no positive path annotation.
An unresolved effect, uncertain chance or incomplete bounded enumeration
cannot establish a positive result.

This evidence describes captured resource balances. It does not certify atom
provenance, native machine execution or whether removing a window preserves
every condition. It changes neither discovery nor path order and does not
filter recipes. Empty annotations do not certify absence of material detours.

`route` contains `status`, `strategy`, ordered `resource_ids` and ordered
`process_ids`. The strategy field retains `shortest_known_dependency_path`.
For diverse and shortest selection this means fewest process steps in the
discovered graph through supported positive consumed inputs, with stable ID
ordering for ties. Material selection uses the preference described above.
Explicit presence and tool roles are
requirements, not dependency-spine transitions.
The statuses are `found`, `not_found`, `incomplete` and `same_resource`.
`found` establishes a dependency connection, not best yield, minimum energy,
batch feasibility or satisfaction of every machine condition.
`not_found` is scoped to the captured supported graph. An identical start and
target gives `same_resource` with one resource and no process steps.

`paths` contains ordered `{resource_ids, process_ids}` records. `route`
identifies the first qualifying path. The returned process IDs are exactly
the union of complete emitted paths. Only transitions belonging to those
paths become recipe-to-recipe connections in the GUI.

`max_paths` defaults to 8 and accepts 1..100. `max_extra_steps` defaults to 6
and accepts 0..64, relative to the shortest qualifying path. `max_depth`
accepts 1..64 and bounds total path steps. `max_processes` accepts 1..5000
and bounds the union of distinct recipes. Each path is included whole or
omitted. A path that cannot fit is never represented as a successful fragment.
Selected-path recycling explicitly uses shortest selection and retains its
two-extra-step default. Its quantities and recovery ranking still refer to
concrete recipe witnesses.

`required_resource_ids` and `excluded_resource_ids` are arrays of exact
snapshot resource IDs. Every required ID must occur along the material path,
and every excluded ID must be absent. Intrinsic side ingredients, presence
requirements and co-products do not satisfy an intermediate constraint.
HTTP uses repeated singular `required_resource_id` and `excluded_resource_id`
query parameters. CLI uses repeatable `--required-resource-id` and
`--excluded-resource-id`. MCP uses the plural array arguments.

Shortest selection discovers target ancestors through indexed output
references, then enumerates simple paths in that graph. Diverse selection
reserves a shortest qualifying witness, seeds a graph with bounded forward
transitions from the supplied start, and discovers target ingredient branches
in turn. Enumeration favors distinct material spines before deferred concrete
recipe variants. Deferral groups search candidates by their ordered resource
IDs. It does not merge identities, quantities, chances or native recipe data.
A path does not repeat a resource or process, so cycles cannot create infinite
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
`examined_states`, `queued_states`, `peak_queue`,
`expansion_work`/`work_limit` (100,000),
`enumeration_work`/`enumeration_limit` (100,000), and `truncated`.
Shortest search uses one 20,000-state budget. Diverse search reports separate
20,000-state discovery and enumeration budgets, plus the primary search under
`primary`. Its aggregate state limit is 40,000. Source seeding reports its
two-step depth and 2,000-process optimization bound under `source`. Reaching
that seed bound does not prune reverse discovery, which continues toward the
actual start. `enumeration` also reports deferred concrete variants and its
1,000-variant pool bound.

`limit_reasons` distinguishes `depth`, `path_limit`, `path_process_limit`,
`search_process_limit`, `search_state_limit`, `search_work_limit` and
`search_enumeration_limit`, plus `search_variant_limit` when the deferred
variant pool fills. Top-level `truncated` is true if any applies.
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

## Production networks and offline query views

`plan_network` discovers bounded concrete recipe variants and solves an exact
steady-state balance. `audit_energy` adds a selected nominal-energy benchmark.
`plan_to_bases` resolves the permitted external feeds from a boundary profile.
The target net quantity is exact. Every other non-feed resource must have
nonnegative net quantity. Energy audits additionally require strictly negative
net primary-feed consumption in each accepted witness. Zero-feed optima are
rejected, with bounded support exclusions rather than an invented epsilon.

A discovery variant has a distinct `variant_id`, native `process_id`, selected
input indexes and a detached accounting `process` view. Dataset validates the
native predicate before concretizing that view. `discovery.processes` retains
the original canonical records. The two must not be confused in inspection.

Each solution carries executions, exact per-execution ledgers, the whole net
ledger, imports, coproducts, nominal energy, integer batch scale and startup
stock. Rational values serialize as `{numerator, denominator}`. Guaranteed
and expected yields remain separate. The startup witness orders funded
producer batches before consumers where possible and declares conservative
seeds for deadlocks. It never claims the minimum startup inventory.
`start_stock_declared` distinguishes omitted inventory from an explicit empty
inventory. `final_stock_semantics` identifies declared stock plus the batch net,
or a batch net change when no starting inventory was supplied. A net change
must not be presented as a known final inventory.

Nominal EU is positive captured EU/t times positive ticks. GT EU/t already
includes recipe-map amperage. Unknown, nonpositive and non-EU energy are
unsupported for the energy objective. Target-to-basics may minimize recipe
runs while leaving unknown energy explicit. It does not minimize raw imports.
Machine conditions are retained and not universally evaluated.

`optimization.scope` is `bounded_candidate_variants`, with
`global_optimum_proven=false`. Discovery limits and solver limits are separate.
An accepted exact witness may coexist with incomplete candidate coverage.
Alternative support exclusions do not enumerate all networks or all cycles.

Boundary profiles contain exact snapshot IDs, basic resource IDs, revision
numbers and a query scope. Their atomic JSON sidecar is separate from the
canonical snapshot and rebuildable index. Basic resources are declared
external-feed assumptions. A target already marked basic returns a boundary
quantity without inventing a delivery recipe.

Scope fields are `excluded_resource_ids`, `excluded_group_ids`,
`excluded_namespaces` and `excluded_family_ids`. Namespaces use the exact item
registry prefix. Unqualified fluid names imply no mod ownership. Families use
the exact captured `process.family`. Canonical getters remain available.
The current shared scope covers resource search, network planning,
acquisition inspection and statistics. Historical trace, selected-path
recycling and loop enumeration keep their existing arguments.

Resource search may attach `acquisition_analysis`. Canonical record getters
remain unchanged. Captured native unification anchors can identify canonical,
noncanonical and ambiguous variants. Alias membership does not establish
universal output replacement. Incomplete acquisition coverage prevents an
absolute unobtainability claim. Grounding is structural possibility, requires
all selected inputs including presence, and cannot seed a closed cycle from
its own products. Generated world blocks and unresolved mining candidates
are not treated as inventory seeds.

`analyze_statistics` streams scoped canonical records. Recipe scope uses
family and output-resource filtering, while input declarations stay unchanged.
Comparable cost cohorts preserve all captured predicates and conditions,
including presence and chance. Only consumed and produced quantities are
normalized by an exact common batch factor. Findings describe cost spreads
within identical captured declarations, not proven execution equivalence or
confirmed balance bugs. Family/tier cost distributions are exploratory.
Limits on records, signature buckets, findings and wall time remain explicit.

## Stack decision

Java/GTNHGradle captures the running Forge 1.7.10 pack. Python 3.11+ owns
Dataset with standard-library SQLite/FTS5, gzip and JSON. FastAPI exposes
local HTTP, Uvicorn runs it, and the official Python MCP SDK exposes stdio.
React/TypeScript/Vite provides the human UI. This gives GUI and agents one
domain implementation. A separate TypeScript query engine would duplicate
matching and acquisition semantics, so the UI remains a client. A native
desktop wrapper is not required for the local browser UI.
