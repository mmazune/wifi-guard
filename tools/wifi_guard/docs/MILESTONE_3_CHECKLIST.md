# Milestone 3 checklist

## Interface and scope

- [x] Provider boundary with deterministic demo and explicit local metadata modes
- [x] No Scapy or shell commands used for interface enumeration
- [x] Stable identifier, IPv4/netmask/network, state, loopback, source, and eligibility
- [x] Connection type remains unknown without authoritative evidence
- [x] Fresh backend validation of interface, selected address, containment, and state
- [x] Canonical RFC1918 IPv4 only; public, IPv6, loopback, link-local, and multicast rejected
- [x] Scope capped at 256 total addresses; no default route or `/24` assumption

## Persistent jobs and worker

- [x] Forward-only schema v2 migration adds jobs without changing inventory/history
- [x] Atomic one-active-job constraint, claim, transitions, cancellation, and pagination
- [x] Lease expiry becomes terminal `worker_lost`; work is not silently rerun
- [x] Terminal retention is bounded without deleting active jobs
- [x] Separate unprivileged CLI with bounded polling and clean signal handling
- [x] Fresh validation before execution and deterministic fake adapter
- [x] Adapter work outside transactions; complete results applied transactionally
- [x] Failure/cancellation ingest no partial results
- [x] Custom names survive; missing observations do not create offline events
- [x] API and worker startup import no Scapy modules

## Dashboard and local HTTP boundary

- [x] Interface/address/network selection and scope guidance
- [x] Explicit synthetic/offline language and disabled real-discovery behavior
- [x] Queued versus running progress, cancellation, failures, and recent jobs
- [x] Polling only for active jobs with unmount cleanup
- [x] Inventory reload after successful completion and responsive controls
- [x] Explicit CORS, Origin checks for mutations, and Host validation
- [x] Requests without Origin documented; controls are not described as authentication

## Verification

- [x] Backend test suite uses temporary databases, fixtures, clocks, and fake adapters
- [x] Existing Milestone 1–2 tests retained
- [x] Frontend tests, TypeScript checks, and production build
- [x] Separate API/worker demo flow and queued-without-worker browser check
- [x] No real discovery, packet transmission, capture, or network changes

Milestone 4 may add explicitly enabled Scapy ARP discovery behind the existing
adapter boundary. It has not been started here.
