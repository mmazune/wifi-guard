import { apiService } from "./apiService";
import { demoService } from "./demoService";

const configuredMode = import.meta.env.VITE_DATA_MODE;

if (configuredMode && configuredMode !== "api" && configuredMode !== "hosted") {
  throw new Error(`Unsupported VITE_DATA_MODE: ${configuredMode}`);
}

export const service = configuredMode === "hosted" ? demoService : apiService;
export const isHostedDemo = service.mode === "hosted";
export const loadDashboard = service.loadDashboard.bind(service);
export const loadDevices = service.loadDevices.bind(service);
export const loadDeviceDetails = service.loadDeviceDetails.bind(service);
export const updateDeviceName = service.updateDeviceName.bind(service);
export const refreshDemoInventory = service.refreshDemoInventory.bind(service);
export const loadInterfaces = service.loadInterfaces.bind(service);
export const loadDiscoveryJobs = service.loadDiscoveryJobs.bind(service);
export const loadDiscoveryJob = service.loadDiscoveryJob.bind(service);
export const startDiscoveryJob = service.startDiscoveryJob.bind(service);
export const cancelDiscoveryJob = service.cancelDiscoveryJob.bind(service);
export const resetDemo = service.resetDemo?.bind(service);
export const getStorageNotice = () => service.storageNotice?.() ?? null;
