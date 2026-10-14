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
are needed. The separate typed-operation experiment remains in progress.

HTTP and the actual connected MCP session both return eight Volcanus paths,
10/15 represented branch jobs and 1,113 admissions, with `path_limit` remaining
explicit. Fresh LV casing, hull and double-plate HTTP requests still find their
paths and represent 9/9, 9/9 and 2/2 jobs without search limits. The current GUI
server is running the cursor implementation. These checks do not establish
complete planning or a finished semantic map.
