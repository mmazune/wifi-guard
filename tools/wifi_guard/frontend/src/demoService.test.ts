import { beforeEach, describe, expect, it, vi } from "vitest";

import { demoService } from "./demoService";

const scope = {
  interface_id: "presentation-lan",
  selected_ipv4_address: "192.168.50.10",
  target_cidr: "192.168.50.0/24",
};

beforeEach(async () => {
  vi.useRealTimers();
  await demoService.resetDemo?.();
});

describe("hosted demo adapter", () => {
  it("persists a custom name in browser-local state and resets it", async () => {
    const renamed = await demoService.updateDeviceName("studio-laptop", "Moses laptop");
    expect(renamed.display_name).toBe("Moses laptop");
    expect((await demoService.loadDevices())[0].display_name).toBe("Moses laptop");

    await demoService.resetDemo?.();
    expect((await demoService.loadDevices())[0].display_name).toBe("Studio laptop");
  });

  it("completes a deterministic simulated job without network requests", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    vi.useFakeTimers();
    const job = await demoService.startDiscoveryJob(scope);
    await vi.advanceTimersByTimeAsync(5000);
    const completed = await demoService.loadDiscoveryJob(job.id);

    expect(completed.state).toBe("completed");
    expect(completed.progress_discovered).toBe(6);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("supports cancellation before completion", async () => {
    const job = await demoService.startDiscoveryJob(scope);
    const cancelled = await demoService.cancelDiscoveryJob(job.id);
    expect(cancelled.state).toBe("cancelled");
    expect(cancelled.cancellation_requested).toBe(true);
  });
});
