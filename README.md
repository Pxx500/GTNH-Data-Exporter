# GTNH Data Exporter

Capture a versioned GregTech New Horizons dataset, then explore it with a
human UI or query it through MCP and CLI while Minecraft is closed.

This repository provides a working first capture/query slice, verified against
the running full GTNH pack on 2026-10-11. The first validated snapshot contains
257,788 process records and 122,835 resources. Its six compressed data streams
total 9.73 MB. Build, launch, capture, shutdown and import took 140.62 seconds
on the local setup. These timings describe this captured scope and machine.
Coverage is reported per source. An export is not a declaration that every
recipe family or acquisition route in the pack has been reproduced.
Custom crafting wrappers and non-GT machine integrations remain important
coverage gaps. The current raw crafting catalog includes 46,564 records whose
inputs are explicitly unresolved. Mining-drop transformations are not captured.

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

To inspect an existing snapshot without launching the game:

```powershell
python/.venv/Scripts/python.exe -m gtnh_data import PATH_TO_SNAPSHOT --database exports/index.sqlite
python/.venv/Scripts/python.exe -m gtnh_data status --database exports/index.sqlite
```

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

## Agent interface

Configure an MCP client to launch the virtual-environment Python with these
arguments. Use absolute paths in the client's configuration:

```text
-m gtnh_data mcp --database PATH_TO_INDEX.sqlite
```

MCP runs over stdio and does not require the GUI server. Diagnostic output
must not be written to the protocol's stdout. The CLI exposes the same
operations for clients that prefer ordinary processes and JSON output.
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
