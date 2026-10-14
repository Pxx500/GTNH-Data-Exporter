# Native form ports and material regions

Snapshot `779ea030-ae9c-40ea-8854-99a176f7cc42`, measured 2026-10-14.
Canonical data and the ready version 3 prepared graph were opened read-only.
This diagnostic changes no production code, exporter, index schema, or GUI.

## Decision

The user's same-material region idea is useful for explaining familiar form
operations. Iron and Steel have witnessed ingot → plate → dust → ingot cycles.
Tungstensteel has a witnessed variant with an intermediate molten phase. Those
form changes can stay inside one named material region instead of becoming new
top-level semantic directions. Every recipe step, matching predicate, other
ingredient, tool, and condition still needs its own concrete witness.

The measured projection is a narrower hypothesis: it aliases resources only
when their captured native primary descriptor and exact form agree. That
projection is not a useful speedup or a stronger hop guide. It removes only
762 graph nodes, retains every factor arc, and weakens some concrete hop bounds.
This does **not** reject a material region containing many distinct exact form
ports and lazily refined internal recipe witnesses. That different hypothesis
has not been implemented here.

The lowest-cost next pilot is target ingredient job ranking from declared
positive ItemData constituents, keeping the existing primary-material edge
scoring. Exact-port material-region refinement is a larger follow-up. Neither
should be confused with making every port in a region freely interchangeable.

## Native identity and form rule

A known-form class requires a captured native primary `native_class` and `name`,
a descriptor digest, and an explicit OrePrefix for items or one uniquely
resolved native phase for fluids. The digest preserves the captured native
material metadata and composition structure. Display formula text is never
parsed or used as chemical evidence. The observed primary namespace is
`gregtech.api.enums.Materials`. No same-name descriptor conflicts were found.

Composition-complete descriptors and composition-unresolved descriptors have
separate confidence labels. A typed native name can be useful as a game category
even when it is not a chemical material. For example, `circuit:Master` is a
captured circuit category. It is not an elemental material region. The native
`NULL` placeholder is treated as unknown. Prefix-None ItemData, ambiguous fluid
phases, and missing identities remain exact resource IDs. No label is inferred
from an item display name. No byproduct constituent union controls this map.

The classes are a relaxation for guidance and explanation. They do not merge
registry names, metadata, NBT identities, or ingredient predicates. Material
facts in this snapshot explicitly mark chemical purity as uncertified.

| Native coverage | Count |
| --- | --- |
| Resource identities | 118,717 |
| Resources with native typed identity and explicit form | 26,006 |
| Of those, composition-complete descriptors | 16,940 |
| Of those, composition-unresolved descriptors | 9,066 |
| Known-form classes | 25,244 |
| Exact unknown or complex form ports | 92,711 |
| Captured native material descriptors used | 1,214 |
| Distinct resource ports after this alias projection | 117,955 |

Thus 762 resource aliases collapse. A stricter composition-complete sensitivity
collapses only 392. Both policies give the same negative performance direction.
Raw counts, confidence labels, prefix inventories, and the strict sensitivity
are in `exports/search-research-20261014/forms/experiment_form_map_result.json`
and `experiment_strict_form_map_result.json`.

## Recipe-port map and familiar cycles

The prepared graph retains positive consumed input relations, native matching
memberships, eligible recipe identities, and positive outputs. The diagnostic
keeps its MATCH and recipe nodes. It does not form Cartesian products of AND
ingredient selections or compute all-pairs portal distances.

The form view counts 69,492 within-primary-material form arcs over 123,943
prepared slot/matching relations. These are witnessed relations, not proofs of
quantity-preserving form conversion. The focused Iron, Steel, and Tungstensteel
map has 995 directed form arcs, including 20 between different primary material
descriptors. Its witnesses refer to 976 complete canonical recipe records.
All 995 focused edges were checked against native consumed choices and positive
outputs. Full native AND context is saved in `experiment_focus_witnesses.json`.

| Material | Exact resources with known forms | Form classes | Within-material arcs | Bidirectional form pairs | Largest within-material SCC |
| --- | --- | --- | --- | --- | --- |
| Iron | 124 | 104 | 401 | 50 | 51 |
| Steel | 68 | 60 | 289 | 57 | 56 |
| Tungstensteel | 59 | 59 | 285 | 56 | 56 |

An SCC is a set of ports reachable from one another in both directions in the
relaxed view. The combined focused map puts 169 of its 223 form classes in one
SCC. Condensing it would hide most forming choices and their costs. A useful
human map should name the material region and retain its form ports, rather
than replace that region with one freely traversable node.

Follow-up status: the proposed target-job constituent ranking pilot has now
been tested in eight unrestricted/LV cases and was not promoted. Every selected
path, story, route, represented job set, work count, and admission count stayed
unchanged because the promoted Robot Arm jobs were already covered. Unrestricted
Volcanus's retained-descriptor peak fell from 10,177 to 6,382, but the paired
process measurements do not establish a physical-memory benefit. Evidence is
`semantic/experiment_branch_report.md` and `experiment_branch_summary.json`
under the research exports folder. This supersedes the next-pilot recommendation
below. Exact-port region refinement remains a separate feasibility question.

The diagnostic found these compatible recipe walks:

| Material | Familiar form sequence | Concrete recipe witnesses |
| --- | --- | --- |
| Iron | Ingot → Plate → Dust → Ingot | `p121045`, `p149875`, `p252929` |
| Steel | Ingot → Plate → Dust → Ingot | `p121055`, `p148486`, `p180710` |
| Tungstensteel | Ingot → Plate → Dust → Molten → Ingot | `p122055`, `p145501`, `p118258`, `p115247` |

Every successive output is accepted by the next recipe's actual prepared match
predicate, including the closing leg. The Iron plate witnesses illustrate why
ports matter: one leg outputs `r23770`, while the next stored representative is
`r23769`. Compatibility was checked through that recipe's match membership,
not inferred from the shared Iron/plate label. The example is a valid relaxed
recipe walk. It is not a feasible inventory loop, a conservation proof, or a
reason to ignore its consumed quantities and tools. Detailed port IDs and
checks are in `experiment_story_signatures_result.json`.

Ore and refinement ports can feed the metal-form region. Forming ports can
reach exact component boundaries. This supports a readable progression view,
but it does not turn all ore, ingot, plate, and component ports into equivalent
states. A component with prefix-None ItemData stays an exact boundary port even
when its declared constituents include a familiar metal.

## Comparison with current concrete hop guidance

For the ordinary factor graph, projection adds aliases and preserves each
original arc and cost. Any concrete path maps to a projected walk of the same
cost. Therefore the projected distance can be equal or smaller, never stronger
than the concrete prepared hop lower bound. Its only possible advantage would
be cheaper computation, which this probe did not establish.

| Representation | Nodes | Arcs | Forward CSR bytes |
| --- | --- | --- | --- |
| Existing prepared factor graph | 446,751 | 896,878 | 6,271,398 |
| Native material plus exact form projection | 445,989 | 896,878 | 6,268,350 |

The graph loses 0.171% of its nodes and saves 3,048 CSR bytes. Iron Dust source
traversal scans 575,398 projected arcs versus 569,173 concrete arcs. The measured
times are 72.4 ms and 70.8 ms. Reverse traversal from Volcanus scans 697,058
projected arcs versus 697,043 concrete arcs, with single times of 81.6 ms and
83.8 ms. These are offline graph probes, not end-to-end query speedups.

Source bounds weaken for 138 previously reachable resources, including 67
known-form ports. Goal bounds weaken for 546 resources, including 187 known-form
ports. The alias graph also adds 313 source-reachable and 13 goal-reaching
resources that are unreachable in the corresponding concrete relaxed graph.
Passing projected reachability is therefore weaker evidence. Selected Iron
Dust, casing, hull, crushed ore, double plate, and Volcanus hop values stay
unchanged.

Examples show the information lost: a Copper block port drops from four source
hops to two, and an IC2 Stone Dust port drops from five to three. Iodine Dust's
Volcanus goal distance drops from eight to six. A diode port drops from four to
two. These are guidance aliases, not free native conversions. Exact registry,
metadata, NBT, member IDs, and distances are in
`experiment_bound_examples_result.json`.

The giant SCC is also essentially unchanged: 27,104 concrete resource nodes
versus 26,989 projected resource ports. This projection does not create useful
global search islands. Its classification costs about 1.44 seconds, projection
0.174 seconds, reverse-graph construction 0.319 seconds, and two SCC passes
0.547 seconds. The complete diagnostic takes 4.57 seconds before final output
serialization. Known-class metadata is 19.87 MB of uncompressed JSON, and the
focused witnesses with full recipe context occupy 2.85 MB. Those artifact sizes
are not resident-memory measurements.

All finite source and goal resource distances were checked against their
concrete counterparts. An unfiltered projected bound was also checked against
20,781 finite LV-filtered resources and 59,006 resources with Steel Ingot
excluded. Entire mixed classes were never blocked to represent one excluded
identity. Fifty-four exact ports on the eight saved cursor-only paths were
treated as possible waypoints, and the relaxed source-to-port plus port-to-goal
bound never exceeded the concrete path length. This checks a lower-bound
property, not full AND feasibility or a new required-waypoint solver.

## Distinct construction stories

For explanation only, a material run collects consecutive ports with the same
captured native descriptor. Its forms and all recipe IDs remain attached.
Every unknown or complex port remains a distinct resource boundary. Final
crafting versus assembler witnesses remain separate native paths even when
their region sequence is the same story. No result path is discarded here.

| Saved native result | Paths | Material-run and exact-port stories | Within-material form steps across paths | Native assembler steps | Native component assembly-line steps | Recognized recovery hint steps |
| --- | --- | --- | --- | --- | --- | --- |
| Cursor only | 8 | 4 | 12 | 8 | 2 | 2 |
| Validated soft preference | 8 | 5 | 11 | 6 | 2 | 0 |

Both sets cover ten of 15 target jobs. Recovery counts are copied from the
separate typed-recovery probe, not reclassified by this diagnostic. Zero
recognized hints does not certify that every unknown step is construction.
The soft result's classifier still labels 20 steps unknown. Story signatures
are likewise an explanatory convention, not a chemical ontology or an
optimality metric.

The soft result exposes five stories:

1. Iron → Steel → Tungstensteel forming → exact Robot Arm IV → Volcanus
2. Iron → Steel → Tungstensteel plate → exact IV Machine Hull → exact Computer Cube → Volcanus
3. Iron → exact Molten Hastelloy-W → exact Hastelloy-W Gear → Volcanus
4. Iron → native Iron III Chloride fluid → exact circuit board → native Master circuit category → Volcanus
5. Iron → Stainless Steel forming → exact Heat Vent → exact Volcanus Casing → Volcanus

Hastelloy-W fluid and gear remain exact unknown-form ports because this capture
does not supply the required native association evidence. Their display names
do not authorize assigning a material region. Other unresolved boundaries
include robot arms, hulls, computer cubes, circuit boards, vents, casings, and
Volcanus itself. The older tool-through-Anvil story disappears from the soft
set. These changes come from the separate soft preference, not this form map.

The two source artifacts are
`queue/experiment_production_volcanus.json` and
`semantic/experiment_compact2_volcanus.json` under the research exports folder.
Both signature sets, exact ports, native family counts, and borrowed recovery
annotations are preserved in `forms/experiment_story_signatures_result.json`.

## One bounded next pilot and a larger alternative

Prefer the smaller target-job ranking pilot before replacing concrete traversal
with regional routing. Use complete, positive native ItemData constituent
declarations only to rank target ingredient jobs. Robot Arm IV can then expose
its declared Tungstensteel contribution while remaining an exact composite
resource. Retain the original primary-material scores on every graph edge.
This isolates the earlier flat constituent union's broad low-penalty frontier
from useful target construction context. It is a relevance hint, not evidence
of source atom provenance.

Compare against the validated soft-preference baseline at the same depth 12,
300 result processes, eight paths, six extra steps, 20,000 admissions, 10,000
examined processes, and 100,000 predecessor work. Count constituent validation
and sorting costs. The falsifiable target is earlier useful construction jobs
or more than five distinct stories while preserving at least the current ten
represented jobs and the best supported material spine. If ordering changes
without those benefits, keep the baseline. This pilot is owned and evaluated
separately from the present diagnostic.

A later Iron/Steel/Tungstensteel region pilot would keep all exact form ports,
route across concrete material-changing or component boundaries, and lazily
refine only a query's entered port to a candidate exit. It must charge every
internal recipe step, row scan, validation, cursor, and saved witness to the
existing limits. It must retain depth, exclusions, waypoint history, NBT,
native AND context, and legal recycling. There can be no zero-cost teleport
between ports and no all-pairs portal closure. Familiar internal form operations
would contribute to depth and cost while contributing no new material-region
direction to the explanation. This is a distinct untested hypothesis, not a
positive result inferred from the alias projection.

## Reproduction and scope

Use the project Python environment to run
`exports/search-research-20261014/forms/experiment_form_map.py`,
`experiment_bound_examples.py`, and `experiment_story_signatures.py`.
The strict initial sensitivity source and results are also retained. All raw
artifacts are Git-excluded. Native files' size and modification metadata stayed
unchanged. No production search, exporter, schema, or GUI change was made.

These measurements describe the captured prepared graph and saved native
spines. They do not certify machine access, quantities, chances, chemical
purity, external ingredients, or executable factory inventory plans.

Follow-up region feasibility: the later exact-port pilot is now measured rather
than untested. Six saved-path entries in Iron, Steel, and TungstenSteel reached
all requested form ports within six internal concrete hops. Boundaries were
dense, with 38 to 45 reached boundary ports and 710 to 925 boundary processes
per entry. A bounded read-only membership reversal scanned 486,129 input rows
once in 0.238 seconds, with another 0.063 seconds for metadata loading. Queries
then took 1.66 to 7.28 milliseconds, with 29,441 charged operations across the
six catalogs. The earlier seconds-long queries were repeated SQLite input-table
scans, not intrinsic region costs. Exact history changed a Tungstensteel witness
from two hops to four, and requiring another Iron dust variant stopped at
100,000 work with existence unknown. One of 144 context-free boundary witnesses
conflicted with its saved prefix, so region witnesses need concrete history
validation and charged refinement. This establishes finite witness feasibility,
not a sparse runtime replacement or end-to-end speedup. Details, full native
AND contexts, limits, and cache constraints are in
[the region pilot report](exports/search-research-20261014/forms/experiment_region_report.md).
No production promotion follows from this pilot.
