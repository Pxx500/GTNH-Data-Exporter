# Third-party source and dependency notices

New project code is covered by the root MIT license. This does not relicense
upstream code, build tools, installed dependencies or exported modpack content.

## Reused source

The runtime collector and build scaffold reuse work from
[Samiracle64/gtnh-factory-flow](https://github.com/Samiracle64/gtnh-factory-flow),
commit `04b8d7eac4f7ec17123b294e085e007fc887d6cf`, under MIT.
Copyright 2026 Samiracle64 is retained in the collector and the complete
notice is in [exporter/THIRD_PARTY_NOTICES.md](exporter/THIRD_PARTY_NOTICES.md).

GTNH Toolkit is an MIT-licensed design reference for the offline module.
Any source reuse must retain its copyright and MIT notice alongside the
affected files.

## Direct dependencies and tools

| Dependency | Current version | License |
| --- | --- | --- |
| React and React DOM | 19.3.0 | MIT |
| Vite | 8.3.4 | MIT |
| TypeScript | 7.0.2 | Apache-2.0 |
| FastAPI | 0.143.0 | MIT |
| Uvicorn | 0.54.0 | BSD-3-Clause |
| Official MCP Python SDK | 2.3.0 | MIT |
| HTTPX, test dependency | 0.28.1 | BSD-3-Clause |
| Vitest and Testing Library | Versions in ui/package-lock.json | MIT |
| jsdom and React type declarations | Versions in ui/package-lock.json | MIT |
| Gradle wrapper | 9.2.1 | Apache-2.0, existing notices in wrapper scripts |
| GTNHGradle / Pxx500GTNHGradle | Plugin 2.0.19 and local included build | LGPL v2.1 |

UI package license metadata was checked in the actual lockfile. Python
direct versions are pinned in pyproject.toml. Upstream license texts:
[FastAPI](https://github.com/fastapi/fastapi/blob/master/LICENSE),
[Uvicorn](https://github.com/Kludex/uvicorn/blob/main/LICENSE.md),
[MCP SDK](https://github.com/modelcontextprotocol/python-sdk/blob/main/LICENSE),
[TypeScript](https://github.com/microsoft/TypeScript/blob/main/LICENSE.txt),
[React](https://github.com/react/react/blob/main/LICENSE),
[Vite](https://github.com/vitejs/vite/blob/main/LICENSE).

Java uses existing host APIs and libraries rather than embedding GT5,
Minecraft, Forge or Gson into the exporter JAR. GT5 and NEI have LGPL
declarations and file-specific origins. Their implementation was not copied
into the current independent capture adapters. The actual GTNH pack retains
its own per-mod licenses. Public distribution of captured quests, textures
or other content needs separate provenance and permission checks.

This records the inspected direct dependencies and source reuse. A future
binary release that bundles dependencies requires a license inventory of the
actual packaged files, including transitive dependencies.
