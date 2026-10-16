# Milestone 0 checklist

Completed on 2026-10-14.

## Repository and provenance

- [x] Confirmed the workspace contained no existing repository or WiFi Guard
  work before creating `scapy/`.
- [x] Obtained Scapy from the official `https://github.com/secdev/scapy.git`
  remote without creating a fork or pushing.
- [x] Created local branch `wifi-guard/m0-baseline` from upstream commit
  `5376fcc86aaba7c516fb4aa19576b03b387d217a`.
- [x] Recorded default branch `master`, nearest tag `v2.8.0`, Git description
  `v2.8.0-5-g5376fcc`, and detected version `2.8.0.post5`.
- [x] Inspected root `LICENSE`, `doc/LICENSE`, the root license summary, and
  representative file-level SPDX/copyright notices.
- [x] Preserved upstream notices and made no Scapy core or root packaging/build
  changes.

## Documentation

- [x] Added `tools/wifi_guard/README.md`.
- [x] Added `docs/UPSTREAM.md`.
- [x] Added `docs/ARCHITECTURE.md` with a Mermaid diagram, component boundaries,
  conceptual interfaces, and policy-state semantics.
- [x] Added `docs/CAPABILITIES_AND_LIMITATIONS.md` with sourced limits and an
  explicit list of deployment combinations not tested.
- [x] Added this checklist.
- [x] Documented authorized-networks-only scope, explicit interface/subnet,
  demo-first and inert-startup defaults, metadata minimization, and prohibited
  disruptive techniques.

## Verification evidence

Repository metadata commands and outcomes:

```text
git remote -v
  origin https://github.com/secdev/scapy.git (fetch/push)

git rev-parse HEAD
  5376fcc86aaba7c516fb4aa19576b03b387d217a

git describe --tags --always --long
  v2.8.0-5-g5376fcc

git branch --show-current
  wifi-guard/m0-baseline
```

The repository guidance was inspected in `AGENTS.md` and `CONTRIBUTING.md`.
Documented checks include `./test/run_tests`,
`python3.12 -m tox -e flake8`, and `python3.12 -m tox -e mypy`. The full suite,
lint, and type checks were not run because Milestone 0 adds only isolated
Markdown documentation and changes no executable code.

An isolated smoke check used `PYTHONNOUSERSITE=1`, `PYTHONPATH` set to the
checkout, and `python3 -S`. It imported Scapy, constructed and serialized an
Ethernet/IPv4/TCP packet with explicit test-only addresses, dissected it, and
made no send, sniff, scan, firewall, or DNS call:

```text
scapy_version=2.8.0.post5
scapy_import=/Users/mosesmazune/Desktop/STIMON/scapy/scapy/__init__.py
packet_length=54
result=PASS
```

The first draft of the smoke command omitted explicit Ethernet addresses.
Scapy attempted local MAC resolution and printed a permission-denied warning
for `/dev/bpf0`; it sent and captured no packet. The corrected command above
uses explicit locally administered MAC addresses and completed without that
access attempt or warning. This is recorded so the baseline does not overstate
the check.

## Final review gates

- [x] Confirm final whitespace checks pass for all five new files.
- [x] Confirm final change set contains only the five files under
  `tools/wifi_guard/`.
- [x] No credentials, generated environment files, application scaffold,
  firewall/DNS state, or packet captures were added.
- [x] No live discovery, scanning, capture, enforcement, push, publication, or
  remote fork was performed.

The gates above were marked after the final status, path, and whitespace
review.
