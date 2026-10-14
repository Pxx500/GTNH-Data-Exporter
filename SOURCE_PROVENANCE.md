# Source provenance and bounded initial processing

Checked 2026-10-14 against snapshot `2830da9f-c040-4233-a778-036e4b27f3eb`.
The canonical `exports/runtime-developer-analysis-final/index.sqlite` was opened
with SQLite `mode=ro`. No source records, native rules or canonical indexes were
changed.

## Purpose and owner

Resource search should distinguish a captured world definition from a captured
inventory drop, a stochastic mining candidate and an early processing derivative.
None proves that a player can find the source, satisfy its conditions or obtain
the inventory needed by a complete plan.

`gtnh_data.acquisition.summarize_acquisition` owns this interpretation. It adds
`provenance` beside the existing `acquisition` and `unification` fields. Dataset
resource pages and the acquisition inspector use the same summary. No separate
source store, changed resource identity or mining recipe is introduced.

Provenance is a snapshot fact or an explicitly bounded inference. It is independent
of profile membership. A profile's base materials remain the user's selected
planning boundary. The summary never stops recipe expansion automatically.

## Contract

Each resource's `acquisition_analysis` has this additional structure:

```json
{
  "provenance": {
    "world_source": {
      "status": "mining_rule_candidate_only",
      "evidence_counts": {
        "generated_ore_block": 0,
        "confirmed_mining_drop": 0,
        "mined_item_rule_candidate": 39,
        "direct_world_source": 0,
        "unresolved_source": 0
      },
      "evidence": [],
      "inventory_obtainable_proven": false
    },
    "initial_processing": {
      "status": "inferred",
      "confidence": "heuristic",
      "max_steps": 3,
      "evidence": [],
      "limit_reasons": [],
      "execution_proven": false,
      "reason": "Bounded native ore-processing families, prefix transitions and same-material main products with captured mining evidence. Other recipe inputs and machine conditions remain unproven"
    },
    "renewable": {
      "status": "unknown",
      "reason": "Captured sources and recipe cycles do not prove replenishment or a self-sustaining supply"
    },
    "basic_suggestion": {
      "suggested": true,
      "requires_user_selection": true,
      "reason": "Captured sources or bounded initial processing can inform a user-selected planning boundary"
    }
  }
}
```

The existing `acquisition.source_count` still counts captured source records,
including generated blocks and unresolved definitions. It must not be interpreted
as confirmed inventory acquisition. Its existing `obtainable_proven` stays false.

`world_source.status` is one of:

| Status | Evidence |
| --- | --- |
| `captured_inventory_source` | An active or conditional positive baseline mining output, or a captured direct supply definition |
| `mining_rule_candidate_only` | An active or conditional native mining-rule candidate, without a confirmed baseline or direct supply definition |
| `generated_block_only` | Active or conditional generated ore-block definitions, without inventory-source evidence |
| `no_active_source_evidence` | No evidence in those categories. Disabled or unknown sources can still appear as unresolved references |

`confirmed_mining_drop` means a captured native baseline definition with a
positive amount and positive chance. It does not confirm final player harvest
after tool and event modifiers. `mined_item_rule_candidate` remains a candidate
from the imported stochastic rule, without a fixed independent amount or chance.
Import validation already checks the native rule's positive support and exclusive
outcome semantics.

Native underground-fluid definitions have no fixed output amount. An active or
conditional fluid resource from `GTMod.proxy.mUndergroundOil`, with positive
native `min_amount` and consistent `max_amount`, is direct world-source evidence.
The native configuration range remains in details. It is not converted into a
guaranteed inventory quantity or a renewable-supply claim.

Source evidence references contain `source_id`, `kind`, `status`,
`resource_semantics`, `classification`, `confidence`, `environment_ids`,
`generated_source_id`, `generated_resource_id` and `native_owner`. Confidence is
`captured_definition`. Examples are bounded by `evidence_limit`, default 5.

`summarize_acquisition(..., include_source_details=True)` adds original
`conditions`, `parameters` and complete exported `environments` to those examples.
Default resource search keeps concise references. The inspector should use the
details flag. Environment IDs remain references to captured rules, including
unresolved dimension mappings or gates. They do not certify an actual deposit in
a saved world.

## Initial-processing heuristic

The inference examines at most three recipe transformations backward from the
requested resource. It requires all of these witnesses:

- A concrete item with captured `GTOreDictUnificator.getItemData` association and
  native `gregtech.api.enums.Materials` identity
- Matching material name on both sides, from the native association rather than
  display text, chemical formula or ore-dictionary spelling
- Null NBT and concrete metadata. Wildcard or tagged identities remain outside
  this bounded heuristic because native material association ignores NBT
- A captured executable, enabled, nonfake process with interpreted inputs and
  positive first captured output. This is the bounded heuristic's main-product
  convention. Unresolved dynamic recipes cannot supply evidence
- Native `GTRecipe` provenance whose map agrees with its process family
- A permitted prefix transition in the table below
- One consumed item slot. Fluids and presence requirements remain recipe
  obligations, while extra consumed solid slots reject this simple inference
- A source-backed input identity, matched through its exact or captured
  unified/ore-dictionary input rule. Output variants are never relabeled through
  unification membership
- A baseline or candidate native mining source from `GTOreAdapter`, whose captured
  mining material matches the input's native material

| Family | Permitted transitions |
| --- | --- |
| Hammer and macerator | `ore*` or `rawOre` to `crushed`, `crushed` to `dustImpure`, `crushedPurified` to `dustPure`, `crushedCentrifuged` to `dust` |
| Ore washer | `crushed` to `crushedPurified` |
| Thermal centrifuge | `crushed` or `crushedPurified` to `crushedCentrifuged` |
| Centrifuge | `dustImpure` or `dustPure` to `dust` |

The whitelist is a declared heuristic. It does not cover every mod's processing
family. Ore prefixes include captured stone variants. Smelting, construction,
recycling, material changes and secondary recipe outputs do not extend the tag.
The native snapshot contains real recycling and secondary Iron Dust outputs, so
family-only or generic reachability classification would give false positives.

An inferred witness records `source_resource_id`, `source_id`, `source_semantics`,
`source_classification`, `material`, ordered `process_ids`, ordered `resource_ids`
and native `prefixes`. Candidate-backed evidence stays candidate-backed. The
`confidence` is `heuristic` and `execution_proven` is false.

Default examples prefer a confirmed baseline witness and a `rawOre` seed before
more conditional candidate or stone-variant examples. This changes which bounded
witnesses are shown, not resource identity or recipe execution.

The query has resource and process budgets of 10,000 discovered candidate
identities and 20,000 producer reads. Hitting a budget is reported in
`limit_reasons`. `no_bounded_evidence` means no witness was found under this scope,
not that no other origin exists. Budget-limited results must not enter a
per-resource cache, because batch composition can change what was inspected.

The witness does not solve every AND dependency, presence requirement, machine
condition, quantity, stochastic inventory outcome or startup-stock requirement.
An acquisition inspector's grounding result remains separate. Source-distance
experiments and user-assumed base seeds also remain separate from provenance.

## Native examples

IDs below were freshly resolved in the final canonical snapshot. Prior capture
notes have different IDs. For example, `r113637` is Pollucite Ore in this snapshot
and must not be reused as an Iron Ore example from an earlier capture.

| Resource | Identity | Result |
| --- | --- | --- |
| `r109382` | Iron Ore, `gregtech:gt.blockores2`, metadata 8032 | Natural generated world block. Three generator records, no captured inventory drop for this exact natural identity |
| `r13340` | Iron Ore, `gregtech:gt.blockores2`, metadata 32 | Actual nonnatural inventory ore block from three captured silk baseline branches |
| `r25437` | Raw Iron Ore, `gregtech:gt.metaitem.03`, metadata 5032 | Actual plain mining product, 117 captured baseline source records |
| `r4010` | Crushed Iron Ore, `gregtech:gt.metaitem.01`, metadata 5032 | 39 native small-ore candidate records and separate bounded processing evidence |
| `r5459` | Impure Pile of Iron Dust, `gregtech:gt.metaitem.01`, metadata 3032 | A captured native small-ore candidate used by a dust-processing witness |
| `r5090` | Iron Dust, `gregtech:gt.metaitem.01`, metadata 2032 | No direct source. Bounded initial-processing evidence and canonical native unification anchor |
| `r5089` | Iron Dust, `IC2:itemDust`, metadata 5 | No captured source or producer and no bounded processing witness. Noncanonical variant prefers `r5090`, without confirmed output replacement |

`vein:ore.mix.magnetite` directly lists natural Iron Ore `r109382` as the
between-layer Stone output. The paired source
`mining:vein:ore.mix.magnetite:r109382:fortune0:plain` returns one `r25437`.
The silk branch returns one `r13340`. Both retain native Fortune 0, the live
`FortuneItem` policy, pickaxe level 2 and unmodeled tool/event modifiers. The silk
branch's effective mode is `Block`. Generation and inventory identities remain
distinct.

`mining:small:ore.small.iron:r116767:fortune0` includes `r4010` and `r5459`
as weighted native candidates. It does not emit them as a simultaneous inventory.

Examples of captured early-processing witnesses:

- The default confirmed witness is `r25437` to `r4010` through `p122475`, extended
  to `r4066` and `r5090` through `p183847` and `p121731`
- `r5459` to `r5090` through `p45275`, retaining the small-ore candidate source
- `r4010` to `r4066` to `r5090` through `p183847` and `p121731`, retaining the
  candidate source and the `crushed`, `crushedCentrifuged`, `dust` prefixes
- Confirmed silk-mined Iron Ore `r13340` to `r4010` to `r4066` to `r5090`
  through `p122798`, `p183847` and `p121731`

## Performance and preparation

Measured locally with Python 3.14, SQLite and a read-only canonical connection.
These are diagnostics rather than stable timing guarantees. Full summary results
include unification, producer counts, source evidence and bounded processing.

Two existing join plans were expensive. The producer query chose all process
records as its outer scan, then probed each requested resource. Explicit
`outputs CROSS JOIN records` keeps indexed output matches first. Native
unification now starts with resources and reverse membership, then loads only
their groups and anchors. NBT equality, native anchor ownership, wildcard
exclusion and ambiguous-anchor behavior remain unchanged.

| Probe | Observed time |
| --- | --- |
| Original full broad 1,000-resource summary | 48.7 to 50.6 s |
| Original isolated unification for 1,000 resources | 6.24 s |
| Revised isolated unification for 1,000 resources | 0.070 s |
| Source evidence only, 10 or 30 general resources | Less than 1 ms |
| Source evidence only, 1,000 general resources | 0.269 s |
| Full summary, 10 general Iron-named resources | 0.059 to 0.062 s |
| Full summary, 10 or 30 Iron Dust-named resources | 0.285 or 0.313 s |
| Full summary, 30 dust/crushed resources | 0.653 to 0.654 s |
| Full summary, 1,000 general resources | 0.377 to 0.380 s |
| Full summary, challenging 1,000 dust/crushed resources | 4.07 to 4.09 s, with resource and process budgets disclosed |
| Detailed source examples for seven native probes | 0.120 s |

Dataset retains up to 1,024 complete per-resource summaries to make repeated
autocomplete inexpensive. The cache belongs to that immutable Dataset instance,
uses a lock, returns detached copies and does not retain budget-limited inference.
No new persistent provenance store is justified by these measurements. Inspector
details remain a fresh bounded summary and keep profile grounding separate.

## Verification

Focused tests exercise the real snapshot importer and public acquisition summary.
They cover generation versus baseline versus candidates, disabled definitions,
source environment details, recycled raw items retaining their origin, native
fluid definitions, three-step inference, a four-step rejection, material changes,
unproven generated blocks, unresolved dynamic output, NBT, secondary products,
additional consumed solids, input group matching and unchanged output-variant
identity. Existing acquisition, resource-search and Dataset tests also run.

The first source test failed for the expected missing summary details keyword
after fixture schema corrections. The initial-processing fixture was temporarily
blocked by a concurrent Windows flow-index file-handle failure. Its owner fixed
that issue. A controlled in-memory mutation removing processing transitions then
made the real summary regression fail with `no_bounded_evidence` instead of
`inferred`. The restored production code passes the focused suite.

Final verification command, from the `python` directory with `PYTHONPATH=src`:

```text
python -m unittest tests.test_acquisition tests.test_resource_search tests.test_dataset
```

All 29 tests passed in 3.737 seconds after the final source change.

Native examples were separately checked against exported source payloads and
actual recipe identities. No game launch or mining trial was performed. Full
player/tool harvest, observed deposit locations, complete acquisition coverage
and renewable supply remain unverified.
