import argparse
import logging
import signal
import threading
from collections.abc import Sequence
from uuid import uuid4

from .config import Settings
from .discovery import DiscoveryAdapter, DiscoveryCancelled, FakeDiscoveryAdapter
from .interfaces import DemoInterfaceProvider, InterfaceProvider, ScopeValidationError, validate_scope
from .models import DiscoveryJob
from .storage import InventoryStore, InvalidJobTransitionError, PersistenceError


log = logging.getLogger(__name__)


class OfflineDiscoveryWorker:
    def __init__(
        self,
        store: InventoryStore,
        interface_provider: InterfaceProvider,
        adapter: DiscoveryAdapter,
        lease_seconds: int,
        worker_id: str | None = None,
    ) -> None:
        self.store = store
        self.interface_provider = interface_provider
        self.adapter = adapter
        self.lease_seconds = lease_seconds
        self.worker_id = worker_id or f"offline-{uuid4()}"
        self.stop_event = threading.Event()

    def stop(self) -> None:
        self.stop_event.set()

    def process_one(self) -> bool:
        job = self.store.claim_discovery_job(self.worker_id, self.lease_seconds)
        if job is None:
            return False
        self._execute(job)
        return True

    def _execute(self, job: DiscoveryJob) -> None:
        if job.mode != "demo" or job.source.value != "demo":
            self.store.fail_discovery_job(
                job.id,
                self.worker_id,
                "unsupported_source",
                "Only synthetic demo discovery jobs can execute.",
            )
            return
        try:
            validated_scope, _, _ = validate_scope(job.scope, self.interface_provider)
        except ScopeValidationError as error:
            self.store.fail_discovery_job(
                job.id, self.worker_id, "scope_changed", str(error)
            )
            return

        cancellation_requested = False

        def update_progress(processed: int, discovered: int) -> None:
            nonlocal cancellation_requested
            cancellation_requested = self.store.update_discovery_progress(
                job.id,
                self.worker_id,
                processed,
                discovered,
                self.lease_seconds,
            )

        def cancelled() -> bool:
            return cancellation_requested or self.stop_event.is_set()

        try:
            observations = self.adapter.discover(
                validated_scope, update_progress, cancelled
            )
            if cancellation_requested:
                self.store.cancel_claimed_discovery_job(job.id, self.worker_id)
            elif self.stop_event.is_set():
                self.store.fail_discovery_job(
                    job.id,
                    self.worker_id,
                    "worker_stopped",
                    "The worker stopped before discovery completed.",
                )
            else:
                self.store.complete_discovery_job(
                    job.id, self.worker_id, observations
                )
        except DiscoveryCancelled:
            if cancellation_requested:
                self.store.cancel_claimed_discovery_job(job.id, self.worker_id)
            else:
                self.store.fail_discovery_job(
                    job.id,
                    self.worker_id,
                    "worker_stopped",
                    "The worker stopped before discovery completed.",
                )
        except InvalidJobTransitionError:
            return
        except Exception:
            log.debug("Offline discovery adapter failed", exc_info=True)
            self.store.fail_discovery_job(
                job.id,
                self.worker_id,
                "adapter_failed",
                "The offline discovery adapter failed.",
            )


def build_store(settings: Settings) -> InventoryStore:
    return InventoryStore(
        settings.database_path,
        settings.history_limit_per_device,
        job_retention_limit=settings.job_retention_limit,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WiFi Guard offline demo worker")
    parser.add_argument(
        "--once", action="store_true", help="Process at most one queued job"
    )
    args = parser.parse_args(argv)
    settings = Settings()
    store = build_store(settings)
    store.initialize()
    worker = OfflineDiscoveryWorker(
        store,
        DemoInterfaceProvider(),
        FakeDiscoveryAdapter(),
        settings.worker_lease_seconds,
    )

    def stop_worker(_: int, __: object) -> None:
        worker.stop()

    signal.signal(signal.SIGINT, stop_worker)
    signal.signal(signal.SIGTERM, stop_worker)
    try:
        while not worker.stop_event.is_set():
            processed = worker.process_one()
            if args.once:
                return 0
            if not processed:
                worker.stop_event.wait(settings.worker_poll_seconds)
    except PersistenceError:
        return 1
    finally:
        store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
