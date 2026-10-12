# GTNH Data Exporter

Capture a versioned GregTech New Horizons dataset, then explore it with a
human UI or query it through MCP and CLI while Minecraft is closed.

The 2026-10-12 full-pack capture contains 259,462 processes, 122,972 resources
and 23,122 acquisition-source records. Its six compressed streams total
11.07 MiB. Build, launch, capture, shutdown and import took 178.72 seconds
on the local setup. This adds 1,663 native EnderIO Sag Mill baseline recipes,
11 ordinary Alloy Smelter recipes and 22,898 conditional normal-ore mining
branches. Public Sievert and Materials metadata is structured in 279 GT
records. Timings describe this captured scope and machine.
Coverage is reported per source. An export is not a declaration that every
recipe family or acquisition route in the pack has been reproduced.
Custom crafting wrappers and non-GT machine integrations remain important
coverage gaps. The first raw crafting catalog included 46,564 records with
unresolved inputs. The collector now captures declared inputs for the exact
GT shaped and shapeless classes. Their dynamic matching and runtime output
transformations remain explicit gaps. Small-ore drop distributions, grinding-ball
variants and other non-GT machine families are still incomplete or unsupported.

A later full-pack run verified declared inputs in all 34,881 GT shaped and
2,702 GT shapeless records. That snapshot has 257,788 processes and 122,972
resources. Its compressed streams total 10.46 MiB. Capture took about nine
seconds and the full build/launch/capture/import pipeline took 153.18 seconds.
Native display output templates remain inspectable, with a visible GUI
notice, but cannot establish material paths until runtime outputs are resolved.

## Stack

| Responsibility | Technology |
| --- | --- |
| Read the running GTNH pack | Java, Forge 1.7.10 and GTNHGradle |
| Portable authoritative snapshot | Versioned JSONL, gzip and checksummed manifest |
| Matching, lookup and process graphs | Python 3.11+ Dataset module |
| Rebuildable offline index | Standard-library SQLite and FTS5 |
| Human interface | React, TypeScript and Vite |
| Local GUI server | FastAPI and Uvicorn on localhost |
| Agent interface | Official Python MCP SDK over stdio, plus JSON CLI |

GUI, HTTP, CLI and MCP share the same Dataset operations. The UI does not
implement its own recipe matcher or graph discovery. No embeddings or remote
service are required. See [FORMAT.md](FORMAT.md) for the shared contract.
Potential later extensions are recorded in [FUTURE.md](FUTURE.md). The current
focus is faithful capture, offline lookup and bounded material paths.

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

The current adapters cover four exact GT recipe maps and the exact NEI
furnace handler. Other handlers remain unverified. RecipeId signatures omit
quantities and alternatives, and NEI's NBT projection loses type information.
Neither signature agreement nor display agreement proves pack-wide execution
semantics. See [FORMAT.md](FORMAT.md) for the reference contract.

The latest paired full-pack run on 2026-10-12 captured 366 handlers and 287,513
views/signatures in a 176.56-second pipeline. Independent item presentation
context retains 32,109 original GT alias queries and 223 NEI item pools,
with exact typed NBT and binding to the closed canonical streams.
The scoped comparison finds 45,209 matching projections, no differences
and no missing matches. Earlier runs reported 26 differences and 148 missing
matches before the alias/wildcard presentation rules were mapped.
Semantic case accounting confirms 173 earlier observations now match.
One Lapotron Crystal case remains explicitly unsupported because Java's
floating-point NBT display formatting is not mapped. It is not a missing recipe.
Five native recycling recipes still contain unregistered door objects after
MalisisDoors replaces the vanilla registry entries. NEI cannot serialize
those objects. Their errors remain explicit, and two scoped canonical anchors
also make presentation context incomplete. Validation therefore still fails
its completeness thresholds. This does not establish whole-pack equivalence.
The comparator exits 1 for failed thresholds and 2 for invalid evidence.

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
Filters run in Dataset before results are selected. Fewest steps does not
mean best yield or minimum energy. No-route, identical-resource and search
limits remain explicit. Every included recipe belongs to a returned path.

Each graph tile represents a whole recipe, with its input slots, required
tools, outputs, quantities, chances and machine parameters together. Tiles
connect through transitions belonging to the returned paths. Shared recipes
appear once on a freely pannable and zoomable map. Drag tiles, fit the view,
or arrange them automatically. Choose one path to highlight its steps.
Additional inputs and co-products stay inside each recipe, with identities
and complete native records available in the inspector.
Generation definitions describe world blocks. Inventory availability follows
captured acquisition outputs. Normal-ore mining sources retain separate
Fortune 0 plain and silk branches, native quantities, harvest requirements,
dimension context and links to their generator definitions. These are base
drops before tool/event modifiers, not observed deposits or final harvests.
The UI omits routine 100% chances and default flags. Exceptional chances
appear as percentages, while unknown chances remain explicit. Exact fractions
and technical fields remain available in the full recipe record.

## Agent interface

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
