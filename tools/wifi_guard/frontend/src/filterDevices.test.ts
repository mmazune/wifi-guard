import { describe, expect, it } from "vitest";

import { filterDevices } from "./filterDevices";
import type { Device } from "./types";

const devices: Device[] = [
  {
    id: "one",
    display_name: "Studio laptop",
    ipv4_address: "192.168.50.12",
    mac_address: "02:00:00:00:10:01",
    status: "online",
    connection_type: "wifi",
    data_source: "demo",
    provider_name: "Studio laptop",
    custom_name: null,
    first_seen: "2026-10-14T12:00:00+00:00",
    last_seen: "2026-10-14T12:00:00+00:00",
  },
  {
    id: "two",
    display_name: "Guest phone",
    ipv4_address: "192.168.50.37",
    mac_address: "02:00:00:00:10:03",
    status: "offline",
    connection_type: "wifi",
    data_source: "demo",
    provider_name: "Guest phone",
    custom_name: null,
    first_seen: "2026-10-14T12:00:00+00:00",
    last_seen: null,
  },
];

describe("filterDevices", () => {
  it.each(["studio", "192.168.50.12", "02:00:00:00:10:01"])(
    "matches name, IP, or MAC using %s",
    (query) => expect(filterDevices(devices, query, "all")).toEqual([devices[0]]),
  );

  it("combines status and search filters", () => {
    expect(filterDevices(devices, "phone", "offline")).toEqual([devices[1]]);
    expect(filterDevices(devices, "phone", "online")).toEqual([]);
  });
});
