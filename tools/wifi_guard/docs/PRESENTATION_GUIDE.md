# Lecturer presentation guide

## 3–5 minute script

**Opening (30 seconds)**
“WiFi Guard addresses a simple but important problem: keeping an understandable
record of devices without confusing inventory evidence with traffic monitoring
or enforcement. The current project is deliberately safe to demonstrate. It
uses deterministic synthetic observations and never touches this network.”

**Architecture (45 seconds)**
“The local system has four parts: a React dashboard, a FastAPI API, SQLite
storage, and a separate unprivileged worker. The API accepts work; it does not
perform work itself. Jobs are claimed transactionally, leased, cancellable, and
ingested only after a complete result. This hosted site is different: it is a
static presentation build with a typed fixture adapter and browser-local state.
It does not claim to run the API, database, or worker.”

**Device workflow (60 seconds)**
“I can search by device name, IP, or MAC, and filter the reported status. Each
device keeps its provider identity separate from a user-assigned name. The
history records synthetic status transitions rather than packets or traffic.
On this hosted build, my name edit stays only in this browser and Reset demo
removes it.”

**Discovery workflow (60 seconds)**
“The discovery screen requires an explicit interface address and RFC1918 IPv4
scope. Here it runs a visibly labelled browser simulation. Locally, the same
workflow creates a persistent job for the separate offline worker. I can watch
the job progress or cancel it. Neither version sends a real packet.”

**Status and close (45 seconds)**
“Milestones 0 through 3 are complete: architecture, synthetic inventory,
SQLite persistence, and durable offline jobs. Milestone 4—live Scapy ARP
discovery—is explicitly not implemented. The next work is authorized ARP
discovery, monitoring design, authentication, router and Pi-hole enforcement,
optional managed-browser URL rules, and controlled final evaluation.”

## Practical demo walkthrough

1. Open **Overview**. Expected: “Interactive demo · Synthetic data” remains
   visible and the explanation distinguishes hosted and local architectures.
2. Open **Devices**, search for `phone`, and select **Offline**. Expected: the
   guest phone is the only matching record.
3. Clear filters and open **Studio laptop**. Expected: provider name,
   timestamps, and three deterministic presence events are visible.
4. Enter `Lecturer laptop` and choose **Save name**. Refresh the page. Expected:
   the name remains in this browser and the provider name remains separate.
5. In **Discovery demonstration**, choose **Start demo discovery**. Expected:
   queued changes to running and then completed, reporting six synthetic
   devices. Start another job and choose **Cancel job**. Expected: cancelled.
6. Choose **Reset demo**. Expected: custom names and job history return to the
   original presentation state.
7. Open **Project progress**. Expected: Milestones 0–3 are complete and
   Milestone 4 is explicitly “Not implemented.”

Do not describe the hosted site as a scanner, monitor, or blocker. Do not imply
that a reported offline device has disconnected from a real network.
