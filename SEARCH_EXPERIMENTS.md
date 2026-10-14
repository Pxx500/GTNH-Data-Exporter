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
