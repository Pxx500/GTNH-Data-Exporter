# Third-party source and dependency notices

Project code is covered by GNU LGPL version 3 only (`LGPL-3.0-only`).
See [LICENSE](LICENSE) and the incorporated GPLv3 terms in [COPYING](COPYING).
This does not relicense
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
| React Flow | 12.12.0 | MIT |
| Dagre | 3.1.1 | MIT |
| html-to-image, graph PNG/SVG export | 1.11.11 | MIT |
| Vite | 8.3.4 | MIT |
| TypeScript | 7.0.2 | Apache-2.0 |
| FastAPI | 0.143.0 | MIT |
| Uvicorn | 0.54.0 | BSD-3-Clause |
| Official MCP Python SDK | 2.3.0 | MIT |
| SymPy, exact network optimization | 1.14.0 | BSD-3-Clause |
| HTTPX, test dependency | 0.28.1 | BSD-3-Clause |
| Vitest and Testing Library | Versions in ui/package-lock.json | MIT |
| jsdom and React type declarations | Versions in ui/package-lock.json | MIT |
| Gradle wrapper | 9.2.1 | Apache-2.0, existing notices in wrapper scripts |
| GTNHGradle / Pxx500GTNHGradle | Plugin 2.0.19 and local included build | LGPL v2.1 |
| NotEnoughItems, host API | 2.8.159-GTNH | LGPL-3.0-or-later declaration in upstream README |
| EnderIO, host API | 2.10.49 | LGPL-3.0-or-later GTNH modifications, original public-domain declaration |
| ForestryMC, host API | 4.11.39 | Upstream host dependency, no implementation bundled |
| Botania, host API | 1.13.38-GTNH | Upstream host dependency, no implementation bundled |

UI package license metadata was checked in the actual lockfile. Python
direct versions are pinned in pyproject.toml. Upstream license texts:
[FastAPI](https://github.com/fastapi/fastapi/blob/master/LICENSE),
[Uvicorn](https://github.com/Kludex/uvicorn/blob/main/LICENSE.md),
[MCP SDK](https://github.com/modelcontextprotocol/python-sdk/blob/main/LICENSE),
[TypeScript](https://github.com/microsoft/TypeScript/blob/main/LICENSE.txt),
[React](https://github.com/react/react/blob/main/LICENSE),
[Vite](https://github.com/vitejs/vite/blob/main/LICENSE).

React Flow and Dagre versions and licenses were checked against their pinned
npm records and installed package license files. Their graph dependencies
use MIT, ISC and BSD-3-Clause. The retained texts are in
[ui/public/THIRD_PARTY_NOTICES.txt](ui/public/THIRD_PARTY_NOTICES.txt), which
Vite copies into the GUI distribution. Source licenses:
[React Flow](https://github.com/xyflow/xyflow/blob/main/LICENSE) and
[Dagre](https://github.com/dagrejs/dagre/blob/master/LICENSE).

Java uses existing host APIs and libraries rather than embedding GT5,
Minecraft, Forge or Gson into the exporter JAR. GT5 and NEI have LGPL
declarations and file-specific origins. Their implementation was not copied
into the current independent capture adapters. The actual GTNH pack retains
its own per-mod licenses. Public distribution of captured quests, textures
or other content needs separate provenance and permission checks.

The NEI reference adapter calls the installed mod's public APIs. NEI source
was inspected at commit `550e85c456ff2a2ac92c47af4235ad3aa46beecb` to establish
the native projection semantics. No NEI implementation source is copied or
embedded. The tested runtime JAR identifies LGPLv3 in its mod metadata.

EnderIO's pinned `LICENSE.txt` declares LGPLv3 or later for GTNH changes and
public domain for the original source. The runtime JAR also contains an
Apache-2.0 `META-INF/LICENSE`, a packaging discrepancy retained in the local
evidence. No EnderIO implementation is copied or bundled. The CoreMod 2.9.88
host declares GPLv3. Login readiness observes its existing handler through
Forge and Netty interfaces, without a CoreMod compile dependency or copied
implementation. Project code retains LGPL-3.0-only.
Forestry's inspected development JAR has no embedded LICENSE/COPYING notice
or explicit `mcmod.info` license field. The API dependency is not vendored,
and both exporter JARs contain no Forestry implementation classes.

This records the inspected direct dependencies and source reuse. A future
binary release that bundles dependencies requires a license inventory of the
actual packaged files, including transitive dependencies.
