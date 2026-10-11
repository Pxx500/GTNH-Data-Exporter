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

## Current coverage

- The live GT recipe-map catalog and all entries are visited, including fake,
  hidden and disabled recipes. Fake/disabled entries are non-executable
- The real Assembly Line registry carries research as a structured condition
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

This is partial pack coverage. Non-GT machine/NEI-only recipe handlers, other-mod
acquisition, mining-drop distributions and saved deposits are unsupported.
Native machine metadata not structurally understood carries its class/text
and an uninterpreted status. Conditional worldgen is not observed occurrence.
Underground-fluid blacklist/provider matching remains unresolved, with raw
rules and captured config digests. Referenced resources are not a full NEI
catalog. Counts are not a claim of complete semantics.

## Verification

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
