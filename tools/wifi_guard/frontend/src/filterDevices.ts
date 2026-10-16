import type { Device, DeviceStatus } from "./types";

export type StatusFilter = "all" | DeviceStatus;

export function filterDevices(
  devices: Device[],
  query: string,
  status: StatusFilter,
): Device[] {
  const normalizedQuery = query.trim().toLocaleLowerCase();
  return devices.filter((device) => {
    const matchesStatus = status === "all" || device.status === status;
    const matchesQuery =
      normalizedQuery.length === 0 ||
      [device.display_name, device.ipv4_address, device.mac_address].some(
        (value) => value.toLocaleLowerCase().includes(normalizedQuery),
      );
    return matchesStatus && matchesQuery;
  });
}
