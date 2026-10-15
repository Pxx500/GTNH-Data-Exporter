# GTNH Data Exporter

Capture data from a running GregTech New Horizons pack, then explore recipes,
materials and acquisition sources while Minecraft is closed.

GTNH developers can use the offline dataset to follow processing chains,
inspect recipe inputs and byproducts, compare nominal energy costs, and
investigate recycling or material balance. A browser UI, JSON CLI and MCP
server expose the same queries. Everything runs locally.

## How it works

1. The Java exporter reads the loaded pack's registries and writes a versioned
   snapshot, including pack versions, recipe conditions and capture coverage
2. The Python tools validate the snapshot and build a searchable SQLite index
3. Use the browser, CLI or an MCP client to query that index without running
   Minecraft again

Snapshots are separate from the source code. No GTNH dataset is bundled in this
repository. Capture your pack or import a snapshot supplied separately.

## Install the offline tools

You need Python 3.11+ and Node.js 22.12+ or a supported newer version. Node is
needed to build the UI. Once built, Python serves the UI and API together.

Run these commands in PowerShell from the repository root:

```powershell
python -m venv python/.venv
python/.venv/Scripts/python.exe -m pip install -e ./python
npm --prefix ui ci
npm --prefix ui run build
```

The examples below use this virtual environment directly, so activation isn't
required.

## Get a dataset

### Capture a full pack

Full-pack capture currently requires the local `Pxx500GTNHGradle` setup that
provides the `runFullPack` task through a Gradle init script. This repository
doesn't install that setup, and the task isn't assumed to exist in an
unmodified upstream plugin. See the [runtime exporter](exporter/README.md) for
the tested configuration and capture options.

Use a build JDK compatible with that plugin. The tested local setup uses JDK
25. Adjust `--java-home` to your installed JDK, and choose an output directory
that doesn't already exist:

```powershell
python/.venv/Scripts/python.exe scripts/export_full_pack.py --output exports/snapshot --java-home "C:/Program Files/Java/jdk-25.0.4.1"
```

The script builds the exporter, launches the pack, captures in a new isolated
world, exits the game, and validates and imports the snapshot. On success, the
offline database is `exports/snapshot/index.sqlite`. Captures and generated
indexes under `exports/` are Git-excluded.

### Import an existing snapshot

If you already have a snapshot directory containing `manifest.json` and its
compressed data files, import it without launching Minecraft. Replace
`PATH_TO_SNAPSHOT` with that directory:

```powershell
python/.venv/Scripts/python.exe -m gtnh_data import PATH_TO_SNAPSHOT --database exports/snapshot/index.sqlite
```

Check the selected capture and its coverage:

```powershell
python/.venv/Scripts/python.exe -m gtnh_data status --database exports/snapshot/index.sqlite
```

### Try the interface without a pack

For a small synthetic dataset, use this instead of capture or import:

```powershell
python examples/make_snapshot.py exports/snapshot
python/.venv/Scripts/python.exe -m gtnh_data import exports/snapshot --database exports/snapshot/index.sqlite
```

Use a fresh directory for this example. It demonstrates the interface and query
features with invented data, not GTNH recipes or world generation.

## Explore in the browser

```powershell
python/.venv/Scripts/python.exe -m gtnh_data serve --database exports/snapshot/index.sqlite --ui-dist ui/dist
```

Open [http://127.0.0.1:8765](http://127.0.0.1:8765). To use another local port,
add `--port PORT` to the command.

- **Look up a recipe or resource.** Search items and fluids, then inspect their
  producing and consuming recipes, acquisition sources and native material
  information. Details preserve ingredient alternatives, required tools,
  quantities, chances, byproducts and machine conditions
- **Trace a processing chain.** Select start and target resources from the
  suggestions. Filter by voltage tier or required and excluded intermediates,
  then inspect complete recipes on the graph. Material searches support pause
  and continue. Open path explanations to inspect possible material detours
  and the starting stock they need. Arrange the cards and export the board
  as PNG or SVG
- **Investigate balance and cost.** Inspect recycling paths and material or
  chemical loops. The Analysis workspace can plan a target from selected base
  resources, compare nominal recipe energy with alternative networks, and
  show catalog statistics worth investigating

Results expose coverage gaps and search limits. A trace shows how a material
can contribute to a target. Inspect side inputs before treating it as a full
production plan. Network planning uses an explicit profile of permitted
external resources and reports its actual imports and startup requirements.

Trace groups matching material transformations into one tile and equivalent
retained paths into one route family. Expand machine variants to compare their
costs, tools and other requirements, or inspect an exact recipe. Different
material amounts and outputs remain separate.

## Query from the command line

The CLI returns JSON. Start with a small name search, then use the exact IDs
returned by your selected snapshot:

```powershell
python/.venv/Scripts/python.exe -m gtnh_data resources --database exports/snapshot/index.sqlite --q "Iron" --limit 10
python/.venv/Scripts/python.exe -m gtnh_data processes --database exports/snapshot/index.sqlite --output-id RESOURCE_ID
python/.venv/Scripts/python.exe -m gtnh_data trace --database exports/snapshot/index.sqlite --start-id START_ID --target-id TARGET_ID --path-selection material --view concise
```

Replace `RESOURCE_ID`, `START_ID` and `TARGET_ID` with selected IDs. IDs belong
to one snapshot, so resolve them again when switching captures. Use
`python/.venv/Scripts/python.exe -m gtnh_data --help` or a command's `--help`
for available operations and options.

New imports prepare material-flow search automatically. If an older index
reports missing or incompatible flow data, rebuild its derived index once:

```powershell
python/.venv/Scripts/python.exe -m gtnh_data rebuild-flow-index --database exports/snapshot/index.sqlite
```

## Agent interface

Configure an MCP client to launch the virtual-environment Python executable
with these arguments. Use absolute paths for the executable and database:

```text
-m gtnh_data mcp --database ABSOLUTE_PATH_TO_REPOSITORY/exports/snapshot/index.sqlite
```

The server uses stdio and runs independently of the GUI server. Read the
[MCP query guide](MCP_GUIDE.md) for tool choices and examples covering lookups,
traces, balanced plans, acquisition and statistics. Connected clients can read
the same guide at `gtnh-data://guide/query-workflows`.

## Coverage and interpretation

Capture coverage depends on the pack and exporter version. Supported recipe
families retain native inputs, outputs and conditions. Unsupported or dynamic
mechanics can remain searchable declarations with unresolved execution, and
aren't treated as confirmed production steps. Check coverage in the selected
snapshot before drawing conclusions about a missing route.

World-generation definitions and mining rules describe possible sources, not
observed deposits or player inventory. Searches are bounded. Energy analysis
uses captured nominal costs and doesn't model overclocking or machine
efficiency. These limits appear in the results where they affect analysis.

For more detail, see the [snapshot and query contract](FORMAT.md),
[runtime exporter guide](exporter/README.md),
[UI development guide](ui/README.md) and [MCP query guide](MCP_GUIDE.md).

## License

Project code is licensed under GNU LGPL version 3 only (`LGPL-3.0-only`).
Copyright (c) 2026 Pxx500 and GTNH Data Exporter contributors.
See [LICENSE](LICENSE), the incorporated GPLv3 terms in [COPYING](COPYING), and
[THIRD_PARTY.md](THIRD_PARTY.md) for dependency and reused-source notices.
Exporting a mod's data doesn't relicense that mod's code or content.
