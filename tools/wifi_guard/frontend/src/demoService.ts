import type { DashboardService } from "./service";
import type { Capabilities, Device, DiscoveryJob, DiscoveryScope, NetworkInterface, PresenceEvent } from "./types";

const STORAGE_KEY = "wifi-guard-hosted-demo-v1";

const CAPABILITIES: Capabilities = {
  demo_device_inventory: { available: true, detail: "Deterministic synthetic inventory." },
  demo_discovery_jobs: { available: true, detail: "Browser-simulated job lifecycle." },
  live_discovery: { available: false, detail: "Planned after Milestone 3." },
  traffic_capture: { available: false, detail: "Not implemented." },
  device_ip_enforcement: { available: false, detail: "Planned router integration." },
  domain_enforcement: { available: false, detail: "Planned Pi-hole integration." },
  exact_url_enforcement: { available: false, detail: "Optional managed-browser work." },
};

const INTERFACES: NetworkInterface[] = [{
  id: "presentation-lan",
  name: "Presentation lab network",
  ipv4_addresses: [{ address: "192.168.50.10", netmask: "255.255.255.0", network: "192.168.50.0/24" }],
  connected_ipv4_networks: ["192.168.50.0/24"],
  is_up: true,
  is_loopback: false,
  connection_type: "unknown",
  source: "demo",
  eligible: true,
  ineligible_reason: null,
}];

const INITIAL_DEVICES = [
  ["studio-laptop", "Studio laptop", "192.168.50.12", "02:00:00:00:10:01", "online", "wifi", "2026-10-14T08:12:00Z"],
  ["lecture-display", "Lecture display", "192.168.50.18", "02:00:00:00:10:02", "online", "wired", "2026-10-14T08:15:00Z"],
  ["guest-phone", "Guest phone", "192.168.50.37", "02:00:00:00:10:03", "offline", "wifi", "2026-10-14T07:48:00Z"],
  ["office-printer", "Office printer", "192.168.50.44", "02:00:00:00:10:04", "online", "wired", "2026-10-14T08:03:00Z"],
  ["lab-tablet", "Lab tablet", "192.168.50.63", "02:00:00:00:10:05", "online", "wifi", "2026-10-14T08:21:00Z"],
  ["media-hub", "Media hub", "192.168.50.71", "02:00:00:00:10:06", "offline", "unknown", "2026-10-13T16:42:00Z"],
].map(([id, name, ip, mac, status, connection, seen]) => ({
  id, display_name: name, provider_name: name, custom_name: null,
  ipv4_address: ip, mac_address: mac, status, connection_type: connection,
  data_source: "demo", first_seen: "2026-10-14T07:30:00Z",
  last_seen: status === "online" ? seen : "2026-10-13T16:42:00Z",
})) as Device[];

interface DemoState { devices: Device[]; jobs: DiscoveryJob[]; names: Record<string, string>; }
const initialState = (): DemoState => ({ devices: INITIAL_DEVICES.map((device) => ({ ...device })), jobs: [], names: {} });
let memoryState = initialState();
let storageWarning: string | null = null;

function readState(): DemoState {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return memoryState;
    const parsed = JSON.parse(raw) as Partial<DemoState>;
    if (!Array.isArray(parsed.devices) || !Array.isArray(parsed.jobs) || !parsed.names) throw new Error("Invalid state");
    memoryState = parsed as DemoState;
    storageWarning = null;
  } catch {
    storageWarning = "Browser storage was unavailable or invalid. This visit is using temporary in-memory demo state.";
    memoryState = initialState();
  }
  return memoryState;
}

function writeState(state: DemoState) {
  memoryState = state;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    storageWarning = null;
  } catch {
    storageWarning = "Browser storage is unavailable. Changes will last only until this page is closed.";
  }
}

function evolve(job: DiscoveryJob): DiscoveryJob {
  if (job.state === "cancelled" || job.state === "completed") return job;
  const elapsed = Date.now() - new Date(job.created_at).getTime();
  if (elapsed >= 4500) return { ...job, state: "completed", started_at: job.started_at ?? new Date(new Date(job.created_at).getTime() + 700).toISOString(), finished_at: new Date(new Date(job.created_at).getTime() + 4500).toISOString(), progress_processed: 256, progress_discovered: 6, worker_id: "browser-simulator" };
  if (elapsed >= 700) {
    const ratio = Math.min(1, (elapsed - 700) / 3800);
    return { ...job, state: "running", started_at: job.started_at ?? new Date(new Date(job.created_at).getTime() + 700).toISOString(), progress_processed: Math.max(1, Math.floor(256 * ratio)), progress_discovered: Math.min(5, Math.floor(6 * ratio)), worker_id: "browser-simulator" };
  }
  return job;
}

function evolvedState() {
  const state = readState();
  const jobs = state.jobs.map(evolve);
  if (jobs.some((job, index) => job !== state.jobs[index])) writeState({ ...state, jobs });
  return { ...state, jobs };
}

function historyFor(device: Device): PresenceEvent[] {
  const base = new Date(device.first_seen).getTime();
  return [
    { event_id: 3, device_id: device.id, previous_status: device.status === "online" ? "offline" : "online", new_status: device.status, observed_at: device.last_seen ?? device.first_seen, source: "demo" },
    { event_id: 2, device_id: device.id, previous_status: "online", new_status: "offline", observed_at: new Date(base + 2_700_000).toISOString(), source: "demo" },
    { event_id: 1, device_id: device.id, previous_status: null, new_status: "online", observed_at: device.first_seen, source: "demo" },
  ];
}

export const demoService: DashboardService = {
  mode: "hosted", persistence: "browser",
  async loadDashboard() { return { health: { application: "WiFi Guard", version: "presentation", mode: "demo" }, capabilities: CAPABILITIES, devices: evolvedState().devices }; },
  async loadDevices() { return evolvedState().devices; },
  async loadDeviceDetails(deviceId, offset = 0) {
    const device = evolvedState().devices.find((item) => item.id === deviceId);
    if (!device) throw new Error("The synthetic device record was not found.");
    const all = historyFor(device); const items = all.slice(offset, offset + 5);
    return { device, history: { items, limit: 5, offset, total: all.length, next_offset: offset + 5 < all.length ? offset + 5 : null } };
  },
  async updateDeviceName(deviceId, customName) {
    const state = evolvedState();
    if (!state.devices.some((item) => item.id === deviceId)) throw new Error("The synthetic device record was not found.");
    const devices = state.devices.map((device) => device.id === deviceId ? { ...device, custom_name: customName, display_name: customName ?? device.provider_name } : device);
    const names = { ...state.names }; if (customName) names[deviceId] = customName; else delete names[deviceId];
    writeState({ ...state, devices, names });
    return devices.find((item) => item.id === deviceId)!;
  },
  async refreshDemoInventory() { return { source: "demo", observed: 6, created: 0, updated: 6, transitions: 0, pruned_events: 0 }; },
  async loadInterfaces() { return INTERFACES; },
  async loadDiscoveryJobs() { const jobs = evolvedState().jobs; return { items: jobs, limit: 10, offset: 0, total: jobs.length, next_offset: null }; },
  async loadDiscoveryJob(jobId) { const job = evolvedState().jobs.find((item) => item.id === jobId); if (!job) throw new Error("The simulated discovery job was not found."); return job; },
  async startDiscoveryJob(scope: DiscoveryScope) {
    const state = evolvedState();
    if (state.jobs.some((job) => job.state === "queued" || job.state === "running")) throw new Error("A simulated discovery job is already active.");
    const job: DiscoveryJob = { id: `demo-${Date.now()}`, mode: "demo", source: "demo", scope, state: "queued", created_at: new Date().toISOString(), started_at: null, finished_at: null, progress_total: 256, progress_processed: 0, progress_discovered: 0, failure_code: null, failure_message: null, cancellation_requested: false, worker_id: null, lease_expires_at: null };
    writeState({ ...state, jobs: [job, ...state.jobs].slice(0, 10) }); return job;
  },
  async cancelDiscoveryJob(jobId) {
    const state = evolvedState(); const current = state.jobs.find((item) => item.id === jobId);
    if (!current) throw new Error("The simulated discovery job was not found.");
    const cancelled: DiscoveryJob = { ...current, state: "cancelled", cancellation_requested: true, finished_at: new Date().toISOString() };
    writeState({ ...state, jobs: state.jobs.map((job) => job.id === jobId ? cancelled : job) }); return cancelled;
  },
  async resetDemo() { memoryState = initialState(); try { window.localStorage.removeItem(STORAGE_KEY); storageWarning = null; } catch { storageWarning = "Browser storage is unavailable. The in-memory demonstration was reset."; } },
  storageNotice: () => storageWarning,
};
