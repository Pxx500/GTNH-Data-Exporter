# Search queue research

Research date: 2026-10-14. This report supplements `FLOW_SEARCH_RESEARCH.md`.
It records primary research, bounded experiments, and the verified queue change.
Raw fetched papers, parsed text, implementation excerpts, metadata, and failures
are under `exports/search-research-20261014/queue/`. Git excludes `exports/`.

## Recommendation

The lazy successor cursor is implemented and verified at the existing budgets.
The final section records its measured coverage gain and production checks.
An early dominance filter remains an experiment that must prove continuation
legality. Admission-aware scheduling showed no additional coverage benefit in
the measured matrix. The existing material objective, complete recipe records,
matching predicates, and search limits remain intact. The papers alone do not
establish a GTNH performance result.

The native reference is Iron Dust `r5090` to Volcanus `r41034`, unrestricted,
depth 12, `max_processes=300`, `max_paths=8`, and six extra steps. Its supplied
measurement is 0.437 seconds, six paths, 21 recipes, eight of 15 branch jobs,
512 examined states, 20,000 cumulative queued states, peak frontier 6,334,
9,992 expansion work, and 1,862 prepared processes. These counters identify an
admission limit. They do not establish why admissions were consumed.

The engine owner reports that the current implementation already has
score/depth Pareto pruning after heap removal, cycle checks for resource and
process history, and round-robin job advances of at most 64 removals. Its
cumulative queue counter also includes admissions into eventually abandoned
heaps and the reference-hop pass. These observations came from the owner's
graph-backed inspection. The later experiment and production work below add
independent code inspection and native validation. Avoid describing the engine as
lacking dominance pruning or branch scheduling.

The owner subsequently supplied read-only instrumentation for the fresh native
Volcanus query. It observed 20,000 heap admissions and 512 removals, with 302
exact duplicate tuple admissions. Score/depth comparisons keyed only by
resource and waypoint mask flagged 13,005 admissions. Comparisons requiring
identical resource and process ancestor sets flagged only 302. No pruning was
performed and outcomes stayed identical. Evidence is
`exports/search-research-20261014/queue-probe.json`. The 13,005 count is an
optimistic diagnostic that ignores continuation legality. It is not a safe
savings estimate. Subset-history dominance was not measured by this probe.
These results strengthen the priority of lazy admissions over assuming a large
easy duplicate win.

The owner's additional inspection identifies a concrete duplicate source:
predecessor rows distinguish input slots, while the selected spine transition
does not use that slot field. Repeated input identities across crafting slots
can therefore produce an identical heap tuple. Deduplicating identical spine
successors is a narrow candidate for that observed waste. It must preserve
target-slot jobs and the complete native AND recipe. It does not authorize
merging resource identities or treating repeated consumed slots as optional.

## Five new primary papers

### Enhanced Partial Expansion A*, May 2014

Goldenberg, Felner, Stern, Sharon, Sturtevant, Holte, and Schaeffer distinguish
expanded nodes from generated surplus nodes. PEA* retains the parent with the
best deferred child's value. EPEA* uses a domain and heuristic-specific operator
selection function to generate the requested cost band and find the next band
without creating every child. The main presentation assumes a consistent
heuristic. Its inconsistent-heuristic discussion identifies a tradeoff with
information that could otherwise improve estimates. The operator-selection
function is a prerequisite, not a free property of a high-branching domain.
[Paper, JAIR 50, 141–187](https://pdfs.semanticscholar.org/5090/8dfdaa80b180f24c9f809fb2e3491a94a8d4.pdf),
[author institution metadata and May 2014 date](https://cris.biu.ac.il/en/publications/enhanced-partial-expansion-a/)

For GTNH, prepared producer/input summaries can support resumable successor
lists. A sorted list built eagerly saves queue admissions and state allocations,
but not the descriptor scans or sorting work. An on-demand cursor only saves
generation work if it can identify the next promising descriptors cheaply.
Material hints are ordering preferences. Their presence does not establish
EPEA*'s admissible cost bands or optimality assumptions.

### A Simple and Fast Bi-Objective Search Algorithm, 2020-06-01

Hernández Ulloa, Yeoh, Baier, Zhang, Suazo, and Koenig define a finite directed
graph with two nonnegative, additive edge costs. BOA* exploits two objectives,
consistent heuristics, and lexicographic queue ordering to reduce dominance
checks to constant time. It combines eager checks against settled information
with lazy checks after removal. It computes cost-unique Pareto solutions,
not every structurally distinct route with an equal cost vector. Those are
substantive contract differences for a developer search tool.
[Publisher title, abstract, and publication date](https://ojs.aaai.org/index.php/ICAPS/article/view/6655),
[parsed full paper](https://ojs.aaai.org/index.php/ICAPS/article/download/6655/6509/9884)

This supports a precise distinction between checking against settled labels
before admission and maintaining an antichain over all pending labels. The latter
may avoid admissions but has comparison costs. BOA* is not evidence that eager
checks are always faster. A GTNH label must retain every fact that changes legal
continuations. Resource identity alone is insufficient when cycle exclusions or
waypoints depend on path history.

### Bi-Objective Search with Bi-Directional A*, ESA 2021

Ahmadi, Tack, Harabor, and Kilby extend BOA* to opposite search directions and
objective orders. The model is still a finite directed graph with two
nonnegative additive costs and consistent, admissible vector heuristics. The
paper explicitly identifies pending dominated nodes as a cost of lazy checking.
It obtains lower and upper bounds through preliminary searches and uses valid
solution bounds to restrict those searches. Reported road-network speedups do
not establish savings in recipe dependency search.
[Author-hosted full paper, DOI 10.4230/LIPIcs.ESA.2021.3](https://harabor.net/data/papers/athk-esa21-boba.pdf)

Bidirectional joins in GTNH must agree on concrete identity, waypoint state,
legal resource/process histories, and chosen matching semantics. Meeting at a
resource is not proof of an AND recipe's other ingredients or required tools.
Preparation and join work must be charged to the same budgets. Copying the full
algorithm is a larger experiment than using its narrower observation about
pending dominance and bounded preparation.

### Recursive Best-First Search with Bounded Overhead, AAAI 2015

Hatem, Kiesel, and Ruml show that ordinary RBFS can incur unpredictable
regeneration overhead, particularly with many distinct evaluation values.
RBFSCR uses subtree evaluation histograms and liberal thresholds, with
branch-and-bound checks against incumbents. Its regeneration bound assumes
histograms accurately reflect subtree distributions without precision loss and
contain enough counts to select thresholds. Those assumptions are stronger
than retaining one best score per resource. Linear-space search still retains
path and sibling information.
[Author-hosted full paper](https://www.cs.unh.edu/~ruml/papers/rbfscr-aaai-15.pdf)

It is useful evidence against treating frontier-memory reduction as equivalent
to coverage improvement. Regenerated children consume work again. No adopted
histogram model or measurement currently supports the paper's overhead guarantee
for GTNH's material scores and constrained histories. Defer replacing the heap
with RBFS until evidence shows resident memory is the limiting factor.

### Recursive Best-First AND/OR Search for Optimization in Graphical Models, UAI 2014

Kishimoto and Marinescu introduce RBFAOO with context-keyed caching, local
thresholds, and controlled overestimation to reduce re-expansion. The solution
tree includes every child of an AND node and one child of an OR node. Their
completeness theorem assumes a finite DAG produced from a graphical model's
pseudo tree, plus preservation of values for the current path and siblings.
The context key summarizes an independent subproblem's conditioning variables.
It is not simply the displayed resource name.
[Official UAI proceedings full paper](https://auai.org/uai2014/proceedings/individuals/110.pdf)

This gives a useful context-equivalence principle but no direct correctness
proof for cyclic recipe graphs, shared multi-output processes, or reusable
tools. Unrolling bounded recipe paths can produce an acyclic search tree, but
merging them back by resource requires a separate legality argument. AND-sum
costs must not double-count shared process outputs when the claimed objective
is distinct recipe use.

## Primary implementations checked

The BOA* author's C implementation is an explicit-graph implementation. At
commit `4dd21e6eb54ba7b6586164f8334cc4b65ac8e0a9`, `boastar()` checks
`gmin` after `popheap()` and also checks the child's cost against settled `gmin`
before allocating and inserting it. It does not perform a general comparison
against every pending label. The code uses a packed numeric key for its two
costs. That representation should not be copied without checking range and
ordering semantics. The license is MIT with copyright 2021.
[Source](https://github.com/jorgebaier/BOAstar/blob/4dd21e6eb54ba7b6586164f8334cc4b65ac8e0a9/src/boastar.c),
[README](https://github.com/jorgebaier/BOAstar/blob/4dd21e6eb54ba7b6586164f8334cc4b65ac8e0a9/README.md),
[license](https://github.com/jorgebaier/BOAstar/blob/4dd21e6eb54ba7b6586164f8334cc4b65ac8e0a9/LICENSE.md)

Moving AI Lab's HOG2 at commit
`af9d42d06827e5bd96d093c17e4d98b5e4f99e79` contains an EPEA* header by
Nathan Sturtevant. `DoSingleSearchStep()` requests `GetNextSuccessor`, retains
the parent's `special` cursor, changes its queue key while more moves remain,
and closes it when exhausted. This is concrete evidence for a resumable parent
protocol. It is not a ready recipe-search library. The repository's license
file says MIT, but this exact source header says GPL version 2 or later. Code
reuse needs that conflict resolved. Independently implementing the published
algorithm avoids relying on an unverified permissive interpretation.
[Implementation](https://github.com/MovingAILab/hog2/blob/af9d42d06827e5bd96d093c17e4d98b5e4f99e79/generic/EPEAStar.h),
[repository license](https://github.com/MovingAILab/hog2/blob/af9d42d06827e5bd96d093c17e4d98b5e4f99e79/LICENSE.txt)

For a Python experiment, ordinary `heapq`, tuples, immutable sets, and existing
prepared arrays suffice. Neither checked implementation justifies introducing
a foreign-language runtime or a new dependency.

## Narrow experiments at the existing limits

### 1. Resumable, ordered successor admissions

Retain a parent plus a cursor over its eligible recipe/input successors. Admit
one successor or a small priority band, then requeue the cursor at the best
deferred child's exact priority or a proven lower bound. Use deterministic
identity tie-breaking. Keep all successors reachable through the cursor until
ordinary filters, depth, or the existing budget terminate the search. Do not
retain only a fixed top-N child list.

An exact ordering can reproduce eager best-first order on an unbounded finite
path-state graph if the cursor always advertises the best deferred key. A
cheaper approximate material ordering is a heuristic and must say so. Sorting
every successor before yielding the first is a useful first ablation, but it
cannot be reported as avoided successor scanning.

Hypothesis: under the same 20,000-admission limit, lazy materialization produces
more represented branch jobs or fewer wasted admissions at unchanged coverage,
without worsening the first material route. Record descriptor scans, successor
allocations, cursor admissions, cursor resumes, accepted paths, branch coverage,
and work remaining when a job completes. A cursor counts as a queue admission.
Deferred descriptor lists and resumptions remain visible in memory and work
accounting. This prevents a renamed queue entry from appearing as free work.

Falsify the proposal if priority equivalence fails on bounded exhaustive cases,
if scans or cursor churn erase the savings, or if coverage and material ordering
do not improve in the native case and existing casing, hull, and double-plate
regressions.

### 2. Early, continuation-safe dominance

Keep a per-job admitted-label antichain before heap insertion, while retaining
stale checks at removal. Begin with exact context equivalence. A candidate can
be rejected only if another retained label can reproduce every legal suffix
with no worse relevant accumulated cost and remaining depth. Do not interpret
equal endpoint IDs as equivalent states.

For the present simple-spine cycle policy, a sufficient comparison is the same
concrete resource, job, waypoint progress, and any other history-dependent
state, with no greater score or used depth, plus a subset of visited resource
IDs and a subset of visited process IDs. The subset rule works because fewer
forbidden IDs permit at least the suffixes permitted by the other label. This
argument is conditional on future cost increments and matching legality being
independent of discarded history. If continuity score depends on earlier
materials or output roles, that context also belongs in the comparison.

Start with equal histories if subset comparisons are too costly. Retain a
witness or a complete continuation representation for the dominating label.
Don't delete the only witness and then use its old label to prune new work.
Cost-unique dominance also assumes the accepted result contract needs a
representative per branch. It can discard equal-cost alternative chains that
would matter to an all-paths contract.

Hypothesis: a measured portion of current admissions is provably dominated
before insertion, and removing them improves branch coverage at the same
limits. Report pre-admission rejection counts, comparisons, antichain sizes,
stale removals, and full-history checks. Falsify if the safety predicate rejects
a valid winning route on exhaustive cycle/waypoint/NBT/multi-output cases, or
if comparisons increase latency without coverage or relevance benefit.

### 3. Admission-aware branch scheduling

The existing 64-removal round robin does not necessarily bound admissions made
by one high-fanout removal. Give every unresolved target branch a small turn
with an admission quantum, then reuse remaining turns for the best pending
material candidates. A resumable parent lets a turn stop without truncating its
successor set. Keep the same global admission limit and path limit.

This is an application-specific coverage heuristic, not a theorem from BOA*
or RBFAOO. It may improve coverage while delaying the globally best material
route. Preserve within-job priorities and expose the tradeoff through the
observed first-route score and branch-by-branch admission trace.

Typed material/form transformation guidance could order branch turns or cursor
successors within the same budget. Treat it as a semantic preference with
explicit provenance. It must not collapse concrete identities, change matching
legality, or silently discard byproduct routes. The separate semantic research
owns the choice of those transformations. This report only specifies where such
guidance can enter queue scheduling.

Hypothesis: the native query starts useful work on more than eight of 15 branch
jobs before consuming 20,000 admissions and preserves the best material spine
found by the baseline. With `max_paths=8`, no experiment can promise 15 returned
branch representatives. Compare attempted jobs, solved jobs, returned branch
representatives, and reasons separately. Falsify if started-job coverage rises
without solved/returned coverage or if low-value branches displace useful paths.

## Bounds, constraints, and deferred directions

The source-relaxed distance already addresses a useful structural lower bound.
An optional waypoint-aware relaxed bound can take the maximum of minimum recipe
distances from the current reverse state to the source and each still-missing
waypoint. Every valid suffix must reach each waypoint, so the maximum can bound
recipe-step count if distances use the same concrete identity/filter semantics
and relax other obligations. Summing these distances is unsafe because route
segments can overlap. This is a derived proposal, not a published GTNH result.
Its preparation cost belongs in the experiment.

A learned score can reorder candidates after exact legality checks. Without
calibration proving a lower bound, it must not prune or support an optimality
claim. This research found no verified training corpus or learned model suited
to GTNH recipe identity, tool presence, and native conditions. A learned-bound
project is not the narrow first experiment requested here.

Multi-output recipes and OR alternatives remain complete recipe records even
when the selected result is a spine. Dominance must compare concrete NBT-aware
identities or exactly equivalent predicates. Tool presence remains an external
obligation unless a separate solver establishes it. Bidirectional meeting and
AND/OR values do not transform a spine into an executable inventory plan.

Memory-bounded replacement, full BOBA* joining, and full RBFAOO planning are
deferred. Their guarantees require a new state and cost contract. The three
recommended experiments instead test the admission pressure directly, without
increasing depth, process, path, or queue limits.

## Evidence quality and limitations

All five papers have substantive parsed text. The EPEA* manuscript mirror
returned HTTP 200 and 48 parsed pages, with title and May 2014 publication
metadata checked at an author institution. BOA* returned nine PDF pages through
the publisher's actual download link and a publisher date of 2020-06-01.
RBFSCR returned seven pages with matching title and 2015 copyright. RBFAOO
returned ten pages from the official 2014 proceedings path. BOBA* returned 15
pages with matching title, ESA 2021, and DOI. Parsed text sizes range from 34,383
to 128,217 characters. Implementations were read from source and pinned to
resolved commit IDs. Pinned BOA* source and license matched the initially
fetched default-branch content.

DuckDuckGo results were read through a private background CUA tab. Citations
use fetched papers and primary repositories, not search snippets. Python
`pypdf` availability was checked before PDF parsing. Context Mode HTTP requests
used bounded reads and explicit timeouts. No database, GUI, or production code
was changed.

The author-hosted Eppstein PDF failed certificate verification and its
eScholarship entry returned HTTP 403. They are discarded leads, not supporting
sources. The first BOA* HTML decode failed because the body was gzip-compressed.
Magic-byte decompression enabled the subsequent successful extraction. These
failures were reported before alternative routes and recorded in
`fetch-failures.json`. This report makes no Eppstein-specific guarantee.

The next useful evidence is cursor behavior and complete frontier-lifecycle
accounting, especially job completion leftovers and per-branch admissions.
The observed 302 safe identical-history cases leave limited room for that
specific dominance filter. A cheaper but unsafe 13,005-label approximation
must not drive a production claim. If additional counters identify a different
dominant cause, adjust the first experiment instead of claiming these papers
prove the cause.

## Confirmed experiment and production change

The isolated cursor matrix used the fresh native snapshot
`779ea030-ae9c-40ea-8854-99a176f7cc42` and the ready version 3 prepared index.
Its original search source is frozen in
`exports/search-research-20261014/queue/experiment_original_source.py`.
`experiment_replay.py` restores that source for the isolated matrix after the
production change. The original matrix and separate constituent-hint combination
remain in `experiment_result.md` and `experiment_combo_result.md`.

The experiment improved Volcanus from six paths covering eight of 15 jobs to
eight paths covering ten jobs. All six original paths and the same best route
were retained. The smaller admission-turn treatment had no additional coverage
benefit and retained more descriptors. Combining the cursor with the experimental
constituent union also reached eight paths and ten jobs, but increased the
descriptor frontier and changed two dependency spines. Only the ordinary cursor
was promoted. Material tokens, matching predicates, and index version remain
unchanged.

The production change stays inside `flow_index.find_paths`. A tagged heap entry
holds one actual child path. Removing it examines that child once, then admits
the next sibling with a charged insertion. Other successors retain compact
descriptors and shared parent histories. Sorting preserves the original child
priority and deterministic resource/process tie order. There is no beam cutoff,
new dominance rule, or identity merging. Cursors are released when exhausted,
when their branch has its representative, and after the hop-reference phase.

### Fixed-budget native verification

Each production observation used a fresh worker and Dataset handle, compact
presentation, depth 12, 300 result processes, eight paths, six extra steps,
20,000 cumulative admissions, 10,000 examined prepared processes, and 100,000
predecessor expansion work. The canonical database and prepared sidecar stayed
read-only. Single timings are indicative.

| Case | Paths, baseline → production | Represented jobs, baseline → production | Admissions, baseline → production | Production seconds |
| --- | --- | --- | --- | --- |
| Volcanus | 6 → 8 | 8/15 → 10/15 | 20,000 → 1,113 | 0.450 |
| Casing | 3 → 3 | 10/10 → 10/10 | 11,404 → 114 | 0.575 |
| Hull | 7 → 7 | 9/9 → 9/9 | 17,279 → 300 | 0.643 |
| Double plate | 4 → 4 | 5/5 → 5/5 | 10,620 → 460 | 0.547 |

Production Volcanus examines 665 child states versus the baseline's 512 and
charges the same 9,992 predecessor work. Its 1,113 admissions consist of 1,090
cursor child entries and 23 ordinary initial target entries. The 633 sibling
resumes are included in those admissions. No child is processed without removing
its heap entry. The existing literal hop-reference root is still initialized
without an admission increment, as in the baseline.

`search.partial_expansion` reports created, admitted, resumed, removed, and
released cursors, candidate validations, sorted candidates, retained/deferred
candidate counts and their peaks, and pending cursor entries. These distinguish
small heap occupancy from the still-retained descriptor frontier. Production
Volcanus has a peak of 7,977 deferred descriptors. Its 27,512 candidate validations
and 27,295 sorted descriptors remain visible. The unchanged predecessor-work
counter does not claim that all these operations were free. Per-operation clocks
and object-size profiling remain in the experiment rather than production.

### Regression and checks

The new public Dataset regression has 2,000 reachable same-material group
variants, a producer with 12 repeated consumed group slots, a simple second
ingredient branch, and a final recipe requiring both branches. The original
search fails with `route.status == 'incomplete'`. The cursor returns both spines
and preserves the exact 12-slot and final AND recipe records. The test asserts
public behavior and complete records, not private queue mechanics.

The regression was run red before implementation and green afterward. The
project Python environment passed 73 focused flow, route, Dataset, balance, and
transport tests. The four production native results exactly match the isolated
lazy prototype's paths and branch coverage. All baseline paths and best routes
remain present. Native recipe payloads and transitions were checked again through
the original matching predicates. Database and sidecar size and modification
metadata stayed unchanged. `git diff --check` passed.

The positive result addresses bounded branch coverage and admission pressure.
It does not certify inventory feasibility or complete semantic material flow.
The eight-path limit remains explicit. The new robot-arm branch is useful, while
another newly found computer-cube spine still passes through tool construction.
That semantic relevance question remains separate from this queue fix.
