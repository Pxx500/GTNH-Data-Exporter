# Dataset explorer UI

This local React interface reads the Dataset HTTP contract in the repository's
`FORMAT.md`. It does not match ingredients or discover chains in TypeScript.

Use Node.js 22.12+ or a supported newer version. Run `npm ci` in this directory,
then `npm run build`. FastAPI can serve `ui/dist` on the same origin as `/api`.
For development, `npm run dev` binds to `127.0.0.1:5173` and proxies `/api` to
`127.0.0.1:8000`. Adjust that proxy in `vite.config.ts` if using another local
backend port.

`npm run typecheck` checks the TypeScript contract. `npm test` verifies presence,
unknown quantities and chances, consumption chance, NBT sensitivity, opaque IDs,
trace bounds and visible truncation through rendered interfaces. Test data is
synthetic and is never loaded by the production app.

The library searches resources and pages processes and sources. Process details
retain input slot roles, alternatives, rational chances, conditions and all raw
extension fields. The environment catalog distinguishes registered definitions
from observed world deposits. A supplied trace start remains an explicit
assumption, and cycle groups are displayed as mutually reachable members.

The finite SVG graph uses a simple three-lane presentation. Select a node with
a mouse or by keyboard to inspect its full record. Large results scroll and
have zoom controls. This layout is intended for inspection, not optimization.
Each resource detail loads at most 500 environment records for inline name
resolution and announces that limit if additional records exist. The separate
environment catalog is paginated.

No snapshot or synthetic production data is bundled. The UI and its own source
are MIT licensed. Third-party package licenses are retained by npm dependencies.
