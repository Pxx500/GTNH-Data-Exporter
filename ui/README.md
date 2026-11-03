# Dataset explorer UI

The local React interface uses the dataset HTTP API described in
[FORMAT.md](../FORMAT.md). It requires Node.js 22.12+ or a supported newer
version.

Run `npm ci` and `npm run build` in this directory. FastAPI can serve `ui/dist`
on the same origin as `/api`. For development, `npm run dev` starts on
`127.0.0.1:5173` and proxies `/api` to `127.0.0.1:8000`. Change the proxy in
`vite.config.ts` if the backend uses another port.

Use `npm run typecheck` to check types and `npm test` to run the UI tests.
Test data is synthetic and is not loaded by the production app.

The UI supports resource and recipe lookup, source inspection and trace
visualization. Resource details load up to 500 environment records for name
resolution and show when more are available. The environment catalog is
paginated.

The UI is licensed under LGPL-3.0-only. See [LICENSE](LICENSE),
[../COPYING](../COPYING) and the npm dependency notices.
