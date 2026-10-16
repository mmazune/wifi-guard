# Development and deployment

## Local application

Requirements: Python 3.11 or newer, Node.js 20 or newer, and npm.

```console
cd tools/wifi_guard
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install './backend[dev]'
cd frontend && npm ci && cd ..
```

Run the three local processes in separate terminals:

```console
backend/.venv/bin/python -m uvicorn wifi_guard_api.main:app --host 127.0.0.1 --port 8000
backend/.venv/bin/wifi-guard-worker
cd frontend && npm run dev
```

Open <http://127.0.0.1:5173>. The default is local API mode. It never silently
falls back to hosted fixtures.

## Hosted presentation mode

```console
cd tools/wifi_guard/frontend
npm ci
npm run dev:hosted
npm run build:hosted
```

`VITE_DATA_MODE=hosted` selects the typed browser adapter at build time. The
output is `frontend/dist/`. The Vercel project uses:

- root directory: `tools/wifi_guard/frontend`
- framework: Vite
- install command: `npm ci`
- build command: `npm run build:hosted`
- output directory: `dist`

`frontend/vercel.json` supplies SPA routing and intentionally contains no
`rootDirectory` property.

## Verification

```console
cd tools/wifi_guard
backend/.venv/bin/python -m pytest backend
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
npm --prefix frontend run build:hosted
```

No production migration should use `migrate dev` or `db push`. The current
application uses its own forward-only SQLite migrations at startup.
