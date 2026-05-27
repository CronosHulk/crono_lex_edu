# CronoLex Admin Web

React/Vite admin SPA for `/api/v1/admin`.

## Local development

Run npm/node commands inside Docker only; do not install `node_modules` on the host working tree.

```bash
docker run --rm -it \
  -p 5174:5174 \
  -v "$PWD":/work:ro \
  -w /tmp/admin_web \
  node:22-alpine \
  sh -c "cp -a /work/. . && npm ci && npm run dev"
```

Vite proxies `/api` to `http://127.0.0.1:8000` in development.

## Navigation And Routes

Admin sections should use router-backed URLs as the source of the current screen. Do not add page-local tab state for main navigation sections that belong in the sidebar.

Billing subsections are sidebar children under `Billing`:

- `/admin/billing/payments`
- `/admin/billing/monobank-audit`
- `/admin/billing/task-logs`
- `/admin/billing/settings`

The old `/admin/billing?tab=...` shape is legacy-only and redirects to the matching route while preserving list filter query parameters.

## Production build

```bash
docker build -t cronolex-web-admin .
```

The production build runs `vite build` and then `scripts/apply-sri.mjs`, which adds SHA-384 SRI integrity attributes to generated `script`, `modulepreload`, and stylesheet tags in `dist/index.html`.

The static output is written to `admin_web/dist`. Runtime assets are bundled locally; no CDN assets are required. Optional Roboto files can be placed in `admin_web/public/fonts` as:

- `Roboto-Regular.woff2` or `Roboto-Regular.woff`
- `Roboto-Medium.woff2` or `Roboto-Medium.woff`

## Tests

Frontend refactoring is test-first. New modules under `src/api`, `src/app`, `src/features`, `src/i18n`, `src/shared`, and `src/theme` must keep 100% coverage for statements, branches, functions, and lines.

```bash
docker run --rm \
  -v "$PWD":/work:ro \
  -w /tmp/admin_web \
  node:22-alpine \
  sh -c "cp -a /work/. . && npm ci && npm run lint && npm run typecheck && npm run test:coverage"
```

`npm run lint` uses ESLint with `--max-warnings=0`; `npm run test` and `npm run test:coverage` also run lint before Vitest.

The legacy `src/main.jsx` is excluded from the initial coverage gate while it is being split into typed, test-covered modules. Do not add new business or parsing logic there if it can be extracted into a covered module.

## Security Headers

The admin nginx config sends CSP, iframe denial, nosniff, referrer, permissions and same-origin cross-origin policy headers. Caddy sends matching headers at the public edge for `cronolex.uno` and local `cronolex.local`.
