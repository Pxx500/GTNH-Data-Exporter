# Static GT crafting outputs

Investigated 2026-10-14 against GT5-Unofficial `5.09.54.221`, commit
`0c2037baa0a0c145f4f2e021729cf5621a1850f5`. The exported compile dependency is
the matching `GT5-Unofficial-5.09.54.221-dev.jar`.

## Confirmed gap and correction

The canonical snapshot contains Double Iron Plate recipe `p230995`, casing
recipe `p200220`, and hull recipe `p226207` as exact `GTShapedRecipe` declarations.
They have `keeping_nbt=false`, but CraftingCapture previously marked every exact
GT shaped recipe's output unresolved. Their output chances were null and
`executable` was null. Search and planning therefore excluded them.

CraftingCapture now recognizes certain output for an exact GT shaped declaration
only when all of these hold:

- Keeping NBT is disabled
- The declared output is positive and has no NBT compound
- The actual captured private `mEnchantmentsAdded` field is null
- The output is not electric under the native electric-item tier criterion
- Both native item-update calls are statically proven to have no effect

For supported declarations it exports a certain output chance, removes the
native-template output marker, and sets `dynamic_output=resolved_static`.
Known inputs can make the recipe executable. Unknown ingredients still prevent
an executable claim. This capability lives in the existing CraftingCapture owner.
No inventory is crafted, no native output callback runs, and no world callback
is invoked.

Supported static shapes also capture
`recipe_voltage_applicability=not_applicable_crafting_grid`. Dataset represents
this as known non-applicability with no numeric tier. It permits those grid
recipes under machine-voltage filters without inferring zero EU consumption.
Energy, duration, and amperage remain null. Other unknown-voltage recipes still
follow the explicit unknown-tier policy.

## Native semantics supporting the boundary

GT shaped output calculation copies the Forge declared output, calls
`GTUtility.updateItemStack`, conditionally copies input NBT, conditionally
transfers electric charge, conditionally adds configured enchantments, and
calls item update again. Its matching method adds NBT equality correlation only
when keeping NBT is enabled, then delegates to Forge shaped matching.
[Matching GTShapedRecipe source](https://github.com/GTNewHorizons/GT5-Unofficial/blob/0c2037baa0a0c145f4f2e021729cf5621a1850f5/src/main/java/gregtech/api/util/GTShapedRecipe.java)

`GTUtility.updateItemStack` calls `isItemStackUsable` only for GTGenericItem
outputs. Other output items therefore have no update transformation in this
method. `GTGenericItem.isItemStackUsable` itself returns true without mutation.
`MetaBaseItem.isItemStackUsable` runs its per-metadata behavior list before
delegating. Reflection checks the actual method owner, and the existing native
`mapEachBehavior` operation detects whether the list is empty without executing
behavior methods. Tool output overrides and other update implementations remain
unsupported. The metal MetaGeneratedItemX32 family inherits this MetaBaseItem
update path.
[GTUtility](https://github.com/GTNewHorizons/GT5-Unofficial/blob/0c2037baa0a0c145f4f2e021729cf5621a1850f5/src/main/java/gregtech/api/util/GTUtility.java),
[GTGenericItem](https://github.com/GTNewHorizons/GT5-Unofficial/blob/0c2037baa0a0c145f4f2e021729cf5621a1850f5/src/main/java/gregtech/api/items/GTGenericItem.java),
[MetaBaseItem](https://github.com/GTNewHorizons/GT5-Unofficial/blob/0c2037baa0a0c145f4f2e021729cf5621a1850f5/src/main/java/gregtech/api/items/MetaBaseItem.java)

GT shapeless recipes also have a private inventory Predicate and optional NBT
overwrite behavior. They remain unresolved. Exact-class dispatch also retains
unresolved status for subclasses that could replace native matching or output.
[Matching GTShapelessRecipe source](https://github.com/GTNewHorizons/GT5-Unofficial/blob/0c2037baa0a0c145f4f2e021729cf5621a1850f5/src/main/java/gregtech/api/util/GTShapelessRecipe.java)

Tool inputs cannot be labelled permanently reusable. GT tool container logic
copies one tool, applies its native crafting damage, and may return a damaged
tool, replace a broken tool, or return nothing. Its returned state depends on
NBT and native tool stats. The captured hammer slot also includes a Single Use
Hard Hammer, while the casing's wrench slot includes a Single Use Wrench.
The static output result does not settle these alternatives' return accounting.
[MetaGeneratedTool container and damage source](https://github.com/GTNewHorizons/GT5-Unofficial/blob/0c2037baa0a0c145f4f2e021729cf5621a1850f5/src/main/java/gregtech/api/items/MetaGeneratedTool.java)

The exporter retains `container_returns=native_unknown`. Supported static
outputs add explicit `tool_accounting=container_damage_and_breakage_unresolved`
and `input_accounting=declared_consumption_without_container_return_credit`.
Inputs retain the existing conservative consumed-slot representation. This
supports a dependency trace and a plan that supplies consumed input stock, but
does not certify tool reuse or an exact material balance including returned tools.

## Verification

Four focused tests cover ordinary exact GT shaped output, keeping NBT, tagged
outputs, configured enchantments, custom shaped subclasses, shapeless validators,
and electric output charge transfer. The ordinary static case failed before the
classifier was implemented and passes after it. All 30 exporter tests pass with
zero failures, errors, or skipped tests.

IntelliJ 2026.2.2 completed its inspection. Its latest report has 61 findings
elsewhere and no findings in CraftingCapture or CraftingCaptureTest. The initial
cast warning was corrected with an explicit MetaBaseItem type check.

The combined runner's PMD path first failed to load Get-FileHash, then reported a
skip because its Git-root wrapper check misses the nested exporter wrapper.
That skip is not analysis. PMD 7.26.0 was then run directly against all 24 exporter
Java files using the exported 123-entry classpath and Java 17 source parser.
It completed with zero processing or configuration errors and 173 advisory
findings. The focused recheck leaves seven complexity and nesting findings in
CraftingCapture. Six describe the existing capture method's structure. The new
classifier's cyclomatic count is 12 because it lists the independent exclusions
needed for output certainty. These short guards are retained without a metric-only
refactor. The new test file has no remaining PMD findings.

Logs and reports are in `exports/machine-coverage-20261014/`, including
`crafting-red.log`, `crafting-green.log`, `crafting-all-tests.log`,
`crafting-pmd.json`, `crafting-pmd-focused.json`, and the matching source extracts.
The successful library inventory and native source confirm API availability.

## Completed runtime comparison

Root authorized one coordinated autorun capture. It published snapshot
`779ea030-ae9c-40ea-8854-99a176f7cc42` in
`exports/runtime-crafting-static-20261014` and exited successfully after 2 minutes
54 seconds. The saved runtime clone had expired. The retained Daily 783 manifest,
dated 2026-10-11, was pinned through a local HTTP endpoint and a scoped Gradle
init script so preparation did not intentionally fetch the mutable daily manifest.
Its SHA256 is `1944cbd2d5efefc28aa433265058442d596525fc68145356cfb7499a04a5a431`.

The canonical database SHA256 remained
`231696a424ca5d36dd66d5b6fb266dacbdcdd35e81917047f42d2abf88e64ae4`.
All 323 mod entries match except the expected exporter JAR hash change.
Ten config or generated-cache byte hashes differ. Six are proven timestamp-only
by reconstructing the exact old hash. BogoSorter keybinds differ only in JSON
object order, also proven against the old hash. The IguanaTinkerTweaks restrictions
file and two MobsInfo cache files remain unproven as serialization-only. This is
not a claim of byte-identical configuration.

All 118,717 resource identities match as multisets, though 6,926 local IDs moved.
The comparison therefore remaps resources and unified-group anchors by full
kind, registry, metadata, and typed NBT identity. All 25,228 source records and
119 environment records match after that remapping.

Both captures contain 259,781 recipes. I/O, matching alternatives, roles, amounts,
chances, and EU/duration/amperage match as multisets after the intended static
interpretation change, resource remapping, OR/output ordering, and native capture
indices are normalized. Forestry's native product Map required removing its
within-run output index for comparison. All 154 Forestry recipe records then
match, including their conditions. A stricter ordered full-record comparison
still has 224 occurrences differing in array or opaque condition presentation
order. Uninterpreted Java object identity hashes are normalized only as capture
metadata and retain their uninterpreted status. This does not certify opaque
native conditions or identical native HashSet selection order.

The three accepted GT recipes retain exact ingredient and output identities and
amounts at their native indices. They now have `executable=true`, chance 1/1,
static-output interpretation, known voltage non-applicability, and explicit
unsupported tool-return accounting. Energy, duration, and amperage remain null.
The capture contains 11,822 supported static GT shaped declarations, with no
other recipe class marked static by this capability.

The saved declaration matcher also verifies all three against the fresh raw
NEI shaped views: casing at h0/12809, hull at h0/38656, and double plate at
h0/43432. Native identity, amount, ingredient slot count, and output presentation
chance agree. A default full NEI presentation chance alone is not independent
stochastic proof. Native GT source establishes the static output contract.

The complete mapped NEI comparer reports 78,389 matches and zero differences or
missing entries in each capture. Both references remain partial with 15 capture
failures and 366 handlers. Fresh reference views total 287,123 compared with
287,464 before. This is scoped presentation verification, not full game coverage.

The fresh database imported successfully and has a ready version 3 flow sidecar.
Import took about 38 seconds, including 16.94 seconds of flow preparation. The
sidecar occupies 97,185,792 bytes.

## LV route results and observed latency regression

Every request below uses `max_tier=1`, `unknown_tier_policy=exclude`, depth 12,
300 admitted processes, 8 paths, and 6 extra steps. Fresh identities were resolved
from canonical registry, metadata, and NBT identities rather than assumed IDs.

| Case | Material mode seconds | Result |
| --- | --- | --- |
| Crushed Iron Ore to Double Iron Plate | 0.620 | Iron dust, magnetic dust, ingot, plate, then native shaped double plate |
| Iron Dust to LV Machine Casing | 0.648 | Steel ingot and steel plate, then native shaped casing |
| Iron Dust to LV Machine Hull | 0.734 | Seven routes, including steel plate and steel casing branches |

Material mode reports no search limit for these cases. Its branch-job counts are
2/2, 9/9, and 9/9 respectively. These are represented search jobs, not proof that
all side ingredients or tools are available. The first hull spine uses Cast Iron
Plate, while the steel and casing spines are also returned. It does not require
the caller to force steel as a waypoint.

Diverse mode also finds all three, taking 3.482, 5.847, and 5.859 seconds, but
continues to report applicable work, state, variant, or enumeration limits.
It retains its existing shortest dependency-path interpretation and can explain
byproduct routes.

The first fresh queries exposed a real 100 to 232 second regression in a shared
unresolved-input scan. The engine owner replaced the global ingredient scan with
a correlated EXISTS query using the existing process-input index. Its focused
profile confirmed the same material result while removing about 99 seconds of
scan work. Four slow pre-fix results remain preserved separately from the six
`postfix` results. No duplicate query ran during that profile.

Runtime evidence is retained in `runtime-static-validation.json`,
`config-delta-proof.json`, `registry-equivalence.json`,
`forestry-order-equivalence.json`, `source-environment-equivalence.json`,
`fresh-raw-shape-nei.json`, `paired-nei-baseline.json`, `paired-nei-fresh.json`,
`fresh-LV-routes.json`, and `postfix-LV-routes.json` under the coverage evidence
directory. The current HTTP dataset pointer was not changed by this investigation.
