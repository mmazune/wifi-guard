# Milestone 2 checklist

Completed on 2026-10-14.

## SQLite and lifecycle

- [x] Added an ignored, application-relative default database location with an
  environment override.
- [x] Added forward-only schema version 1 without reset or delete behavior.
- [x] Created directories safely and initialized persistence through FastAPI's
  lifespan without blocking the async loop.
- [x] Used operation-scoped SQLite connections, foreign keys, parameterized
  queries, explicit refresh transactions, and safe database error responses.
- [x] Kept existing records across restarts and seeded demo data idempotently.

## Inventory semantics

- [x] Persisted source-scoped provider identity, separate provider/custom
  names, addresses, connection type, current status, and UTC timestamps.
- [x] Preserved custom names during provider refresh and allowed clearing them.
- [x] Advanced `last_seen` only for positive online observations.
- [x] Recorded initial status and transitions without unchanged duplicates.
- [x] Added deterministic newest-first history and transactional per-device
  retention (default 100).
- [x] Serialized overlapping refreshes and kept reads free of refresh effects.

## API and dashboard

- [x] Added device details, custom-name patch, bounded history pagination, and
  explicit synthetic refresh endpoints.
- [x] Kept existing device fields and added provider/custom names plus seen
  timestamps.
- [x] Added refresh pending/success/failure UI, persisted details, name editing
  and clearing, and paginated history.
- [x] Kept search, filters, responsive presentation, demo labeling, and API-as-
  source-of-truth failure behavior.
- [x] Explained that history is synthetic provider observation, not captured
  network activity.

## Verification

- [x] Backend tests use pytest temporary databases exclusively.
- [x] Covered fresh schema, idempotent startup, restart persistence, custom
  names, transitions, `last_seen`, validation, unknown devices, pagination,
  retention, overlapping refreshes, and transaction rollback.
- [x] Covered frontend loading/error, details/history, failed name editing, and
  duplicate refresh prevention/success reporting.
- [x] Backend tests, frontend tests, TypeScript check, and production build pass.
- [x] Confirmed startup adds no Scapy imports and source contains no discovery,
  capture, transmission, DNS, firewall, or privileged operation.
- [x] Kept all application work under `tools/wifi_guard/` and made no Scapy core
  change.

## Deferred to Milestone 3 or later

- [ ] Live discovery and an isolated Scapy worker.
- [ ] Background refresh scheduling.
- [ ] Authentication and multi-user name ownership.
- [ ] Router, DNS, browser-extension, capture, and enforcement integrations.
