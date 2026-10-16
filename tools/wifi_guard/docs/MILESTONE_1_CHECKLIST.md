# Milestone 1 checklist

Completed on 2026-10-14.

## Handoff and isolation

- [x] Read repository instructions and all Milestone 0 documents.
- [x] Inspected status, diff, staged diff, and file hashes for
  `scapy/__init__.py`; it matches `HEAD` exactly and required no reversion.
- [x] Kept application code and configuration under `tools/wifi_guard/`.
- [x] Made no Scapy core or root packaging/build changes.

## Backend

- [x] Added an independently installable Python package with explicit runtime
  and test dependencies.
- [x] Added validated demo-only settings, loopback binding, and local-origin
  CORS defaults.
- [x] Added typed health, capability, and deterministic device endpoints.
- [x] Added a minimal device-provider interface and synthetic demo provider.
- [x] Used only private IPv4 addresses and locally administered synthetic MAC
  addresses.
- [x] Added no Scapy import, socket operation, interface discovery, MAC
  resolution, packet operation, or persistence.

## Dashboard

- [x] Added the React/TypeScript/Vite application and dependency lockfile.
- [x] Added a persistent demo banner, backend health, summary, responsive device
  table, capabilities panel, and accessible controls.
- [x] Added search by name/IP/MAC and status filtering.
- [x] Added loading, empty, API-error, and retry states with no fallback data.
- [x] Bound Vite development and preview servers to loopback.

## Verification

- [x] Backend tests cover health, capability truthfulness, deterministic
  inventory, and live-mode rejection.
- [x] Frontend tests cover name, IP, MAC, and combined status filtering.
- [x] Frontend TypeScript check and production build completed.
- [x] Browser smoke check completed against the running backend, including the
  successful dashboard, filtering, and visible retryable backend error state.
- [x] Source and startup inspection found no Scapy import or network-discovery
  behavior.
- [x] Final diff and whitespace checks completed.
