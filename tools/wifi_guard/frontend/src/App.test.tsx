import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import type { Device } from "./types";

const device: Device = {
  id: "demo-laptop-01",
  display_name: "Studio laptop",
  provider_name: "Studio laptop",
  custom_name: null,
  ipv4_address: "192.168.50.12",
  mac_address: "02:00:00:00:10:01",
  status: "online",
  connection_type: "wifi",
  data_source: "demo",
  first_seen: "2026-10-14T12:00:00+00:00",
  last_seen: "2026-10-14T12:00:00+00:00",
};

const capabilities = {
  demo_device_inventory: { available: true, detail: "Synthetic inventory." },
  demo_discovery_jobs: { available: true, detail: "Synthetic jobs." },
  live_discovery: { available: false, detail: "Later." },
  traffic_capture: { available: false, detail: "Later." },
  device_ip_enforcement: { available: false, detail: "Later." },
  domain_enforcement: { available: false, detail: "Later." },
  exact_url_enforcement: { available: false, detail: "Later." },
};

const response = (body: unknown, ok = true, status = 200) =>
  Promise.resolve({ ok, status, json: () => Promise.resolve(body) });

function dashboardFetch(extra?: (url: string, init?: RequestInit) => unknown) {
  return vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const custom = extra?.(url, init);
    if (custom) return custom;
    if (url === "/api/health") {
      return response({ application: "WiFi Guard", version: "0.3.0", mode: "demo" });
    }
    if (url === "/api/capabilities") return response(capabilities);
    if (url === "/api/devices") return response([device]);
    if (url === "/api/network/interfaces") {
      return response([
        {
          id: "demo-private-1",
          name: "Synthetic private LAN",
          ipv4_addresses: [
            {
              address: "192.168.50.10",
              netmask: "255.255.255.0",
              network: "192.168.50.0/24",
            },
          ],
          connected_ipv4_networks: ["192.168.50.0/24"],
          is_up: true,
          is_loopback: false,
          connection_type: "unknown",
          source: "demo",
          eligible: true,
          ineligible_reason: null,
        },
      ]);
    }
    if (url === "/api/discovery/jobs?limit=10&offset=0") {
      return response({ items: [], limit: 10, offset: 0, total: 0, next_offset: null });
    }
    throw new Error(`Unhandled request: ${url}`);
  });
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("dashboard request states", () => {
  it("shows a loading state while the backend request is pending", () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)));

    render(<App />);

    expect(screen.getByText("Loading demo inventory")).toBeInTheDocument();
  });

  it("shows a retryable error without fallback devices", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        json: () => Promise.resolve({}),
      }),
    );

    render(<App />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The local backend could not be reached",
    );
    expect(screen.getByRole("button", { name: "Retry connection" })).toBeEnabled();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
});

describe("persisted inventory flows", () => {
  it("opens device details and paginated synthetic history", async () => {
    const fetch = dashboardFetch((url) => {
      if (url === "/api/devices/demo-laptop-01") return response(device);
      if (url.includes("/api/devices/demo-laptop-01/history")) {
        return response({
          items: [
            {
              event_id: 1,
              device_id: device.id,
              previous_status: null,
              new_status: "online",
              observed_at: device.first_seen,
              source: "demo",
            },
          ],
          limit: 5,
          offset: 0,
          total: 1,
          next_offset: null,
        });
      }
      return undefined;
    });
    vi.stubGlobal("fetch", fetch);
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "Studio laptop" }));

    expect(await screen.findByRole("heading", { name: "Presence history" })).toBeInTheDocument();
    expect(screen.getByText("Initial status: online")).toBeInTheDocument();
    expect(screen.getByText(/no network activity was captured/i)).toBeInTheDocument();
  });

  it("keeps the old name visible when saving fails", async () => {
    const fetch = dashboardFetch((url, init) => {
      if (url === "/api/devices/demo-laptop-01" && init?.method === "PATCH") {
        return response({ detail: "Inventory storage is unavailable." }, false, 503);
      }
      if (url === "/api/devices/demo-laptop-01") return response(device);
      if (url.includes("/history")) {
        return response({ items: [], limit: 5, offset: 0, total: 0, next_offset: null });
      }
      return undefined;
    });
    vi.stubGlobal("fetch", fetch);
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Studio laptop" }));
    const input = await screen.findByLabelText("User-assigned name");
    fireEvent.change(input, { target: { value: "My laptop" } });
    fireEvent.click(screen.getByRole("button", { name: "Save name" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Inventory storage is unavailable.",
    );
    expect(screen.getAllByText("Studio laptop").length).toBeGreaterThan(0);
  });

  it("prevents duplicate refreshes and reports the persisted result", async () => {
    let resolveRefresh!: (value: unknown) => void;
    const pending = new Promise((resolve) => {
      resolveRefresh = resolve;
    });
    const fetch = dashboardFetch((url, init) => {
      if (url === "/api/inventory/refresh" && init?.method === "POST") {
        return pending;
      }
      return undefined;
    });
    vi.stubGlobal("fetch", fetch);
    render(<App />);
    const button = await screen.findByRole("button", { name: "Refresh demo inventory" });

    fireEvent.click(button);
    expect(screen.getByRole("button", { name: "Refreshing…" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Refreshing…" }));
    expect(fetch.mock.calls.filter(([url]) => url === "/api/inventory/refresh")).toHaveLength(1);

    resolveRefresh({
      ok: true,
      status: 200,
      json: () => Promise.resolve({
        source: "demo",
        observed: 1,
        created: 0,
        updated: 1,
        transitions: 0,
        pruned_events: 0,
      }),
    });
    await waitFor(() => {
      expect(screen.getByText(/Refreshed 1 synthetic devices/)).toBeInTheDocument();
    });
  });
});

describe("offline discovery", () => {
  it("shows queued worker absence and supports cancellation", async () => {
    const queued = {
      id: "job-1",
      mode: "demo",
      source: "demo",
      scope: {
        interface_id: "demo-private-1",
        selected_ipv4_address: "192.168.50.10",
        target_cidr: "192.168.50.0/24",
      },
      state: "queued",
      created_at: "2026-10-15T08:00:00+00:00",
      started_at: null,
      finished_at: null,
      progress_total: 256,
      progress_processed: 0,
      progress_discovered: 0,
      failure_code: null,
      failure_message: null,
      cancellation_requested: false,
      worker_id: null,
      lease_expires_at: null,
    };
    const fetch = dashboardFetch((url, init) => {
      if (url === "/api/discovery/jobs" && init?.method === "POST") {
        return response(queued);
      }
      if (url === "/api/discovery/jobs/job-1/cancel") {
        return response({
          ...queued,
          state: "cancelled",
          cancellation_requested: true,
          finished_at: "2026-10-15T08:01:00+00:00",
        });
      }
      return undefined;
    });
    vi.stubGlobal("fetch", fetch);
    render(<App />);

    fireEvent.click(
      await screen.findByRole("button", { name: "Start demo discovery" }),
    );
    expect(
      await screen.findByText("Queued — waiting for offline worker"),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Cancel job" }));
    expect(await screen.findByText("Cancelled")).toBeInTheDocument();
  });
});
