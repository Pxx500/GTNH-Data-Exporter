# GTNH Data Exporter

Capture a versioned GregTech New Horizons dataset, then explore it with a
human UI or query it through MCP and CLI while Minecraft is closed.

The 2026-10-12 full-pack capture contains 259,781 processes, 118,717 resources
and 25,228 acquisition-source records. Its six compressed streams total
13.47 MiB. Build, launch, capture, shutdown and import took 210.53 seconds
on the local setup. This adds 1,663 native EnderIO Sag Mill baseline recipes,
11 ordinary Alloy Smelter recipes, 154 Forestry Centrifuge recipes,
152 interpreted Botania Mana Infusion recipes and 13 unresolved subclass records,
22,898 conditional normal-ore mining branches and 2,106 small-ore drop rules.
Public Sievert and Materials metadata is structured in 279 GT
records. Timings describe this captured scope and machine.
Coverage is reported per source. An export is not a declaration that every
recipe family or acquisition route in the pack has been reproduced.
Custom crafting wrappers and non-GT machine integrations remain important
coverage gaps. A pinned 2026-10-14 capture retains the same catalog counts and
resolves 11,822 static GT shaped outputs after checking their native NBT,
electric-item, enchantment and item-update behavior. Supported crafting-grid
recipes explicitly require no machine voltage. Tool returns and damage remain
unresolved. Dynamic and unsupported crafting classes remain excluded from
material paths. See [CRAFTING_OUTPUT_RESEARCH.md](CRAFTING_OUTPUT_RESEARCH.md)
for the verified scope and independent NEI comparison.
The first raw crafting catalog included 46,564 records with
unresolved inputs. The collector now captures declared inputs for the exact
GT shaped and shapeless classes. Their dynamic matching and runtime output
transformations remain explicit gaps. Small-ore rules preserve joint native
draws, while joint inventory feasibility and final tool/event delivery remain
unresolved. Grinding-ball variants and other non-GT machine families are still
incomplete or unsupported.

A previous full-pack run verified declared inputs in all 34,881 GT shaped and
2,702 GT shapeless records. That snapshot has 257,788 processes and 122,972
resources. Its compressed streams total 10.46 MiB. Capture took about nine
seconds and the full build/launch/capture/import pipeline took 153.18 seconds.
Unresolved native display output templates remain inspectable, with a visible
GUI notice, but cannot establish material paths.

## Stack

| Responsibility | Technology |
| --- | --- |
| Read the running GTNH pack | Java, Forge 1.7.10 and GTNHGradle |
| Portable authoritative snapshot | Versioned JSONL, gzip and checksummed manifest |
| Matching, lookup and process graphs | Python 3.11+ Dataset module |
| Rebuildable offline index | Standard-library SQLite and FTS5 |
| Exact bounded production-network optimization | SymPy rational linear programming |
| Human interface | React, TypeScript and Vite |
| Local GUI server | FastAPI and Uvicorn on localhost |
| Agent interface | Official Python MCP SDK over stdio, plus JSON CLI |

GUI, HTTP, CLI and MCP share the same Dataset operations. The UI does not
implement its own recipe matcher or graph discovery. No embeddings or remote
service are required. See [FORMAT.md](FORMAT.md) for the shared contract.
Potential later extensions are recorded in [FUTURE.md](FUTURE.md). The current
focus is faithful capture, offline lookup and bounded material paths.

Developer analysis now adds nominal GT recipe voltage bounds, selected-path
recycling and exact material/chemical loop ledgers. The latest snapshot has
4,695 resources with source-backed chemical accounting. Unknown composition
and resource states remain unsupported rather than inferred from names.

## Install the offline tools

On Windows with Python 3.11+ and a Vite-compatible Node installation:

```powershell
python -m venv python/.venv
python/.venv/Scripts/python.exe -m pip install -e ./python
npm --prefix ui ci
npm --prefix ui run build
```

The resulting UI runs in a normal browser. FastAPI serves the built UI and
API together, so using it does not require a separate Node server.

## Export a full pack

The local GTNHGradle installation must supply `runFullPack`. The inspected
Pxx500GTNHGradle fork provides it through the user's Gradle init script.
This command is not assumed to exist in an unmodified upstream plugin.
The build JDK must satisfy that plugin. The tested local setup uses JDK 25.

```powershell
python/.venv/Scripts/python.exe scripts/export_full_pack.py --java-home "C:/Program Files/Java/jdk-25.0.4.1"
```

The script requests an opt-in automatic capture in a new output directory,
waits for the game to exit, then validates and imports the snapshot. It
rejects a reused output directory. An old dump cannot count as a successful
new run. Captures and generated indexes stay under Git-excluded `exports/`.
The isolated client disables automatic focus-loss pausing in memory and waits
for the native CoreMod login-policy handler to finish. The gate supports the
verified CoreMod 2.9.88 protocol and observes its actual Forge handler, including
the installed ModularUI2 pipeline naming. Unsupported registration fails
before publication. Autorun requires a fresh isolated client.

To inspect an existing snapshot without launching the game:

```powershell
python/.venv/Scripts/python.exe -m gtnh_data import PATH_TO_SNAPSHOT --database exports/index.sqlite
python/.venv/Scripts/python.exe -m gtnh_data status --database exports/index.sqlite
```

## Compare against NEI

Capture an independent NEI reference from the same running pack:

```powershell
python/.venv/Scripts/python.exe scripts/export_full_pack.py --output exports/paired-capture --nei-reference --java-home "C:/Program Files/Java/jdk-25.0.4.1"
python/.venv/Scripts/python.exe scripts/compare_nei.py exports/paired-capture --report exports/paired-capture/comparison.json
```

The reference records registered handler inventories, native RecipeId API
signatures and raw handler views. It retains ingredients, result stacks and
auxiliary stacks separately. It does not render images. Both captures share
the canonical snapshot ID and pack manifest. The comparator verifies their
compressed checksums and counts before comparing source-proven projections.

The current adapters cover five exact GT recipe maps and the exact NEI
furnace handler. Other handlers remain unverified. RecipeId signatures omit
quantities and alternatives, and NEI's NBT projection loses type information.
Neither signature agreement nor display agreement proves pack-wide execution
semantics. See [FORMAT.md](FORMAT.md) for the reference contract.

The latest paired full-pack run on 2026-10-12 captured 366 handlers and 287,464
views/signatures in a 210.53-second pipeline. Independent item presentation
context retains 55,875 original GT alias queries, 231 NEI item pools and
62,131 native item projections, bound to the closed canonical streams.
The scoped five-map GT/furnace comparison finds 78,389 matching projections,
no differences and no missing matches. Of these, 28,895 belong to Fluid
Solidifier. The original four-map/furnace scope has 49,494 matches, including
the previously unsupported Lapotron Crystal double-NBT case. Native Java
serialization now supplies its exact display without approximated formatting.
Handler views now retain exact typed item facts before native serialization.
The comparator checks those facts together with the native payload. This
verifies 20,196 additional TiC Bolt Molding and 4,284 recycling views without
equating null and empty-compound NBT. A display-name getter in TGregworks
mutates its argument. Reading names on detached copies removes the resulting
false canonical variants. All 28,715 affected input choices now agree with
their unified group members. The 4,288 removed empty-compound variants have
retained null-NBT counterparts, while genuine tagged variants stay distinct.
Five native recycling recipes still contain unregistered door objects after
MalisisDoors replaces the vanilla registry entries. NEI cannot serialize
those objects. The same five failures are counted separately in signatures,
native serialization and typed facts. Two scoped canonical anchors
also make presentation context incomplete. Validation therefore still fails
its completeness thresholds. This does not establish whole-pack equivalence.
The comparator exits 1 for failed thresholds and 2 for invalid evidence.

Botania is checked separately against its ingredient/result views. All 152
base recipes agree, including eight wildcard cases resolved by independent
pools. The 13 subclass display templates agree while execution stays unknown.
Auxiliary catalyst fields agree in raw presentation, without a selected-writer
proof. Mana, production probabilities and runtime gates remain source-backed
facts rather than independent NEI validation results.

## Human interface

```powershell
python/.venv/Scripts/python.exe -m gtnh_data serve --database exports/index.sqlite --ui-dist ui/dist
```

Open the local URL printed by the server. Search for an item or fluid, inspect
producing/consuming processes and sources, then select start and target
resources for a process graph. Recipe details preserve alternative input
slots, presence requirements, all outputs, chances and structured conditions.
The UI shows source coverage and graph truncation.

The trace fields autocomplete resource names through the shared Dataset
search. Select a suggestion with the mouse or the arrow keys and Enter.
Suggestions identify the registry, item/fluid kind, metadata and NBT presence
so equally named variants remain separate. Editing a name clears the selection.
Trace requests use the selected resource IDs rather than the typed text.
The trace finds several bounded material paths to the target. Require or
exclude intermediate resources using autocomplete, limit the number of
paths, and set how many extra steps may follow the shortest qualifying path.
The GUI defaults to Main material flow. It uses prepared native-material hints
to find one representative route per target ingredient branch, while preserving
the complete recipes and their external side inputs. Diverse routes spreads
additional alternatives across target ingredients. Fewest steps first is also
available. CLI, HTTP and MCP keep their explicit `diverse` default. Trace defaults
allow six extra steps within a total depth of 12. The GUI admits up to 150
distinct processes across eight whole paths. These bounds remain editable.
Filters run in Dataset before results are selected. Fewest steps does not
mean best yield or minimum energy. No-route, identical-resource and search
limits remain explicit. Every included recipe belongs to a returned path.

New imports prepare a snapshot-bound flow sidecar automatically. For an existing
index, run `gtnh-data rebuild-flow-index --database PATH_TO_INDEX.sqlite` once.
Inspect readiness with `gtnh-data flow-index --database PATH_TO_INDEX.sqlite`.
Preparation changes derived search data only. Material mode rejects missing or
incompatible sidecars with an explicit rebuild message.

MCP traces default to `view="compact"`, retaining complete selected recipes,
declared choices and path resources with explicit omission counts for expanded
matching candidates. Request `view="full"` for the expanded candidate graph.
Dataset, HTTP and CLI retain the full default. CLI accepts `--view compact`.
The [agent guide](python/src/gtnh_data/agent_guide.md) explains matching references
and source-boundary evidence in both presentations.

Each graph tile represents a whole recipe, with its input slots, required
tools, outputs, quantities, chances and machine parameters together. Tiles
connect through transitions belonging to the returned paths. Shared recipes
appear once on a freely pannable and zoomable map. Ordinary wheel scrolling
scrolls the page. Hold Ctrl while scrolling, or pinch, to zoom the graph.
The +/- controls also zoom. Drag the canvas to pan and a tile header to move
it, fit the view, or arrange recipes automatically. The minimap is a static
overview. Choose one path to highlight its steps.
Click a recipe or material to inspect it beside the board. Missing identities
and producing recipes load there without switching workspaces. Open in Library
is a separate action. Returning to Trace keeps the result, camera, moved cards
and filters. The inspector uses a scrolling body with a separate close header,
and becomes a fixed drawer in a narrow viewport. Escape closes it and returns
focus to the opener. Full records remain in collapsed technical sections with
Copy JSON, while ordinary quantities include their units and exceptional
chances appear as percentages.
Use the controls above the canvas to export, then click Download PNG or
Download SVG to save the prepared image. The link stays available without
rendering the board again. Export whole board PNG includes every tile, link
and label at twice the natural
tile resolution, regardless of the live zoom or screen size. Export whole
board SVG uses natural dimensions and suits very large boards. Exports keep
the current arrangement, expanded sections and path highlighting, without
moving the live camera. PNG is rejected above 16,384 pixels on either side or
64 million total pixels rather than shrinking the text. Use SVG in that case.
The SVG embeds HTML through foreignObject and is intended for modern browsers,
so some vector editors may not render the recipe cards.

Additional inputs and co-products stay inside each recipe, with identities
and complete native records available in the inspector.
Cards use their content size, wrap input slots into rows and place labeled
outputs below. Automatic arrangement uses measured card dimensions. Recipe
titles and resource names retain the same readable font sizes.
Generation definitions describe world blocks. Inventory availability follows
captured acquisition outputs. Normal-ore mining sources retain separate
Fortune 0 plain and silk branches, native quantities, harvest requirements,
dimension context and links to their generator definitions. These are base
drops before tool/event modifiers, not observed deposits or final harvests.
Small ores retain weighted replacement draws and exclusive host-dust outcomes
as one native rule. Potential products remain searchable without invented
fixed quantities. These candidates do not automatically ground inventory
availability or dependency cycles.
The UI omits routine 100% chances and default flags. Exceptional chances
appear as percentages, while unknown chances remain explicit. Exact fractions
and technical fields remain available in the full recipe record.

## Developer route and loop analysis

Trace accepts minimum and maximum recipe voltage tiers, from ULV 0 through
the captured GT range. HV is 3. An active bound excludes unknown tiers unless
the caller explicitly includes them. These are nominal recipe voltage
requirements, not a certificate of machine capability or overclocking.

Select a recipe output in the trace graph to search recycling paths. Choose
the consumed main input to return, then resolve any ambiguous ingredient
alternatives. The shared Dataset calculates the selected main path and bounded
secondary paths. It reports exact net recovery, returned-input percentage,
all extra inputs, presence requirements and initial stocks. Complete
alternatives rank by recovery within the discovered paths. This does not prove
a global optimum. Side paths cannot import extra copies of the selected
byproduct beyond the main path's available surplus.

The combined ledger retains effects on every product, including the main
target. Inspect it when a recycling path consumes useful output. Guaranteed
accounting and expected probabilistic yield are separate modes. Fractional
execution counts describe normalized quantities and expose the required
integer batch scale. Startup stock is sufficient for the declared batch
order, rather than globally minimal scheduling stock. Machine gates and
energy remain separate from material accounting.

Resource inspection shows native material trees and elemental accounting
per native resource unit. The developer loop audit below a trace searches
bounded closed return witnesses. Material gain/loss and chemical gain/loss
have separate filters. Every witness retains recipe IDs, selected inputs,
quantities, startup stock, external consumption and exact net balances.
Loop witnesses currently use ordered recipe inspection rather than a separate
interactive loop map.

Chemical accounting follows the [GTNH Chemical Balance convention](https://wiki.gtnewhorizons.com/wiki/Chemical_Balance)
and pinned native quantity rules. It uses native GT component trees, density,
prefix amounts and fluid identities. Formula text is display-only and purity
is not certified. If a fluid has several native associations, all candidates
are preserved. Accounting is resolved only if every candidate agrees exactly
on quantity basis and elemental vector. Water retains Water and Ice while
both yield H2/O1 per 1,000 native fluid units. Unsupported material integrations,
tagged states and missing components remain explicit.

Native validation confirms a conserving Iron dust/molten/ingot loop and a
Forge Hammer variant returning two dusts from three, with Fe loss one. A loss
can be intentional. No pack-wide absence of amplification is claimed.

HTTP, MCP and CLI expose `plan_recycling`, `find_loops` and
`inspect_chemistry`, alongside the tier-filtered trace. For structured CLI
recycling requests:

```powershell
python/.venv/Scripts/python.exe -m gtnh_data recycle --database PATH_TO_INDEX.sqlite --request-file plan.json
python/.venv/Scripts/python.exe -m gtnh_data loops --database PATH_TO_INDEX.sqlite --start-id RESOURCE_ID --chemical-kind lossy --max-tier 3
python/.venv/Scripts/python.exe -m gtnh_data chemistry RESOURCE_ID --database PATH_TO_INDEX.sqlite
```

Loop bounds are depth 20, processes 1,000 and states 50,000. Partial discovery
and unresolved alternatives remain visible. The latest changes passed 26 Java,
92 Python and 28 GUI tests, the UI production build and native HTTP/MCP parity
checks. The full Crushed Iron Ore to Double Iron Plate query with an HV bound
hit the 10,000-process trace search limit. Its result is incomplete rather
than evidence that no qualifying route exists.

## Network planning, acquisition and offline analysis

The Analysis workspace has two modes. Energy benchmark compares a selected
recipe with bounded networks that consume the selected primary feed and
regenerate other consumed materials. Target from basics expands a target
using a saved profile of permitted external resources. These modes retain
every AND input, selected OR choice, coproduct and presence requirement.

Energy uses captured nominal EU/t times ticks. GT recipe EU/t already includes
amperage. Unknown, nonpositive or non-EU energy cannot certify a cheap
conversion. The comparison exposes benchmark cofeeds and coproducts, without
inventing container credits. Overclocking and machine efficiency remain
outside this nominal comparison.

The shared solver uses exact rational quantities, independently rechecks
every witness and reports integer batch scaling and sufficient startup stock.
It can combine several regenerating branches. Candidate discovery, solver
dimensions, alternative support exclusions and wall time are bounded.
Finding a cheap witness does not prove that all loops have been searched.
Target-from-basics ranks by normalized recipe runs, not minimum raw-material
consumption. Alternative plans show their actual net imports.

Profiles are snapshot-bound JSON sidecars next to the SQLite index. Basics
are explicit external-feed assumptions. They do not establish worldgen or
inventory availability. Profiles also exclude exact item namespaces, captured
groups, resource IDs and recipe families. Resource search and network analysis
use this scope. Existing Trace, recycling and loop queries retain their
existing filters. The complete canonical snapshot is never deleted or edited
by a profile. These view filters reduce search noise, not snapshot disk size.

Autocomplete favors captured canonical unification anchors. Noncanonical
variants and missing acquisition evidence have separate badges. Acquisition
inspection follows captured sources and interpreted producers, then checks
bounded structural grounding from declared sources and selected basics.
Unseeded recipe cycles cannot ground themselves. An absent known route is
never a proof of absolute unobtainability with incomplete capture.

Statistics analyzes the existing offline index by resource namespace, native
group, recipe family and tier. Cost-spread findings compare identical captured
predicates and conditions after exact batch normalization. Distribution
quartiles are exploratory. Neither result labels a recipe as a confirmed bug.
Each finding retains process IDs for inspecting the original records.

The same operations are available through HTTP, MCP and JSON CLI:

```powershell
python/.venv/Scripts/python.exe -m gtnh_data boundary-profiles --database PATH_TO_INDEX.sqlite
python/.venv/Scripts/python.exe -m gtnh_data audit-energy --database PATH_TO_INDEX.sqlite --request-file audit.json
python/.venv/Scripts/python.exe -m gtnh_data plan-to-bases --database PATH_TO_INDEX.sqlite --request-file plan.json
python/.venv/Scripts/python.exe -m gtnh_data acquisition RESOURCE_ID --database PATH_TO_INDEX.sqlite
python/.venv/Scripts/python.exe -m gtnh_data statistics --database PATH_TO_INDEX.sqlite --request-file statistics.json
```

## Agent interface

Read the [MCP query guide](MCP_GUIDE.md) for tool choices, small request examples
and the limits of traces, balanced networks, acquisition hints and statistics.
Connected clients can read the same packaged guide through the MCP resource
`gtnh-data://guide/query-workflows`. The live tool schemas define arguments and
bounds. Use selected IDs from the connected snapshot rather than copying IDs
from another capture.

Configure an MCP client to launch the virtual-environment Python with these
arguments. Use absolute paths in the client's configuration:

```text
-m gtnh_data mcp --database PATH_TO_INDEX.sqlite
```

For Codex, register it with absolute Python and database paths:

```text
codex mcp add gtnh-data -- ABSOLUTE_PATH_TO_PYTHON -m gtnh_data mcp --database ABSOLUTE_PATH_TO_INDEX.sqlite
codex mcp get gtnh-data
```

The registration uses Codex's shared MCP configuration. Start a fresh
session if an existing session has not loaded the new server.

MCP runs over stdio and does not require the GUI server. Diagnostic output
must not be written to the protocol's stdout. The CLI exposes the same
operations for clients that prefer ordinary processes and JSON output.
Use `get_source(id)` to follow a mining source's `generated_source_id` directly
to its worldgen definition. HTTP exposes `/api/sources/{id}` and CLI accepts
`sources SOURCE_ID --database PATH_TO_INDEX.sqlite`.
Successful MCP results place the data once in `structuredContent`, with a
brief text summary instead of a second full JSON copy.

## Synthetic example

For UI and transport development without a pack capture:

```powershell
python examples/make_snapshot.py exports/example
python/.venv/Scripts/python.exe -m gtnh_data import exports/example --database exports/example/index.sqlite
python/.venv/Scripts/python.exe -m gtnh_data serve --database exports/example/index.sqlite --ui-dist ui/dist
```

The example is explicitly synthetic. It is not GTNH recipe or worldgen data.
It demonstrates group inputs, a presence requirement, a probabilistic
co-product, a dimension condition and a cycle.

## License

Project code is licensed under GNU LGPL version 3 only (`LGPL-3.0-only`).
Copyright (c) 2026 Pxx500 and GTNH Data Exporter contributors.
The license text is in [LICENSE](LICENSE), with the incorporated GPLv3 terms
in [COPYING](COPYING). Reused code retains its original notices and license.
Using or exporting a mod does not relicense that mod's JAR, textures, quests
or other content. See [THIRD_PARTY.md](THIRD_PARTY.md) for inspected direct
dependencies and reused-source notices.
The graph dependencies use MIT, ISC and BSD-3-Clause licenses. Their notices
are retained in [ui/public/THIRD_PARTY_NOTICES.txt](ui/public/THIRD_PARTY_NOTICES.txt)
and copied into the GUI distribution.
