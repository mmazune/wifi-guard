import type { DashboardService } from "./service";
import type { Capabilities, Device, DiscoveryJob, DiscoveryJobList, DiscoveryScope, Health, NetworkInterface, PresenceHistory, RefreshSummary } from "./types";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { ...init, headers: { Accept: "application/json", ...init?.headers } });
  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // Non-JSON failures use the status-only message above.
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export const apiService: DashboardService = {
  mode: "api",
  persistence: "server",
  async loadDashboard() {
    const [health, capabilities, devices] = await Promise.all([
      requestJson<Health>("/api/health"),
      requestJson<Capabilities>("/api/capabilities"),
      requestJson<Device[]>("/api/devices"),
    ]);
    return { health, capabilities, devices };
  },
  loadDevices: () => requestJson<Device[]>("/api/devices"),
  async loadDeviceDetails(deviceId, offset = 0) {
    const encodedId = encodeURIComponent(deviceId);
    const [device, history] = await Promise.all([
      requestJson<Device>(`/api/devices/${encodedId}`),
      requestJson<PresenceHistory>(`/api/devices/${encodedId}/history?limit=5&offset=${offset}`),
    ]);
    return { device, history };
  },
  updateDeviceName: (deviceId, customName) => requestJson<Device>(`/api/devices/${encodeURIComponent(deviceId)}`, {
    method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ custom_name: customName }),
  }),
  refreshDemoInventory: () => requestJson<RefreshSummary>("/api/inventory/refresh", { method: "POST" }),
  loadInterfaces: () => requestJson<NetworkInterface[]>("/api/network/interfaces"),
  loadDiscoveryJobs: () => requestJson<DiscoveryJobList>("/api/discovery/jobs?limit=10&offset=0"),
  loadDiscoveryJob: (jobId) => requestJson<DiscoveryJob>(`/api/discovery/jobs/${encodeURIComponent(jobId)}`),
  startDiscoveryJob: (scope: DiscoveryScope) => requestJson<DiscoveryJob>("/api/discovery/jobs", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(scope),
  }),
  cancelDiscoveryJob: (jobId) => requestJson<DiscoveryJob>(`/api/discovery/jobs/${encodeURIComponent(jobId)}/cancel`, { method: "POST" }),
};
