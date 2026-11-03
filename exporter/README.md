# Runtime exporter

This module captures the running GTNH registries into the canonical format in
[FORMAT.md](../FORMAT.md). It contains no images, query engine or user inventory
capture. Opt-in autorun starts a unique isolated creative flat world, waits for
FML load completion, server start, GT's completed first-world callbacks and an
attached client world/player, then captures at ServerTick END with LOWEST
priority. It exits only after publishing the manifest, or with exit code 2 on
capture failure.

Mod versions are captured as provenance and do not gate execution or interpretation.
Adapters use the available native APIs, exact recipe and manager classes, and
observed data to identify unsupported behavior. Inventory artifact hashes must
match the current capture's manifest. They are not release allowlists.
Unknown subclasses and unresolved runtime transactions remain explicit.

The readiness signal is `GTValues.worldTickHappened`, set after
`GregTechAPI.sFirstWorldTick` by the native `GTProxy.onWorldTickEvent`.
There is no fixed menu delay. The isolated world is left in the prepared
runtime's saves directory. No existing save is opened or overwritten.
An integrated server stop before readiness is a failure. A separate bootstrap
deadline also reports failure and exits with code 2 even if client world launch
blocks. `gtnh.data.bootstrapTimeoutSeconds` sets that error deadline, default
180 seconds. The deadline never establishes readiness or starts a fallback run.

The isolated world uses a fixed nonzero seed, recorded in the manifest as an
exact decimal string.

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

For an optional registration-provenance trial, add
`-PdataNativeRecipeCallsites=true`, or use `--native-recipe-callsites` with
`scripts/export_full_pack.py`. This requests native GT callsite collection
before recipes are constructed and retains bounded raw stacks in process
provenance. It does not enable lookup validation or interpret ingredient roles.
Collection runs across native GT recipe construction. The export's byte limits
do not bound initialization or game memory. Runs without this option omit the
new provenance field. See the exact field and limits in [FORMAT.md](../FORMAT.md).

Add `-PdataNeiReference=true` to the autorun invocation for a paired NEI
validation reference. The equivalent JVM property is
`gtnh.data.neiReference=true`. This mode waits for `NEIClientConfig.isLoaded()`
and `ItemList.loadFinished` before the canonical server capture. It then
captures the NEI reference on the client thread and publishes the canonical
manifest after the reference summary. The existing bootstrap deadline covers
NEI readiness. `gtnh.data.neiCaptureTimeoutSeconds`, default 180 seconds, bounds
the paired capture and fails the process if a native query blocks.

The `nei-reference/` directory contains the paired reference and summary.
It is separate from the canonical snapshot. A partial reference reports
`complete=false`. Fatal I/O or deadline failures leave no canonical manifest.
See [FORMAT.md](../FORMAT.md#independent-nei-reference) for the reference
streams, comparison scope and limitations.

For a source-coverage inventory without querying recipe views, use
`--nei-reference inventory` with `scripts/export_full_pack.py`. Generate its
report with `python scripts/compare_nei.py PATH_TO_SNAPSHOT --mode coverage
--report exports/coverage.json --markdown exports/coverage.md`.

## Current coverage

- The live GT recipe-map catalog and all entries are visited, including fake,
  hidden and disabled recipes. Fake/disabled entries are non-executable
- The real Assembly Line registry carries research as a structured condition
- Avaritia 1.100 Extreme Crafting declarations are read from its separate
  registry. Exact shaped and shapeless classes retain ingredient occurrences,
  grid shape, mirroring, quantities and matching predicates. Precedence,
  repair and container returns remain unresolved, so these records have
  unknown executability. Other versions have explicit unsupported coverage
- Exact GT shapeless recipes retain output-transformation evidence. A verified
  static output supports lookup while custom input validation remains unresolved
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

## Attribution

The collector adapts MIT-licensed source from Calculation Oracle. See
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for the full notice.
