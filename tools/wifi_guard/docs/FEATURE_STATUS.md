# Feature and status matrix

| Area | Local application | Hosted presentation | Status / evidence |
| --- | --- | --- | --- |
| Dashboard | React, TypeScript, Vite | Same UI | Implemented |
| Device inventory | FastAPI + SQLite | Deterministic browser fixtures | Implemented |
| Search and status filters | Client-side | Client-side | Implemented |
| Device details | API-backed | Adapter-backed | Implemented |
| Custom names | SQLite persistence | Browser-local persistence | Implemented |
| Presence history | Bounded SQLite events | Deterministic fixture events | Implemented |
| Interface metadata | Demo or explicit local metadata provider | Synthetic presentation interface | Implemented |
| IPv4 scope validation | Backend validation | Fixed safe fixture scope | Implemented locally |
| Discovery jobs | SQLite state machine | Visible browser simulation | Implemented with synthetic data |
| Separate worker | Unprivileged local process | Not present or claimed | Implemented locally |
| Claiming, leases, recovery | Transactional local job model | Not applicable | Implemented locally |
| Cancellation | Durable/cooperative | Browser-simulated | Implemented |
| Origin and Host checks | FastAPI middleware | Not applicable to static demo | Implemented locally |
| Visitor isolation | Local single-operator app | Per-browser local state | Implemented |
| Live Scapy ARP discovery | None | None | **Milestone 4: Not implemented** |
| Traffic monitoring | None | None | Planned |
| Authentication/hardening | None | None | Planned |
| Router device/IP enforcement | None | None | Planned |
| Pi-hole domain blocking | None | None | Planned |
| Browser URL filtering | None | None | Optional future work |
