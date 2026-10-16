from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "wifi-guard-progress-report.pdf"
SCREENSHOTS = ROOT / "docs" / "screenshots"

NAVY = colors.HexColor("#07111D")
PANEL = colors.HexColor("#101D2B")
CYAN = colors.HexColor("#29AAA4")
AMBER = colors.HexColor("#E9A92E")
INK = colors.HexColor("#102132")
MUTED = colors.HexColor("#526779")
PALE = colors.HexColor("#EEF5F8")
LINE = colors.HexColor("#CBD8E1")


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(18 * mm, 13 * mm, 192 * mm, 13 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(18 * mm, 8 * mm, "WiFi Guard - Moses Mazune")
    canvas.drawRightString(192 * mm, 8 * mm, f"Page {doc.page}")
    canvas.restoreState()


styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="TitleWG", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=31, leading=33, textColor=colors.white, spaceAfter=10))
styles.add(ParagraphStyle(name="SubtitleWG", parent=styles["Normal"], fontSize=12, leading=18, textColor=colors.HexColor("#C6D7E3")))
styles.add(ParagraphStyle(name="H1WG", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=21, leading=25, textColor=INK, spaceBefore=4, spaceAfter=10))
styles.add(ParagraphStyle(name="H2WG", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=13, leading=17, textColor=INK, spaceBefore=10, spaceAfter=5))
styles.add(ParagraphStyle(name="BodyWG", parent=styles["BodyText"], fontSize=9.3, leading=14, textColor=INK, spaceAfter=7))
styles.add(ParagraphStyle(name="SmallWG", parent=styles["BodyText"], fontSize=7.6, leading=11, textColor=MUTED))
styles.add(ParagraphStyle(name="CalloutWG", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=10, leading=15, textColor=INK, borderColor=AMBER, borderWidth=0, borderPadding=9, backColor=colors.HexColor("#FFF4D8"), spaceAfter=10))


def p(text, style="BodyWG"):
    return Paragraph(text, styles[style])


def bullet(text):
    return Paragraph(text, ParagraphStyle(name="bullet", parent=styles["BodyWG"], leftIndent=11, firstLineIndent=-7, bulletIndent=0, spaceAfter=4), bulletText="-")


story = []
cover = Table([
    [p("INTERACTIVE DEMO / PROGRESS REPORT", "SmallWG")],
    [p("WiFi Guard", "TitleWG")],
    [p("A local-first network inventory and discovery-workflow project", "SubtitleWG")],
    [Spacer(1, 12 * mm)],
    [p("Moses Mazune", "SubtitleWG")],
    [p("16 October 2026", "SubtitleWG")],
    [Spacer(1, 24 * mm)],
    [p("Milestones 0-3 complete", "SubtitleWG")],
    [p("Milestone 4: Not implemented", "SubtitleWG")],
], colWidths=[174 * mm], rowHeights=[9 * mm, 19 * mm, 14 * mm, 12 * mm, 9 * mm, 8 * mm, 22 * mm, 10 * mm, 10 * mm])
cover.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), NAVY),
    ("BOX", (0, 0), (-1, -1), 0.8, CYAN),
    ("LEFTPADDING", (0, 0), (-1, -1), 14 * mm),
    ("RIGHTPADDING", (0, 0), (-1, -1), 14 * mm),
    ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
]))
story += [Spacer(1, 18 * mm), cover, PageBreak()]

story += [p("Executive summary", "H1WG"), p(
    "WiFi Guard helps an authorized operator keep understandable device records while preserving a strict boundary between inventory evidence, traffic monitoring, and policy enforcement. The current application demonstrates inventory, search, filtering, details, custom names, presence history, and persistent discovery jobs using deterministic synthetic data. It does not discover, monitor, or block real devices."
), p(
    "The local application combines React and TypeScript, FastAPI, SQLite, and a separate unprivileged worker. The hosted presentation uses the same interface with a typed deterministic adapter and browser-local state. It does not run the local API, database, or worker and cannot access a visitor's network."
), p("Milestone 4 - live Scapy ARP discovery - is explicitly not implemented.", "CalloutWG"), p("Problem statement", "H2WG"), p(
    "Small network operators often lack a clear record of observed devices and how their reported state changes. A credible solution must show the source and limits of that evidence. An ARP response is not proof that a device is wireless, and a missing response is not proof that a device is absent."
), p("Aim and objectives", "H2WG")]
for item in [
    "Present safe deterministic records without touching a network.",
    "Persist inventory, custom names, and presence-state changes locally.",
    "Validate an explicitly selected interface address and private IPv4 scope.",
    "Process synthetic discovery through a durable job model and separate worker.",
    "Prepare a bounded adapter design for later authorized Scapy discovery.",
]: story.append(bullet(item))

story += [Spacer(1, 5 * mm), p("What Scapy contributes", "H1WG"), p(
    "Scapy is an open-source Python packet manipulation library. It can construct, send, receive, dissect, and inspect packets; its documentation includes ARP discovery helpers and sniffing. These capabilities can require appropriate privileges and must be used only on authorized networks."
), p("What WiFi Guard adds", "H2WG"), p(
    "WiFi Guard adds the application workflow: dashboard, typed API, durable inventory, presence history, explicit scope validation, persistent jobs, cancellation, worker leases, and capability boundaries. The current worker uses only a deterministic fake adapter. No current WiFi Guard process imports Scapy or performs packet I/O."
), PageBreak()]

story += [p("Architecture", "H1WG")]
architecture = Table([
    [p("LOCAL APPLICATION", "SmallWG"), p("HOSTED PRESENTATION", "SmallWG")],
    [p("React dashboard<br/>↓ loopback HTTP/JSON<br/>FastAPI API → SQLite<br/>↑ transactional job state<br/>Separate offline worker<br/>↓<br/>Deterministic adapter"), p("React dashboard<br/>↓ typed service contract<br/>Hosted demo adapter<br/>↓<br/>Browser-local state<br/><br/><b>No API, worker, database, or LAN access</b>")],
], colWidths=[84 * mm, 84 * mm])
architecture.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), PANEL), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("BACKGROUND", (0, 1), (-1, 1), PALE), ("BOX", (0, 0), (-1, -1), .7, LINE),
    ("INNERGRID", (0, 0), (-1, -1), .7, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
]))
story += [architecture, Spacer(1, 5 * mm), p(
    "The API and worker are independent processes. SQLite schema migrations preserve inventory while adding the job model. Claims, progress, cancellation, leases, failure, and completion use legal-state predicates and short transactions. Completed results and inventory updates commit together; failed or cancelled jobs ingest no partial observations."
), p(
    "The hosted mode is selected explicitly with VITE_DATA_MODE=hosted. It never silently falls back after an API failure. Invalid browser storage degrades to temporary in-memory state with a visible notice."
), p("Completed milestones", "H2WG")]
milestones = [
    ["0", "Scope, provenance, architecture and evidence limits", "Complete"],
    ["1", "FastAPI and React synthetic inventory", "Complete"],
    ["2", "SQLite persistence, custom names and history", "Complete"],
    ["3", "Persistent jobs and separate offline worker", "Complete"],
    ["4", "Live Scapy ARP discovery", "NOT IMPLEMENTED"],
]
mt = Table([["Milestone", "Delivered scope", "Status"], *milestones], colWidths=[22 * mm, 105 * mm, 41 * mm])
mt.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), PANEL), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("GRID", (0, 0), (-1, -1), .5, LINE), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTNAME", (2, 1), (2, -1), "Helvetica-Bold"), ("TEXTCOLOR", (2, 1), (2, 4), CYAN),
    ("TEXTCOLOR", (2, 5), (2, 5), colors.HexColor("#A16800")),
    ("FONTSIZE", (0, 0), (-1, -1), 8), ("LEADING", (0, 0), (-1, -1), 11),
    ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
]))
story += [mt, PageBreak()]

story += [p("Hosted interface", "H1WG"), p("The deployed interface labels synthetic data persistently and keeps local and hosted architectures distinct."), Image(str(SCREENSHOTS / "wifi-guard-overview.png"), width=174 * mm, height=121 * mm), Spacer(1, 4 * mm), p("Figure 1. Hosted overview with the evidence boundary, inventory snapshot, and presentation route.", "SmallWG"), PageBreak()]

detail = Image(str(SCREENSHOTS / "wifi-guard-device-detail.png"), width=73 * mm, height=186 * mm)
detail.hAlign = "CENTER"
story += [p("Inventory and workflow", "H1WG"), detail, p("Figure 2. Full hosted workflow showing inventory, record detail, discovery, progress, and architecture limits.", "SmallWG"), PageBreak()]

story += [p("Feature and status matrix", "H1WG")]
rows = [
    ["Capability", "Local", "Hosted", "Status"],
    ["Inventory and filters", "FastAPI + SQLite", "Synthetic adapter", "Implemented"],
    ["Custom names", "SQLite", "Browser-local", "Implemented"],
    ["Presence history", "Bounded events", "Fixture events", "Implemented"],
    ["Discovery jobs", "Worker state machine", "Visible simulation", "Implemented / synthetic"],
    ["Cancellation", "Durable/cooperative", "Browser simulation", "Implemented"],
    ["Visitor isolation", "Local operator", "Per browser", "Implemented"],
    ["Live ARP discovery", "None", "None", "M4 not implemented"],
    ["Monitoring", "None", "None", "Planned"],
    ["Authentication", "None", "None", "Planned"],
    ["Router / Pi-hole rules", "None", "None", "Planned"],
    ["Browser URL filtering", "None", "None", "Optional future"],
]
ft = Table(rows, colWidths=[46 * mm, 43 * mm, 43 * mm, 36 * mm], repeatRows=1)
ft.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), PANEL), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("GRID", (0, 0), (-1, -1), .5, LINE), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 7.6),
    ("LEADING", (0, 0), (-1, -1), 10), ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
]))
story += [ft, Spacer(1, 6 * mm), p("Current limitations", "H2WG"), p(
    "There is no real discovery, packet capture, traffic monitoring, authentication, remote multi-user service, firewall change, DNS change, OpenWrt control, Pi-hole integration, or exact URL filtering. Reported presence is synthetic provider evidence and is not packet evidence."
), p("Remaining work", "H2WG")]
for item in [
    "Authorized live ARP discovery through a separately enabled Scapy adapter.",
    "Monitoring from an appropriate observation point, with evidence limits.",
    "Authentication, hardening, audit, and safe remote-access decisions.",
    "Router-based device/IP enforcement and Pi-hole domain blocking.",
    "Optional managed-browser URL filtering and final controlled evaluation.",
]: story.append(bullet(item))
story.append(PageBreak())

story += [p("Verification evidence", "H1WG")]
checks = [
    ["Check", "Current result"],
    ["Backend pytest", "39 passed; 1 dependency deprecation warning"],
    ["Frontend Vitest", "13 passed across 3 test files"],
    ["TypeScript", "Passed"],
    ["API-mode production build", "Passed"],
    ["Hosted-mode production build", "Passed"],
    ["Hosted adapter lifecycle", "Persistence/reset, completion, cancellation, no fetch passed"],
    ["Browser interactions", "Navigation, filter, detail, name persistence, completion, cancellation, reset passed"],
    ["Mobile", "390 x 844; no horizontal overflow"],
    ["Browser console", "No warnings or errors in tested hosted flows"],
]
checks = [[p(cell, "SmallWG") for cell in row] for row in checks]
ct = Table(checks, colWidths=[60 * mm, 108 * mm], repeatRows=1)
ct.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), PANEL), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("GRID", (0, 0), (-1, -1), .5, LINE), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8),
    ("LEADING", (0, 0), (-1, -1), 11), ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
]))
story += [ct, Spacer(1, 5 * mm), p(
    "The backend environment emitted a Starlette deprecation warning about current TestClient/httpx compatibility. It did not fail a test. No real network scan, packet capture, packet transmission, firewall change, or DNS change was run."
), p("Presentation route", "H2WG")]
for item in [
    "Open Overview and explain the hosted/local boundary.",
    "Filter devices, open one record, and save a browser-local name.",
    "Run a simulated job to completion, then demonstrate cancellation.",
    "Reset the demo and show Milestone 4 marked Not implemented.",
]: story.append(bullet(item))

story += [PageBreak(), p("Sources and attribution", "H1WG"), p(
    "The repository preserves official Scapy history from secdev/scapy at commit 5376fcc86aaba7c516fb4aa19576b03b387d217a. Scapy code and tools retain upstream GPL-2.0-only notices. Documentation has separate notices described in the repository. WiFi Guard work is isolated under tools/wifi_guard and does not claim authorship of Scapy."
), p("Primary references", "H2WG")]
for item in [
    "Scapy introduction: https://scapy.readthedocs.io/en/stable/introduction.html",
    "Scapy usage guide: https://scapy.readthedocs.io/en/stable/usage.html",
    "RFC 826 - Address Resolution Protocol: https://www.rfc-editor.org/info/rfc826",
    "RFC 4861 - IPv6 Neighbor Discovery: https://www.rfc-editor.org/rfc/rfc4861.html",
]: story.append(bullet(item))
story += [Spacer(1, 8 * mm), p("Published links", "H2WG"), p("GitHub and production deployment links are recorded in the repository README and Markdown progress report after publication."), Spacer(1, 8 * mm), p("Evidence first", "CalloutWG"), p(
    "The central project principle is to describe exactly what the available evidence supports. Inventory, association, monitoring, and enforcement are different claims and must remain visibly distinct."
)]

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
doc = SimpleDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=18 * mm, bottomMargin=19 * mm, title="WiFi Guard progress report", author="Moses Mazune")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUTPUT)
