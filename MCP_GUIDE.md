# MCP guide for agents

The [query workflow guide](python/src/gtnh_data/agent_guide.md) explains how to
choose tools, keep queries small and interpret bounded GTNH results. It is the
single maintained guide and is included in the Python package.

Connected MCP clients can discover and read the same Markdown resource at
`gtnh-data://guide/query-workflows`. The server advertises 23 tools, concise
tool descriptions and startup instructions. Resource reads accept that exact
URI. Other resource URIs are rejected instead of opening arbitrary files.

Use [README.md](README.md#agent-interface) to launch the server and
[FORMAT.md](FORMAT.md) for the detailed dataset contract. Example captured IDs
in the guide are explicitly snapshot-bound. Resolve names in the connected
snapshot before reusing them.
