# Prepared flow search research

Snapshot `2830da9f-c040-4233-a778-036e4b27f3eb`, researched 2026-10-14.
The source database was opened read-only with SQLite immutable mode. Scripts,
parsed papers, and measurements are in `exports/flow-research-20261014/`.

## Decision

Prefer Dataset-owned prepared symbolic matching, early goal-distance guidance,
and an explicit material preference. Reject SCC islands as the primary macro
search abstraction for the accepted examples. Keep recipe identities, consumed
slots, OR choices, required-presence obligations, positive outputs, NBT matching,
and conditions intact. A dependency spine is not proof that all AND requirements
can be supplied.

Source depth is a useful optional diagnostic for Target from basics ordering.
It is not a sufficient material-flow objective or a new production requirement.

## Existing algorithm and useful candidates

Dataset already has a reverse shortest-path discovery pass, per-query match
caches, depth bounds, and enumeration within the discovered graph. Diverse
selection also has a forward seed pass, reverse discovery per consumed ingredient
of a target recipe, round-robin branch coverage, and A*-style enumeration using
reverse distance. The useful comparison is with this implementation, not an
artificial forward-only BFS.

| Candidate | Expected benefit | Evidence and decision |
| --- | --- | --- |
| Prepared symbolic matches plus goal-directed lower bounds | Reuse identity/group expansion between queries and prune before expensive discovery | Best-supported direction. Prepared relaxed distances are cheap and substantially reduce bounded traversal work |
| Explicit material-cost best-first search with target-slot coverage | Prefer construction material branches while retaining byproduct explanations | Needed for usefulness. Pure hop minimization still chooses the hydrogen branch for the hull. Use a declared objective, not a claim of fewest-hop optimality |
| SCC islands with macro-to-micro refinement | Replace many low-level steps with island crossings | Rejected for the main workload. Nearly every accepted material endpoint shares one giant SCC. Boundary witness preparation would be large |

The author's textbook derives admissible A* heuristics by solving a relaxed
problem. Its lower bound must not exceed the cost under the actual objective.
For a prepared flow graph, count one recipe traversal and relax other AND inputs.
An unfiltered distance remains a lower bound when query filters remove edges or
when the material objective adds nonnegative penalties. It cannot certify an
executable plan. [Poole and Mackworth, Informed Search](https://artint.info/3e/html/ArtInt3e.Ch3.S6.html)

Retro* models a molecule as an OR node and a reaction as an AND node. This is a
useful structural analogy for recipe alternatives and ingredient obligations.
Its learned neural costs and tree assumptions should not be copied into GTNH
without evidence. Cycles, reusable tools, multiple outputs, shared subplans, and
inventory accounting need their own contract. [Chen et al., Retro*, ICML 2020](https://proceedings.mlr.press/v119/chen20k.html)

HPA* precomputes concrete distances between cluster entrances and exits and then
refines a macro path. A sequence of islands alone therefore does not provide a
recipe witness. Its grid results do not establish speed or completeness for
this AND/OR dataset. [Botea, Müller and Schaeffer, Near Optimal Hierarchical Path-Finding](https://webdocs.cs.ualberta.ca/~jonathan/publications/ai_publications/jogd.pdf)

GRAIL uses SCC condensation and interval labels to reject impossible ordinary
directed reachability queries. Passing its label check can be a false positive
and still needs search. This could support a negative reachability filter, but
does not solve AND feasibility or find useful material routes. [Yıldırım et al., GRAIL, PVLDB 2010](https://www.vldb.org/pvldb/vol3/R24.pdf)

LPA* reuses search state across similar queries while graph costs change. The
snapshot is immutable and the accepted workload varies endpoints and filters.
Start with reusable matches and bounded distance caches before introducing
incremental-search state and repair machinery. [Koenig et al., Lifelong Planning A*](https://www.cs.cmu.edu/~maxim/files/aij04.pdf)

## Actual Dataset baseline

`exports/flow-search-20261014/baseline.json` was captured by the engine owner
before implementation changes. Cold means a fresh Dataset handle with the OS
filesystem cache retained. These are complete diverse-route queries, including
payload interpretation and result assembly.

| Case | Cold LV / MV / unrestricted seconds | Unrestricted examined processes | Unrestricted target branches |
| --- | --- | --- | --- |
| Iron Dust to LV Machine Casing | 8.70 / 9.50 / 10.29 | 10,000 | 1/1 |
| Iron Dust to LV Machine Hull | 7.00 / 11.20 / 10.77 | 10,000 | 3/3 |
| Crushed Iron Ore to Double Iron Plate | 2.39 / 8.70 / 6.75 | 8,415 | 2/2 |
| Iron Dust to Volcanus | 4.63 / 5.06 / 12.20 | 10,000 | 6/6 |

Steel already appears in casing and hull results. The unrestricted hull has
hydrogen first and steel third. The problem is ordering and work spent under
budgets, rather than an absolute absence of the steel route. LV double plate and
LV/MV Volcanus have no represented target branches in this baseline.

## Bounded prepared-graph experiment

`island_probe.py` builds resource-to-match-to-process-to-output arcs. Matching
mirrors Dataset's registry, metadata, NBT, wildcard, unified, and ore-dictionary
semantics. It includes positive consumed choices and positive outputs of
interpretable executable recipes. AND inputs are deliberately relaxed for this
experiment. No ingredient Cartesian product, all-pairs closure, or inventory
solver is built. A deterministic sample of 180 distinct descriptors, including
large sets and all supported match modes, exactly matched
`Dataset._choice_resources`.

| Prepared representation | Measurement |
| --- | --- |
| Resources / process nodes / match nodes | 118,717 / 211,800 / 68,518 |
| Total nodes / arcs | 399,035 / 806,837 |
| Shared match-resource memberships | 198,339 |
| Match-process memberships | 341,006 |
| Flattened process-input memberships | 750,243 |
| Flattened input/output pair upper bound | 824,494 |
| Preparation time | 5.49 s |
| CSR array storage | 5.63 MB |

Preparation includes reading and parsing resource and process payloads, building
identity maps, and constructing the graph. It excludes compressed serialization.
CSR storage is not Python peak process memory. That peak was not measured.
The compressed graph artifact is 5.38 MB and the explanatory JSON metadata is
12.87 MB. These are experimental formats, not prescribed production storage.

NBT-insensitive exact matching can expand more than an ore group. A Data Stick
descriptor has 933 candidates and tool descriptors have over 650. Production
keys should reflect matching semantics so equivalent insensitive anchors can
share preparation. Group membership is an input predicate, not resource identity.

`query_probe.py` compares plain Dijkstra with A* using exact reverse distances on
the prepared relaxed graph. Each recipe crossing costs one. It deliberately
does not reproduce Dataset's filtering, diverse enumeration, payload loads,
required-resource constraints, or result assembly.

| Case | Plain / guided arc work | Plain / guided milliseconds | Cold goal-distance milliseconds |
| --- | --- | --- | --- |
| Casing | 113,676 / 579 | 74.98 / 0.58 | 17.84 |
| Hull | 113,748 / 601 | 69.86 / 0.59 | 17.53 |
| Volcanus | 111,297 / 124 | 68.07 / 0.16 | 18.50 |
| Double plate | 12,422 / 187 | 6.72 / 0.20 | 17.84 |

Graph loading cost 88 ms. Each float64 goal vector occupies 3.19 MB. Include
distance preparation in cold query comparisons and bound any cache. The double
plate example shows that preparing a new exact goal distance can cost more than
a small unguided query. These numbers support early guidance, not an end-to-end
speedup claim. The hull still returns Iron Dust to Hydrogen to Molten Polyethylene
to Hull in three hops. A faster shortest route does not resolve material relevance.

## Island and hub measurements

The graph has 213,171 SCCs, with 272 containing more than one resource. Its largest
SCC has 24,494 resources, 20.63% of all resources, and 118,688 processes, 56.04% of
eligible processes. The next largest has 29 resources. Iron Dust, casing, hull,
crushed ore, and double plate all share the giant SCC. Volcanus is a singleton.

| Relaxed graph | Largest resource SCC | Largest process SCC |
| --- | --- | --- |
| Complete | 24,494 | 118,688 |
| Water removed | 24,488 | 117,472 |
| Hydrogen removed | 24,490 | 118,664 |
| Oxygen removed | 24,493 | 118,512 |
| All three removed | 24,483 | 117,270 |

The three fluids have 244, 262, and 319 positive-output producers. They matter to
local search order but do not create the SCC collapse on their own. Removing
them is a diagnostic experiment and is not a proposed search restriction.

There are 428,288 cross-SCC factor arcs and 276,145 distinct condensed arcs. The
giant component has 16,447 incoming boundary nodes and 5,750 outgoing boundary
nodes. A naive entry/exit preparation has up to 94.57 million potential pairs,
before exact recipe and AND witnesses. This was counted without materialization.

Grouping by native primary material is small but incomplete: 1,220 labels cover
28,631 resources, 24.12% of the snapshot. Largest labels are Wood 615, Steel 300,
and Iron 177. Family grouping has 146 recipe families, with fluid solidifier
28,895 and macerator 24,993 processes. Neither is evidence of small independent
search islands. Material labels and family labels are useful hints, not legal
boundaries or identity equivalence. Only 122,883 eligible processes have known
primary materials on both input and output sides.

## Source-depth hypothesis

The additional experiment assigns source seeds zero and iterates the following
consumed-slot potentials. An OR slot takes the minimum depth of its legal
identity alternatives. A recipe needs a finite value for every consumed slot.
Its output candidate is one plus either the maximum slot depth or the sum of
slot depths. A resource takes the minimum over producer recipes and its seed
value. This computes a derivation-depth hint under AND-max or a repeated-subtree
cost under AND-sum. It is not quantity feasibility.

Seeds have separate evidence classes. The world-rule scenario uses 7,621 positive
`mined_item_baseline` outputs from active or conditional captured sources.
These confirm a native drop rule under its conditions, not observed player stock.
The 240 `mined_item_rule_candidate` resources are tested separately. The 9,597
generated ore blocks are not treated as mined inventory. Underground-fluid
records have no output amount, so this strict experiment does not seed them.
The actual boundary-profile file is empty. Assumed Water is a distinct synthetic
profile sensitivity case. There are no measured-inventory seeds.

The experiment covers 202,902 recipes and 330,491 consumed slots. It excludes five
recipes with unresolved consumed choices and does not invent world seeds from
8,893 recipes without consumed inputs. Required-presence slots appear in 63,326
recipes and remain separate obligations. The metric does not certify tools,
machine access, voltage, quantities, chance, or native conditions.

| Potential | Baseline world rules | Plus candidate rules | Plus assumed Water |
| --- | --- | --- | --- |
| Finite resources | 49,620 | 49,643 | 49,620 |
| Crushed Iron Ore max / sum | 1 / 1 | 0 / 0 | 1 / 1 |
| GT Iron Dust max / sum | 1 / 1 | 1 / 1 | 1 / 1 |
| Water max / sum | 2 / 2 | 1 / 1 | 0 / 0 |
| Hydrogen max / sum | 1 / 1 | 1 / 1 | 1 / 1 |
| Casing max / sum | 4 / 5 | 4 / 4 | 4 / 5 |
| Hull max / sum | 6 / 26 | 5 / 23 | 6 / 25 |
| Volcanus | unknown | unknown | unknown |

IC2 Iron Dust remains unknown. Double Iron Plate has value 2 in every scenario.
Preparation cost 3.09 s. Each max/sum pass converged in 30 rounds and 89 to 97 ms.
With no external seeds, positive recipe-step costs cannot start an unseeded
cycle. In the actual baseline potential, 186 cyclic resource SCCs containing
679 resources remain wholly unknown. Recycling adds a positive step and does
not create arbitrarily decreasing labels.

The concrete shallow-hub witness is `p78242`: Raw Hydrogen Ice, a depth-zero
mining baseline, is fluid-extracted to Hydrogen at depth one. Source depth alone
would therefore encourage a cheap hydrogen branch even while the hull's steel
construction branch is deeper. Do not replace material relevance with this
scalar or hard-prune unknown resources in an incomplete dump.

AND-max is easier to explain as dependency depth. AND-sum can count the same
subplan repeatedly and ignores reusable/shared outputs, so its larger values
are not an admissible bound on a quantity plan's distinct recipe cost. Either
can order planning candidates or suggest a boundary, provided the evidence
class, assumptions, missing presence requirements, and unknown state remain
visible. Adoption is optional until an end-to-end planning benchmark shows value.

## Evidence and limits

Artifacts include `island-results.json`, `group-boundaries.json`,
`match-verification.json`, `query-results.json`, `source-depth-results.json`, and
`source-depth-witnesses.json`. Scripts retain exact resource and process IDs.
Timing samples are bounded single-run measurements on this host. End-to-end
Dataset improvements must be measured separately with the original filters,
limits, branch coverage, warm/cold costs, and regression cases.

Verified sources were fetched with bounded HTTP and PDF text parsing. The cited
PDFs returned HTTP 200, matching titles, and substantive parsed text. Discarded
lookups included an irrelevant arXiv ID, guessed CMU and Alberta paths returning
404, a disconnected JAIR request, Google challenge results, and a Bing shell
without search records. DuckDuckGo DOM results located the author-hosted HPA*
paper. None of those failed extractions is used as supporting evidence.

## Production implementation and measured results

The production implementation follows the prepared symbolic matching and explicit
material-selection direction above. Dataset owns a rebuildable SQLite sidecar
bound to the canonical snapshot manifest and analysis version. It stores shared
ingredient predicates, positive consumed relations and outputs, process voltage
declarations, material hints, and a compact factor graph. It does not materialize
ingredient combinations or all possible recipe chains.

Prepared source distances apply the query's tier and excluded-resource filters.
They relax other AND obligations and required waypoints only for the lower bound.
A prepared qualifying-hop pass establishes the reference for `max_extra_steps`.
Material selection then orders exploration using native primary-material and
component overlap, secondary-output hints and remaining distance. It explains one
representative spine per target ingredient branch, up to `max_paths`. The original
shortest and diverse algorithms retain their contracts. No iron, steel or
resource-ID exception controls selection.

Material continuity is a hint, not a chemical certification or identity rule.
Secondary-output hints retain the basis `secondary_output_position_hint`.
Byproduct routes remain legal. Complete native process records preserve amounts,
chances, OR choices, all AND slots, NBT predicates, tools and conditions. Reported
leaves expose other supplied or unresolved inputs. A dependency spine still does
not certify inventory, heat, machine access or a complete production plan.

### Same-snapshot end-to-end comparison

The following baseline and treatment use the original immutable snapshot
`2830da9f-c040-4233-a778-036e4b27f3eb`. These are complete Dataset queries with
result construction, not the relaxed graph probes above. The baseline is the
unchanged diverse mode and the treatment is explicit material mode with analysis
version 2. Cold means a fresh Dataset handle with the OS filesystem cache retained.
Warm observations use the same handle and are retained in the raw artifacts.
Single local samples are indicative, not latency percentiles. Some final matrix
timings overlap a separate memory probe, so work counts and route quality are the
stronger evidence for the search change.

| Case and filter | Cold seconds, baseline → material | Examined processes, baseline → material | Represented target branches, baseline → material |
| --- | --- | --- | --- |
| Casing, LV | 8.70 → 1.01 | 10,000 → 294 | 1/1 → 1/1 |
| Casing, unrestricted | 10.29 → 0.99 | 10,000 → 438 | 1/1 → 1/1 |
| Hull, LV | 7.00 → 3.83 | 10,000 → 1,818 | 1/3 → 3/3 |
| Hull, MV | 11.20 → 2.91 | 10,000 → 2,805 | 3/3 → 3/3 |
| Hull, unrestricted | 10.77 → 3.46 | 10,000 → 3,995 | 3/3 → 3/3 |
| Double plate, MV | 8.70 → 2.22 | 7,594 → 4,829 | 1/2 → 2/2 |
| Double plate, unrestricted | 6.75 → 1.63 | 8,415 → 1,167 | 2/2 → 2/2 |
| Volcanus, unrestricted | 12.20 → 10.51 | 10,000 → 3,161 | 6/6 → 6/6 |

Baseline process counts describe full process records in the diverse phase. Its
primary search has separate, overlapping counts that cannot be added as a unique
total. Material counts describe prepared process summaries. Actual full process
loads are reported separately as `loaded_process_records`. Source-distance work
and cache costs are also explicit, rather than being hidden from cold timings.

All final material queries in that matrix finish without a search budget limit.
For casing LV, examined states fall from 1,989 to 11 and expansion work from
55,673 to 647. For unrestricted hull, the counts fall from 789 to 96 states and
66,728 to 6,072 expansion units. For unrestricted Volcanus, they fall from 1,407
to 307 states and 29,057 to 5,497 expansion units.

Steel was already present in the old casing and hull results. Material mode places
the casing and steel construction spine first and improves LV hull coverage from
one branch to all three. MV double plate now represents both target producers.
Volcanus keeps all six target ingredient branches and naturally discovers Steel
Ingot → Steel Dust → Tungstensteel Dust → Molten Tungstensteel → Long Tungstensteel
Rod → Robot Arm (IV) → Volcanus. Another steel spine reaches an IV hull and
Gregtech Computer Cube. Those selected baseline Volcanus paths contained no
Steel-labelled material.

The old LV double-plate and LV/MV Volcanus requests have no allowed target producer
under the default unknown-tier exclusion policy. This describes the old dump and
filters, not a claim that those items are unobtainable in the game.

Fresh-process unrestricted hull memory probes measure a peak working set of
157.1 MB for baseline and 102.7 MB for material search. Post-query working sets
are 134.9 MB and 53.8 MB. Opening Dataset takes 26 ms and 28 ms. These are process
memory measurements, unlike the experimental CSR storage figures above.

### Version 3 preparation and verification

The version 2 sidecar on the old snapshot took 18.59 seconds to prepare and used
86,102,016 bytes. It contains 68,548 ingredient descriptors, 198,371 resource
memberships, 365,181 symbolic consumed relations, 441,140 graph nodes and 798,055
arcs. Rebuilding version 3 on the same snapshot took 20.56 seconds and used
87,822,336 bytes. Version 3 persists voltage-applicability status and adds truthful
depth-cutoff reporting and omission of recipe explanations for zero-step traces.

Verified static exact GT shaped crafting recipes can declare that machine voltage
is not applicable. Recognition requires the captured marker and the appropriate
family, owner, native class, static-output declaration, executable status and null
EU value. Such recipes pass minimum and maximum voltage-tier filters. Other
unknown machine tiers retain their existing policy. Null EU is never converted
into zero energy. Older sidecars fail explicitly and require rebuilding.

Representative version 3 checks on the old snapshot retain steel-first hull paths
and both MV double-plate branches without limits. Hull cold/warm observations are
3.25/2.99 seconds and double-plate observations are 1.67/1.46 seconds. The later
fresh snapshot below has a larger version 3 sidecar, 97,185,792 bytes, prepared in
16.94 seconds. These preparation samples are reported separately, not combined
into a single claimed speedup across different data.

Regression coverage includes material preference, legal byproduct branches,
qualifying-hop detour bounds, required and excluded resources, OR, NBT, presence
requirements, tiers, cyclic ancestors, canonical and noncanonical group variants,
zero yield, snapshot/version mismatch, rebuilds and canonical-file immutability.
Review regressions cover known depth and required-waypoint cutoffs, disconnected
negative results, zero-step explanations and trusted crafting voltage metadata.
Existing energy audit tests remain part of verification.

### Fresh-snapshot regression and focused SQL fix

The fresh static-crafting snapshot is
`779ea030-ae9c-40ea-8854-99a176f7cc42`. It makes the LV double-plate crafting
producer interpretable. Its newly available recipe expands NBT-insensitive tool
choices into 1,717 result resources. Initial full queries take 100.18 seconds in
material mode and 106.45 seconds in diverse mode. This is a new snapshot and a
newly represented route, so these numbers must not replace the same-snapshot
table above.

A bounded cProfile run reproduces 100.197 seconds. Material search itself takes
0.708 seconds. The shared unresolved-producer SQL consumes 98.842 seconds across
1,717 calls. EXPLAIN QUERY PLAN identifies a global ingredient-table scan rebuilt
for every resource. The fix replaces that membership subquery with a correlated
`EXISTS` query on the producer ID, using the existing `input_process` index. The
predicate remains equivalent. No matching alternatives, recipes or result data
are pruned, and no new prepared-index version or canonical database write is
needed.

The matching post-fix profile takes 0.946 seconds. The formerly expensive SQL
takes 0.070 seconds across the same 1,717 calls. Search work stays unchanged.
The full result matches the saved pre-fix result after excluding only three
runtime source-distance metrics. It preserves 1,717 resources, six complete
recipes, 1,724 edges, 1,710 leaves, paths, conditions, coverage and limit reasons.
The configured environment passes 69 relevant tests after this fix, including
unresolved producer evidence across expanded tool alternatives in all three
selection modes.

### Compact presentation and payload size

Dataset accepts `view='full'` and `view='compact'`, with full as its unchanged
default. Compact presentation runs after the same analysis. It retains complete
native recipe records, paths, path details, search accounting, limits, branch
coverage, coverage evidence and full cycle node IDs. Embedded resource records
retain endpoints, all path resources, declared input-choice anchors and outputs.
An anchor outside its resolved group is fetched and counted explicitly without
inventing a matching edge or acquisition leaf.

Expanded candidate records, corresponding input edges and leaves can be omitted
from presentation. Metadata reports omission counts, matching-predicate
references, the resolved full-edge count scope, omitted leaf statuses and reasons,
omitted source IDs and any unembedded cycle resource count. Candidate counts do
not claim that literal group listing or unsupported matching is complete. The
response explicitly remains a dependency spine with external input requirements.

For the fresh LV double-plate material result, minified UTF-8 JSON falls from
2,161,648 bytes to 96,046 bytes, a **95.56% reduction**. Resources fall from 1,717
to 15, edges from 1,724 to 22 and leaves from 1,710 to eight. All six full native
recipe records and selected paths are identical. The 1,702 omitted leaves remain
explicitly counted as unresolved. This is a presentation benefit, not a search
speed claim. Regression-first tests cover a 2,000-member group in all three
selection modes, the chosen matched variant, declared anchors, boundary evidence,
search accounting and the out-of-group anchor case. The focused core run passes
53 tests, and all ten flow tests pass after the final metadata wording change.

### Production evidence artifacts

The detailed local report is `exports/flow-search-20261014/report.md`. Baseline and
treatment are `baseline.json` and `material.json`. Memory is recorded in
`baseline-memory.json` and `material-memory.json`. Preparation is separated into
`preparation.json` and `preparation-v3.json`, with version 3 representative checks
in `material-v3-hull.json` and `material-v3-double-plate.json`. Canonical and
experiment-copy hashes match in `database-provenance.json`.

The fresh regression has `fresh-profile-before.json`, `fresh-profile-after.json`,
their pstats files, `fresh-profile-after-result.json` and
`fresh-profile-result-comparison.json`. Compact evidence is in
`compact-native-size.json` and `compact-native-result.json`. These Git-excluded
artifacts remain local. This durable production summary preserves the conclusions
without committing ignored exports. The relaxed research scripts above remain
separate evidence and do not substitute for these complete Dataset measurements.
