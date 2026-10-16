import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import {
  cancelDiscoveryJob,
  isHostedDemo,
  loadDiscoveryJob,
  loadDiscoveryJobs,
  loadInterfaces,
  startDiscoveryJob,
} from "./api";
import type { DiscoveryJob, NetworkInterface } from "./types";

interface DiscoverySectionProps {
  onInventoryChanged: () => Promise<void>;
}

const jobLabel = (job: DiscoveryJob) => {
  if (job.state === "queued") return isHostedDemo ? "Queued — browser simulator preparing" : "Queued — waiting for offline worker";
  if (job.state === "running" && job.cancellation_requested) {
    return "Running — cancellation requested";
  }
  if (job.state === "running") return isHostedDemo ? "Simulation running in this browser" : "Actively running in offline worker";
  return job.state.charAt(0).toUpperCase() + job.state.slice(1);
};

export default function DiscoverySection({
  onInventoryChanged,
}: DiscoverySectionProps) {
  const [interfaces, setInterfaces] = useState<NetworkInterface[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [selectedAddress, setSelectedAddress] = useState("");
  const [targetCidr, setTargetCidr] = useState("");
  const [jobs, setJobs] = useState<DiscoveryJob[]>([]);
  const [currentJob, setCurrentJob] = useState<DiscoveryJob | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const handledCompletions = useRef(new Set<string>());

  const selectedInterface = useMemo(
    () => interfaces.find((item) => item.id === selectedId) ?? null,
    [interfaces, selectedId],
  );
  const selectedAddressRecord = selectedInterface?.ipv4_addresses.find(
    (item) => item.address === selectedAddress,
  );

  const refreshJobs = async () => {
    const listing = await loadDiscoveryJobs();
    setJobs(listing.items);
    const active = listing.items.find(
      (job) => job.state === "queued" || job.state === "running",
    );
    if (active) setCurrentJob(active);
  };

  useEffect(() => {
    let active = true;
    Promise.all([loadInterfaces(), loadDiscoveryJobs()])
      .then(([available, listing]) => {
        if (!active) return;
        setInterfaces(available);
        setJobs(listing.items);
        const existing = listing.items.find(
          (job) => job.state === "queued" || job.state === "running",
        );
        if (existing) setCurrentJob(existing);
        const initial = available.find((item) => item.eligible) ?? available[0];
        if (initial) {
          const address = initial.ipv4_addresses[0];
          setSelectedId(initial.id);
          setSelectedAddress(address?.address ?? "");
          setTargetCidr(address?.network ?? "");
        }
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(reason instanceof Error ? reason.message : "Discovery is unavailable.");
        }
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!currentJob || !["queued", "running"].includes(currentJob.state)) return;
    let active = true;
    const timer = window.setInterval(() => {
      loadDiscoveryJob(currentJob.id)
        .then(async (job) => {
          if (!active) return;
          setCurrentJob(job);
          if (job.state === "completed" && !handledCompletions.current.has(job.id)) {
            handledCompletions.current.add(job.id);
            await onInventoryChanged();
          }
          if (!["queued", "running"].includes(job.state)) await refreshJobs();
        })
        .catch((reason: unknown) => {
          if (active) setError(reason instanceof Error ? reason.message : "Job status failed.");
        });
    }, 1000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [currentJob?.id, currentJob?.state, onInventoryChanged]);

  const chooseInterface = (id: string) => {
    const next = interfaces.find((item) => item.id === id);
    const address = next?.ipv4_addresses[0];
    setSelectedId(id);
    setSelectedAddress(address?.address ?? "");
    setTargetCidr(address?.network ?? "");
    setError(null);
  };

  const chooseAddress = (address: string) => {
    const record = selectedInterface?.ipv4_addresses.find(
      (item) => item.address === address,
    );
    setSelectedAddress(address);
    if (record) setTargetCidr(record.network);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (submitting || !selectedInterface) return;
    setSubmitting(true);
    setError(null);
    try {
      const job = await startDiscoveryJob({
        interface_id: selectedInterface.id,
        selected_ipv4_address: selectedAddress,
        target_cidr: targetCidr,
      });
      setCurrentJob(job);
      await refreshJobs();
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "The job was not created.");
    } finally {
      setSubmitting(false);
    }
  };

  const cancel = async () => {
    if (!currentJob) return;
    try {
      const job = await cancelDiscoveryJob(currentJob.id);
      setCurrentJob(job);
      await refreshJobs();
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Cancellation failed.");
    }
  };

  return (
    <section className="discovery-panel" aria-labelledby="discovery-heading">
      <div className="section-heading">
        <div>
          <p className="section-kicker">Controlled workflow</p>
          <h2 id="discovery-heading">Discovery demonstration</h2>
        </div>
        <strong className="demo-chip">Synthetic demo only</strong>
      </div>
      <p className="discovery-intro">
        Choose an explicit interface address and private IPv4 scope. {isHostedDemo
          ? "This visible browser simulation uses deterministic fixtures and never contacts a network."
          : "The separate offline worker generates deterministic fixtures; it sends no packets and does not scan local-metadata interfaces."}
      </p>

      {loading ? (
        <p role="status">Loading interface metadata…</p>
      ) : (
        <form className="discovery-form" onSubmit={submit}>
          <label>
            <span>Network interface</span>
            <select value={selectedId} onChange={(event) => chooseInterface(event.target.value)}>
              {interfaces.map((item) => (
                <option key={item.id} value={item.id} disabled={!item.eligible}>
                  {item.name} · {item.source} · {item.eligible ? "eligible" : item.ineligible_reason}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Selected IPv4 address</span>
            <select value={selectedAddress} onChange={(event) => chooseAddress(event.target.value)}>
              {selectedInterface?.ipv4_addresses.map((item) => (
                <option key={item.address} value={item.address}>{item.address} · {item.network}</option>
              ))}
            </select>
          </label>
          <label>
            <span>Target IPv4 CIDR</span>
            <input
              value={targetCidr}
              onChange={(event) => setTargetCidr(event.target.value)}
              inputMode="text"
              spellCheck={false}
              aria-describedby="scope-help"
            />
          </label>
          <button
            type="submit"
            disabled={
              submitting ||
              !selectedInterface?.eligible ||
              selectedInterface.source !== "demo" ||
              currentJob?.state === "queued" ||
              currentJob?.state === "running"
            }
          >
            {submitting ? "Creating…" : "Start demo discovery"}
          </button>
          <p id="scope-help" className="scope-help">
            RFC1918 IPv4 only, entirely within the selected connected network,
            canonical CIDR, and no more than 256 total addresses. Current network: {selectedAddressRecord?.network ?? "none"}.
          </p>
        </form>
      )}

      {error && <p className="inline-error" role="alert">Discovery: {error}</p>}
      {currentJob && (
        <div className="current-job" aria-live="polite">
          <div>
            <span>Current job</span>
            <strong>{jobLabel(currentJob)}</strong>
            <small><code>{currentJob.scope.target_cidr}</code> · {currentJob.progress_processed}/{currentJob.progress_total} processed · {currentJob.progress_discovered} synthetic devices</small>
            <progress value={currentJob.progress_processed} max={currentJob.progress_total} aria-label="Simulated discovery progress" />
            {currentJob.failure_message && <p className="inline-error">{currentJob.failure_message}</p>}
          </div>
          {["queued", "running"].includes(currentJob.state) && (
            <button className="quiet-button" type="button" onClick={cancel} disabled={currentJob.cancellation_requested}>
              {currentJob.cancellation_requested ? "Cancellation requested" : "Cancel job"}
            </button>
          )}
        </div>
      )}

      <div className="recent-jobs">
        <h3>Recent jobs</h3>
        {jobs.length === 0 ? <p>No discovery jobs yet.</p> : (
          <ul>
            {jobs.map((job) => (
              <li key={job.id}>
                <span className={`job-state job-${job.state}`}>{job.state}</span>
                <code>{job.scope.target_cidr}</code>
                <span>{job.progress_discovered} found</span>
                {job.failure_message && <small>{job.failure_message}</small>}
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
