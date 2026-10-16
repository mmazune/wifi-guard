import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { getStorageNotice, isHostedDemo, loadDashboard, loadDeviceDetails, loadDevices, refreshDemoInventory, resetDemo, updateDeviceName } from "./api";
import DiscoverySection from "./DiscoverySection";
import { filterDevices, type StatusFilter } from "./filterDevices";
import type { DashboardData } from "./service";
import type { Device, PresenceHistory } from "./types";

const formatTime = (value: string | null) => value ? new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "Never observed online";
const STATUS_ROWS = [
  ["Milestone 0", "Research, scope and architecture", "Complete"],
  ["Milestone 1", "FastAPI and React synthetic inventory", "Complete"],
  ["Milestone 2", "SQLite persistence, names and history", "Complete"],
  ["Milestone 3", "Persistent jobs and offline worker", "Complete"],
  ["Milestone 4", "Live Scapy ARP discovery", "Not implemented"],
] as const;

function App() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<StatusFilter>("all");
  const [requestKey, setRequestKey] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);
  const [history, setHistory] = useState<PresenceHistory | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [historyOffset, setHistoryOffset] = useState(0);
  const [name, setName] = useState("");
  const [savingName, setSavingName] = useState(false);
  const [nameError, setNameError] = useState<string | null>(null);
  const [guideOpen, setGuideOpen] = useState(false);

  useEffect(() => {
    let active = true;
    setLoading(true); setError(null);
    loadDashboard().then((result) => { if (active) setData(result); })
      .catch((reason: unknown) => { if (active) { setData(null); setError(reason instanceof Error ? reason.message : "Unknown error"); } })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [requestKey]);

  useEffect(() => {
    if (!selectedId) return;
    let active = true;
    setDetailLoading(true); setDetailError(null);
    loadDeviceDetails(selectedId, historyOffset).then((result) => {
      if (!active) return;
      setSelectedDevice(result.device); setHistory(result.history); setName(result.device.custom_name ?? "");
    }).catch((reason: unknown) => { if (active) setDetailError(reason instanceof Error ? reason.message : "Unknown error"); })
      .finally(() => { if (active) setDetailLoading(false); });
    return () => { active = false; };
  }, [selectedId, historyOffset]);

  const visibleDevices = useMemo(() => filterDevices(data?.devices ?? [], query, status), [data?.devices, query, status]);
  const online = data?.devices.filter((device) => device.status === "online").length ?? 0;
  const offline = (data?.devices.length ?? 0) - online;
  const replaceDevice = (device: Device) => {
    setData((current) => current ? { ...current, devices: current.devices.map((item) => item.id === device.id ? device : item) } : current);
    setSelectedDevice(device); setName(device.custom_name ?? "");
  };
  const reloadInventory = useCallback(async () => {
    const devices = await loadDevices(); setData((current) => current ? { ...current, devices } : current);
    if (selectedId) { const details = await loadDeviceDetails(selectedId, 0); setSelectedDevice(details.device); setHistory(details.history); setHistoryOffset(0); setName(details.device.custom_name ?? ""); }
  }, [selectedId]);
  const refreshInventory = async () => {
    if (refreshing) return; setRefreshing(true); setMessage(null); setActionError(null);
    try { const summary = await refreshDemoInventory(); await reloadInventory(); setMessage(`Refreshed ${summary.observed} synthetic devices; ${summary.transitions} status transitions recorded.`); }
    catch (reason: unknown) { setActionError(reason instanceof Error ? reason.message : "The refresh failed."); }
    finally { setRefreshing(false); }
  };
  const saveName = async (event: FormEvent) => {
    event.preventDefault(); if (!selectedId || savingName) return; const trimmed = name.trim();
    if (!trimmed) { setNameError("Enter a name, or use Restore provider name."); return; }
    setSavingName(true); setNameError(null);
    try { replaceDevice(await updateDeviceName(selectedId, trimmed)); setMessage("Custom name saved for this demo."); }
    catch (reason: unknown) { setNameError(reason instanceof Error ? reason.message : "The name was not saved."); }
    finally { setSavingName(false); }
  };
  const clearName = async () => {
    if (!selectedId || savingName) return; setSavingName(true); setNameError(null);
    try { replaceDevice(await updateDeviceName(selectedId, null)); setMessage("Provider name restored."); }
    catch (reason: unknown) { setNameError(reason instanceof Error ? reason.message : "The custom name was not cleared."); }
    finally { setSavingName(false); }
  };
  const reset = async () => { if (!resetDemo) return; await resetDemo(); setSelectedId(null); setMessage("Demo reset to its original synthetic data."); setRequestKey((value) => value + 1); };

  return <div className="app-shell">
    <a className="skip-link" href="#main">Skip to content</a>
    <div className="demo-banner" role="status">Interactive demo · Synthetic data</div>
    <header className="masthead">
      <a className="brand" href="#overview" aria-label="WiFi Guard overview"><span className="brand-mark" aria-hidden="true">WG</span><span>WiFi Guard<small>Network inventory evidence</small></span></a>
      <nav aria-label="Primary navigation"><a href="#overview">Overview</a><a href="#devices">Devices</a><a href="#discovery">Discovery</a><a href="#progress">Progress</a><a href="#about">About</a></nav>
      <div className="header-actions"><span className={`health ${error ? "health-error" : ""}`}><span className="health-dot" />{loading ? "Loading" : error ? "Unavailable" : isHostedDemo ? "Hosted presentation" : "Local API connected"}</span>{isHostedDemo && <button className="text-button" type="button" onClick={reset}>Reset demo</button>}</div>
    </header>

    <main id="main">
      <section id="overview" className="hero" aria-labelledby="overview-heading">
        <div className="hero-copy"><p className="section-kicker">Milestones 0–3 · Demonstration build</p><h1 id="overview-heading">Know what the inventory says. Know what it cannot.</h1><p className="hero-lede">This hosted demonstration presents the interface and workflow. The local application provides the FastAPI API, SQLite storage, and offline worker. Live network discovery is planned.</p><div className="hero-actions"><a className="primary-link" href="#devices">Explore devices</a><button className="secondary-button" type="button" onClick={() => setGuideOpen((value) => !value)} aria-expanded={guideOpen}>{guideOpen ? "Hide presentation guide" : "Presentation guide"}</button></div></div>
        <div className="evidence-snapshot" aria-label="Demonstration summary"><div className="snapshot-head"><span>Inventory snapshot</span><span className="source-pill">Synthetic fixture</span></div><dl><div><dt>Total records</dt><dd>{data?.devices.length ?? "—"}</dd></div><div><dt>Reported online</dt><dd className="online-count">{data ? online : "—"}</dd></div><div><dt>Reported offline</dt><dd>{data ? offline : "—"}</dd></div></dl><p>Presence reflects deterministic provider reports, never captured traffic.</p></div>
      </section>
      {guideOpen && <aside className="presentation-guide" aria-label="Presentation guide"><strong>3-minute route</strong><ol><li>Frame the problem and the evidence boundary.</li><li>Filter devices, open one record, and rename it.</li><li>Run or cancel the simulated discovery job.</li><li>Show Milestones 0–3 complete and Milestone 4 not implemented.</li></ol></aside>}
      {getStorageNotice() && <p className="storage-notice" role="status">{getStorageNotice()}</p>}
      {loading && <section className="state-panel" aria-live="polite"><div className="spinner" /><h2>Loading demo inventory</h2><p>{isHostedDemo ? "Preparing browser-local synthetic records." : "Connecting to the local WiFi Guard API."}</p></section>}
      {!loading && error && <section className="state-panel error-panel" role="alert"><h2>The local backend could not be reached</h2><p>Start the API on port 8000, then try again. No fallback data has been shown.</p><code>{error}</code><button type="button" onClick={() => setRequestKey((value) => value + 1)}>Retry connection</button></section>}

      {!loading && data && <>
        <section id="devices" className="workspace-section" aria-labelledby="devices-heading"><div className="section-heading"><div><p className="section-kicker">Inventory evidence</p><h2 id="devices-heading">Devices</h2><p>Search synthetic records and inspect their stored identity and presence history.</p></div><button className="secondary-button" type="button" disabled={refreshing} onClick={refreshInventory}>{refreshing ? "Refreshing…" : "Refresh demo inventory"}</button></div>{message && <p className="action-message" role="status">{message}</p>}{actionError && <p className="action-message action-error" role="alert">Refresh failed: {actionError}</p>}<div className="inventory-panel"><div className="toolbar"><label className="search-field"><span>Search devices</span><input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Name, IP, or MAC" /></label><label><span>Status</span><select value={status} onChange={(event) => setStatus(event.target.value as StatusFilter)}><option value="all">All devices</option><option value="online">Online</option><option value="offline">Offline</option></select></label><span className="result-count" aria-live="polite">{visibleDevices.length} shown</span></div>{visibleDevices.length === 0 ? <div className="empty-state" role="status"><h3>No devices match</h3><p>Clear the search or choose a different status.</p><button type="button" onClick={() => { setQuery(""); setStatus("all"); }}>Clear filters</button></div> : <div className="table-wrap"><table><thead><tr><th>Name</th><th>IP address</th><th>MAC address</th><th>Status</th><th>Connection</th><th>Source</th></tr></thead><tbody>{visibleDevices.map((device) => <tr key={device.id} className={selectedId === device.id ? "selected-row" : ""}><th scope="row"><button className="device-link" type="button" onClick={() => { setSelectedId(device.id); setHistoryOffset(0); setSelectedDevice(null); setHistory(null); setNameError(null); }}>{device.display_name}{device.custom_name && <small>Provider: {device.provider_name}</small>}</button></th><td data-label="IP address"><code>{device.ipv4_address}</code></td><td data-label="MAC address"><code>{device.mac_address}</code></td><td data-label="Status"><span className={`status status-${device.status}`}>{device.status}</span></td><td data-label="Connection">{device.connection_type}</td><td data-label="Source"><span className="source-pill">synthetic</span></td></tr>)}</tbody></table></div>}</div></section>

        {selectedId && <section className="detail-panel" aria-labelledby="detail-heading"><div className="detail-heading-row"><div><p className="section-kicker">Selected record</p><h2 id="detail-heading">{selectedDevice?.display_name ?? "Device details"}</h2></div><button className="secondary-button" type="button" onClick={() => setSelectedId(null)}>Close details</button></div>{detailLoading && !selectedDevice && <p role="status">Loading device details…</p>}{detailError && <p className="inline-error" role="alert">Details unavailable: {detailError}</p>}{selectedDevice && <div className="detail-grid"><div className="device-facts"><dl><div><dt>Provider name</dt><dd>{selectedDevice.provider_name}</dd></div><div><dt>User-assigned name</dt><dd>{selectedDevice.custom_name ?? "None"}</dd></div><div><dt>First seen</dt><dd>{formatTime(selectedDevice.first_seen)}</dd></div><div><dt>Last seen online</dt><dd>{formatTime(selectedDevice.last_seen)}</dd></div></dl><form onSubmit={saveName} className="name-form"><label><span>User-assigned name</span><input value={name} maxLength={80} onChange={(event) => setName(event.target.value)} aria-describedby="name-help" /></label><p id="name-help">{isHostedDemo ? "Saved only in this browser." : "Stored separately from the provider name."}</p>{nameError && <p className="inline-error" role="alert">{nameError}</p>}<div className="form-actions"><button type="submit" disabled={savingName}>{savingName ? "Saving…" : "Save name"}</button><button className="secondary-button" type="button" disabled={savingName || !selectedDevice.custom_name} onClick={clearName}>Restore provider name</button></div></form></div><div className="history-block"><h3>Presence history</h3><p>Synthetic provider observations only — no network activity was captured.</p>{history && history.items.length > 0 ? <ol className="history-list">{history.items.map((event) => <li key={event.event_id}><span className={`history-marker status-${event.new_status}`} /><div><strong>{event.previous_status ? `${event.previous_status} to ${event.new_status}` : `Initial status: ${event.new_status}`}</strong><time dateTime={event.observed_at}>{formatTime(event.observed_at)}</time></div></li>)}</ol> : !detailLoading && <p>No presence events are stored.</p>}{history && <div className="pagination" aria-label="Presence history pages"><button className="secondary-button" type="button" disabled={history.offset === 0 || detailLoading} onClick={() => setHistoryOffset(Math.max(0, history.offset - history.limit))}>Newer</button><span>{history.offset + 1}–{history.offset + history.items.length} of {history.total}</span><button className="secondary-button" type="button" disabled={history.next_offset === null || detailLoading} onClick={() => history.next_offset !== null && setHistoryOffset(history.next_offset)}>Older</button></div>}</div></div>}</section>}

        <div id="discovery"><DiscoverySection onInventoryChanged={reloadInventory} /></div>
        <section id="progress" className="workspace-section" aria-labelledby="progress-heading"><div className="section-heading"><div><p className="section-kicker">Build status</p><h2 id="progress-heading">Project progress</h2><p>Verified implementation boundaries, without claiming future work.</p></div></div><div className="milestone-list">{STATUS_ROWS.map(([milestone, scope, state]) => <article key={milestone}><span className={`milestone-state ${state === "Complete" ? "complete" : "planned"}`}>{state}</span><h3>{milestone}</h3><p>{scope}</p></article>)}</div></section>
        <section id="about" className="about-section" aria-labelledby="about-heading"><div><p className="section-kicker">Architecture and limits</p><h2 id="about-heading">About WiFi Guard</h2><p>WiFi Guard is a student project by Moses Mazune built alongside the open-source Scapy repository. It adds an inventory workflow, persistent local data model, and isolated job processing. Scapy is the planned packet-crafting foundation for authorized live ARP discovery in Milestone 4; that milestone is not implemented.</p></div><div className="boundary-grid"><article><strong>Local application</strong><p>React dashboard → FastAPI → SQLite, with a separate offline worker and deterministic adapter.</p></article><article><strong>Hosted presentation</strong><p>React dashboard → typed demo adapter → isolated browser storage. No backend, worker, or LAN access.</p></article><article><strong>Planned, not present</strong><p>Live ARP discovery, monitoring, authentication, router enforcement, Pi-hole blocking, and optional browser URL rules.</p></article></div></section>
      </>}
    </main>
    <footer><span>WiFi Guard · Moses Mazune</span><span>Milestone 4: Not implemented</span></footer>
  </div>;
}

export default App;
