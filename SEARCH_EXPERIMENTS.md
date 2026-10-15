# Fixed-budget search experiments

The user requested continued research and investigation on 2026-10-14.
The previous implementation milestone is complete. This document tracks the
new experiments without claiming they have entered production.

## Question

Can the same runtime budgets find more useful material and construction paths
by using better preparation, semantic direction and selective admissions?
Do not increase state, process, expansion, path-count or depth limits to claim
an improvement. Preparation cost and deferred work remain visible.

## Baseline

Fresh snapshot `779ea030-ae9c-40ea-8854-99a176f7cc42`, material policy,
compact presentation, maximum depth 12, 300 returned processes, eight paths
and six extra steps. The engine also bounds 20,000 cumulative heap admissions,
10,000 examined process summaries and 100,000 predecessor expansion units.

Volcanus returns six paths and 8/15 target ingredient branch jobs. It admits
20,000 heap states and examines 512. The existing engine already has pop-time
score/depth dominance, exact-resource and process cycle checks, and branch turns.
The issue is not an absence of all guidance or cycle handling.

An observation-only heap probe preserves the result. It counts 302 exactly
duplicate admissions, 13,005 optimistic dominated admissions that ignore
ancestor legality, and only 302 with identical resource/process ancestor sets.
The larger number is not a safe pruning benefit.

## Experiments

1. **Lazy successor admissions.** Retain a compact resumable successor cursor.
   Materialize promising states as needed instead of flooding the heap during
   one expansion. Count cursor insertions and reinsertion in the same admission
   budget, and disclose every scan, resume and deferred descriptor.
2. **Complete native constituent hints.** The current material-token builder
   reads the primary ItemData material and its recursive composition. Test the
   additional positive native ItemData constituents already in the dump.
   Robot Arm IV has primary Graphene and additional TungstenSteel, Tungsten
   and NeodymiumMagnetic. These are ItemData constituents, not recipe-output
   coproducts or certified source-atom mappings.
3. **Typed semantic map.** Distinguish material conversion, form conversion,
   component construction, assembly and recycling. A macro transition must
   retain exact form ports and concrete recipe witnesses. Internal refinement
   consumes the same search budgets. SCC connectivity is not semantic grouping.
4. **Continuation-safe early dominance.** Test only labels whose future legal
   continuations can be preserved. Required waypoints, resource/process history,
   remaining depth and cost all matter. Do not merge resource identities.
5. **Admission-aware branch scheduling.** Compare work-limited branch turns
   with the current removal-limited turns. This changes bounded exploration
   order and needs explicit coverage and route-quality comparisons.

## Evidence required

- Compare the same native casing, hull, double-plate and Volcanus requests.
- Retain each recipe's full AND/OR, quantities, chance, presence, NBT and conditions.
- Check required/excluded intermediates, cyclic ancestors and tier filtering.
- Report useful route labels, target branch jobs, limits, admissions, expansions,
  examined processes, deferred candidates, latency and memory.
- Distinguish baseline counters, experimental telemetry and proof of completeness.
- Keep canonical databases and running GUI/MCP unchanged during experiments.
- A negative result is a valid result. Promote only a supported improvement.

Primary-source findings are maintained in [SEARCH_QUEUE_RESEARCH.md](SEARCH_QUEUE_RESEARCH.md)
and [REACTION_ROUTE_RESEARCH.md](REACTION_ROUTE_RESEARCH.md). Raw sources and
prototype programs remain in Git-excluded `exports/search-research-20261014/`.

## Results so far

The isolated lazy-admission experiment increases unrestricted Volcanus from
six paths and 8/15 branch jobs to eight paths and 10/15. Admissions fall from
20,000 to 1,113. Each tagged cursor entry is one real admitted child path,
not a separately processed uncharged state. The result preserves all original
paths and the best route. Sample times are 0.430 and 0.429 seconds. Charged
predecessor work remains 9,992. Additional candidate validations total 27,512
and are reported separately. Eight returned paths still limit coverage.

The same experiment preserves the baseline casing, hull and double-plate
path sets. A separate eight-admission branch turn adds no coverage benefit
and retains a larger deferred frontier, so it is not promoted.

The native constituent union changes 5,397 resource hints. Casing, hull and
double-plate coverage stay unchanged. Unrestricted Volcanus falls from six
paths and 8/15 branch jobs to one path and 2/15, still at 20,000 admissions.
More flat shared labels enlarge a low-penalty frontier. This treatment is not
promoted. Its metadata is still useful for typed roles and source evidence.

Combining the union with the lazy cursor restores eight paths and 10/15 jobs,
but adds no coverage over the cursor alone and uses a larger deferred frontier.
Some paths replace an Anvil and advanced-machine recovery detour with Steel
Plate and Assembly Line Casing. This does not yet prove source-material transfer.

The lazy cursor is implemented in the existing production owner and passed
root's consolidated code inspection and all 163 Python tests. A public
2,000-variant, twelve-slot regression
fails before the fix and passes afterward with both target branches and full
AND recipes retained. No API, matching, index version or material hint changes
are needed.

HTTP and the actual connected MCP session both return eight Volcanus paths,
10/15 represented branch jobs and 1,113 admissions, with `path_limit` remaining
explicit. Fresh LV casing, hull and double-plate HTTP requests still find their
paths and represent 9/9, 9/9 and 2/2 jobs without search limits. The current GUI
server is running the cursor implementation. These checks do not establish
complete planning or a finished semantic map.

## Semantic direction and recycling

The typed-operation experiment is complete. A soft recovery weight of two
replaces the Volcanus construction-to-salvage detour through an Advanced Forge
Hammer IV with a material-processing spine through Steel, Tungstensteel,
an IV Machine Hull and a Computer Cube. The hammer assembly already needs
an IV hull and other cofeeds, so the old spine is legal but a poor explanation
of how the source contributes to the target.

The rule uses captured recipe families and native ItemData roles. It recognizes
explicit composite items recovered to ordinary material forms, and crafted
forms recovered to dust of the same primary material. It adds a preference,
not an exclusion. Unknown roles receive no additional weight. Necessary
recovery and chemical loops remain legal. Quantity conservation and atom
provenance are not inferred from a primary material name.

Unrestricted Volcanus still returns eight paths and 10/15 jobs. The exact job
set changes, adding `p204431:1` and losing `p25071:5`. Casing, hull and double
plate preserve their unrestricted path sets. LV Volcanus keeps three paths
and all five jobs. LV hull still includes a Hermetic Casing recovery path.
Strength six produces no measured benefit over two.

A candidate-only cache reproduces all native result fields of the wide
descriptor treatment except search telemetry in eight unrestricted/LV cases.
It uses indexed exact-record JSON extraction and roughly 133–911 KiB of
shallow cache storage. It introduces no persistent store or sidecar rebuild.
Unrestricted Volcanus takes 0.518 seconds versus 0.433 for the cursor baseline,
and LV Volcanus takes 1.517 versus 1.045 seconds in single local samples.
This is an explanation-quality tradeoff, not a speedup. The preference is now
implemented in the existing material-search owner. The main public regression
fails before the change and passes afterward. Additional public cases preserve
required/only-route recovery, plate-to-dust conversion, unknown composition,
complete AND/OR/presence cofeeds and the qualifying hop reference. All 167
Python tests pass. Eight production queries match every one of the 20 native
result fields outside search against the frozen compact treatment, with equal
work, admissions, examined states/processes and hop reference. Native matching
and recipe equality were checked for 35 paths and 173 steps.

The GUI server was restarted with verified ownership at 127.0.0.1:8000.
HTTP Volcanus matches all 20 native result fields of the treatment and reports
1,357 admissions. A Water-to-Hydrogen HTTP check ranks a Large Chemical Reactor
dependency first. It returns eight paths and swaps one alternative under the new ordering,
with 713 admissions versus 866 before the change. All eight paths and 15 steps
pass canonical recipe and native consumed-choice checks. This does not verify
a closed regenerative network. Energy audits and chemical-loop tools are
separate implementations, covered by the unchanged contracts in the full suite.

The existing connected MCP process still serves the previously loaded cursor
code, without `search.recovery_preference`. Its snapshot remains current, but
that session needs a client reconnect to adopt the new ranking. Fresh transport
tests pass. Neither those tests nor the successful HTTP check establishes that
the existing MCP connection has refreshed. No Codex-managed client was killed.
The official MCP documentation describes a client-side Restart action after
configuring a desktop server. It does not establish an agent-callable refresh
operation for this session. The available task tools expose no such operation,
so no unsupported control or automatic reconnection is claimed.
[Official MCP documentation](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)

A later check through the helper's actual MCP connection returns the current
policy with weight two, snapshot `779ea030-ae9c-40ea-8854-99a176f7cc42`, eight
Water-to-Hydrogen paths, 713 admissions and first dependency recipe
`p138456`. Those values agree with the independent fresh HTTP check. This
establishes that the integration serves the new policy through a fresh loaded
connection. It does not establish that root's earlier connection refreshed.

The earlier electrolysis label was incorrect. Saved native p138456 consumes
Water plus Bauxite Dust, Sodium Carbonate Dust and Coal Dust, with circuit
presence, and produces Hydrogen among four outputs. This dependency check
does not compare a regenerative loop against the water-electrolysis benchmark.

The larger semantic-map hypothesis remains separate. Grouping a material's
forms can hide familiar recycling circuits at the overview level, but an
ingot and a plate must stay distinct recipe ports. A quotient graph may guide
search only if it preserves concrete witnesses and charges refinement work.
Its relaxed distance can become too weak when many form edges disappear.
The current diagnostic measures that loss alongside group sizes and remaining
connectivity before proposing a runtime change. The native material-and-form
alias projection is not promoted. It is separate from the coarser region idea
with multiple exact form ports and lazy internal witnesses.

The corrected alias diagnostic collapses 762 resources, reducing factor nodes
from 446,751 to 445,989 while retaining all 896,878 arcs. It saves only 3,048
CSR bytes and weakens 138 source bounds and 546 goal bounds. It does not
strengthen existing concrete hop guidance. The focused Iron/Steel/Tungstensteel
view does support familiar form walks. Root independently checked all ten
successive and closing native matches in those three examples. The current
eight soft-preference paths have five material-run/exact-port story signatures
versus four for the cursor-only paths. This is an explanation convention, not
an optimality metric or a reason to drop a concrete path. Full measurements
and limits are in [FORM_MAP_RESEARCH.md](FORM_MAP_RESEARCH.md).

The branch-only constituent follow-up is also not promoted. Ranking actual
target candidates by positive additional native ItemData constituents correctly
promotes Robot Arm IV through TungstenSteel, Steel and Iron. In all eight
unrestricted/LV cases, those jobs were already represented. Returned paths,
routes, exact represented jobs, work, admissions and hop reference stay equal.
Only the presentation order of Volcanus branch records changes. All 70 paths
and 346 steps across the sixteen runs pass canonical/native checks.
Candidate preparation reads 1–204 records in 0.17–5.77 ms. Unrestricted
Volcanus peak retained descriptors fall from 10,177 to 6,382, but measured
working set does not decrease. This supplies no route-quality, coverage,
physical-memory or speed improvement. Raw evidence remains in
`exports/search-research-20261014/semantic/experiment_branch_report.md`.

A separate diagnostic now checks downstream cofeed obligations. A recipe can
require a side input that a later recipe in the spine produces. Distinguish
an unavoidable captured AND obligation from an OR slot that merely permits
such a resource. External initial supply can still make the spine legal.
This is an explanation signal to investigate, not an impossibility rule or a
reason to exclude regenerative networks.

That bounded scan is complete. Strict later-spine slot overlaps fall from six
to two across the eight paired cases. The soft preference removes both
observed construction patterns: Forge Hammer `p200544` consumes a later IV Hull
`r37930`, and Assembly Line Casing `p200250` consumes a later Robot Arm IV
`r32547` in two AND slots. Optional overlaps remain four. The scanner verifies
70 paths, 347 hops, 182 unique choices and 6,248 candidate matches without
hitting its bounds or encountering unresolved matching.

The remaining Hull chemistry illustrates why no generic exclusion is added.
One recipe consumes Hydrochloric Acid later produced on the spine. Another
consumes Hydrogen later reached on the spine, but the earlier Iron III
Chloride recipe already has a Hydrogen coproduct. That earlier output is a
structural supply witness, not proof of sufficient stock without normalized
batches, all consumption and output chances. A Tin Alloy input permits either
later-spine GregTech Tin Dust or outside-spine IC2 Tin Dust, so it is an
optional overlap rather than an unavoidable native matching obligation.
External initial stock also keeps the old construction spines legal. Raw
slots and coproduct evidence are in
`exports/search-research-20261014/semantic/experiment_obligation_report.md`.
The result supports clearer obligation explanations, not automatic rejection
or an unsupported claim of impossible or autonomous production.

Further useful candidates are operation-aware route diversity and construction
obligations. Distinct recipe IDs often describe the same material-processing
story, while a coproduct can lead into a different story. A diversity signature
should distinguish those stories without replacing exact resource IDs or
dropping ingredient branches. An assembly input already produced elsewhere
in the selected spine is still an AND obligation, not proof of a complete
build plan. These are hypotheses for measured experiments, not implemented
guarantees.

Direct GT++ owner capture is now verified in an isolated real-pack run.
It adds native material/form declarations for 1,709 resources, with 1,646
complete traversals and 63 missing direct CELL material references. Required
Hastelloy gear and double-plate records retain their exact native child parts
and unresolved accounting. No material-token routing change is made.
The first refreshed runtime uses GT `5.09.54.223`, outside the then-supported
accounting versions. Its isolated snapshot is therefore not promoted to the
active dataset. Evidence and limitations are recorded in
[GTPP_MATERIAL_METADATA_RESEARCH.md](GTPP_MATERIAL_METADATA_RESEARCH.md).

## Exact repeated-slot successor deduplication

Repeated native ingredient slots can yield an identical spine child: the same
score, hop bound, recipe and input resource, attached to the same parent
history. The continuation does not choose a slot. Target ingredient jobs still
retain their individual slot identities, and returned native recipes retain
every AND slot and its quantity. Deduplication is local to that one successor
list, with the previous deterministic sorting order.

The eight paired native cases preserve all result fields outside search
telemetry. All 35 paths and 173 steps pass canonical-record and native-matcher
checks. Queue admissions fall by 17 for either casing query, 21 for unrestricted
hull, 128 for LV hull, three for either double-plate query, 26 for unrestricted
Volcanus, and 440 for LV Volcanus. LV Volcanus pops fall from 3,113 to 2,673.
Examined processes and predecessor work stay equal except unrestricted
Volcanus, which scans one additional process and two additional predecessor
rows. No path or branch coverage gain is claimed on these native cases.

Removed descriptors exceed saved admissions because many deferred choices
would never enter the queue. The experiment still scans the original native
predecessor rows and performs their candidate checks. Timing samples are mixed,
including slower LV Volcanus, so these results establish fewer repeated states,
not a latency or memory improvement.

A public synthetic regression uses 21,000 repeated slots to expose exhaustion
of the existing 20,000-admission cap. This is a deliberately large fixture,
not an observed native recipe of that size. The original implementation returns
an incomplete route. Deduplication finds the two-recipe dependency spine with
six admissions and preserves the complete repeated-slot native recipe. The
test failed before the change and passes after it. The full Python suite passes
168 tests before the separate new accounting-version work.

Raw scripts, paired outputs and measurements remain Git-excluded under
`exports/search-research-20261014/successor-dedup/`. Production uses the measured
deduplication inside the existing flow owner. No identity merging, new index,
dependency, pruning rule or global limit change is introduced.

The integrated source later passes all 170 Python tests with the explicit
accounting-version extension. Native direct Dataset validation confirms the
deduplicated results. An attempted GUI process restart was rejected before
execution by the tool policy, with only `blocked by policy` as its reason.
The existing GUI process remains on its earlier loaded code. A direct Dataset
check is not proof that the running GUI or an existing MCP connection refreshed.

## Typed form-cost hypothesis rejected

One point on every known same-material simple-form edge is not useful guidance.
The frozen paired experiment passes five public regressions in its baseline
and only four with the new score. The treatment restores the Anvil-to-machine
salvage shortcut in place of necessary metallurgy. No contiguous return to an
already visited native material/form signature appears in either saved set.
The score therefore penalizes necessary processing, not an observed form loop.

Both unrestricted Volcanus runs cover ten of fifteen jobs, but the treatment
loses three Robot Arm jobs and one Computer Cube job. Its replacement plate
branch uses an iron-derived single-use hammer while the native recipe already
consumes two Hastelloy-N plates. This is a legal dependency edge through the
selected input, not evidence that iron supplies the output plate's material.
The LV treatment also restores the Assembly Line Casing recovery detour.
Unknown transitions increase from 83 of 173 to 104 of 167 returned steps.
All seventy paths and 340 steps retain valid native records and matches.

Unrestricted Volcanus admissions increase from 1,357 to 3,038 and predecessor
work from 11,031 to 11,785. The comparison uses the pre-deduplication freeze
and does not describe current production throughput. No tuning or history-state
implementation was added to rescue this negative score. The transition census
can explain routes, but that alone does not establish better search. Raw
evidence is in `exports/search-research-20261014/typed-transitions/`.

The next narrower question is whether captured native ingredient groups and
tool/remainder declarations establish input-use roles. Such evidence would
distinguish a crafting tool from material feed without guessing from labels.
Consumed tools must retain native consumption semantics. Unknown roles must
remain unknown. This is an evidence investigation before another score change.

## Exact GT accounting version extension

GT `.223` now joins `.221` in an explicit native-version allowlist under the
unchanged `.221` quantity profile. Fifteen relevant source files and 22 actual
runtime classes are byte-identical between the inspected releases. Item,
molten and formula quantities, prefix/NBT/wildcard exclusions, recycling and
native-tree requirements, phase checks and candidate consensus remain intact.
Unknown releases remain unsupported. This preserves the actively supported
persisted `.221` data rather than replacing its profile.

The earlier unresolved `.223` dump is retained without modification. Fresh
snapshot `0d74a12d-9969-4055-b479-8e5573946098` contains 4,693 producer-eligible
resources and 4,695 complete query results, including two equivalent-candidate
cases. All 4,695 canonical complete identities match by kind, registry,
metadata and typed NBT with equal native accounting vectors and quantity bases.
This is scoped accounting equality, not whole-pack or recipe equality.
GT++ Hastelloy declarations remain unsupported for chemistry.

Tests failed first in the intended `.223` cases. The integrated suite passes
170 Python tests, while compilation and all 30 Java tests pass. IntelliJ finds
no new extension warning. Supplemental PMD retains 20 existing advisories with
no processing/configuration error, separately from the combined runner's skip.
Root independently reads four corresponding JAR classes and actual fresh
Iron Dust, Water, Hydrogen and unsupported Hastelloy inspection replies.

The fresh pipeline takes 168.587 seconds, with about 15 seconds of native dump
publication. Both protected indexes retain their hashes. No active dataset
configuration is switched. Raw evidence is under
`exports/search-research-20261014/accounting-223/`.

## Target-directed region nomination rejected for integration

Reverse concrete hop bounds to target ingredient jobs preserve all 18 saved
continuations in the finite regional sample. Early regions still expose
hundreds of boundary processes. On unrestricted Volcanus, Iron Dust retains
316 of 710 boundary processes and explores 51 ports instead of 52. Steel
retains 643 of 925 processes and still explores 56 ports. Later Tungstensteel
Dust is selective: 70 of 822 processes and 29 ports instead of 56, with only
six hops left. This local result does not establish overall savings.

Across the eight cases, admissions fall from 703 to 672 and concrete relation
checks save 291 operations. The extra selector performs 4,747 bound checks.
Combined diagnostic query work rises from 148,469 to 151,977. Its 24 distinct
reverse-job preparations scan 14,731,580 arcs and perform 6,091,880 admissions
and pops in 3.944 seconds. These preparation costs are separate from the
existing query caps. They prevent a same-budget speedup claim.

All 64 actual target-slot jobs, 273 native candidate memberships and 181
witness transitions pass verification. The evidence retains 34 full recipes,
including AND and presence context. This sample has no required or excluded
waypoints, so it does not establish a waypoint-sensitive regional algorithm.
No end-to-end integration follows from this negative result. Raw scripts and
measurements are in `exports/search-research-20261014/region-targeted/`.

A separate native-fact check finds three NULL-sentinel primary declarations:
Advanced Alloy, Carbon Plate and Iridium Reinforced Plate. Current token
extraction treats that sentinel as a name. None of these exact resource IDs
appears in the eight dedup paths, embedded resources or input-choice anchors,
so they do not explain these benchmark results. A future typed projection
should retain their unknown state rather than treating NULL as continuity.
No speculative production fix is added for this finding.

## Native input categories explain routes without changing search

The whole-slot crafting-tool score does not improve the nine native controls.
All twenty non-search result fields remain equal, while unrestricted Volcanus
takes 7.332 seconds instead of 0.556 and the hammer control takes 5.576 instead
of 0.501. The added membership and complete-slot checks are not justified as
search guidance. That score is rejected.

The production change instead annotates exact selected resources belonging to
captured OreDictionary crafting-tool groups after search finishes. This says
that the resource has a native category, not that the selected recipe uses it
as a tool, preserves it, or receives its material from it. Native consumption,
presence, tool accounting and container returns remain separate facts.
Unknown roles stay unknown. The GUI provides short text and existing local
inspection links rather than adding another planner setting.

The nine paired native cases preserve every non-search result field after
removing only the new annotation. Search counters remain equal, apart from
timing. Actual annotation cost including its database connection is
2.815–3.628 ms. Integrated verification passes 173 Python tests and 64 GUI tests.
A temporary HTTP server using the real application verifies the casing's
native wrench annotation and built static bundle, then closes gracefully.
This is not browser visual verification. The main server on port 8000 still
has the earlier loaded backend because automatic approval review blocked its
restart. Existing MCP connections are not claimed to have refreshed.
Evidence is in `exports/search-research-20261014/tool-roles/`.

## GT++ fluid owner capture remains separate from chemistry

The native collector now reads actual fluid references from the public GT++
material registry. It retains every distinct owner and distinguishes unique,
ambiguous, missing and failed association states. It invokes no material
factory or name-based cross-system match. The bound fields describe native
references, not certified phase quantities or purity.

Fresh snapshot `4966d66c-68f3-4689-adf5-ab55c1a8e4b2` contains 268 associated
fluid owners and 1,152 unassociated fluids. No ambiguous or failed association
occurs in this run. Molten Hastelloy-W/N declarations match the corresponding
gear and double plate declarations. The full-pack manifest advances to GT
`.225`, whose accounting remains explicitly unsupported. No implicit version
extension or active dataset switch follows. Both protected `.221` and accepted
`.223` indexes retain their hashes. Compilation and all 30 Java tests pass.
Evidence is in `exports/search-research-20261014/gtpp-fluid-owner/`.

GT++ quantity research finds no public fraction-preserving composition getter
or retained GT5 Element identity. Hastelloy-W/N declarations avoid fractional
loss, but their ratios of `3:1:12:3:31` and `2:4:2:2:15` do not declare an
elemental quantity basis. Nominal prefix amounts and casting batch sizes are
useful operational facts. They cannot independently certify chemical balance.
No new GT++ chemical accounting is introduced. Exact source and runtime
evidence is in `exports/search-research-20261014/gtpp-quantity-feasibility/`.

## Contextual use profiles show a form signal

Leiden communities and typed metapath literature offer directions distinct
from strongly connected components. Connectivity or embedding similarity is
not directed recipe feasibility. No clustering or embedding dependency is
installed. The first bounded diagnostic uses separate consuming and producing
recipe-family profiles with exact resource identities.

Across 33 eligible queries, combined profiles retrieve the same native
form/phase in 75.76% of top-three positions, compared with 30.30% for the degree
control. The fixed improvement is 45.45 percentage points. This is a native
form proxy, not independently validated semantic use or better pathfinding.
The 17 opaque resources have profiles but no evaluation labels.

The diagnostic withholds 1,609 processes producing target or pre-target
components. It excludes same-primary and shared-matcher pairs. All 64 profiles
complete within the fixed caps. Collection, lookup and matching cost 62,998
operations, while scoring and verification cost 48,712. The 20,246 family-row
accesses touching 35.77 MB are reported separately from full evidence records.
Its 0.375-second run is not a runtime search speedup claim. The next question
is whether target-conditioned profiles improve concrete native paths at the
same query limits. Evidence is in
`exports/search-research-20261014/communities/USE_SIGNATURES.md`.

## Decode only the material hints a query uses

Profiling the current search finds about 119,000 JSON decodes per native query.
Most come from eagerly reading every prepared resource's material tokens. These
tokens only guide ordering. The actual search touches a much smaller subset.
The production function now reads tokens by exact ID with a query-local
standard-library cache. Its immutable sets and database connection stay inside
the existing search owner. There is no shared cache, invalidation protocol,
snapshot change, new index format or changed score.

Three alternating baseline/treatment pairs per native case use fresh Dataset
handles and the same limits. Every result field and search counter remains
equal except distance timing. Material decoding falls to 239–2,096 records.
Median wall times are indicative, with warm OS caches and concurrent work:

| Case | Baseline seconds | On-demand seconds | Decoded material records |
| --- | ---: | ---: | ---: |
| Casing | 0.721 | 0.543 | 729 |
| Casing LV | 0.865 | 0.710 | 356 |
| Hull | 1.002 | 0.848 | 1,861 |
| Hull LV | 1.176 | 0.941 | 1,075 |
| Double plate | 0.836 | 0.677 | 1,136 |
| Double plate LV | 0.856 | 0.716 | 239 |
| Volcanus | 0.678 | 0.542 | 1,655 |
| Volcanus LV | 1.962 | 1.852 | 2,096 |

A separate production comparison against the frozen original function preserves
all eight complete native results and counters. All 173 Python tests pass.
Canonical DB and sidecar size/modification metadata stay unchanged. This reduces
unnecessary query work, not the number of search states or semantic ambiguity.
The main already-loaded service is not claimed to contain this update.
Reproducible profiles, baseline, paired measurements and production verification
are in `exports/search-research-20261014/current-profile/`.

## Target-conditioned family tie guidance rejected

The follow-on use-profile experiment orders equal-score, equal-hop successor
choices by similarity to actual target ingredient candidates. It changes no
match, lower bound, native identity or core search cap. Native target producers
are withheld from profile construction. Guidance uses no saved route, display
name or form label.

All eight cases return the same paths, route, represented target-slot set and
full native recipe payloads. All 346 returned steps across sixteen runs pass
native verification. Double plate LV adds four admissions, two pops and 39
predecessor rows for the same result. Median query time rises 82%, and peak
working set rises 58.0–68.6 MiB. Profile collection reaches its separate
100,000-unit cap in seven cases. Preparation reads 12.12 MB and decodes 372,592
identity entries, beyond the existing query work.

This rejects the one tested tie-order policy without tuning. The positive form
retrieval proxy does not translate into better chains under this intervention.
The frozen baseline is the `dc10ec2` function, before the separate on-demand
token optimization. No production profile score is introduced. Evidence is in
`exports/search-research-20261014/use-guided-search/`.

## Returned-path count is separate from scan budgets

The current unrestricted Volcanus benchmark requests eight paths, returns
eight, represents ten of fifteen target ingredient jobs and reports
`path_limit`. Requesting sixteen returns twelve paths, represents all fifteen
jobs and reports no limit reason. The process, state and predecessor limits
remain 10,000, 20,000 and 100,000 respectively. Actual work still increases:
examined processes 1,942 to 2,343, admissions 1,331 to 2,118, pops 781 to 1,195,
and predecessor work 11,033 to 11,483. Indicative query times are 0.499 and
0.667 seconds. This is output-cap diagnosis, not a faster algorithm.

The LV control returns the same three paths covering all five jobs at either
requested count, with equal work and state counters. All twenty-six returned
paths preserve verified native transitions and complete recipe context.
Canonical DB and sidecar metadata remain unchanged. GUI defaults and API limits
are not silently changed. Reproduction and complete results are in
`exports/search-research-20261014/current-profile/output-limit-summary.json`.

## Native catalog and machine identities for opaque components

The existing NativeCapture owner now prepares independent GT and GT++ raw
catalog maps before emitting resources. Both use the same exact registry,
metadata and typed-NBT resource key, ignoring count. All matching symbols are
retained without creating catalog-only resources. GT++ uses one checked private
ItemStack field because its public getter can write the unification cache.
Layout or access failure discards that catalog's partial map and emits failed
coverage. No getter fallback, normalization or generic reflection layer is added.

Machine resources also retain the actual registered template class and metadata
identifier through the native accessor. The reference explicitly says that
the resolver ignores NBT. These facts identify native owners and symbols. They
do not certify semantic use, stock, configured capability, chemical quantities
or source-atom contribution.

One new `.225` capture, `4f42f0e1-b7a0-478b-9440-57113b3d961c`, verifies LV Casing,
LV Hull, Robot Arm IV, Computer Cube, Volcanus Casing and Volcanus references.
GT prepares 3,023 raw anchors across 3,009 identities, and GT++ prepares 614
anchors. Referenced resources receive 2,872 GT anchors, 576 GT++ anchors and
3,093 machine template references. There are 3,433 catalog-tagged resources.

All 118,719 resource identities match the previous `.225` capture. There are
no added or removed identities. Every other resource field is equal after
excluding only snapshot-local IDs and native_source_refs. All six collections
survive import exactly. Root separately checks the six raw gzip records against
fresh Dataset getter replies and independently recomputes both protected DB
hashes. The active `.221` capture and accepted `.223` data remain unchanged.
`.225` chemistry remains unsupported.

Compilation and 32 Java tests pass. The exact identity tests characterize NBT
type and ordering distinctions. Layout/access failure is source-reviewed, not
claimed as injected runtime coverage. IntelliJ completes. The combined runner
skips PMD because of nested-wrapper detection, while the supplemental file
scan completes with metric advisories and no processing/configuration errors.
The actual capture continues after a Context Mode timeout and its retained
logs confirm successful exit. Only one capture is launched. No active dataset
or service is switched. Evidence is in
`exports/search-research-20261014/native-use-identities/`.

## Exact `.225` accounting and combined native data

The fixed accounting matrix finds all fifteen source files and twenty-two
actual runtime classes byte-identical across `.221`, `.223` and `.225`. The
verified `.225` release is commit `548a62b655b6d4864f276cd028fbb81f75eea999`, and
the installed JAR hash is
`5bd8e63070cf1f70785111e5329c58dcc3afaef38c413755958c633bae0b2337`.
The two existing version allowlists now include exactly `.225`, keeping profile
`.221` and every quantity, phase, identity and candidate-consensus gate intact.
Future and development versions remain unsupported. GT++ chemical accounting
is not added.

Consumer regressions fail first in the intended three `.225` quantity cases,
then all twenty-two balance tests pass. All 173 Python tests and thirty-two
exporter tests pass. The producer's private allowlist has real-capture acceptance
rather than an invented Java unit initialization seam. Audit skip and advisory
limits remain explicit in the evidence report.

Fresh snapshot `b2b17000-0da9-4f37-98ec-e33caeb04e57` has 4,693 producer-eligible
resources and 4,695 complete consumer results. All 4,695 previously complete
identities from both `.221` and `.223` match with equal vectors and bases.
The 5,163 resources carrying native source references retain all 6,541 entries.
The six catalog/template controls remain chemically unsupported, as intended.
Root separately checks fresh public Iron Dust, Water and Hydrogen vectors,
the six reference records and all four protected index hashes.

The pipeline takes 168.371 seconds. Compressed streams total 14,585,947 bytes,
and the new index is 1,120,657,408 bytes. Prior unresolved `.225` data remains
unchanged and chemically unsupported after the reader extension. No data is
retro-certified. This creates a coherent separate capture with new source
facts and supported native chemistry, without switching the active snapshot
or refreshing existing GUI/MCP processes. Evidence is in
`exports/search-research-20261014/accounting-225-feasibility/`.

## Separable semantic potential reduces work but loses a branch

The bounded A* pilot establishes an admissible and consistent potential for
the existing internal queue cost. Resource-to-match arcs carry the selected
input's no-source-overlap point, and process-to-resource arcs carry the
minimum native output-position penalty. Continuity and recovery cost zero
in this lower bound. The final target edge is handled separately. Actual g
remains authoritative for dominance, and the hop reference is unchanged.
The bound does not apply to the separately recomputed final path_score.
It relaxes AND and waypoint requirements rather than proving their feasibility.

Concrete work drops substantially. Unrestricted Volcanus admissions fall from
1,331 to 946, pops from 781 to 549 and predecessor work from 11,033 to 9,852.
LV admissions fall from 3,257 to 750, pops from 2,673 to 640 and predecessor
work from 12,931 to 7,273. None of eight cases gains paths or represented slots.
Unrestricted Volcanus exchanges the computer-cube slot `(p204431,7)` for circuit
slot `(p25071,4)`. It loses the Tungstensteel plate to IV hull to computer-cube
story. Distinct resource-sequence stories fall from five to four.

Four complete potentials require 1,847,674 arc scans and 955,849 preparation
heap admissions. Common preparation reads 118,717 material rows, 276,408
output rows and 253,875 tier rows. Eight-query time including preparation
rises from 5.376 to 7.568 seconds. Whole-process peak working set rises from
110.6 to 175.9 MiB. All 342 returned steps, 3,695,326 potential arc checks
and returned-prefix bound checks pass. No unfinished potential guides search.

Reject this default policy for the current coverage and relevance objective.
The work reduction is positive evidence, not a production speedup or better
semantic map. A faster branch can consume a result slot before a useful
construction branch under the same returned-path limit. Future allocation
research should distinguish branch relevance from queue efficiency, rather
than retuning this potential after seeing the failed control. Evidence is in
`exports/search-research-20261014/semantic-potential/`.

## Captured group exclusions and compact GUI results

Trace now accepts optional excluded_group_ids through Dataset and MCP, repeated
excluded_group_id over HTTP, and repeatable --exclude-group through CLI.
The existing membership table remains authoritative. Each group is validated
and resolved once to literal members, then unioned with exact resource exclusions
for all three search policies. Recipes and their cofeeds are preserved in full.
Wildcard and NBT predicate expansion are separate from literal group membership.

Canonical native evidence demonstrates the gap. Excluding the GT nugget alone
still permits a MagicBees nugget to Iron Ingot through the Alloy Smelter.
Excluding ore:nuggetIron blocks the five captured members. unified:r12261 is a
distinct three-member group. Neither identifies all Nugget forms. Compact
group_exclusions summaries provide names, kinds and counts without an ID dump.

The GUI uses a removable captured-group picker with path-only help. Real browser
QA selects the GT Crushed Iron Ore and Double Iron Plate identities, then the
five-member group. The applied summary is visible and four paths still complete.
A separate real HTTP check confirms that every returned path avoids group members.
The temporary listener and browser tab are closed after verification.

Browser QA also establishes a concrete payload issue: the GUI was relying on
HTTP's full-view default. The native result expanded 1,724 resource variants.
Explicit compact presentation returns 21 resources, with the same four paths,
five represented jobs and ten complete selected recipes. It uses the existing
presentation contract, preserving native choices and quantities. No additional
mode or matching rule is introduced. The interaction assertion fails first
without the view parameter, then passes.

All 178 Python tests and 66 GUI tests pass. Typecheck and the isolated production
build pass. Root reviews the complete backend/UI diff. The served main ui/dist
hash stays unchanged. The new bundle is built only into the excluded QA directory
because the main already-loaded backend lacks the new parameter. It is not
claimed deployed on port 8000 or on existing MCP connections. Old API callers
retain their current argument semantics. Optional result metadata preserves
supported earlier trace responses in the UI, without a capability fallback.
Evidence, raw requests, browser proof and the candidate bundle are in
`exports/search-research-20261014/group-filter-ux/`.

## Fixed-pool coverage selection exposes a relevance tradeoff

The saved twelve-path Volcanus pool permits a bounded offline comparison
without another search. The same-pool best eight by native quality cover
ten of fifteen exact target slots and four resource-sequence stories.
Greedy newly covered slots inside equal penalty/hop tiers reaches eleven
slots and five stories, preserving the same quality-tier vector. Exhaustive
inspection of all 495 eight-path subsets confirms eleven as this pool's ceiling.
Both Computer Cube branches remain, without a manual whitelist.

The saved current eight also have five stories and ten covered slots, but
retain the stainless-steel heat-vent and Volcanus-casing history. The greedy
selector drops those and adds Single Use Hard Hammer to Double Hastelloy-N
Plate. Its exact native hint places the selected input in craftingToolHardHammer
and retains unresolved damage, breakage and container returns. This is a
dependency witness, not plate-material provenance. The initial research label
misidentified that plate as a heating coil. Exact resource inspection corrected
the label before the final report. The metric improvement remains valid.

Twenty-eight of eighty pool resources, including nine spine identities, lack
material tokens. This unrestricted pool has no native recovery-hint or
coproduct-position steps, so it cannot demonstrate protection of those absent
controls. All sixty-two steps and complete records pass native verification.
Offline selection and validation take about 0.067 seconds. The larger pool's
historical discovery uses 2,118 admissions and 1,195 pops, versus 1,331 and
781 for the saved eight. Selection does not erase that extra discovery work.

Retain the positive coverage tie-break evidence, but do not promote it as a
default relevance improvement. Coverage of every dependency branch differs
from identifying where the starting material contributes to the product.
Native input roles, declared composition and opaque components remain separate
evidence dimensions. No policy changes follow from this single fixed pool.
Evidence is in `exports/search-research-20261014/branch-selection/`.

## GT++ factory provenance is a deferred integration path

The exact .225 factory exposes the actual GT material input, nullable Element
reference and new native Material object at its fresh return. Actual JAR
disassembly distinguishes cache-hit return at 32, construction at 423, cache
publication at 434 and fresh return at 442. Observing every return would assign
later cached requests as origins incorrectly. The label-based cache key is not
material identity.

This could preserve historical construction provenance for GT-derived wrappers.
It would not establish chemical equivalence, current attributes, purity or form
units. The factory does not copy GT components or density normalization. Direct
Hastelloy-W/N and Fermium construction remains outside the seam. Constructors
can catch initialization failures, and attributes can change after construction.

All six inspected hook APIs exist in the installed UniMixins runtime but none
exists in the exporter's actual 121-entry compile classpath. The exporter has
Mixins disabled and no hook configuration. Installation before the first target
load and material singleton initialization has not been demonstrated. Prefer a
future upstream provenance getter on the native owner. Defer instrumentation
pending an explicit integration decision and isolated pack lifecycle evidence.
No dependency, configuration, code or capture changes follow from this study.
Evidence is in `exports/search-research-20261014/gtpp-factory-provenance/`.

## Literal tool exclusion exposes an NBT-specific category gap

Two fresh canonical Volcanus queries keep the material policy and the same
search caps, requesting sixteen returned paths. The baseline returns twelve
paths covering fifteen target jobs. Excluding the five literal members of
ore:craftingToolHardHammer removes both Single Use Hard Hammer stories, but
replaces them with Iron Ingot to Iron Hammer Head to Hammer to Double
Hastelloy-N Plate. Both results retain twelve paths and fifteen represented jobs.

The replacement Hammer r42150 has registry gregtech:gt.metatool.01, metadata 12
and typed native GT.ToolStats NBT specifying Iron and Wood. It has no captured
ItemData association and no literal crafting-tool category hint. A different
Hammer identity r3688 is registered in the selected group. This establishes a
specific gap in descriptive category evidence, not an error in exact group
filtering. Missing hints cannot certify material contribution.

Expansion rows fall from 11483 to 10989 and admissions from 2118 to 2060, while
examined processes rise from 2343 to 3000. No cap is reached. All native steps
and full selected recipes pass verification, and both store fingerprints remain
unchanged. No automatic tool ontology, wider group matching or search bias is
introduced. Source research will check actual native membership and tool APIs.
Evidence is in `exports/search-research-20261014/tool-route-filter/`.

## Equal native material does not permit cross-form dominance

The current search already blocks repeated exact resource and recipe identities.
The saved native Volcanus witness requires Iron Dust to Steel Ingot to Steel
Dust to Tungstensteel Dust. Steel Dust r7439 and Steel Ingot r11342 have identical
complete native primary material descriptors. In backward search their actual
cumulative costs are both one, at depths five and six. A material-only key would
reject the necessary ingot continuation as dominated.

Mixer p171532 accepts the dust port and rejects the ingot port. Macerator
p155691 is the required bridge and correctly receives no recovery penalty.
The shorter dust history is a subset of the ingot history, so adding a visited
history subset check does not rescue the material-only comparison. Fuel, ash
chance, tungsten cofeed and presence circuit remain in the verified full records.

Equal descriptors are useful descriptive grouping evidence. They do not prove
interchangeable recipe ports. Safe pruning would need a concrete costed port
simulation preserving requirements, history, cofeeds and audit context. Reject
blanket cross-form dominance without a runtime experiment. Nineteen canonical
lookups and 115 logical work units verify seven native steps in about 0.039
seconds. No actual query work or results change. Alternative routes were not
searched, so no whole-query coverage-loss estimate is claimed.
Evidence is in `exports/search-research-20261014/form-cycle-dominance/`.

## Native categories can explain routes without asserting atom flow

A bounded census of nine saved routes and thirty-three steps finds twelve
steps with both native form prefixes and nineteen with both primary material
declarations. Those fields, recipe families and native input/output records can
describe processing. None assigns the material of a selected input to a specific
output. The hammer-to-plate recipe has plate cofeeds, while multi-output chemistry
does not expose an input-to-output atom assignment.

Three selected inputs have literal tool-category hints. Exact Forge source
matching predicts five when NBT variants are included. This is a source-backed
prediction pending native acceptance, not a measured new capture result.
getOreIDs reads wildcard and exact item/metadata maps, and getOreName reads the
name list. Persist native names, not runtime-local numeric IDs. Keep this matching
evidence separate from literal captured group members and path exclusions.

The lookup calls ItemStack.getItemDamage, which dispatches to Item.getDamage.
The inspected GT metatool hierarchy inherits the passive raw metadata getter.
Arbitrary custom overrides are outside that proof, so the API analysis does not
claim universal absence of mod callbacks. Avoid GT getToolStats on originals,
which can mutate enchantment NBT. Native matching capture and basis-specific
annotations are being implemented in existing owners without a search bias.
Evidence is in `exports/search-research-20261014/route-meaning/`.

## Conditional AND/OR landmarks need a declared supply boundary

The full [Keyder, Richter and Helmert paper](https://ai.dmi.unibas.ch/papers/keyder-et-al-ecai2010.pdf),
[LAMA paper](https://arxiv.org/abs/1401.3839) and official
[Fast Downward documentation](https://www.fast-downward.org/latest/documentation/search/LandmarkFactory/)
support a distinct research direction. AND nodes retain joint recipe prerequisites,
OR nodes retain alternative producers, and shared support can explain more than
a single dependency spine. Current implementation sources are pinned rather
than assumed identical to historical LAMA.

Their guarantees require a defined initial state and producer model. Our external
cofeeds, quantities, consumption, chance, startup and incomplete captured frontiers
prevent a direct global-necessity or admissibility claim. The proposed pilot uses
the existing boundary/network owner with a conditional shared-cofeed agenda,
neutral unknown frontiers and unchanged preparation-inclusive budgets.

The read-only prerequisite check returns no existing boundary profiles for the
canonical snapshot. Its profile sidecar is absent. LV Casing and Volcanus resolve
to exact native identities, but no baseline, treatment or map runs. Supplies are
not invented. The canonical hash remains unchanged. Map preparation, complete
AND support and ranking quality are unmeasured, not zero. Defer this pilot until
an explicit boundary exists through the existing owner. This is a prerequisite
result, not a negative algorithm experiment.
Evidence is in `exports/search-research-20261014/planning-landmarks/`, including
the bounded `pilot/` prerequisite report.

## Native matching membership closes the generated-tool explanation gap

NativeCapture now records the actual OreDictionary.getOreIDs result once for
each emitted item, through the existing resource owner and prepared ore-group
roster. Names are sorted and unique. Success, explicit empty and failure remain
distinct. Fluids omit the field. No group members, matching rules, quantity
profiles or recipe arrays are replaced.

One isolated .225 capture produces snapshot bed9f2cf-3362-420a-a1c3-d074cabfd348.
All 117299 items have captured membership, with zero failures and 63800 explicit
empty results. All 1420 fluids omit it. The registered hammer and Iron/Wood NBT
hammer share craftingToolHardHammer. The NBT variant remains outside the literal
group, so literal group exclusions keep their original meaning.

The consumer uses a native matching basis for successful native evidence and
retains literal-member evidence for supported immutable captures with the field
absent. Empty, failed and malformed native fields do not substitute older hints.
No search score or policy changes. Four saved native route sets retain every
non-hint explanation field. Annotation alone costs 2.388 to 3.036 ms in these
samples, including its connection and 4 to 17 group-record reads. These samples
do not establish a query speedup.

All 180 Python, 67 GUI and 32 Java tests pass. An official isolated MCP client
and HTTP agree on three native hammer paths, their complete recipes and new
basis. Real candidate GUI shows four paths and correct basis tooltips. Local
inspection retains all five recipe tiles. Temporary client, browser and server
are closed. Main port 8000, its served bundle and existing MCP connections remain
unchanged. Older supported data keeps its explicitly documented evidence basis.

Independent root checks verify both public hammer records, preserved typed NBT
and earlier fields, all item/fluid status counts and two protected hashes.
Producer verification preserves all five protected hashes, all 118719 resource
identities and earlier fields, and all 186528 normalized group memberships.
Snapshot-local ID changes and thirteen member-order differences remain recorded.
Whole-process parity is not claimed. Native condition/object text and ordered
matcher differences remain separate comparison evidence.

IntelliJ finds no issue in added code. The audit wrapper skips PMD because of
nested wrapper discovery. Supplemental classpath-aware PMD adds one collector
complexity advisory, retained rather than split into unnecessary types. A direct
native collector unit test would require artificial Minecraft initialization,
so no private test hook or producer RED is claimed. Public consumer RED/GREEN
and real native capture provide the behavioral acceptance.
Evidence is in `exports/search-research-20261014/native-ore-membership/` and
`exports/search-research-20261014/route-meaning/`.

## Custom machine declarations correct an Eye of Harmony phantom plan

The .225 capture contains 43 Eye of Harmony GT display projections. They report
zero EU/t, a derived ULV tier and presence inputs without consumed quantities.
A concrete public accounting reproduction accepts guaranteed outputs with no
consumed material and a recipe-runs network accepts a phantom production step.
The nominal-energy audit already rejects the zero energy, but material accounting
and recipe-tier discovery need a separate correction.

One shared exact-marker diagnostic now rejects these projections in accounting
and discovery, including supported immutable older snapshots. Recipe voltage is
unknown. Raw inspection remains unchanged. Ordinary native zero-EU recipes keep
their existing semantics. Unknown-tier inclusion cannot restore the unsupported
accounting step.

The producer now decodes the native EyeOfHarmonyRecipe declaration through its
public getters. Output resource references retain ordered base quantities as
exact decimal strings. Requirements, energy, timing, casing and rocket tiers,
base success chance and efficiency retain their source API. These fields do not
establish executed quantities or guaranteed machine yield. The original GT arrays
remain visible beside null executability, unresolved dynamic inputs and outputs,
and unresolved voltage without a derived nominal tier.

One isolated capture produces snapshot 5b2dbdde-c08b-4efa-b85d-3e4b55893587.
All 43 declarations pass exact long-string, source, reference and unresolved-state
checks. Their declaration resource order matches the GT projection within this
capture. Against the preceding capture, all 43 input identities and raw output
multisets preserve amounts and chances, as do duration, EU/t and amperage.
Output order differs in all 43 records. Prior source inspection explains native
hash collection and tied sorting behavior without claiming the cause of every
movement or treating order as a primary-output designation.

All 118719 resource identities and prior fields remain unchanged apart from local
IDs. Native matching membership is retained. All 19 protected indexes keep their
hashes. The bounded phantom-plan control now returns no solutions, which is not
a global unreachability proof. All 183 Python tests pass. Producer build, Java
checks and scoped audits pass their established checks, with audit limits recorded
in the evidence. Root independently checks one fresh public process, all its 350
native output references, exact start EU above JavaScript's integer precision,
the older public rejection and its protected database hash.

This correction changes fidelity and accounting, not search budgets or ranking.
The active snapshot, main served GUI and established MCP processes remain unchanged.
Evidence is in `exports/search-research-20261014/eoh-native-declarations/` and
`exports/search-research-20261014/output-order-semantics/eye-of-harmony/`.

## Two bounded controls avoid unjustified recipe exclusions and score changes

A read-only GTRecipe census covers 186917 records in 206 family, recipe-class
and special-object-type groups. Twenty groups have a typed special object or
a record with no positive consumed input. This is a review signal, not a proof
of unresolved execution. Several display groups already carry fake flags.
Eye of Harmony supplies the verified positive control.

Only the strongest additional candidate, Fish Pond, receives source inspection.
Exact .225 source and installed bytecode show standard ProcessingLogic and
ParallelHelper execution of its declared output chance arrays. Three native
recipes contain 49 outputs, all below certainty, with circuit presence selectors
and 15 EU/t at nominal LV. Six shared-ledger checks retain fractional expected
outputs and no guaranteed outputs. The indexed lookup reads three records.
The protected database hash stays unchanged. No new exclusion is justified.
Algae Pond and BacteriaVat remain uninspected signals, not invalidity findings.
No blanket rule for presence-only, no-input or zero-EU recipes follows.
Evidence is in `exports/search-research-20261014/custom-projection-census/`.

The source-verified Temporal comb import also receives a finite ranking probe.
Two exact canonical GT counterparts resolve through complete native identities,
amounts and chances. The observed 32 plus 32 cross-capture order differences are
not treated as a source-verified roster. Preparation costs 23.033 ms, eight
identity lookups and two candidate process reads. Across eight saved regression
requests neither verified recipe reaches predecessor processing or score
evaluation. Current paths, target branch sets, complete recipes, non-hint details
and charged counters equal the saved controls. Both native stores remain unchanged.
No treatment is fabricated when there is no reachable effect. This result gives
no benefit for that exact roster in these queries. It does not establish that
output-position preference is harmless throughout the dataset.
Evidence is in `exports/search-research-20261014/output-order-semantics/centrifuge/pilot/`.

## Repeated scores are mostly protected by the existing fact caches

A private probe counts exact query-local penalty arguments: selected source,
destination, native output position and process. Casing makes 10298 logical
calls with 1441 unique argument sets and 8857 repeats, about 86%. These repeats
do not imply equivalent repeated database work. Existing material, family and
resource-role caches already protect the expensive reads and JSON decoding.

One standard-library query-local LRU treatment preserves all eight frozen outputs,
their route ordering, branch sets, full native recipes, cofeeds and charged work.
Three alternating pairs per case do not show a useful total-query improvement.
The sum of case median times changes from 6.109 to 6.144 seconds, about 0.6% slower.
Casing improves about 6%, but other cases vary from small gains to a 4.8% loss.
Its separately profiled penalty shrinks from 65.1 to 59.7 ms while first-time
family and resource-fact work stays unchanged. Profiled primitive savings do not
establish a total-query speedup. The Casing-only Python allocation peak changes
from 43366501 to 43367169 bytes. This is neither RSS nor a dataset-wide memory bound.

The treatment is rejected without tuning or another production cache. Preparation,
logical calls, physical evaluations, cache hits and changed internal diagnostic
counts remain separate in the saved evidence. No scoring rule, ranking, search
cap, native store or service changes follow. Evidence is in
`exports/search-research-20261014/score-reuse/`.

## A held-out silicon route exposes an incomparable-label preference

One plain-wafer target is resolved through exact .221 source catalog declarations,
not its display name. Raw Silicon Dust is r6488 and plain Wafer is r30750. Before
search, four complete native recipes establish Raw Silicon Dust to Trichlorosilane,
Solar Grade Silicon Dust, plain boule and wafer. Their cofeeds, batches, circuit
presence, voltage classes and EBF coil heat remain explicit. This is a dependency
witness, not an inventory or normalized production plan.

A single unchanged-default material query takes 0.856 seconds. It returns eight
paths covering all eight target ingredient jobs, examines 5759 processes and
charges 24096 expansion-work units. The only reported limit is path_limit.
The four-step witness is absent. All four boule branches instead use seven
steps through Dark Steel and a hammer. Crafting p233032 consumes that selected
hammer alongside Centrifuged Solar Grade Silicon Ore. That ore already has a
native SiliconSolarGrade association. The source participates through the tool
dependency, while the separate ore cofeed remains visible. These captured paths
are valid dependencies. Neither contribution of source atoms nor illegality is
established. Full branch representation does not capture this narrative weakness.

Static score breakdown explains the preference without another search. Current
flat labels treat Trichlorosilane to SiliconSolarGrade as disjoint at cost four,
while the unassociated hammer bridge costs one. Native output position adds two
on the chemical route. Four-step and seven-step witnesses have returned sorting
scores eight and four. Both fit the same depth bound. One representative clears
each target job, so this is more than simple exhaustion of the result count.

The labels have different evidence bases. Native Trichlorosilane declares actual
Hydrogen, Silicon and Chlorine components with element-backed children. Native
Materials.SiliconSG declares the display formula Si* but no element or components.
Its captured composition remains unresolved. The current flattened descriptor
drops that distinction. Disjoint text across these bases is not a statement of
chemical disjointness. No formula parser, purity rule or native grade alias follows.

Independent exact lookups preserve ten complete process records and 31 resources,
with every declared reference resolved. The selected hammer's typed NBT is Dark
Steel primary and Wood secondary. There is no Solar Grade handle. Native .221
source excerpts corroborate the component and formula distinction. Original
request, before-search witness, complete result and immutable store fingerprints
remain saved in `exports/search-research-20261014/material-heldout/`.
One basis-aware private treatment retains weights and caps. It keeps exact shared
labels as descriptive hints, and compares a complete native declaration tree
against opaque or partial evidence as unknown rather than strongly disjoint.
Completeness here describes captured structure, not chemical purity or certified
atom flow. Status, coefficient and truncation uncertainty remain explicit.

The treatment runs once on the new wafer request and each of the eight frozen
controls. Four direct chemical boule spines appear. Wafer coverage remains 8/8,
admissions fall from 6215 to 4211 and charged work from 24096 to 20761. Seven
control path sets stay identical. However Volcanus loses its only represented
LuV-circuit branch for another Computer Cube branch. Its aggregate 10/15 hides
that loss. LV Hull work rises from 4533 to 8900 and admissions from 912 to 1971,
with unchanged results. This fails the predeclared coverage and cost criteria.

Per-query native metadata work is 187 to 1688 reads, 0.135 to 2.078 MB parsed,
1.28 to 19.10 ms parsing and classification, and 7.59 to 69.70 ms SQL in these
single samples. All complete native/cofeed matcher checks pass. Original stores
and production code remain unchanged. No formula parsing, weight tuning, second
treatment or default change follows. The positive held-out result is evidence
of the local cause, not grounds to promote a globally worse heuristic. Final
evidence is in `material-heldout/diagnosis/BASIS_PILOT_REPORT.md` and its nine
case artifacts.

## A contextual matching-category proof is available for the hammer input

One slot and one native group are inspected without another search. The captured
ore:craftingToolHardHammer group contains exactly the five anchors of p233032
slot zero. Selected generated hammer r42238 is not a literal member and lacks
the newer native Ore IDs field. It matches declared choice one, r3688, through
the actual item, metadata and explicitly NBT-insensitive predicate.

Verified Forge 1614 source and bytecode establish item/metadata membership keys
without NBT or count. Exact .221 GT hierarchy source establishes the passive
metadata getter for this tool. No native API, getter, tool-stat mutation or
matching call is executed by the study. Thirteen reused source hashes and the
actual Forge artifact are checked.

This supports a distinct contextual declared_input_anchor_category explanation,
retaining selected resource, process, slot, choice, anchor and native group.
It is not literal membership or direct captured native Ore IDs. Present empty,
failed or malformed native fields must not be overridden. It establishes no
actual use, wear, material noncontribution or atom flow. The current path_details
category_groups owner already holds the literal and native category conventions.
A new basis would be a visible contract extension. No implementation or score
change has been made. Interface and query-cost feasibility remain the next step.
Evidence is in `exports/search-research-20261014/material-heldout/tool-match-proof/`.

Interface feasibility chooses contextual input evidence over global resource
inference. Canonical relations preserve anchors and choice indexes, while the
prepared graph does not preserve their retrievable descriptors. Post-selection
explanation can use existing resolved edges. A bounded scoring point check would
need to deepen the current matcher before a hot-path experiment. No prototype
or extension follows. The user asks to deprioritize tools, so this strand is
deferred. Evidence is in `material-heldout/tool-match-design/`.

The continuing focus is general upstream route diversity and distinct target
requirements. Formal jobs can repeat the same boule or Computer Cube requirement
across alternative endpoint recipes. Exact equivalence and its effect on result
allocation are not yet measured. Native recipe variants, cofeeds and predicates
must remain distinct and inspectable. Any new experiment must preserve the
circuit branch and construction controls within the existing result and work
caps. It must not repeat the rejected larger-pool selection experiment.

The bounded saved-result census confirms the exact requirement redundancy.
Wafer has eight formal jobs but five snapshot-scoped requirement classes.
Its four boule jobs have the same accepted resource, consumed amount, chance
and NBT semantics, and repeat three upstream prefixes. Volcanus has fifteen
jobs but nine classes. Baseline covers seven classes, while the rejected
basis treatment covers six, despite both reporting 10/15 formal jobs. The lost
class is the complete five-resource LuV-circuit requirement. Exact and unified
Computer Cube choices accept the same singleton here. Original declarations
remain distinct. Consume-one and consume-two gear, arm and plate slots are
not merged. Forty-three bounded matcher calls return 3906 candidates without
another search or store change. Evidence is in
`exports/search-research-20261014/target-branch-diversity/`.

Source review shows that first completion, including duplicate completion,
clears a job and releases its remaining cursors. The next finite pilot keeps
all independent heaps, dominance states and endpoint histories. For identical
canonical ingredient declarations, it can skip an already represented exact
upstream prefix and resume at most one further completion. It creates no larger
pool and changes no score or cap. Native endpoint history cannot be rebound
between variants because coproducts can affect upstream legality. Existing
dominance may already remove the useful alternative. Formal endpoint coverage
and distinct requirement coverage must therefore remain separate. No production
benefit has been established. Design evidence is in
`exports/search-research-20261014/upstream-route-diversity/`.

The single class-local completion pilot fails the useful-story criterion.
Wafer returns six paths instead of eight and keeps all five requirement classes.
The only new exact prefix substitutes p173920 for p171292 while preserving the
same complete resource sequence and later process chain. It is a producer variant,
not a new upstream processing story. The predeclared chemical chain remains
absent. Admissions change from 6215 to 6218, pops from 4530 to 4533 and examined
processes stay at 5759. Charged work rises from 24096 to 25013, including grouping
and continuation. Eight controls preserve their paths, coverage and state counts
with extra bookkeeping charged. No tuning or production change follows.
Frozen functions, raw results and the final report remain in
`upstream-route-diversity/pilot/`. The next question concerns the exact earlier
dominance rule. Its role in the chemical-chain omission is not yet proven.

The focused source answer establishes the precise limitation. Each job keeps
Pareto cost/depth labels at a resource, with a resource-set history only when
explicit intermediate requirements exist. PID history is absent from the key.
Equal labels keep only the first suffix. The saved chemical and technical
forming suffixes both reach Solar Grade at cost 3 and depth 2 with the same
resource history. Stable ordering and the returned technical witness establish
collapse of the exact alternate forming suffix. This is a source-level proof,
not an instrumented prune event. A chemical upstream prefix can still attach
to the surviving forming recipe, so its complete omission remains unexplained
by this collision alone. Evidence is in the pilot's `DOMINANCE.md`.

The next single private pilot changes only scheduling between exact requirement
classes, with independent endpoint queues and unchanged dominance, scores and
caps. It must charge grouping and retain native recipe contexts. A separate
source-only contract check and two-paper primary-source comparison examine the
general alternative-path limitation. Tool-category work stays deferred following
the user's instruction. None of these studies changes production or active data.

The contract check produces a concrete six-resource, five-recipe witness.
Root reproduced it through the public Dataset API using existing fixture helpers.
The unchanged search returns p/u/f. A private full blocked-resource/PID history
key returns p/r/q/u/f, a better-ranked legal dependency spine. Both preserve p's
complete AND inputs, including unresolved cofeed x. This is measured omission,
not an invalid baseline path or a certified manufacturing plan. The temporary
fixture uses no GTNH store. Production files remain unchanged. Evidence is in
`route-diversity-contract/reproduce.py` and `reproduction-summary.json`.

The bounded literature check verifies Eppstein's author-hosted paper and its
retained sidetrack histories and heap frontier. It permits cyclic walks, so its
theorem does not certify our resource-simple and process-simple routes. Yen's
original paper remains unread after HTTP 403 and unavailable/challenged browser
extraction. No algorithm claims are attributed to that unread paper. Evidence
and page extracts are in `alternative-path-literature/`.

One further private correctness pilot tests history-safe Pareto dominance.
At the same resource and covered-required mask, a stored label must have no
greater cost/depth and a subset of blocked resources and PIDs before discarding
another label. The inverse condition removes stored labels. Bookkeeping and
comparisons share the existing cap. Scores, job clearing and scheduler remain
unchanged. This is not K-alternative enumeration. Nine fixed controls and the
reproduced toy determine whether the extra retained histories are affordable.

The class scheduler is not promoted. Volcanus represents eight rather than
seven strict requirements, with no lost classes or old upstream prefixes. Exact
native inspection shows that its new prefix passes from Iron Dust through
Molten Steel and a Single Use Hard Hammer into Double Hastelloy-N Plate.
p230507 still needs two actual Hastelloy-N plates in separate AND slots.
The added dependency spine does not establish manufacture of their material.
Its formal assembler casing job is replaced by equivalent crafting coverage,
while the complete assembler declaration remains returned unchanged.
Aggregate charged work across nine separate requests rises 79184 to 111471.
Dynamic grouping and scheduling account for 31837 units, with 450 extra
native predecessor units. No fixed cap was increased. The prepared rebuild
already has canonical slot effects and matcher memberships needed to derive
classes offline, but that reuse would not itself resolve route meaning.
Reports are in `requirement-class-scheduling/`.

One synthesis pilot combines the exact frozen basis-aware discontinuity change
with this exact class scheduler. The earlier basis change recovered silicon
chemistry but lost Volcanus's circuit requirement to a repeated Computer Cube
class. This interaction motivates one test, with both preparation costs charged.
It changes neither weights nor dominance nor caps. It must retain the circuit,
casing and steel construction controls and inspect actual new material routes,
rather than accepting class-count growth alone. Evidence will remain private
under `basis-and-class-scheduling/` until the bounded result is assessed.

The history-safe bucket-scanning implementation is rejected at its fixed cap.
It repairs the toy, but five native cases stop on work: wafer 8 to 2 paths,
hull 7 to 5, LV hull 7 to 4, Volcanus 8 to 6 and LV Volcanus 3 to 0. Casing
and plate controls retain their exact paths. No new native route appears.
All returned native witnesses and cofeeds remain valid. Conservative label
comparisons and potential subset-member reservations account for 62 to 84
percent of the five exhausted budgets. They are logical reservations, not
measured C-level probes or elapsed time. Exact blocked-set hash keys could
avoid cross-history scans, but their native-case viability is untested.
The predicate's continuation safety and this implementation's budget failure
remain separate conclusions. Evidence is in `history-safe-dominance/`.

The class-scheduler report's initial statement that Computer Cube was absent
is corrected. Baseline and scheduler both cover its crafting slot, while the
assembler variant is absent. The baseline's two missing strict classes are
the consume-one and consume-two double-plate requirements. Raw measurements
were correct. The earlier basis treatment duplicates the Cube endpoints and
loses the circuit class, which remains the specific synthesis hypothesis.

The combined pilot confirms that interaction. Four wafer endpoint variants
recover Raw Silicon Dust to Trichlorosilane to Solar Grade Silicon Dust to
Boule, then cutting. Native processes are p139174/p139349/p118805 plus the
selected cutter. Full acid, hydrogen, circuit, gallium-arsenide and coolant
requirements remain. This is a chemical prefix change, not only a forming
variant swap. The exact predeclared PIDs differ. Its primary route still
illustrates lubricant participation, so main-route ranking is not solved.
Volcanus retains the circuit and original construction prefixes, with 8/9
strict classes and 11/15 formal jobs. Its added plate branch still uses two
actual plate cofeeds. Seven other cases preserve ordered paths and routes.

Dynamic production readiness is rejected. LV hull admissions rise 912 to
1971 and native predecessor work 4533 to 8900, without route improvement.
LV Volcanus admissions rise 3257 to 4051. Total charged work is 437921 across
nine separate requests versus 79184 baseline. Basis preparation contributes
324163 units and class preparation/scheduling 31872. Removing those two costs
leaves 81886 native predecessor units, about 3.4% more than baseline. No cap
fails. All 205 returned native steps pass verification. Complete evidence
is in `basis-and-class-scheduling/`.

The offline candidate follows the existing owner's design. Prepared format 4
stores resource material basis and exact interned requirement signatures with
slot links. Pending matcher-row ranges and persisted matches are reused without
another native matching pass. Class IDs and small material facts replace dynamic
full-payload preparation during Trace. The scoring/explanation comparison is
shared. Root review corrected an eager explanation preload to selected-resource
lazy caching, protecting full presentation's large expanded variant lists.
Twenty-five focused tests and 187 full Python tests pass after that fix.
Copied-native acceptance and build-cost measurement remain pending. Active
data and services are untouched. Design and acceptance artifacts stay under
`prepared-semantic-hints/`.

The user's additional terminal-artifact proposal is separate from this index
candidate. Tinkers tools/parts and GT tools are requested as direct-target-only
route categories. Full cofeeds remain inspectable. Additional group proposals
must distinguish native category evidence from acquisition, chemical validity
or physical noncontribution. No bulk ID file or name-based classifier is added.

Copied-canonical acceptance passes all nine frozen combined requests. Ordered
paths, full native recipes, quantities, matching, cofeeds and branch coverage
agree. Only five wafer continuity/reason annotations intentionally change to
partial under the shared evidence comparison. Their expected changes were
independently derived before continuing the remaining cases. No held-out query
was repeated merely to bypass the stop.

The fresh rebuild takes 42.53 seconds and produces 133861376 bytes, versus
97185792 in the protected old sidecar. Its fresh-process peak working set is
293609472 bytes, including Python and SQLite. All 74159 native matcher calls
have unique keys. Class assembly reuses their results, with 20084162 membership
visits explicitly recorded as offline work. Nine queries charge 83818 units,
including 1932 class lookup/scheduling units, rather than the dynamic pilot's
437921. These counters are not a measured time speedup. Known native widening
in LV hull and LV Volcanus remains, and coolant can still be the primary route.

The nine-case batch uses source 06b95100731746c582f5f01ce637d88635e93e0a7cabcdf145a7d397c1650edb.
The final observation-only correction separates represented resolved classes
from represented unresolved singleton jobs. Existing public unknown fixtures
prove that the previous mixed count could suggest 2/2 known coverage while only
one known class was represented. Internal scheduling and the represented set
remain unchanged. All nine native controls have no unresolved jobs. Twenty-five
flow tests and 187 Python tests pass on final source
3d9f56acad556049306aca25ded8427f7ab0081ed5b94e8e8b1c3e8904cc9628.
One HTTP request and one actual fresh stdio MCP request against the copy pass
on that final source, retaining chemistry, native records and partial annotations.
Reports and gates are in `prepared-semantic-hints/acceptance/`. Original canonical,
sidecar and copy hashes remain unchanged. No active service or data switch occurs.

The user confirms that GT turbine rotors are direct-target-only too. The earlier
recommendation to retain industrial turbines is not adopted. Other extra groups
remain proposals, with all native recipe cofeeds visible and audits unaffected.

The user also confirms Tinkers ammunition as direct-target-only. Native ToolCore
ancestry is therefore fully within the reviewed scope. Passive item ancestry
capture and a shared selected-edge policy are implemented. Their default
rollout requires accepted native evidence. Old snapshots without this evidence
must report unknown recognition rather than receive a name-based classifier.

### Cutter role presentation probe

A fixed-pool wafer probe promotes the existing silicon chemistry with stable
order [1, 2, 3, 4, 0, 5, 6, 7]. All eight paths and their complete native
records, cofeeds, quantities and search counters remain. Only presentation
order and attached indices change. No query, matcher call or larger pool is
used. The source proves that the inspected classic-fluid wafer helper keeps
the item transformation while varying fluid and duration.

This does not justify a generic Cutter fluid-role classifier. Matching item
transformation peers and a default fluid identity cannot distinguish automatic
variants from an explicit provider that uses the same fluid differently.
The production rule remains deferred until native evidence identifies the
operational role. No wafer ID rule or universal coolant assumption is added.
Evidence is in `cutter-role-evidence/` and `cutter-role-pilot/` under the local
20261015 research directory.

The actual GT model has no dedicated Cutter-purpose/default-alternative tag.
It does expose optional `GTRecipe.stackTraces` registration provenance.
Exact relevant .221/.225 sources agree, and the consuming dev JAR exposes the
public field. The existing `gt.recipe.lookup.validate.capture_callsite=true`
property enables native collection before recipe construction independently
of lookup validation. The source-proven classic-fluid helper can remain in
those traces. Calling `reloadOwner` during export would manufacture exporter
provenance and is not a valid reconstruction.

Native copies can lose registration origins, traces can be overwritten, and
collection is global. The next candidate experiment must retain explicit
missing/ambiguous evidence and measure full-pack initialization/memory cost.
No callsite collection is enabled in the item-ancestry acceptance capture.
The `cutter-native-role-options/` report separates the failed library-search
preparation from successful actual source/JAR checks.

### Native terminal-policy acceptance

Prepared analysis version 5 adds native item-type classifications to the same
flow sidecar. All three Trace selectors accept `terminal_artifact_policy`.
Recognized terminal inputs may feed only recognized terminal outputs, so
material → part → tool remains valid. Co-feeds and lookup remain complete.
Recycling explicitly uses unrestricted traversal. Public defaults remain
`allow` pending data/service rollout. HTTP, MCP, CLI and the GUI share the option.

The single .225 capture bfa4c6f5-73d7-4366-8a13-805b4cc4b787 completes in
239.60 seconds including startup, dump, import and preparation. It contains
117299 captured item hierarchies with zero failures or category mismatches,
plus 1420 not-applicable fluids. Categories include 21212 GT tool variants
and 32609 tool-part variants. The GT turbine and Detrav subsets are retained.
Ordinary component rotors, casts and GGfab remain outside the rule.
Finished Tinkers ToolCore/ammunition resources are absent from this corpus,
so their positive coverage is source/public-fixture evidence, not runtime proof.

All nine predeclared bounded native Trace calls pass. A Green Sapphire
TGregworks shard-to-gem carrier is blocked by all selectors while direct
part manufacture stays available. Native recipe records, exact NBT, consumed
cofeeds and presence inputs are retained. Before endpoint preflight, shortest queued states fall
1760→54, but classification adds 39815 charged units and total work rises
3619→41728. There is no blanket speedup. Prepared material mode reads stored
classifications without those hierarchy-array visits.

Game mod versions and hashes match the EOH .225 baseline. Only the exporter
JAR intentionally differs. Both captures have the same 118719 full resource
identities. The initial 2282 strict differences are solely top-level local IDs.
After exact-identity alignment and removal of new item_type, every other old
resource field matches. No recipe-order or new quantity-certification claim
follows. Twenty-two protected files and all harness-inspected hashes remain
unchanged. All 194 Python, 67 GUI and 32 Java tests pass. Java audits add no
new advisory meanings. Evidence stays local under `terminal-native-acceptance/`.
Root checked the native shard, part target and ordinary component-rotor facts.
No active dataset, main bundle, service or configuration was switched.

### Terminal endpoint preflight

The static terminal-edge rule yields an early impossibility proof: every
permitted successor of a recognized terminal resource is terminal. Such a
start cannot reach an ordinary or unclassified target under the restrictive
policy. The shared Dataset loader now checks endpoints before shortest
discovery or material source-distance construction. Diverse reuses its
shortest preflight. Actual classification reads and ancestry visits remain
charged. Endpoint checks have separate telemetry and do not invent recipe edges.

The public regression is RED, then GREEN across all three selectors and both
ordinary/unknown targets. It proves zero examined recipes, queued states and
distance work while preserving terminal targets. All 84 focused checks pass.
The GUI explains policy rejection and retains the selected filter. All 68 GUI
tests, typecheck and candidate build pass. The combined Python working-tree
suite passes too. The earlier nine native measurements remain the original
baseline, without repeated queries, rebuilds or a new speedup claim.

### Opt-in native registration provenance

One optional native collection/export path is implemented through the existing
GT provenance owner and full-pack launcher. It preserves bounded literal
`GTRecipe.stackTraces`, with explicit missing/malformed/truncated/failed states.
Collection and export require the explicit opt-in property. No NEI activation
rule, lookup-validation enablement, reconstruction or semantic classifier is
added. A public CLI regression is RED, then GREEN, with a default-off control.
All 197 Python tests, 68 GUI tests and 32 Java tests pass. Java audits retain
two scoped complexity metrics after one extraction, with no processing errors.

The single native trial 8a3b3c60-d683-4170-a007-98c2544ab31c completes with exit
0 in 252.50 orchestration seconds. Same-log startup milestones are 103 seconds
versus the earlier 99, and capture/publication spans 17 seconds in each.
These runs are not a controlled overhead estimate. Wall includes import,
preparation and post-run integrity checks, with no exact import-only timer.
The uniquely identified game process has OS peak working set 8340537344 bytes
and sampled private maximum 9678991360 across 132 observations. Baseline peak
memory and raw origins were not recorded, so there is no memory delta.

Raw encoding and coverage pass. Of 186917 GT records, 40939 are captured and
145978 truncated, with no missing/malformed/failed fields. 2067527 strings use
134217700 raw UTF-8 bytes, 28 below the 128 MiB budget. The budget fills during
Canner. All 9329 Cutter records lack retained strings. Each of the four full
identity-matched wafer declarations has 48 observed frames but retains [null]
with a total-byte-limit reason. Their source-role utility is negative. No limit
was increased, no second capture was attempted and no role/ranking was promoted.

Actual game versions and hashes match the ancestry baseline except the exporter.
Resource identities and old fields match after local-ID alignment. Ordered GT
recipe parity remains false, with 4423 unmatched occurrences on each side.
Diagnostics separate native-index movement, object-text changes and ordered
input/output candidates. They do not establish cause or parity. All 24 protected
files remain unchanged. The snapshot stays an experimental local artifact.
Acceptance and absolute measurements are in `native-callsite-design/`.

The next fixed-corpus study measures exact string and ordered-trace repetition
among retained data. Lossless sharing may fit more information in a byte budget.
It cannot reconstruct omitted Cutter origins, establish all-corpus compression
or remove native collection RAM. No new capture is part of that offline study.

### Fixed-prefix callsite compression

All 40939 fully captured records contain 2050410 frame occurrences but only
7221 exact strings. Whole ordered trace objects have 6912 unique values.
Both frame and whole-trace pools round-trip every studied record exactly,
including order, counts and metadata, in memory and from persisted gzip files.
The dictionaries are included in every comparison.

Flat callsite JSONL uses 152695269 raw bytes and 1185869 gzip-6 bytes.
Frame pooling uses 19692892 and 239215. Whole-trace pooling uses 34479653 and
399903. Frame pooling is better once the 23375203-byte whole-trace dictionary
is included. The complete native subset's gzip size falls from 2637624 to
1462511 with the frame dictionary included. The pilot takes 57.79 seconds,
with 113.74 MB Python traced peak and 225.34 MB process peak. Declared scan,
time and memory bounds are not reached. No query, mutation or new capture runs.

These are prefix-corpus measurements, not a claim about the missing tail.
All 9329 Cutter origins remain unavailable. The current occurrence-byte budget
is not changed or silently reinterpreted by the prototype. Native collection
RAM is unaffected. A format design must choose dictionary ownership and an
explicit encoded/unique-byte budget before any production change. Root checked
dictionary artifact sizes, and the private helper verified all eight files.
Evidence stays local under `callsite-compression-pilot/`.

The follow-up format design chooses a separate checksum-verified frame
dictionary owned by SnapshotWriter. An inline manifest dictionary would
inflate ordinary Dataset status responses. This remains a deferred design,
without a schema change, budget reinterpretation or additional game capture.
The next core studies return to material-route choice and observed runtime
costs, using saved witnesses and unchanged search limits.

### Input-conditioned output preference rejected

One nine-request baseline/treatment pilot replaces the existing two-point
array-position hint only when complete native declarations identify exactly
one output sharing material-reference tokens with the selected consumed input.
The Raw Silicon Dust to Trichlorosilane witness changes score as intended.
This descriptive hint does not prove atom contribution or cofeed supply.

Classification adds 465299 logical work units. Wafer exhausts its 100000-work
cap and returns no paths, versus eight paths and five baseline classes. The
other eight cases retain exact represented classes and primary routes. Three
changes only swap native producers. One Hull alternative takes nine steps
through machine manufacture and polymer recovery instead of a five-step
chemical route. Neither satisfies the material-story improvement gate.
Measured query time totals 7.737 versus 8.166 seconds, separately from logical
work, with one observation per case. No tuning or production change follows.

All 43 baseline and 35 returned treatment paths retain verified native steps
and full records. A single protected-copy v5 rebuild costs 50.334 seconds and
134836224 sidecar bytes. The copy, sidecar and protected originals retain
their hashes. Evidence is in `core-route-next/pilot/`.

### Cursor heap ordering rejected at cost gate

One recorded Casing baseline provides 23 exact batches, 11377 distinct
descriptors and 87 requested heads. Offline heap replay preserves every full
sequence and consumed prefix, including 302 equal-score/bound groups. The
existing full key totally orders distinct descriptors without a new tie rule.

Replay ordering costs 4.058 ms for sort and 2.072 ms for heap preparation and
requested pops. The 1.986 ms saving is 0.0765% of the recording-adjusted 2.596 s
instrumented query. Actual baseline sort/dedup takes 5.346 ms, only 0.206%.
Recording, allocation tracing and setup remain explicit measurement limits.
This is no end-to-end speedup estimate. The practical cost gate is negative,
so there is no heap treatment query, wafer control or acceptance batch.
The exact native baseline and all protection hashes pass. Source and services
remain unchanged. Evidence is in `core-cost-next/pilot/`.

### Two current-source profiles identify larger metadata costs

Exactly one Casing and one Wafer query are profiled with standard cProfile,
using fresh Dataset instances and the unchanged v5 copy. Both preserve full
responses and work counters, apart from elapsed distance time. Profiled wall
times are 0.728 and 0.847 seconds. These include profiler overhead and are not
unprofiled latency or a speedup comparison.

Wafer makes 5489 first-time recipe-family reads from canonical JSON, while
the existing query-local cache handles 13647 hits. Family lookup takes 0.209 s,
including 0.191 s attributed to SQLite execute. Rebuild already parses every
process and has the exact family available. The chosen implementation stores
that field in the existing prepared process table, with explicit version 6.
It preserves the per-query cache and identifies the new metadata source.
All 197 Python tests pass. Native acceptance and actual latency remain separate
gates, with no claimed gain from profile percentages.

Casing loads 2199 full canonical records, taking 0.087 s in the record owner.
Another 4359 direct trace SQL calls take 0.164 s, but their individual statement
costs are not attributed. Only known full-resource reads are considered for
bounded batching. Acquisition and unresolved-producer statements stay outside
that proposal. Cold source-distance construction takes about 0.21 s each and
already has a Dataset-local cache. No duplicate cache is added.
Evidence is in `core-runtime-profile/` and `trace-record-batching/`.

Prepared-family acceptance runs one frozen v5 baseline and one v6 treatment
for each of the nine requests, alternating pair order and using fresh Dataset
instances. All nine pairs retain exact payloads and semantic work/cache counters.
Only distance time, prepared-index database/version/size/build time and the
explicit family-source marker are exempted. All 259781 prepared family values
literally match canonical JSON, with 172 distinct families and no nulls.

The single paired series totals 6.883 s baseline and 6.103 s treatment. Wafer
changes from 0.627 to 0.439 s. Every pair is lower in this observation, without
a repeated benchmark or profiler-derived speedup claim. One v6 rebuild takes
46.481 s and produces 142098432 bytes, 7262208 above the v5 copy. Matcher work
remains 74159 unique calls and 205990 memberships. Protection hashes remain
equal. Memory-sampler failures occurred before any rebuild/query and were
fixed by restoring one omitted field in the 72-byte Windows structure. Their logs
remain explicit. Evidence is in `prepared-family-acceptance/`.

### Verified path-deviation boundary

Official NetworkX documentation and source were retrieved successfully.
The implementation retains root/spur alternatives in a candidate buffer.
It is not a direct replacement for the current constrained enumeration.
The saved pair-cost matrix for one recipe is [[6,2],[1,3]], which cannot be
factored into entry-plus-exit costs through one shared recipe node. Separate
transition nodes preserve costs but allow the same PID on distinct transitions.
The stock generator also lacks our hop and internal work limits.

A bounded adapter would need explicit PID-group checks, independent endpoint
frontiers and charged spur operations. It could emit legal dependency spines,
without certifying cofeed supplies or guaranteeing K results within the budget.
No solver, query or package installation is promoted from this source reading.
The original inaccessible Yen paper remains unread. Verified sources and exact
content hashes are in `path-deviation-research/`.

### Elemental alias evidence stops at the native data gap

The saved silicon witness has one complete Element.Si leaf at Raw Silicon Dust.
Trichlorosilane declares H, Si and Cl. Solar Grade Silicon has Element null,
empty components and unresolved accounting. Boule and wafer have no captured
ItemData association. All five facts have chemistry_purity:not_certified.
The existing accounting owner already keys element leaves by native Element
ID, independently of material names and with separate quantity scales.

No supported single-element grade pair exists in this witness. Native display
Si* and recipe output cannot certify composition or purity. No alias, formula
parser, compound-atom union or new scan is added. Exact evidence is in
`elemental-alias-evidence/`.

### Known-resource batching stops below the performance gate

A private Dataset clone runs one baseline and one batching query for Casing
and Wafer, in alternating pair order over the accepted read-only v6 copy.
Every full response and work counter is equal except distance elapsed time.
Casing reduces changed payload SELECT calls from 2177 to 20 for the same 2177
rows. Instrumented wall time changes from 2.188101 to 2.130459 seconds, a
2.634% gain. Wafer changes 51 to 43 calls for 51 equal rows and saves 1.172 ms.
The frozen 5% Casing gate fails. No production helper, nine-case extension or
repeat follows. Tracemalloc and counter instrumentation remain in the timing
scope. This is not an uninstrumented latency estimate. Temporary raw-row
storage adds about 555 KB for Casing. All protection hashes match.
Evidence is in `trace-record-batching/pilot/`.

### Trace-enrichment statements have separate measured costs

One exact Casing statement diagnostic preserves the accepted v6 response and
work. Acquisition executes 2179 times, returning 41 rows for two resource IDs,
and takes 55.870 ms including fetch. The unresolved-producer probe executes
2179 times, returning 2160 LIMIT-1 positives, and takes 96.863 ms. The query
takes 507.225 ms wall. Measured wrapper bookkeeping takes 17.445 ms, with
additional instrumentation overhead unmeasured. Fetched rows are not internal
SQLite row visits. No treatment or second query runs.

The unresolved-producer Boolean is snapshot-invariant but includes every
captured declaration. Existing prepared positive eligible outputs cannot
substitute for its exact canonical SQL scope. Any proposed owner must preserve
availability explanations and shortest/diverse without a prepared sidecar.
It must never become an exclusion or acquisition proof. Evidence is in
`trace-enrichment-profile/`.

### Molten recovery has native evidence, but no baseline regression

The rejected Hull treatment's p84812 consumes a prefix-free item with positive
explicit ItemData composition and primary Plastic. Its output has one native
molten association with the same primary. Polyethylene Pulp and Tin Dust
controls instead have declared dust prefixes, no explicit extra constituents
and preserve normal processing. The old pilot prose's item coproduct label
was corrected to Titanium Ingot from the unchanged native JSON.

These fields support a narrow descriptive soft-recovery guard. The bad route
occurs only in the rejected treatment, not the nine unchanged-baseline returns.
There is no current native route improvement claim or new production penalty.
The study inspected no latex witness and cannot certify all natural inputs or
atom flow. Evidence is in `fluid-recovery-evidence/`.

### Correlated boundary probes pass the fixed pilot

The exact unresolved-producer predicate is evaluated request-locally through
bounded correlated EXISTS statements. It retains every canonical declaration
and introduces no persisted flag, cache or prepared-format requirement.
One Casing pair changes 2179 point probes to five statements and measured
instrumented wall time from 472.788 to 403.799 ms. One treatment-first Wafer
pair changes 53 probes to one, with 376.067 versus 373.415 ms wall. Wafer CPU
increases 4.35% at the observed clock granularity, below the declared 5% gate.
Full responses, work and unresolved-ID sets match exactly. Observer overhead
also falls with call count, so this is not an isolated production speedup.
Root integrates the same small Dataset helper, with acquisition unchanged.
Evidence and exact SQL are in `trace-enrichment-profile/pilot/`.

### Declared Cutter ordering improves the retained material story

The old fixed-pool result can support a declared presentation convention,
while its proposed universal coolant claim remains rejected. Material results
now order retained item-entry paths before fluid-entry paths within exact
comparable final Cutter transformations. Native ownership, typed positive
templates, conditions and full transformation fields constrain comparison.
Missing, mixed and unresolved evidence stays neutral. No discovery score,
path pool, quantity, matcher or native role is changed. UU-Matter consumption
is an explicit counterexample to interpreting this convention as fluid purpose.

The result owner remaps route, branch indices and path details consistently.
Optional path_ordering discloses the policy, permutation and structural visits.
GUI explanation appears only after a real reorder. A public ordering regression
follows RED then GREEN. Five public tests protect NBT, native cofeeds, peer/neutral
positions, other selectors and required/fluid-only paths. Combined code passes
202 Python tests and 71 GUI tests, with typecheck and candidate build.

One integrated nine-pair acceptance compares the frozen ed44c34 trace with the
current Dataset and unchanged v6 engine. Wafer reproduces [1,2,3,4,0,5,6,7],
promoting p139174/p139349/p118805/p51142 while retaining every fluid path.
Classification visits eight paths, four recipes, eight slots, eight choices
and eight outputs. Undoing the independently verified bijection restores exact
paths, route, details and branch indices. Every other response/work field is
equal except distance elapsed time. Non-Cutter cases retain their exact order.
The old 205-step native proof is reused through exact body/path/store equality.

One paired series totals 5.436 s baseline and 4.993 s treatment, median ratio
0.925. No observer or allocation tracer runs inside latency windows. These
single observations do not isolate the two changes or establish a repeated
benchmark. All 13 protected hashes, including served bundle files, match.
No rebuild, capture, service switch or new matcher expansion runs. Evidence is
in `mechanical-continuity-design/` and `cutter-and-boundary-acceptance/`.

Targeted transport QA makes exactly one HTTP ASGI and one fresh stdio MCP
Wafer call. Both full payloads equal accepted treatment except distance time,
with eight paths, five classes and aligned route/details/branch indices.
HTTP returns 200. MCP negotiates protocol 2025-11-25, returns a complete
successful structured result and serves the updated format-6 guide. Seventeen
protected hashes match. Only the SDK-owned QA child is closed. This does not
establish a reload of connected MCP or served UI. Evidence is in
`cutter-transport-acceptance/`.

### Concise trace presentation reduces repeated resource metadata

The saved eight-path MCP result is 248726 bytes as compact UTF-8 JSON. Its
93-byte text receipt contains no duplicate result. Resource material_facts
and provenance dominate the avoidable response size. This is a byte census,
not evidence of a particular client's prompt insertion or token accounting.

Client-owned projection was compared with an opt-in view in the existing
Dataset owner. The latter works across transports without a fields language,
response cache or new tool. view=concise uses the compact graph and removes
only those two resource keys. It discloses actual omission counts and directs
same-snapshot exact-ID lookups. All native selected recipes, NBT identities,
coverage, boundaries, path ordering and work remain. Existing defaults stay.

The saved projection is 132199 bytes, 46.85% smaller. Root independently
checked every resource against the allowed omissions and all other result
sections for exact equality. This is an offline projection, not a new native
query, timing benchmark or token estimate. Public Dataset, HTTP, CLI and MCP
tests demonstrate RED then GREEN, including complete get_resource afterward.
All 205 Python tests pass. No GUI source, dataset, prepared format or running
service changes. Evidence is in mcp-payload-study/.

### Hub popularity does not yet define a material-direction prior

The current policy has no degree-normalized score. Related source-distance,
reverse-region and use-profile studies do not constitute a direct trial of
that idea. A shared Hydrogen identity has the same popularity after either
an incidental iron byproduct or a useful reagent path. The prepared factor
graph's resource fan-out counts matcher predicates, not unique recipes.

The saved Water-to-Hydrogen witness also legitimately targets a non-first
coproduct with external cofeeds. It corrects the earlier electrolysis label
above. These observations leave soft query-conditioned normalization open,
but do not yet define its scalar, cost or quality objective well enough for
a fixed-budget pilot. No penalty, exclusion or additional preparation was
implemented. Evidence is in hub-direction-study/.

### Unresolved producers retain distinct native boundaries

The earlier Casing profile finds an unresolved producer for 2160 of 2179
resources. A bounded follow-up selects five IDs from those recorded positives.
Six read-only SELECTs retrieve five resources and seven producer records,
at most two producers per resource. Their causes include dynamic GT crafting,
an uninterpreted universal crafting recipe and a native unregistered door
input. None of these seven declarations is explicitly fake or disabled.
This sample does not identify the dominant cause of all positive flags.

The Boolean tests for any unresolved canonical producer. It neither replaces
picker acquisition counts nor claims an item is unobtainable. Global coverage
is separate too: 172 entries share the reason that all registered map entries
were captured while dynamic backend and machine conditions remain metadata.
Their partial status is not evidence of missing registered recipe records.

Iron Dust producer p150070 retains an ItemDoor input with metadata zero,
null NBT, amount one and native_unknown matching. Its native reverse registry
lookup is null. Prior NEI context already records the same failed shape among
five door-object failures. Local MalisisDoors replacement code explains how
old GT stacks can outlive a replaced registry entry without their delegates
being redirected. That source is 1.19.11-GTNH at b0d85584, while the saved
runtime pins 1.19.12-GTNH. It supports the known mechanism, not exact-version
proof for this individual object. A delegate name alone cannot establish the
replacement as the original recipe's native input.

No identity fallback, predicate weakening, Java diagnostic, build or capture
was added. Protected artifact hashes remain. Evidence is in
unresolved-boundary-study/ and the existing runtime-selected-projections-botania/
NEI presentation context.

### Frozen holdouts expose candidate loss and opaque-composition ranking

Three new controls were selected from bounded native lookups before any trace
result was inspected. Their four-, three- and five-step witnesses preserve
all native inputs, coproducts, conditions and matching evidence. Each current
query then ran once at material, compact, depth 12, max_processes 300, eight
paths and six extra steps on the unchanged v6 copy.

Rutile to Titanium Plate returns eight paths, including the frozen hot-ingot
story. Its primary is a coherent shorter chloride-to-molten forming route.
Scheelite to Tungsten Dust returns the frozen three-step acid route at index
2, behind a legal seven-step QFT/tungstensteel/space-mining dependency.
Naphtha to Polyethylene Pulp returns zero paths after 10000 examined processes,
53108 work units and a found five-hop reference. max_processes 300 did not
cause that search stop. The three observed trace times are 0.270249, 1.020009
and 0.798940 seconds. These are behavior controls, not speedup measurements.

Independent QA checks 84 returned hops and exact canonical bodies. Its 221
full-record calls and 99 matcher calls are outside trace timing. The empty
polymer result has zero validated hops, not a successful-route proof. All 41
frozen hashes remain. Evidence is in holdout-route-controls/.

Source diagnosis establishes that the hop reference contains a concrete
resource/PID witness. The owner uses its length and discards it before material
exploration. A bounded candidate design now retains that witness provisionally
through the same admission owner and existing K/recipe-union caps. Compatible
material completions can improve it. Retained coverage and settled exploration
are separate. Existing guard semantics and prepared format stay. A real-cap
public regression demonstrates RED then GREEN. A K=1 test verifies replacement
and removal of old recipe-union members. All 207 Python tests pass. Diagnosis
and design are in polymer-search-diagnosis/.

Twelve single native treatments against saved baselines preserve exact ordered
path/resource/process arrays for the old nine controls and Rutile. Wafer keeps
its chemical primary. Polymer retains one legal container/cofeed witness but
still lacks its frozen cracking/polymerization story. Scheelite keeps eight
classes and chemical alternative index 2, changes one route and newly reaches
the process limit. Charged work rises from 199355 to 205787. The reference
subcounter is 3278, not the entire delta. These are explicit limits on quality
and work, not a speedup claim. All 45 protected hashes remain. No baseline
rerun, rebuild or active switch occurs. Native proof reuse covers 282 hop
occurrences, with 23 new step checks separately charged. Evidence is in
reference-candidate-acceptance/.

Scheelite's saved material scores are 2 for the long primary and 6 for the
chemical route. Two distinct opaque declarations contribute 4 despite lacking
constituent structure. Mixed structured/opaque comparison contributes 1.
This is not evidence of known disjoint constituents. The search-only surcharge
tests source-material overlap, not step cost. Aligning its score with final
ordering would still prefer the long route. All 43 retained paths in the old
nine controls lack that distinct opaque/opaque case, which says nothing about
unseen frontier changes. No replacement weight or formula inference was added.
Evidence is in scheelite-primary-study/.

### Empty-cell authority is narrower than a fluid-container guess

The retained Polymer reference follows Empty Cell into a canner that requires
already supplied molten polyethylene, then drains the same amount. Saved
native declarations identify the untagged empty state through associated
prefix cell and primary gregtech.api.enums.Materials.Empty. Hydrogen Cell
shares the cell prefix and Tin byproduct but has Hydrogen primary. Filled
molten polyethylene uses cellMolten and Plastic primary. They are not empty
states. No absent ore membership or container-registry relation was invented.

A private material-spine pilot tests excluding only positively recognized
empty intermediates, preserving explicit start/target/required requests, full
native cofeeds, filled cells and audit edges. It reuses the current role-cache
owner after a cheap token screen. Its six calls fail the story gate: Polymer
instead follows Potassium and Hydrogen into a QFT that consumes separately
supplied Carbon and other fluids. There is no Ethylene processing story.
Wafer and Scheelite retain exact ordered paths and classes. All native checks
and 48 protection hashes pass, but that does not justify the policy.

Polymer work rises from 53178 to 76419, including 14726 explicitly charged
classification units. Observed single-pair wall time is 0.805 to 0.896 seconds.
Wafer and Scheelite single pairs move in opposite directions. No speedup,
physical-memory attribution or full causal benchmark is claimed. The optional
Windows sampler fails before Dataset construction or any query and is removed
through a preserved setup correction. Six calls run once, without tuning.
No production code, index, dataset or service changes. Evidence and policy
alternatives are in empty-container-routing-study/.

### Space Mining declarations are not an operation-yield projection

The saved Scheelite primary includes p183528, a native Space Mining declaration.
Exact GT .221 source and the manifest-matching cached JAR establish weighted
asteroid-pool selection with repeated output draws. Amount 64 is the actual
selected stack size per draw. Weight 3000 out of 10000 describes its selection
in this saved pool, not a 30 percent stack chance once per completed operation.
Runtime plasma, parallelism, filters and asteroid selection add further context.

Possible-output dependency lookup remains useful. Current expected accounting
can instead treat 64 * 3000/10000 as output per execution. That is the proven
model gap. Guaranteed accounting supplies zero ore for these individual
outputs, so it does not falsely fund an ore target. Exact chemical accounting
is already unresolved for the saved drill-tip and ore forms.

The selected fix deepens the existing shared projection-issue owner. Accounting
refuses the recognized unmodeled operation in both yield modes with a visible
reason. Nominal voltage uncertainty remains separate. Inspection carries the
same issue outside the unchanged raw process. Neither this guard nor the source
study deletes dependency edges or claims rods transform into ore. No native
text parser, guessed draw multiplier, broad family ban or version inference is
introduced. Evidence and the two interface alternatives are in
space-mining-role-study/.

The implemented shared issue passes the public RED/GREEN regression and all
210 Python tests. One native acceptance passes 15 frozen assertions. p183528
retains its exact raw item, all five 64-stack outputs and weights, ZPM tier 7
and direct dependency. Both ledgers report the shared unsupported reason.
Ordinary p183912 retains its exact expected 1111/10000 coproduct. Canonical,
private v6 and consumer hashes remain unchanged. The one tiny trace reports
truncation, so it proves retention of this dependency rather than exhaustive
coverage. Evidence is in space-mining-accounting-acceptance/.
The GUI carries the same optional issue through explicit recipe inspection,
without fetching every graph tile. All 73 GUI tests, typecheck and the private
candidate build pass. No active UI bundle or running server was switched.

An adjacent exact-.221 Space Pumping source check is negative. Its catalog
quantity scales directly with parallels and batch size. The checked controller
does not use Mining-style weighted repeated draws. A zero-amount NEI display
stack has a separate per-operation quantity in its wrapper. No snapshot query
was performed, so this is not a persisted exporter defect. Normal execution
scaling does not justify another accounting guard. Evidence is in
space-mining-role-study/ADDENDUM-space-pumping.md.

### Target-Element presence needs prepared exact identities

A target-conditioned support measure can sum the target's native mass fractions
whose exact Element IDs occur in a complete intermediate declaration. It avoids
diluting Ti support by the chlorine in TiCl4. Polymer's native C/H target gives
Ethylene support 1, Hydrogen 1/7 and Potassium 0. Polycaprolactam and filled
Polyethylene Cell also receive 1, so this is not a carrier-detour proof. Actual
Wafer has no associated target declaration and remains unknown.

Current prepared material tokens are names and material_basis is a status.
Neither supplies exact Element IDs. The selected private pilot adds a nullable
field in the existing prepared resource owner during its normal rebuild pass.
Quantity-independent declaration support stays separate from eligible unit
accounting in the existing chemistry owner. Target preparation, descriptor
decoding and Element inspections must be charged. No per-intermediate canonical
decoding is hidden in query timing. The one frozen twelve-case pilot must return
a real cracking/polymerization primary, retain saved signatures and classes,
and respect existing caps. No production promotion or speedup is presumed.
Design and frozen protocol belong to target-constituent-relevance/.

The one private v7 pilot is rejected after all twelve frozen calls once. The
first ten preserve exact ordered routes and classes without a gain. Scheelite
falls from eight routes/classes to four and loses the frozen chemical witness.
Polymer returns the same supplied-polymer container route without an Ethylene
processing path. Returned records and hops remain native-correct. Saved outputs
do not establish every unretained candidate visited during exploration.

Total charged work rises from 205787 to 317457, including 134584 support units.
Scheelite reports 100001 at the inherited increment-before-rejection boundary,
not unbounded continuation. The quality regression rejects the variant even
without that one-unit boundary. Polymer reaches the work cap exactly. No work
limit, score, query or acceptance gate was changed to promote it.

One private rebuild adds 380928 sidecar bytes, including 254506 Element payload
bytes. There are 19058 complete supports and 99659 unknowns. Rebuild wall time
266.589 seconds includes tracemalloc instrumentation. Peak traced Python
allocations are 218080561 bytes, excluding native allocations and physical
memory. No controlled preparation-speed comparison follows. Protected stores
and frozen private sources remain exact. The initial copied version-fixture
expectation and its authorized setup correction are preserved. Evidence is in
target-constituent-relevance/pilot/REPORT.md. Production format stays v6.

Saved-counter interpretation identifies 113864 repeated exact `1 - support`
subtractions, 84.60 percent of added support units. Support is already cached
per RID. Its immutable complement can be reused in that same entry without a
numeric policy change. This is charged-operation evidence, not CPU attribution
or proof that more useful routes would follow. Known guidance applies to 27.43
percent of attempts. Seven target profiles are unavailable.

Casing and Hull have a complete primary Steel declaration, but the pilot's
whole-resource accounting gate rejects their prefix quantity. Relative primary
composition is a different evidence scope from per-item accounting. Hull also
declares Tin, so primary Steel cannot be called whole-item composition. No gate
was loosened. A separate complement-cache pilot is frozen around computation
reuse alone, with the original score, target eligibility and quality gates.
It reuses the immutable private v7 preparation and does not change production.
See pilot/COST-INTERPRETATION.md for the measured scope and limits.

The separately frozen cached-complement variant is also rejected. A public
fixture preserves all 33 heap admissions and exact values while avoiding
repeated subtraction. Its twelve native calls preserve the first v7's exact
returned paths in every case. Physical subtractions fall from 113864 to 6246,
but Scheelite still loses four original routes/classes and Polymer still
returns the carrier reference without an Ethylene processing path.

Total work is 231582, lower than first v7 but 12.5 percent above v6. Scheelite
now stops at the 10000-process cap and Polymer at 20000 admissions. Coverage
loss therefore is not explained solely by repeated subtraction consuming the
work budget. Every current call respects its fixed caps. Native QA and protected
hashes pass. There is no rebuild or production promotion. Evidence is in
target-constituent-relevance/complement-cache-pilot/REPORT.md. Saved results
do not establish the content of unretained candidate histories.

### Reaction-local correspondence needs more than Element presence

The checked ReTrace primary paper and official KEGG REACTION documentation
distinguish substrate-product correspondence from the full input-output graph.
ReTrace retains currency-compound endpoint queries by following mapped atom
positions instead of deleting those compounds globally. Its checked graph maps
C, N and P, so it does not establish Hydrogen/water coverage for this project.
Our Element-presence declarations supply neither atom positions nor transfer
relations within a reaction. This is a missing representation prerequisite, not a
ready scoring improvement or justification to infer atom lineage. One Heath
full-text request returned HTTP 500 and was not treated as freshly verified.
Primary links and limits are in causal-reaction-pairing/RESEARCH.md.

### Space Pumping is outside the current canonical catalog collectors

The source and saved coverage check finds no adapter for
SpacePumpingRecipes.RECIPES, a separate native selector-to-fluid catalog rather
than a registered GT RecipeMap. This does not establish a persisted recipe with
the wrong amount or a database-wide absence count. The optional NEI reference
owner does not convert its zero-size display stack and separate wrapper amount
into a canonical process. A passive acquisition/capture model needs actual
catalog quantities, selector context and explicit execution uncertainty. Its
existing-owner design is pending, without a new guard or native capture.
Evidence is in space-mining-role-study/ADDENDUM-pumping-capture.md.

The implemented informational adapter passes compilation, 32 Java tests,
74 GUI tests, typecheck and candidate build. IntelliJ completes without a new
adapter finding. The combined runner skips PMD on its nested-root check.
Supplemental PMD completes on the changed file with the actual classpath,
retaining bounded-pass complexity and the source-defined 20-tick literal
advisories without suppression or unrelated refactoring.

One isolated `.225` capture/import completes in 202.155 seconds. Snapshot
c74341b1-a58d-4207-986b-c7ac965a2201 contains 40 informational pumping records,
with 40 catalog entries and zero invalid entries in coverage. All exact lookup
checks, 80 ledger refusals and one bounded native-record discovery refusal
pass. Nominal energy is 1966080 EU/t, with selectors and actual fluid amounts
preserved. Protected original stores/configuration remain unchanged.

The previous `.225` manifest has 259785 processes and the new one 259825.
Both have 118719 resources, 25228 sources and 119 environments. This is a
count/cohort check, not semantic equality of every existing record. Actual
runtime JAR SHA matches the verified `.225` source. Acceptance is source-backed
capture/coverage consistency, not an independent observation of every live
Pair/FluidStack. Evidence is in space-pumping-runtime-acceptance/.

An underground-fluid coverage check finds the native catalog already supported:
48 saved definitions and 55 registered numeric dimension IDs. The current
source model preserves relative weights, amount bounds and depletion settings,
without a fixed one-unit yield. Provider matching, raw blacklist, seeded
deposits and current availability remain explicit partial context. No duplicate
collector or new supply assumption was added. Exact `.221`/`.225` owners and
consumer limits are documented in underground-fluid-coverage/REPORT.md.

### Preserve the raw underground-fluid blacklist without resolving worlds

The existing WorldgenCapture now reads and serializes the actual native int
array once, attaching detached facts to existing underground-rule environments.
Order, duplicate values, empty arrays and unresolved null remain distinct.
Source status, class decisions and assumed feeds remain unchanged. Source and
acquisition views share compact presentation of each distinct filter once per
view, avoiding repetition across several rule sources of one fluid.

Compilation and 32 Java tests pass. IntelliJ completes without a changed-block
finding. The combined runner's PMD root check still skips the nested wrapper,
while supplemental PMD completes with the actual classpath and no processing
errors. The public preservation characterization and all 211 Python tests pass,
as do 78 GUI tests, typecheck and the candidate build.

One isolated capture/import takes 192.445 seconds and publishes snapshot
09961ff8-0679-4db1-83e8-c749753fd96a. All 22 underground-rule environments retain
the raw [-1,1] list with exact API/scope. All 48 underground-fluid source
declarations match after resolving typed output references. Across 25228 source
bodies, 25219 match raw and nine differ only in snapshot-local IDs of four exact
fluid identities. No cause for those ID differences is asserted.

The actual old/new acquisition sample has min amount 0 and stays unresolved
with false inventory-proof flags. Metadata does not strengthen its category.
All 23 protected files, compared databases and producer hashes remain unchanged.
Ten runtime configuration/script digests differ, so no identical-configuration
cohort claim follows. Field-read authority remains source-backed, without an
independent live-array observer. Native null/empty branches are unobserved.
Evidence is in underground-blacklist-runtime-acceptance/REPORT.md.

### Prefer retained processing alternatives before Space Mining acquisition

The saved Scheelite result already contains its three-step chemical path at
index 2. Its primary path instead enters Space Mining through manufactured
operation requirements. Exact source and actual JAR evidence verifies the narrow
acquisition role for GT `.221`, `.223` and `.225`. Both complete source files and
the two corresponding top-level class files are byte-identical across these
releases. This establishes output origin, not atom correspondence or per-operation
quantities. All requirements, cofeeds and outputs remain in the native records.

The existing Dataset presentation owner now composes its Cutter preference with
a higher-priority stable partition of retained acquisition paths. Unknown cohorts
remain neutral. There is one final permutation for paths, primary route, branch
indices and path details. Search guidance, limits, candidate admission and the
returned path pool remain unchanged. The shared native-model identity seam is
independent of whether operation accounting is currently supported.

Every material result discloses presentation visits, including neutral results.
These visits are separate from discovery counters. GUI notices require an actual
reorder and identify the preference that changed it. Public regressions cover
exact cohorts, unknown evidence, direct and sole acquisition requests, native
records, Cutter composition and index alignment. All 215 Python tests, 84 GUI
tests, typecheck and the isolated candidate build pass.

One twelve-request acceptance against the frozen v6 index passes. All 60 paths,
full native records, requirement classes and search counters remain exact, with
the declared aligned permutation. Scheelite becomes [1,2,3,4,5,6,7,0]. The eleven
other saved responses retain their order. Chemistry becomes second. The new
first path is the existing two-step QFT and Tungstensteel route. This preference
cannot recover a missing route or establish the best processing chain.

Across the twelve requests, presentation visits 60 paths and 289 process
references, classifies 174 unique processes within their respective queries and
scans 323 manifest entries only for Scheelite. These are extra logical operations,
not unchanged discovery work or a measured CPU speedup. All 29 protected files
and approved source hashes remain unchanged. Existing native matcher proofs are
reused through exact bodies, paths and immutable stores, without new game calls.

Two harness assertions initially confused the old Cutter permutation basis and
its eligible subset with the saved response order and all retained paths. Both
failures and corrections remain recorded. Offline comparisons establish exact
production equality for those cases. Their responses were reused, with exactly
twelve total trace calls and no reruns. Evidence and the frozen protocol are in
acquisition-route-presentation/. The live app and MCP still use their earlier
code and data.

### Check declared catalog gaps separately from partial semantics

The latest isolated snapshot `09961ff8-0679-4db1-83e8-c749753fd96a` has 202
coverage records: six complete, 190 partial and six unsupported. A partial
registered RecipeMap reports captured entries with unresolved runtime semantics.
Its declared record count is not a count of missing recipes.

The explicit unsupported rows identify EnderIO grinding-ball variants and
vanilla furnace mode, Forestry factories beyond Centrifuge, Botania recipes
beyond Mana Infusion, remaining mod catalogs and remaining acquisition domains.
Their zero declared records do not establish the size of the missing catalogs.
The next bounded source check concerns Forestry Squeezer, with actual manifest
cohort Forestry `4.11.39` and JAR SHA256
`f3cacea1f523a5b94bf3f7bcc811c49dd5224d5024ac3d98fb6ac3b26a51547f`.
This is a coverage feasibility gate, without a new capture or adapter yet.

### Reaction-local exact Element evidence adds little on retained paths

Material search already compares the selected input and output of each recipe
transition, using native material names and recursive components. A separate
saved-body gate checks whether the existing pure chemistry owner can provide
complete native Element vectors for the same transitions, without replacing
whole-item accounting with relative primary composition.

Of 289 transition occurrences across the twelve saved responses, 147 have both
vectors and 142 remain unknown. There are 55 eligible selected resources and
52 unknown resources. No known result contradicts existing material comparisons.
Four unique pairs, five occurrences, resolve previously unknown continuity
because equivalent native Water candidates yield one vector. The sole disjoint
pair is Water to Titanium Plate through a Cutter, with its full Titanium Block
cofeed retained. The existing presentation convention already addresses it.

This gate supports neither a new search pilot nor pruning. It concerns retained
paths, not unseen frontiers, and Element intersection is not atom mapping.
No Dataset, SQL, trace, formula parsing, source edit or index rebuild occurred.
Exact vectors and unknown reasons are in reaction-local-element-feasibility/.

### Capture two missing native catalogs without inventing execution

Exact source and actual JAR checks verify Forestry Squeezer 4.11.39 and Botania
Runic Altar 1.13.39-GTNH. Relevant Botania classes also match compiled .38
classes. Existing ForestryCapture and BotaniaCapture owners now retain these
catalogs. Static Squeezer input declarations remain native_unknown because
initial selection, cached selection and removal differ. Generated containers
are separate templates. Runic material projections include controller-supplied
Livingrock and retained literal runes. Conditional returns and custom classes
remain unresolved. HeadRecipe is not probed through its stateful matcher or
dynamic output getter. Actual runtime version replaces the old hardcoded Mana
Infusion version label, without changing its projection.

Compile and all 34 Java tests pass. The two new safety tests exercise passive
declaration order/runtime facts and refusal to call unsafe subclass overrides,
including HeadRecipe. They were added with implementation, without a claimed
preimplementation RED run. Source collectors still lack an isolated FML test
seam for full emitted records, so no test-only hook or mirror was added.
IntelliJ completes with 61 advisories. The combined runner skips PMD at its
nested-wrapper root check. Supplemental PMD analyzes all three changed owners
with the actual 119-entry classpath, no processing/configuration errors and 60
advisories. Concrete source review retains complexity/native-literal/style
findings and rejects an unreachable null warning without redundant guards.

One capture/import completes in 185.49 seconds. New snapshot
6af4b2b0-0c98-487e-94cd-4f8101c6bd1c has 260154 processes, 118721 resources and
15.19 MiB across six compressed streams. Its 329 additional records are 280
exact Squeezer declarations and 49 Runic entries. All Squeezer execution and
physics fields stay null. There are two separately counted container templates.
Runic has 48 represented exact-base projections and one diagnostic HeadRecipe.
Actual JARs match Loader and source authority. No mixed-role or other unknown
subclass branch is runtime-observed. The preferred multi-input Squeezer with
remnant sample is absent, so the observed one-input case is used with that limit.

Seven Dataset reads and eight guaranteed/expected ledger calls pass. Informational
Squeezer and HeadRecipe records receive no stock credit. Imported records retain
their full bodies. All 78 protected files, four absence gates, the complete UI
directory and 46 frozen inputs remain unchanged. No service or active snapshot
is switched. Existing native observer limitations still apply.

The prior comparison proves 129999 strict complete-body pairs with explicit
typed-reference mappings and full provenance. All 165 Mana Infusion records
match after only the two documented version corrections. Centrifuge's 154
records have explicit registry-order changes, and 32 also have output-order and
native-output-index permutations. Complete output elements retain their amounts,
identities, thresholds and probabilities. Raw order is preserved, because first
match and RNG draw assignment can depend on it. No execution equivalence follows.
Nine config/script digests differ. Remaining unmatched prior records stay
unproven. No global recipe-equality claim or broad provenance deletion is made.

Source contracts, audit and runtime evidence are in forestry-squeezer-coverage/,
botania-runic-altar-coverage/, native-catalog-adapters-audit/ and
native-catalog-adapters-acceptance/. There is no independent live catalog
observer, controller execution proof or live GUI/MCP acceptance in this phase.

### Further catalogs expose a declaration-query gap

Source-only gates verify passive Carpenter and Petal Apothecary catalogs in the
same actual Forestry 4.11.39 and Botania 1.13.39-GTNH JARs. Neither collector is
implemented in this phase. Carpenter exposes its pattern, box, fluid, work time
and full main output, but consumes the selected phantom-grid stock with ore
equivalence and container callbacks. Petal consumes its ingredients, including
runes, plus a seed selected by the native unlocalized-name predicate. Water is
controller state with several refill paths. Neither transaction can honestly be
replaced by one fixed generic container or seed group. Full execution models
remain deferred. Source evidence is in forestry-carpenter-coverage/ and
botania-petal-apothecary-coverage/.

The existing input query excludes native_unknown anchors from known matches.
This is correct for acceptance, but those concrete declarations are not
discoverable by ingredient lookup. Native slots retained only in
conditions.native_inputs are also outside its relationship index. The existing
public unknown-matcher regression confirms the distinction without a native
query. Family/output lookup and direct inspection still expose the records.

The accepted design deepens find_processes with input_mode matched/declared,
preserving the matched default. Declared mode finds exact literal resource-ID
references in two supported slot locations, without group or predicate
expansion. It preserves raw items and reports matching_evaluated false under
input_lookup, omitting native-matching counters. Existing indexed anchors and
fixed guarded SQLite JSON1 traversal suffice without a schema change or
reimport. Count and page may each scan JSON-only declarations, so performance
must be measured before a speed claim. The implementation passes 220 Python
tests, 85 GUI tests, typecheck and a private build. Design and bounded acceptance
evidence are in declared-input-lookup/.

One related reachable diagnostic bug is included: named dynamic_inputs reasons
with cleared top-level slots, as in the observed HeadRecipe, evade the old exact
unresolved marker test. The fix corrects uncertainty counts without making
those recipes executable or changing known match results.

Exactly five read-only public requests on snapshot
6af4b2b0-0c98-487e-94cd-4f8101c6bd1c preserve full stored item bodies and both
protected database hashes. Squeezer input r46252 has zero known matches with
280 unresolved processes in family scope. Declared mode finds its p259622 in
1.203 seconds with the family filter and four references in 1.328 seconds
without it. The latter count and page statements take 0.644 and 0.681 seconds.
EXPLAIN confirms a collection scan with indexed top-level anchor membership
and correlated JSON virtual-table walks. These are single instrumented reads,
not a warmed benchmark or evidence of index-only lookup. Native-input-only
references remain fixture-tested rather than observed mixed-rune records.

The Runic family request reports one unresolved HeadRecipe. Adding a fixed
output filter excludes that diagnostic record and correctly reports zero
unresolved processes within the narrower scope. No extra public query, rebuild,
capture, native matcher call or live UI/MCP activation occurred.

### Carpenter and Petal declarations become searchable

The existing Forestry and Botania capture owners now preserve these passive
catalogs under the exact source/JAR contracts described above. Carpenter keeps
ordered pattern cells, alternatives, raw stack counts, packaging, fluid and fixed
main output. Petal keeps ingredient occurrences, consumed runes, seed predicate
and component-admission precedence, plus consumed water state and separate refill
paths. Both retain native_inputs declarations with empty interpreted inputs,
null executability and null canonical physics. No callback-dependent transaction
or universal container debit is invented.

Final Java compile and all 39 tests pass. A hostless FluidStack fixture initially
failed on Forge registry initialization. The fixture-only correction removes
that construction and its fluid assertions, leaving actual fluid serialization
to runtime acceptance. A later source cross-check fixes the Carpenter catalog
error status from invalid failed to valid error. Historical IntelliJ and PMD
results remain separate from this literal correction's focused review and final
Java gate. IntelliJ has 67 advisories. The combined PMD component is skipped by
the nested-root check, while supplemental PMD has 78 advisories and zero
processing/configuration errors. No metric-only refactor or suppression was added.

One capture/import takes 185.501 seconds and produces snapshot
8ece9e9c-0711-4658-b3d4-fe5a0137682f. It adds 434 Carpenter and 45 Petal records.
The snapshot has 260633 processes and 118977 resources. Six compressed streams
total 15994139 bytes. Eight public reads and eight ledger checks pass. Actual
native_inputs-only references are discoverable through declared input mode,
with unchanged raw items. Matched family queries return zero and report
uncertainty for 434 and 45 records. Both guaranteed and expected accounting
refuse these incomplete operations without crediting stock.

The consumer harness first stopped before any public/ledger call because it
incorrectly expected the fresh sidecar to be absent. The normal importer creates
it. The corrected harness preserves both new hashes and uses only the original
eight/eight calls once. No capture, import or accepted request was repeated.
All 87 protected files, four absence gates, whole active UI and frozen inputs
remain unchanged. Only the exporter mod differs, but nine config/script digests
also differ. Prior family counts agree. Bounded Mana/Runic/Head bodies agree
after explicit PID remapping. Same-index Centrifuge/Squeezer samples differ and
do not establish cross-run identity or equality. There is no global pairing,
independent live catalog observer, controller-execution proof or live UI/MCP
activation. Evidence is in carpenter-petal-audit/ and carpenter-petal-acceptance/.

### Further Forestry source gates

Fermenter is deferred. Its output declaration supplies a fluid type without a
fixed amount. Subcycle rounding, persistent fuel capacity, cached resource
modifiers and full final-cycle fluid drain prevent a simple fixed operation.
The current numeric-output format and output lookup cannot represent that type
declaration usefully without a separate design. Do not fill the gap with an
invented amount, a source record or a recipe/fuel Cartesian product.

Still is a feasible declaration-only candidate. Its actual input/output
FluidStack templates have numeric amounts and typed NBT. The controller scales
them by cycles, buffers input and checks output space using only the unscaled
template. It ignores the final accepted fill amount. Native templates can be
preserved with explicit per-unit scope, unknown chance and null execution,
without claiming a guaranteed batch or canonical energy. Neither family is
implemented in this source-gate phase. Exact evidence is in
forestry-fermenter-coverage/ and forestry-still-coverage/.
