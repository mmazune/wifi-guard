# Upstream provenance

Recorded on 2026-10-14 for the Milestone 0 baseline.

| Field | Value |
| --- | --- |
| Official project | Scapy |
| Official upstream | <https://github.com/secdev/scapy> |
| Remote name | `origin` |
| Upstream default branch | `master` |
| Checked-out commit | `5376fcc86aaba7c516fb4aa19576b03b387d217a` |
| Nearest release tag | `v2.8.0` |
| Git description | `v2.8.0-5-g5376fcc` |
| Scapy-reported version | `2.8.0.post5` |
| Local working branch | `wifi-guard/m0-baseline` |

The commit was obtained from the official remote and is five commits after
`v2.8.0`. The reported version was checked with an isolated local import; it
was not inferred from an unrelated installed package.

## License and notices

- The repository root `LICENSE` contains the GNU General Public License,
  version 2, June 1991. Scapy source files identify this as
  `GPL-2.0-only` in SPDX headers.
- The root `README.md` says Scapy's code, tests, and tools are licensed under
  GPL v2. It separately says the documentation under `doc/`, except where
  marked otherwise and except the logo, is licensed under CC BY-NC-SA 2.5.
  `doc/LICENSE` contains that documentation license.
- Copyright is held by the people identified in the individual files. For
  example, `scapy/__init__.py` names Philippe Biondi; other files contain
  additional notices for their respective contributors. Those per-file
  notices are authoritative and remain unchanged.
- WiFi Guard does not claim authorship of Scapy's packet engine, protocols,
  discovery helpers, capture facilities, tests, documentation, or tooling.
  The original WiFi Guard contribution begins under `tools/wifi_guard/`.

All upstream license, copyright, attribution, and warranty notices must be
preserved. Before redistribution, the distributor must review the applicable
license texts and the notices on every included file; this document is an
inventory, not legal advice.

## Development workflow inspected

The repository's `AGENTS.md` and `CONTRIBUTING.md` define the current workflow.
The portable suite is `./test/run_tests`. CI-aligned lint and type checks are
`python3.12 -m tox -e flake8` and `python3.12 -m tox -e mypy`. Scapy uses
UTScapy `.uts` campaigns, and contribution commits require the repository's
documented `AI-Assisted` trailer. Milestone 0 changes documentation outside
Scapy core, so no protocol campaign or full suite was run.

Useful upstream references:

- Repository: <https://github.com/secdev/scapy>
- Scapy introduction: <https://scapy.readthedocs.io/en/stable/introduction.html>
- Scapy usage, ARP ping, and sniffing: <https://scapy.readthedocs.io/en/stable/usage.html>
- Contribution guide: <https://github.com/secdev/scapy/blob/master/CONTRIBUTING.md>
