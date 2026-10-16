# Capabilities and limitations

WiFi Guard must describe evidence precisely. “Observed,” “associated with this
access point,” and “policy verified” are different claims.

## Discovery and identity

- Local IPv4 ARP discovery broadcasts requests on the selected layer-2
  segment and learns from replies. It finds responding IPv4 neighbors; it is
  not a guaranteed inventory of every Wi-Fi client. Sleeping/offline hosts,
  client isolation, proxy ARP, filtering, timing, and hosts outside that layer-2
  segment can make the result incomplete.
- ARP results do not say whether a host is wireless or wired. Reliable Wi-Fi
  association requires router/AP station data, correlated carefully with DHCP,
  neighbor, and bridge state. A missing ARP reply is not proof of absence.
- IPv6 uses Neighbor Discovery rather than IPv4 ARP. An IPv4-only discovery
  implementation is therefore incomplete on dual-stack or IPv6-only networks.
- Randomized/rotating MAC addresses weaken long-term device identity and can
  make one physical device appear as multiple records. Identity must retain
  provenance and confidence instead of silently merging on MAC alone.

## Traffic visibility

- An ordinary laptop on a switched or managed Wi-Fi LAN cannot automatically
  observe every other device's unicast traffic. Promiscuous mode cannot recover
  frames the switch/AP never delivers to that laptop.
- Network-wide monitoring needs an appropriate observation point such as the
  gateway, an authorized mirrored switch port, a supported AP capture path, or
  another deliberately configured sensor. Even then, encryption and network
  topology limit what metadata or content is visible.
- Packet payloads are not stored by default. Passive HTTPS observers cannot
  read URL paths because HTTP application data is protected by TLS. WiFi Guard
  will not perform TLS interception.

## Enforcement

- Scapy constructs, sends, receives, and dissects packets; it is not a
  network-wide policy enforcement system. Reliable blocking belongs at a
  controlled forwarding/DNS endpoint, with verification and rollback.
- Initial OpenWrt device blocking means restricting forwarded Internet access
  with firewall4/nftables policy. It does not necessarily disconnect a client
  from the access point, stop local peer traffic, or affect traffic that takes
  another gateway. AP association control is a separate, hardware/driver-
  dependent capability.
- Destination-IP rules are brittle when services share or rotate addresses and
  must cover the relevant address families. An IPv4 rule does not block IPv6.
- Pi-hole makes decisions on DNS names. Domain blocking is not exact URL-path
  blocking: DNS does not carry `/path`, query strings, or page resources as a
  URL policy object. Clients can bypass Pi-hole by using another resolver,
  cached/direct IPs, a VPN, or encrypted DNS unless the network separately and
  lawfully constrains those paths.
- HTTPS encrypts URL paths from passive network observers. Exact HTTPS URL
  enforcement is therefore limited to the optional managed Chromium extension
  and only in browsers where that extension is installed, enabled, authorized,
  and up to date. It does not govern other browsers or native applications.
- Client isolation can prevent peer discovery/traffic. Sleeping devices may
  not respond. VPNs hide destination detail behind a tunnel. Encrypted DNS
  hides DNS exchanges from ordinary DNS inspection. All reduce coverage or
  confidence and must be surfaced in the UI.

## Scope and defaults

- Use only on networks the operator is authorized to administer.
- Milestone 3 accepts an explicit interface, one assigned IPv4 address, and a
  canonical target network. Targets must be RFC1918, directly connected,
  IPv4-only, and no larger than 256 total addresses. Loopback, link-local,
  multicast, public, IPv6, malformed, and ambiguous inputs are rejected.
- Demo interfaces are the default. Local OS metadata inspection requires
  `WIFI_GUARD_INTERFACE_SOURCE=local_metadata`; it does not enable discovery.
- The offline worker generates labelled synthetic observations only. Real ARP
  discovery remains unavailable even when local metadata inspection is enabled.
- Startup performs no scanning, capture, firewall write, or DNS write.
- Milestone 3 presence is a synthetic provider report. Offline does not prove
  disconnection, and only positive online observations advance `last_seen`.
- Presence history stores initial and changed statuses, not packet or traffic
  activity, and is bounded per device (100 events by default).
- Packet payload retention is off by default.
- ARP poisoning, Wi-Fi deauthentication, TLS interception, and disruptive
  packet tricks are out of scope for blocking.

## Persistent job limitations

- The API and worker are separate local processes. `queued` means the worker
  has not claimed the job; it is not reported as active discovery.
- One queued or running job is permitted. Terminal records are retained up to
  the configured bound (100 by default).
- An expired worker lease fails the job as `worker_lost`; partial work is not
  silently replayed and partial observations are not ingested.
- Host and Origin validation reduce local browser and DNS-rebinding exposure,
  but are not authentication. Requests without Origin are allowed for local
  command-line clients.

## Verification sources

Sources were checked on 2026-10-14. “Verified” means the linked primary or
official project documentation directly supports the central technical claim;
it does not mean every product/network combination has been tested.

| Claim | Status | Source |
| --- | --- | --- |
| Scapy supports ARP ping and packet sniffing; packet I/O may need privileges | Verified | [Scapy usage](https://scapy.readthedocs.io/en/stable/usage.html) |
| ARP maps protocol addresses to local link addresses and uses local broadcast | Verified | [RFC 826](https://www.rfc-editor.org/info/rfc826/) |
| IPv6 Neighbor Discovery performs the IPv6 role corresponding in part to ARP | Verified | [RFC 4861](https://www.rfc-editor.org/rfc/rfc4861.html) |
| A switched port usually does not receive other ports' unicast; mirroring is a capture option | Verified | [Wireshark switch reference](https://wiki.wireshark.org/SwitchReference) and [Ethernet capture setup](https://wiki.wireshark.org/CAPTURESETUP/Ethernet) |
| OpenWrt 22.03+ uses firewall4 with nftables and effective state can be inspected | Verified | [OpenWrt firewall overview](https://openwrt.org/docs/guide-user/firewall/overview) and [netfilter management](https://openwrt.org/docs/guide-user/firewall/netfilter_iptables/netfilter_management) |
| OpenWrt client isolation is distinct AP behavior | Verified | [OpenWrt wireless configuration](https://openwrt.org/docs/guide-user/network/wifi/basic) |
| Pi-hole manages exact/regex domain allow/deny entries | Verified | [Pi-hole domain database](https://docs.pi-hole.net/database/domain-database/) |
| TLS 1.3 protects application-layer data with authenticated encryption | Verified | [RFC 8446](https://www.rfc-editor.org/info/rfc8446/) |
| DoH encrypts DNS traffic and defeats filtering that relies on unsecured DNS transport | Verified | [RFC 8484](https://www.rfc-editor.org/info/rfc8484/) |
| Chromium extensions can block requests using URL-pattern rules | Verified | [Chrome declarativeNetRequest](https://developer.chrome.com/docs/extensions/reference/api/declarativeNetRequest) |
| Modern clients may randomize MAC addresses | Verified for Android, not every client platform | [Android MAC randomization](https://source.android.com/docs/core/connect/wifi-mac-randomization) |
| Sleeping behavior, VPN topology, caches, and vendor AP behavior affect individual observations | Architecture inference; not lab-verified in Milestone 0 | To be covered by controlled integration fixtures and hardware tests in later milestones |

No live network, OpenWrt device, Pi-hole installation, managed browser, IPv6
segment, VPN, or client-isolation setup was tested in Milestone 0. Statements
about those deployment combinations remain documentation-backed design limits,
not claims of end-to-end validation.
