export type DeviceStatus = "online" | "offline";
export type ConnectionType = "wifi" | "wired" | "unknown";

export interface Device {
  id: string;
  display_name: string;
  ipv4_address: string;
  mac_address: string;
  status: DeviceStatus;
  connection_type: ConnectionType;
  data_source: "demo" | "demo_discovery";
  provider_name: string;
  custom_name: string | null;
  first_seen: string;
  last_seen: string | null;
}

export interface Health {
  application: string;
  version: string;
  mode: "demo";
}

export interface Capability {
  available: boolean;
  detail: string;
}

export interface Capabilities {
  demo_device_inventory: Capability;
  demo_discovery_jobs: Capability;
  live_discovery: Capability;
  traffic_capture: Capability;
  device_ip_enforcement: Capability;
  domain_enforcement: Capability;
  exact_url_enforcement: Capability;
}

export interface InterfaceIPv4 {
  address: string;
  netmask: string;
  network: string;
}

export interface NetworkInterface {
  id: string;
  name: string;
  ipv4_addresses: InterfaceIPv4[];
  connected_ipv4_networks: string[];
  is_up: boolean | null;
  is_loopback: boolean;
  connection_type: "unknown";
  source: "demo" | "local_metadata";
  eligible: boolean;
  ineligible_reason: string | null;
}

export interface DiscoveryScope {
  interface_id: string;
  selected_ipv4_address: string;
  target_cidr: string;
}

export type DiscoveryJobState =
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

export interface DiscoveryJob {
  id: string;
  mode: "demo";
  source: "demo" | "local_metadata";
  scope: DiscoveryScope;
  state: DiscoveryJobState;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  progress_total: number;
  progress_processed: number;
  progress_discovered: number;
  failure_code: string | null;
  failure_message: string | null;
  cancellation_requested: boolean;
  worker_id: string | null;
  lease_expires_at: string | null;
}

export interface DiscoveryJobList {
  items: DiscoveryJob[];
  limit: number;
  offset: number;
  total: number;
  next_offset: number | null;
}

export interface PresenceEvent {
  event_id: number;
  device_id: string;
  previous_status: DeviceStatus | null;
  new_status: DeviceStatus;
  observed_at: string;
  source: "demo" | "demo_discovery";
}

export interface PresenceHistory {
  items: PresenceEvent[];
  limit: number;
  offset: number;
  total: number;
  next_offset: number | null;
}

export interface RefreshSummary {
  source: "demo";
  observed: number;
  created: number;
  updated: number;
  transitions: number;
  pruned_events: number;
}
