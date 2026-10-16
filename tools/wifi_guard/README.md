# WiFi Guard

**[Open the hosted presentation](DEPLOYMENT_URL_PLACEHOLDER)** · **Moses Mazune**

WiFi Guard is a local-first device inventory and discovery-workflow project
built alongside the open-source Scapy repository. The public presentation uses
synthetic browser-local data; it does not scan, monitor, or block a visitor's
network.

WiFi Guard Milestone 3 is a local device inventory plus persistent, offline
demo discovery jobs. The FastAPI process accepts work, SQLite stores it, and a
separate unprivileged worker generates deterministic synthetic observations.
Neither process imports Scapy, sends packets, captures traffic, resolves real
MAC addresses, or changes network settings.

## Requirements and installation

- Python 3.11 or newer
- Node.js 20 or newer and npm

From `tools/wifi_guard/`:

```console
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install './backend[dev]'
cd frontend && npm ci && cd ..
```

No sudo, packet-capture setup, router credentials, or live network is needed.
`psutil` is used only for explicitly enabled operating-system interface
metadata; no command is constructed from user input.

## Run all three processes

API, from `tools/wifi_guard/`:

```console
backend/.venv/bin/python -m uvicorn wifi_guard_api.main:app \
  --host 127.0.0.1 --port 8000
```

Offline worker, in a second terminal:

```console
backend/.venv/bin/wifi-guard-worker
```

Use `backend/.venv/bin/wifi-guard-worker --once` to claim at most one queued
job and exit. The API never starts this process.

Dashboard, in a third terminal:

```console
cd frontend
npm run dev
```

Open <http://127.0.0.1:5173>. Vite binds to loopback and proxies `/api` to
port 8000. The API docs are at <http://127.0.0.1:8000/docs>.

## Demo and local metadata modes

The default `WIFI_GUARD_INTERFACE_SOURCE=demo` returns fixed synthetic
interfaces and permits only synthetic jobs. Set
`WIFI_GUARD_INTERFACE_SOURCE=local_metadata` explicitly to inspect names,
IPv4 addresses, netmasks, connected networks, and up/loopback state reported by
the OS. Connection type remains `unknown`; names such as `en0` are not treated
as evidence of Wi-Fi or Ethernet. Local metadata can be inspected and scope
validation runs against it, but job creation returns `409` because real
discovery remains unavailable.

Every requested scope must identify one current interface IPv4 address and a
canonical IPv4 CIDR entirely inside that address's directly connected network.
The target must be RFC1918 private space, contain at most 256 total addresses,
and cannot be loopback, link-local, multicast, public, or IPv6. There is no
default-route selection and no assumed `/24`.

## Job lifecycle and recovery

Jobs move through `queued`, `running`, and one of `completed`, `failed`, or
`cancelled`. A SQLite partial unique index enforces one queued/running job,
including concurrent submissions; a second submission receives `409`. Claims
and transitions are atomic. Queued cancellation completes immediately;
running cancellation is cooperative and never ingests partial results.
Cancellation is idempotent, and terminal jobs cannot return to running.

Workers lease claimed jobs and renew the lease with bounded progress updates.
The next worker marks an expired running job `failed` with code `worker_lost`;
it never silently reruns partially executed work. Adapter execution occurs
outside SQLite transactions. Final results and the completed state commit in a
single transaction. Existing custom names are preserved, and an absent result
does not mark a device offline. Terminal job retention defaults to the newest
100 (`WIFI_GUARD_JOB_RETENTION_LIMIT`); active jobs are never pruned.

## Local request protections

The app retains explicit loopback bind and CORS defaults. It rejects unexpected
`Host` values on all requests and rejects an unlisted `Origin` on state-changing
requests. Requests without `Origin` are accepted for same-machine tools such as
`curl`; this is intentional and means these controls are not authentication.
They reduce browser-origin and DNS-rebinding risk but do not authorize remote
access or defend against other local processes.

## API examples

```console
curl http://127.0.0.1:8000/api/network/interfaces
curl -X POST http://127.0.0.1:8000/api/discovery/jobs \
  -H 'Content-Type: application/json' \
  -d '{"interface_id":"demo-private-1","selected_ipv4_address":"192.168.50.10","target_cidr":"192.168.50.0/24"}'
curl 'http://127.0.0.1:8000/api/discovery/jobs?limit=10&offset=0'
curl -X POST http://127.0.0.1:8000/api/discovery/jobs/JOB_ID/cancel
curl http://127.0.0.1:8000/api/devices
curl -X POST http://127.0.0.1:8000/api/inventory/refresh
```

Job listings are newest-first with deterministic `(created_at, id)` ordering,
bounded `limit`/`offset`, and `next_offset`.

## Checks

```console
backend/.venv/bin/python -m pytest backend
cd frontend
npm run test
npm run typecheck
npm run build
npm run build:hosted
```

## Hosted presentation

The frontend has an explicit `VITE_DATA_MODE=hosted` build. It uses a typed
deterministic demo adapter, visible simulated discovery jobs, cancellable job
states, browser-local name edits, and a Reset demo action. It makes no API
request and never silently falls back from API mode.

See the [progress report](docs/PROGRESS_REPORT.md), [feature matrix](docs/FEATURE_STATUS.md),
[presentation guide](docs/PRESENTATION_GUIDE.md), and
[development/deployment guide](docs/DEVELOPMENT_AND_DEPLOYMENT.md).

## Current boundary

Implemented: deterministic and local-metadata interface providers, validated
scope selection, persistent jobs, crash recovery, cooperative cancellation,
an offline fake adapter, transactional result ingestion, and dashboard job
status. Explicitly not implemented: Scapy/ARP discovery, real probing, packet
capture, default-route scanning, enforcement, authentication, or remote access.

See [Architecture](docs/ARCHITECTURE.md),
[capabilities and limitations](docs/CAPABILITIES_AND_LIMITATIONS.md), and the
[Milestone 3 checklist](docs/MILESTONE_3_CHECKLIST.md).

## Project boundary and licensing

The Scapy checkout and its notices remain upstream work. WiFi Guard files are
isolated under `tools/wifi_guard/`; this milestone changes no Scapy core file
or root build configuration. See [upstream provenance](docs/UPSTREAM.md).
