# Runtime exporter

This module captures the running GTNH registries into the canonical format in
[FORMAT.md](../FORMAT.md). It contains no images, query engine or user inventory
capture. Opt-in autorun starts a unique isolated creative flat world, waits for
FML load completion, server start, GT's completed first-world callbacks and an
attached client world/player, then captures at ServerTick END with LOWEST
priority. It exits only after publishing the manifest, or with exit code 2 on
capture failure.

The readiness signal is `GTValues.worldTickHappened`, set after
`GregTechAPI.sFirstWorldTick` by the native `GTProxy.onWorldTickEvent`.
There is no fixed menu delay. The isolated world is left in the prepared
runtime's saves directory. No existing save is opened or overwritten.
An integrated server stop before readiness is a failure. A separate bootstrap
deadline also reports failure and exits with code 2 even if client world launch
blocks. `gtnh.data.bootstrapTimeoutSeconds` sets that error deadline, default
180 seconds. The deadline never establishes readiness or starts a fallback run.

The isolated world uses a fixed nonzero seed. GT's XSTR generator degenerates
to an all-zero stream for seed zero, which caused repeated ruin generation and
a native enchantment failure during the original bootstrap. The manifest
records the actual server seed as an exact decimal string.

## Build and run

Run Gradle only through the agreed Context Mode runner. This module uses
GTNHGradle settings convention 2.0.19 and wrapper 9.2.1. The local init script
provides the full-pack task from Pxx500GTNHGradle. A Java 25 override is needed
for that local plugin. It does not change the system Java installation.

```powershell
.\gradlew.bat '-Dorg.gradle.java.home=C:\Program Files\Java\jdk-25.0.4.1' test build --no-daemon
.\gradlew.bat '-Dorg.gradle.java.home=C:\Program Files\Java\jdk-25.0.4.1' runFullPack -PdataAutorun=true '-PdataOutputDir=C:\absolute\new-snapshot-directory'
```

Ordinary `runFullPack` does not activate capture. A JVM caller can instead set
`gtnh.data.autorun=true` and `gtnh.data.outputDir`. The output directory must not
already exist. Failed output directories never have a published manifest and
are retained for diagnostics. Parent automation owns game execution.

Add `-PdataNeiReference=true` to the autorun invocation for a paired NEI
validation reference. The equivalent JVM property is
`gtnh.data.neiReference=true`. This mode waits for `NEIClientConfig.isLoaded()`
and `ItemList.loadFinished` before the canonical server capture. It then
captures the NEI reference on the client thread and publishes the canonical
manifest after the reference summary. The existing bootstrap deadline covers
NEI readiness. `gtnh.data.neiCaptureTimeoutSeconds`, default 180 seconds, bounds
the paired capture and fails the process if a native query blocks.

The fresh `nei-reference/` child contains `handlers.jsonl.gz`,
`signatures.jsonl.gz`, `handler-views.jsonl.gz` and `summary.json`. These are
separate from the six canonical streams. The summary binds the same canonical
snapshot ID and pack/config digest cohort, plus per-file checksums and counts.
It also checksums `presentation-context.json`, which binds closed canonical
resource/process files and declares independent `gt-display-aliases.jsonl.gz`
and `item-pools.jsonl.gz` streams. Context uses direct original GT anchors and
the public NEI item pools before handler enumeration. It preserves ordered
quantities and typed NBT rather than deriving alternatives from recipe views.
Handler errors, empty queries and projection failures remain distinct. A
completed partial reference can publish with `complete=false`. Fatal I/O or a
deadline failure exits with code 2 without a canonical manifest.

Signatures use `Recipe.of(handler,index).getRecipeId().toJsonObject()` and are
labelled `native_recipe_id_api`. This is an API projection, not an actual
`/recipeid` command dump. All registered crafting and serial crafting handlers
are queried through their native all-recipes contract. The command's
recipe-ID blacklist is not applied, and the summary says so.

Handler views preserve ingredient, result and other-stack presentation
categories separately. Every raw `PositionedStack.items` alternative uses
NEI's own `StackInfo.itemStackToNBT` and `NBTJson` conversion. This JSON retains
NEI's projection ambiguities and is independent from canonical typed NBT.
Other stacks can be fuels or auxiliary presentation, not necessarily outputs.
Native `getChance()` values are presentation data whose default can be 10000,
not verified runtime probabilities. Exact `GTNEIDefaultHandler` records map
through public `getRecipeMap()` to the full canonical `gregtech:` family.
Public frontend properties and GT `FixedPositionedStack.realStackSize` retain
quantity/unification presentation context without replacing the raw stack JSON.
Custom frontends, filters and getters still need scoped comparison support.

The NEI reference extension compiled against the consuming module's explicit
`NotEnoughItems:2.8.159-GTNH:dev` dependency. The module model and documented
library-search source CLI found its actual attached sources. The generic
library-search launcher failed to prepare the nested module, and that failure
is retained in `build/nei-library-search.log`. `test build` passed with the
three existing contract tests. IntelliJ completed with 34 advisory findings.
Direct installed PMD, using the same audit rules and 115 actual compile
classpath entries, completed with 43 advisory findings and no processing or
configuration errors. The combined runner still skips PMD because its Git-root
lookup misses this module's wrapper. New findings concern method/class
complexity, duplicate close handling and style, not observed capture failures.
No audit suppressions were added. These checks establish compilation and
static analysis, not runtime NEI coverage or equivalence.

## Current coverage

- The live GT recipe-map catalog and all entries are visited, including fake,
  hidden and disabled recipes. Fake/disabled entries are non-executable
- The real Assembly Line registry carries research as a structured condition
- Native EnderIO Sag Mill no-ball and ordinary Alloy Smelter manager records
  retain ordered AND slots, OR alternatives, quantities, all products and total
  RF. Duration and EU/t stay unknown. Machine modes and native first-match
  selection remain explicit conditions. Grinding-ball variants and the alloy
  vanilla helper path are unsupported
- Forestry Centrifuge retains one-item consumption, native product quantities,
  recipe-side wildcard metadata and asymmetric NBT predicates. Output rolls
  use strict float thresholds separately, with guaranteed outputs bypassing
  RNG. Native work ticks and the five-game-tick work interval remain explicit.
  Effective machine duration and energy are unknown. Native HashSet order is
  within-run selection evidence, not a stable cross-run priority
- GT small ores retain exact Fortune 0 weighted replacement rules and mutually
  exclusive host dust, including combined identical dust outcomes. Potential
  item outputs are indexed without fixed amounts or independent chances and
  cannot establish inventory or cycle seeds. No RNG evaluation is used
- Exact EnderIO `RecipeInput` metadata matching is determined by its public
  matcher using a copied stack at a verified distinct metadata value. NBT is
  ignored by the native predicate. Ore Dictionary inputs retain all current
  public equivalents and their metadata predicates. Unknown/custom predicates
  and nonpositive/fluid inputs remain unresolved
- EnderIO output chances preserve the native float threshold, inclusive
  comparison and shared roll. The canonical probability counts accepted
  outcomes on `Random.nextFloat()`'s 24-bit lattice, so threshold zero retains
  one outcome rather than a false definite-zero probability. Nonfinite
  thresholds remain unsupported. Wrapper UID/class/order evidence accompanies
  coverage, with private manager bindings disclosed as a public-API limitation
- Native zero-count ingredients are presence requirements with their original
  zero recorded. Item/fluid alternatives retain individual quantities
- Item NBT, damage, fluid NBT, output chances and co-products are preserved
- Known vanilla/Forge shaped/shapeless crafting is captured. Dynamic/custom
  crafting records remain explicitly unresolved. Returned containers/tool wear
  are native-unknown rather than silently claimed to be consumed
- Exact `GTShapedRecipe` and `GTShapelessRecipe` classes expose their inherited
  declared input slots and alternatives. Keeping-NBT shaped recipes and all GT
  shapeless recipes retain `native_unknown` matching with declared anchors,
  because NBT correlation and the private shapeless inventory validator are
  not evaluated. Other subclasses remain opaque
- GT crafting outputs are native templates with `dynamic_output=unresolved`,
  unknown chance and unknown execution status. Native item updates, electric
  charge transfer and configured enchantments are not evaluated. The query
  engine can use the declared catalog for lookup but excludes these output
  templates from confirmed material paths
- Unregistered native item inputs retain their class, amount, metadata, typed
  NBT and display name as `native_unknown`. They have no fabricated registry ID
- Active GT normal/small ore lists and underground-fluid config rules are
  exported. Ore outputs identify generated blocks, not mining drops
- The registered Forge dimension catalog includes unloaded dimensions. GT
  named generation contexts are separate when numeric mapping is unresolved
- Actual mod versions/source-file hashes and config/script hashes accompany
  the snapshot

This is partial pack coverage. Other machine/NEI-only recipe handlers, other-mod
acquisition, mining tool/event modifications and saved deposits are unsupported.
Native machine metadata not structurally understood carries its class/text
and an uninterpreted status. Exact native `Sievert` values retain their type,
integer `sievert` and boolean `isExact`. Exact native `Materials` values retain
their type and `material_name` from public `getName()`, the native material
registry key. This is a material identity, not a full material-property model.
Other unsupported metadata objects and subclasses of these two classes remain
explicitly uninterpreted.
Conditional worldgen is not observed occurrence.
Underground-fluid blacklist/provider matching remains unresolved, with raw
rules and captured config digests. Referenced resources are not a full NEI
catalog. Counts are not a claim of complete semantics.

## Verification

The combined Botania and independent-projection extension passed 22 Java,
55 Python and 19 GUI tests. Actual Botania `1.13.38-GTNH` resolves in the
consuming module. The final paired capture/import completed in 179.03 seconds.
All 152 base Mana Infusion ingredient/result records agree with same-run NEI.
Eight wildcard cases use independent pools. Eleven Mini Flower and two Magic
Bees subclass templates remain inspectable with unresolved execution.
GUI recipe details show exact total mana and required catalysts below the pool.

Schema 3 records the selected serializer through one equivalent public reverse
dispatch, with one call per reached handler. All 66,415 scoped projections
selected the default item serializer. The five-map GT/furnace comparison has
53,909 matches, zero differences and zero missing recipes. This includes 8,699
Fluid Solidifier matches and the Lapotron double-NBT case. Another 20,196 TiC
views are unverified because null and empty-compound TGregworks NBT collapse
in NEI's presentation. Native typed data remains distinct. Known Door failures
still prevent strict completeness. Historical contexts retain their captured
scope and original projection rules, with no retrospective inferred facts.

IntelliJ completed with 59 advisory findings. Direct PMD completed against the
actual classpath with 156 advisories and no processing/configuration errors.
The combined launcher still skips PMD because the wrapper is in this nested
module, so its skipped result is not the direct analysis. Complexity metrics,
Java 11 API suggestions for the Java 8 target and a nullable test-result warning
remain documented rather than driving unsupported behavior changes.

The Forestry/small-ore extension passed 15 Java tests and 46 Python tests.
The build resolves the actual Forestry `4.11.39` API. A fresh paired capture
and validated import completed in 179.46 seconds. All 2,106 small-ore rules
passed native sequence, weight, host probability, typed identity, link and
context checks. Existing 22,898 normal mining records remain semantically
unchanged. Potential rule products remain searchable and unresolved in trace.

All 154 native Forestry records were compared with scoped NEI item views.
153 match fully. One comb recipe has 49 native products, of which NEI displays
only nine. All nine displayed products match the native chance ordering and
quantities. Capture retains all 49 rather than treating the display cap as a
recipe limit. Native probabilities are source-backed, not verified through
generic NEI's default chance getter. All 1,674 EnderIO records remain unchanged
after moving their lattice calculation to the shared NativeCapture owner.

IntelliJ completed with 51 advisories. The combined runner still skips PMD
because its Git-root check misses the module wrapper. Direct PMD with the same
rules, actual classpath and Java 1.8 parser completed with 131 advisories across
production/tests and no processing or configuration errors. A consolidated
source review found no actionable correctness issues. Complexity and coupling
findings remain advisory.

The independent presentation extension passed all ten Java tests and a
fresh paired game capture in 176.56 seconds. Typed NBT reconstruction covers
native types 0 through 11, long bounds, empty typed lists and malformed values.
Closed stream declarations remain available before delayed publication.
Context checksum/count tests reject altered input before native queries.
IntelliJ completed with 46 advisories. The combined audit's PMD launcher
failed because `Get-FileHash` was unavailable in its environment. Direct PMD
with the same rules, actual exported classpath and Java 1.8 parser completed
with 96 advisories across production and test sources and no processing or
configuration errors. Complexity and existing style findings remain advisory.
This preserves the failed launcher evidence rather than declaring it healthy.

The bounded EnderIO adapter has a pure probability boundary test covering
threshold zero, one-half, one, negative values and unsupported nonfinite
values. The combined build passed all four Java tests. The real paired
capture verified 1,663 Sag Mill and 11 Alloy records, with no unresolved
inputs/outputs or invalid quantities in this measured set. All 4,403 native
output identity/amount entries agree with scoped NEI views. Native chances
and RF remain source-backed fields because generic NEI chances are defaults.

The integrated extension passed `test build` on 2026-10-12 with four Java
tests. Public API proof comes from attached GT `5.09.54.221` and EnderIO
`2.10.49` sources. No Forge fixture or production test hook was added.
IntelliJ reported 38 advisory findings. Direct PMD completed against the
exported compile classpath with 57 advisory findings and no processing errors.
After the observed login pipeline naming correction, the build passed again.
The focused readiness-file checks reported zero IntelliJ findings and three
PMD complexity advisories. Existing complexity warnings remain. Runtime
validation verified all 122 Sievert and 157 Materials records in the new
full-pack snapshot, with no missing fields or uninterpreted instances of
these exact classes.

The consuming module's actual GT dependency is `5.09.54.221`. Library-search
successfully exported its attached source inventory after model preparation.
The first compile found private GT NBT matching and an unavailable NBT list
getter. The code now reads public native input-matcher properties and a copy
of the list, without reflecting on private fields.

`test build` succeeded on 2026-10-11 with three regression tests. They check
compressed checksums/record counts, last-step manifest publication, refusal to
overwrite an existing snapshot, and typed NBT with exact 64-bit strings.
These were contract regression tests after implementation, not a claimed
red-first TDD cycle. Logs are under local `build/verification.log` and
`build/test-results/test/`. Build verification does not prove game capture.
The parent runs consolidated Java audit and the real full-pack smoke test.

For the exact GT crafting catalog extension, a plain JUnit fixture could not
initialize Forge's live registries without LaunchWrapper. It failed before
capture, so it was removed rather than reported as a behavioral regression
test. The existing three contract tests and build are rerun. The real full-pack
smoke must verify declared slots and unresolved matching/output flags.

The extension passed `test build` on 2026-10-12 with all three existing tests.
IntelliJ completed its recheck with 27 advisory findings. Its new constructor
reachability warning overlooks the Forge lifecycle entry point. The combined
runner skipped PMD because it resolves the Git root rather than this nested
Gradle module. A separate installed PMD run used the same bundled ruleset and
115 entries from the exported compile classpath. It completed without
processing or configuration errors. Complexity and nesting findings remain
advisory, including six for the crafting catalog method. No audit suppressions
or native runtime evaluation were added to hide these findings.

The first full-pack run on 2026-10-11 failed before capture during Galacticraft
server-start initialization of Ross128b. The native ruin chest called
EnchantmentHelper with an enchantment candidate set whose total weight was
non-positive, causing WeightedRandom to throw. The exporter had not entered
capture. The failed directory had no manifest. The exact native enchantment
entry is not present in the log, and no pack bug was patched. The new bootstrap
failure/deadline path compiled successfully. The three contract tests also
passed. The second runtime attempt failed automatically without publishing a
manifest, verifying the error path. A temporary read-only enchantment probe
recorded positive initial candidate sums and zero-weight candidates. It has
been removed, with diagnostic logs retained. The compatibility-filtered set
at the actual throw is unknown, so the exact offending enchantment is not
established. Parent verification covers the final build after probe removal.

The adapted MIT source is attributed in `NativeCapture.java` and
`CraftingCapture.java`, and the full
notice is retained in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Successful full-pack capture

The corrected bootstrap and collector completed a real run on 2026-10-11.
The manifest published after about seven seconds of capture. The game exited
successfully and the Python importer validated all checksums, record counts
and references before activating the SQLite index. Full pipeline time was
140.62 seconds. Local evidence is retained under `../exports/runtime-native-inputs`.

Counts are 122,835 resources, 186,528 groups, 257,788 processes, 224 sources,
119 environments and 185 coverage records. Five unregistered ItemDoor inputs
are explicitly unresolved. All 609 null group references found in the earlier
failed artifact are corrected by omitting absent group references. The failed
artifacts remain diagnostic evidence and were never published as datasets.

This establishes a working full-pack runtime capture for the implemented
domains. Custom crafting and non-GT machine semantics remain partial or
unsupported. Record counts alone do not prove full recipe coverage.
