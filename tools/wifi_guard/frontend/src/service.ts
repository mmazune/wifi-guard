import type {
  Capabilities,
  Device,
  DiscoveryJob,
  DiscoveryJobList,
  DiscoveryScope,
  Health,
  NetworkInterface,
  PresenceHistory,
  RefreshSummary,
} from "./types";

export interface DashboardData {
  health: Health;
  capabilities: Capabilities;
  devices: Device[];
}

export interface DashboardService {
  readonly mode: "api" | "hosted";
  readonly persistence: "server" | "browser";
  loadDashboard(): Promise<DashboardData>;
  loadDevices(): Promise<Device[]>;
  loadDeviceDetails(deviceId: string, offset?: number): Promise<{ device: Device; history: PresenceHistory }>;
  updateDeviceName(deviceId: string, customName: string | null): Promise<Device>;
  refreshDemoInventory(): Promise<RefreshSummary>;
  loadInterfaces(): Promise<NetworkInterface[]>;
  loadDiscoveryJobs(): Promise<DiscoveryJobList>;
  loadDiscoveryJob(jobId: string): Promise<DiscoveryJob>;
  startDiscoveryJob(scope: DiscoveryScope): Promise<DiscoveryJob>;
  cancelDiscoveryJob(jobId: string): Promise<DiscoveryJob>;
  resetDemo?(): Promise<void>;
  storageNotice?(): string | null;
}
