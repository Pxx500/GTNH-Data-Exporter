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

The larger semantic-map hypothesis remains separate. Grouping a material's
forms can hide familiar recycling circuits at the overview level, but an
ingot and a plate must stay distinct recipe ports. A quotient graph may guide
search only if it preserves concrete witnesses and charges refinement work.
Its relaxed distance can become too weak when many form edges disappear.
The current diagnostic measures that loss alongside group sizes and remaining
connectivity before proposing a runtime change. The native material-and-form
alias projection is not promoted. It is separate from the coarser region idea
with multiple exact form ports and lazy internal witnesses.

Further useful candidates are operation-aware route diversity and construction
obligations. Distinct recipe IDs often describe the same material-processing
story, while a coproduct can lead into a different story. A diversity signature
should distinguish those stories without replacing exact resource IDs or
dropping ingredient branches. An assembly input already produced elsewhere
in the selected spine is still an AND obligation, not proof of a complete
build plan. These are hypotheses for measured experiments, not implemented
guarantees.
