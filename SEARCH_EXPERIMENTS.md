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
1,357 admissions. A Water-to-Hydrogen HTTP check still ranks direct electrolysis
first. It returns eight paths and swaps one alternative under the new ordering,
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
Water-to-Hydrogen paths, 713 admissions and direct-electrolysis best recipe
`p138456`. Those values agree with the independent fresh HTTP check. This
establishes that the integration serves the new policy through a fresh loaded
connection. It does not establish that root's earlier connection refreshed.

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
