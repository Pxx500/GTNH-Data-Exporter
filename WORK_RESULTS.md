# Prepared search and usability results

The accepted work is implemented on branch `automatic-export`. The GUI at
`http://127.0.0.1:8000/` serves fresh snapshot
`779ea030-ae9c-40ea-8854-99a176f7cc42`. The original snapshot remains intact.

## More useful routes with less repeated work

Dataset now prepares a rebuildable SQLite flow sidecar after import. Existing
imports can explicitly rebuild it offline. The sidecar records shared matching
predicates and a factor graph rather than ingredient combinations or every
possible chain. Its snapshot identity and analysis version are checked before
material search. No captured recipe facts are replaced by heuristic facts.

The GUI defaults to Main material flow. Native material and component hints,
remaining distance and target ingredient branches guide exploration before its
budget runs out. Steel construction routes appear without a forced waypoint.
Byproduct routes remain available. Shortest and diverse retain their meanings.
HTTP, CLI and MCP callers request material selection explicitly.

| Original snapshot, cold Dataset handle | Baseline | Material policy |
| --- | ---: | ---: |
| Iron Dust to LV casing | 8.70 s | 1.01 s |
| Iron Dust to LV hull | 7.00 s | 3.83 s |
| Iron Dust to unrestricted hull | 10.77 s | 3.46 s |
| Crushed Iron Ore to MV double plate | 8.70 s | 2.22 s |
| Iron Dust to unrestricted Volcanus | 12.20 s | 10.51 s |

All material runs in the 24-case comparison avoided search-budget exhaustion.
Unrestricted Volcanus remains a larger query. Cold means a fresh Dataset handle,
with the operating system's filesystem cache retained. Peak working set for the
separate unrestricted hull probe fell from 157.1 MB to 102.7 MB. Preparation is
an additional offline cost. The final fresh version 3 sidecar took 16.94 seconds
and occupies 97,185,792 bytes.

SCC islands were rejected as the main abstraction. Most accepted endpoints sit
inside one component containing 24,494 resources and 118,688 processes. Removing
Water, Hydrogen and Oxygen barely changes it. A naive portal closure would have
94.57 million candidate pairs. The source-depth hypothesis was also tested with
AND-max and AND-sum potentials. Hydrogen can have depth one while steel branches
are deeper, so that scalar does not resolve the user's material-flow problem.
It remains an experimental diagnostic and is not a production ranking or an
automatic planning boundary. See [FLOW_SEARCH_RESEARCH.md](FLOW_SEARCH_RESEARCH.md).

The final fresh-snapshot unrestricted Volcanus check took 0.437 seconds and
returned six paths with 21 complete recipe records. Its first path passes through
steel and tungstensteel into Robot Arm IV. The new crafting interpretation exposes
15 target ingredient branch jobs. This bounded request represents eight and
reports `search_state_limit` at 20,000 queued states. Seven remain undiscovered.
It is not a like-for-like replacement for the old-snapshot timing or evidence
that every branch has been found. The exact request is preserved in
`exports/flow-search-20261014/final-fresh-volcanus.json`.

## Native coverage and corrected crafting certainty

EBF was already captured: 2,033 declarations, including five steel outputs.
The primitive blast furnace has 418 declarations, including 46 steel outputs.
The selected 70-recipe comparison agrees with saved NEI presentation. EU,
duration, voltage and heat use matching native source and captured data because
those NEI views do not independently expose every parameter.

A real coverage gap prevented ordinary GT shaped recipes from establishing
paths. Capture now resolves 11,822 static outputs after checking the native
recipe class, NBT, enchantment, electric-item and item-update behavior.
Unsupported transformations remain unresolved. Verified crafting grids carry
an explicit voltage-not-applicable marker. Null EU is preserved and does not
become free energy. Tool damage, breakage and container returns remain unknown.

| Fresh snapshot, maximum LV and unknown tiers excluded | Material query |
| --- | ---: |
| Crushed Iron Ore to Double Iron Plate | 0.620 s |
| Iron Dust to LV Machine Casing | 0.648 s |
| Iron Dust to LV Machine Hull | 0.734 s |

The three cases return paths without search limits. Casing includes steel ingot
and plate. Hull returns seven paths including steel and casing branches, with
Cast Iron Plate on its first spine. Represented branch jobs are 2/2, 9/9 and 9/9.
They do not certify that every external AND ingredient is supplied.

The newly available crafting routes exposed a 100-second query regression.
Profiling found repeated global ingredient scans during result assembly.
A correlated EXISTS query reuses the existing process-input index. The same
profile fell from 100.197 seconds to 0.946 seconds. Its complete domain result
matches after excluding runtime distance telemetry.

The pinned recapture keeps 323 mods, with only the exporter JAR hash changed.
All resource identities, 25,228 sources and 119 environments match under the
documented identity normalization. Recipe I/O and energy signatures match after
the report's explicit interpretation and ordering normalization. A stricter
ordered comparison retains 224 differences. Seven of ten config/cache hash
changes are proven serialization-only. Three remain unproven.

Both mapped NEI comparisons have 78,389 matches, zero differences and zero
missing entries. Both references retain 15 capture failures. This is scoped
validation and does not establish complete pack coverage. Details are in
[MACHINE_COVERAGE.md](MACHINE_COVERAGE.md) and
[CRAFTING_OUTPUT_RESEARCH.md](CRAFTING_OUTPUT_RESEARCH.md).

## Origin evidence and agent output

Origin analysis distinguishes generated ore blocks, native mining drops,
stochastic candidates, direct configured sources and bounded initial processing.
Recycling does not remove world origin. Renewable supply remains separate and
unknown. User-selected basics remain explicit planning assumptions.

GT Iron Dust is preferred over its noncanonical IC2 variant. Routine Captured
producer badges are hidden. Relevant source and unification warnings remain,
with inspectable evidence. Missing acquisition evidence is not absolute proof
of unobtainability. Source-summary query improvements reduce the measured broad
1,000-resource scan from about 49 seconds to 0.38 seconds. A bounded per-Dataset
cache retains complete summaries. Budget-limited inference is not cached.
See [SOURCE_PROVENANCE.md](SOURCE_PROVENANCE.md).

MCP exposes 25 tools and a packaged workflow guide. Traces default to compact
presentation. Every selected recipe, declared choice and actual path is kept.
Omitted expanded candidates have explicit counts, predicates and aggregate
boundary evidence. Full expansion remains available with `view="full"`.
The native six-recipe double-plate response falls from 2,161,648 bytes to 96,046
bytes, a 95.56% reduction, without changing the selected recipes or paths.
CLI JSON now escapes Unicode for Windows consoles while preserving parsed values.

The saved Codex MCP configuration points to the fresh database. A new official
SDK client launched with that exact configuration verifies the guide, all 25
tools, compact default and full mode. HTTP and CLI return the same native paths
and recipes. The existing MCP connection in this ongoing conversation still
returns the old snapshot. A new-client test does not establish reconnection of
that session. No Codex processes were killed to force it.

## GUI behavior and verification

Trace and Analysis retain their mounted state after first use. Explicit Library
navigation and return preserve results, filters, camera and node positions.
Ingredient inspection stays beside the board and can load missing identities
and production recipes. New-query actions are separate from inspection.

Close is outside the scrolling inspector body. The narrow layout uses a fixed
drawer. Native scroll checks at 754 px and 1280 px kept Close at exactly the same
screen position while body scroll changed. Escape closes the panel and restores
focus to its opener. Amounts include units, exceptional chances use percentages,
and raw records live in collapsed technical sections with Copy JSON.

Ordinary wheel input scrolls the page without changing the camera. Ctrl+wheel
and pinch zoom are covered by GUI interaction tests, with native zoom controls
also checked. The browser automation interface did not provide an independent
native Ctrl+wheel proof.

Whole-board export retains all tiles, links and labels independently of camera
zoom. The final fresh board generates a 3976 by 7902 PNG and a 1988 by 3951 SVG
with 16 recipe tiles, 17 edges and 17 labels. Prior native zoom comparisons
produced byte-identical PNGs. The final camera remained unchanged during export.
SVG embeds HTML and targets modern browsers. The browser-generated links and
their bytes were verified. CUA could not establish a physical download event,
so saving through the in-app browser's download mechanism remains unverified.
The generated files are preserved locally for direct use.

Verification passed all 162 Python tests after the final CLI fix, the focused
20-test transport and guide suite, all 63 GUI tests, TypeScript checking,
production bundling and all 30 exporter tests. Real PMD analysis ran with no
processing errors. Seven focused complexity findings were retained with reasons.
A consolidated review and focused re-review closed the four confirmed issues
and the voltage-marker UI parity issue. The compact formatter received a scoped
review with no additional findings. The Python wheel builds with standard build
isolation and includes the current workflow guide and prepared-index module.

Evidence stays under Git-excluded `exports/`. Source, tests, guides and these
reports are committed locally. No pull request or remote publication was made.
