# Machine coverage evidence

The selected machine and crafting declarations agree with their captured native
NEI displays. This is a bounded coverage check, not certification that every
recipe in the pack was captured or that every displayed recipe can execute.
The matching native registry and source provide recipe costs and conditions
that the saved NEI views do not expose.

The evidence was collected on 2026-10-14 from the immutable baseline snapshot
`2830da9f-c040-4233-a778-036e4b27f3eb` and the separate static crafting recapture
`779ea030-ae9c-40ea-8854-99a176f7cc42`. The baseline remains preserved.

## Runtime and source versions

The captured runtime contains GT5-Unofficial `5.09.54.221` and
GTNewHorizonsCoreMod `2.9.88`. The GT5 JAR SHA-256 is
`60ceb229cd894dd28393efb6d0013de2835289eeef6fcf84ad3e17a6475baf5b`.
The CoreMod JAR SHA-256 is
`fcc18bde0638931c3559d41a6322a71b6b754e150439de856909d79c7d880117`.

Native source checks use the matching GT5 tag `5.09.54.221`, commit
`0c2037baa0a0c145f4f2e021729cf5621a1850f5`, and CoreMod tag `2.9.88`.
The local GT5 checkout was 19 commits beyond that tag when inspected. Its newer
HEAD is not evidence for the captured runtime. Version-specific source excerpts
are retained in
[gt5-matching-version-source.txt](exports/machine-coverage-20261014/gt5-matching-version-source.txt)
and
[coremod-matching-version-source.txt](exports/machine-coverage-20261014/coremod-matching-version-source.txt).

The fresh capture used a pinned daily 783 manifest dated 2026-10-11. Both
captures contain 323 mods, with only the exporter JAR hash changed. Seven of ten
config or cache hash differences are proven serialization-only. The
IguanaTinkerTweaks restrictions file and two MobsInfo caches remain unproven.
This does not establish byte-identical configuration. The exact comparison and
its normalization rules are recorded in
[CRAFTING_OUTPUT_RESEARCH.md](CRAFTING_OUTPUT_RESEARCH.md).

## Selected declaration check

The selected cohort contains **70 recipes: 66 GT recipe-map declarations and
four vanilla registry declarations**. The latter are one furnace declaration
and three CraftingManager declarations whose native class is `GTShapedRecipe`.
Calling these four vanilla refers to the registry family, not the mod that
registered the crafting recipes.

| Captured family | Selected recipes |
| --- | ---: |
| Primitive blast furnace | 46 |
| Electric blast furnace | 5 |
| Assembler | 2 |
| Bending machine | 4 |
| Forge hammer | 2 |
| Macerator | 2 |
| Ore washer | 1 |
| Thermal centrifuge | 1 |
| Centrifuge | 1 |
| Simple dust washer | 1 |
| Cauldron display | 1 |
| Minecraft smelting | 1 |
| Minecraft crafting | 3 |
| **Total** | **70** |

All selected declarations have matching saved NEI views. The matching method
requires equal input and output slot counts, then finds an order-independent
injective slot match using native identity and amount. It expands captured
native group membership and checks output chances. Intersection with a valid
native alternative permits NEI's unified display representation. It does not
expand every possible combination of ingredient alternatives.

The handler selection contains **16 handlers**. Their full captured view counts
are context for the selection, not counts of individually audited recipes.

| Handler | Captured views |
| --- | ---: |
| Shaped crafting | 51,830 |
| Shapeless crafting | 6,123 |
| Smelting | 9,683 |
| Assembler | 10,578 |
| Blast furnace | 2,033 |
| Macerator recycling | 12,495 |
| Cauldron | 860 |
| Thermal centrifuge | 693 |
| Forge hammer recycling | 200 |
| Ore washer | 680 |
| Macerator | 12,498 |
| Bricked blast furnace | 418 |
| Centrifuge | 1,392 |
| Simple dust washer | 1,247 |
| Forge hammer | 12,816 |
| Bending machine | 3,784 |

The selected steel cohort contains **five electric blast furnace declarations
and 46 primitive blast furnace declarations**. Those numbers describe reviewed
steel-producing declarations, distinct from the 2,033 and 418 total captured
handler views. Recycling handlers can expose another view of a recipe map.
Their display counts must not be added as independent machine recipe totals.

The complete selected records, resource names, matched handler keys and view
indices are in
[coverage-evidence.json](exports/machine-coverage-20261014/coverage-evidence.json).
The unmodified native process declarations are in
[native-processes.json](exports/machine-coverage-20261014/native-processes.json).

## Native steel example

Baseline process `p34292`, native blast furnace map index 401, matches NEI
handler `h209`, view 63. It declares the following conversion:

| Input or output | Native declaration |
| --- | --- |
| Consumed iron | 1 Iron Dust |
| Consumed carbon | 1 item matching `dustAnyCarbon` |
| Required circuit | Programmed Circuit configuration 11, presence only |
| Consumed fluid | 1,000 units Oxygen |
| Main output | 1 Steel Ingot, chance 100% |
| Secondary item output | 1 Ashes, chance 1,111/10,000, or 11.11% |
| Secondary fluid output | 250 units Carbon Dioxide, chance 100% |
| Recipe EU/t | 120 |
| Recipe duration | 500 ticks, or 25 seconds |
| Coil heat condition | 1,000 |
| Nominal recipe voltage class | MV |

The carbon slot has alternatives, including carbon, coal, charcoal and lignite
dust. It requires one valid alternative, not every listed resource. The circuit
has native amount zero. The export models that as a required presence slot with
amount one, rather than consumed circuit stock.

CoreMod `2.9.88` registers this declaration in `BlastFurnaceRecipes.java`, lines
482 to 490, using `.circuit(11)`, output chances `(10000, 1111)`, Oxygen 1000,
Carbon Dioxide 250, duration `25 * SECONDS`, `TierEU.RECIPE_MV`, and coil heat
1000. The matching native process records 120 EU/t, 500 ticks, and the same
heat. These cost and condition claims come from the native capture and matching
source. The saved NEI view does not independently verify EU/t, duration, or heat.
MV is the nominal recipe voltage class, not a claim about every machine's
capability or its overclocked operating cost.

## Broader paired NEI comparison

The separate source-proven comparer supports six profiles: alloy smelter, fluid
solidifier, macerator, metal bender, ore washer, and Minecraft smelting. Electric
and primitive blast furnace displays in the selected check are outside these
six profiles. The two checks therefore have different scopes.

| Paired comparer result | Baseline | Fresh capture |
| --- | ---: | ---: |
| Matched canonical projections | 78,389 | 78,389 |
| Differences | 0 | 0 |
| Missing canonical projections | 0 | 0 |
| Missing NEI projections | 0 | 0 |
| Reference handlers | 366 | 366 |
| Reference views | 287,464 | 287,123 |
| Unsupported reference projections | 209,131 | 208,790 |
| Capture failure events | 15 | 15 |
| Reference complete | false | false |

These counts compare unique canonical presentation projections. They do not
prove duplicate registration multiplicity or full pack coverage. Both reports
have zero ambiguous resource projections and zero ambiguous canonical
candidates. There are 181,390 canonical records outside the mapped profiles.
The 15 failures are capture events, not a count of distinct missing recipes.
Unsupported handlers, maps, frontends, and layouts remain unverified.

The saved comparer records its NEI source commit as
`550e85c456ff2a2ac92c47af4235ad3aa46beecb`. Its source references and exact
limitations are retained in
[paired-nei-baseline.json](exports/machine-coverage-20261014/paired-nei-baseline.json)
and
[paired-nei-fresh.json](exports/machine-coverage-20261014/paired-nei-fresh.json).

## Crafting and execution limits

The selected casing `p200220`, hull `p226207`, and Double Iron Plate `p230995`
were ordinary exact GT shaped declarations with unresolved output metadata in
the baseline. The fresh capture proves their static output transformations
have no effect under the supported classifier. Their declared inputs and
outputs match the baseline and the saved raw NEI views. They now have certain
output chance, resolved static output, and known voltage non-applicability for
the crafting grid.

That result does not certify hammer or wrench reuse. Native container returns,
tool damage and breakage remain unresolved. Energy, duration, and amperage for
these grid declarations remain null. Unsupported dynamic output, custom
subclasses, NBT transfer, enchantments, and electric charge transfer remain
outside the static classifier.

The selected cauldron record is a fake display recipe. Display agreement does
not certify its execution. For other machines, captured executable metadata
and declared ingredients do not prove that every native machine predicate,
environmental condition, or available inventory has been satisfied. Furnace
fuel, time, EU, and XP are also outside the paired display check. Generic NEI
chance fields are presentation data and do not establish production probability
without the native recipe semantics.

This report consolidates existing evidence only. It introduces no additional
game run, source research, or implementation change.
