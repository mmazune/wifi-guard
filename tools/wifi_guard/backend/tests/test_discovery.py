import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient as FastAPITestClient

from wifi_guard_api.config import Settings
from wifi_guard_api.discovery import DiscoveryCancelled, FakeDiscoveryAdapter
from wifi_guard_api.interfaces import DemoInterfaceProvider, ScopeValidationError, validate_scope
from wifi_guard_api.main import create_app
from wifi_guard_api.models import (
    ConnectionType,
    DiscoveryScope,
    InterfaceIPv4,
    InterfaceSource,
    NetworkInterface,
    ProviderDevice,
)
from wifi_guard_api.storage import InventoryStore, InvalidJobTransitionError
from wifi_guard_api.worker import OfflineDiscoveryWorker


class TestClient(FastAPITestClient):
    def __init__(self, *args: object, **kwargs: object) -> None:
        kwargs.setdefault("base_url", "http://127.0.0.1")
        super().__init__(*args, **kwargs)


VALID_SCOPE = {
    "interface_id": "demo-private-1",
    "selected_ipv4_address": "192.168.50.10",
    "target_cidr": "192.168.50.0/24",
}


class ManualClock:
    def __init__(self) -> None:
        self.value = datetime(2026, 10, 15, 8, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.value

    def advance(self, seconds: int) -> None:
        self.value += timedelta(seconds=seconds)


class MutableInterfaceProvider:
    source = InterfaceSource.DEMO

    def __init__(self, interfaces: list[NetworkInterface] | None = None) -> None:
        self.interfaces = interfaces or DemoInterfaceProvider().list_interfaces()

    def list_interfaces(self) -> list[NetworkInterface]:
        return [item.model_copy(deep=True) for item in self.interfaces]


class LocalFixtureProvider(MutableInterfaceProvider):
    source = InterfaceSource.LOCAL_METADATA

    def __init__(self) -> None:
        interface = DemoInterfaceProvider().list_interfaces()[0].model_copy(
            update={"id": "local0", "name": "local0", "source": self.source}
        )
        super().__init__([interface])


class EmptyAdapter:
    def discover(self, scope, progress, cancelled):  # type: ignore[no-untyped-def]
        progress(1, 0)
        return []


def app_settings(path: Path, retention: int = 100) -> Settings:
    return Settings(database_path=path, job_retention_limit=retention)


def test_interface_inventory_includes_eligibility_and_actual_netmasks(
    tmp_path: Path,
) -> None:
    with TestClient(create_app(app_settings(tmp_path / "db"))) as client:
        interfaces = client.get("/api/network/interfaces").json()

    assert interfaces[0]["source"] == "demo"
    assert interfaces[0]["connection_type"] == "unknown"
    assert interfaces[0]["ipv4_addresses"][0] == {
        "address": "192.168.50.10",
        "netmask": "255.255.255.0",
        "network": "192.168.50.0/24",
    }
    assert interfaces[0]["eligible"] is True
    assert interfaces[2]["eligible"] is False
    assert interfaces[2]["ineligible_reason"] == "The interface is down."


@pytest.mark.parametrize(
    ("target", "message"),
    [
        ("192.168.50.1/24", "canonical network"),
        ("192.168.49.0/24", "directly connected"),
        ("192.168.48.0/22", "at most 256"),
        ("8.8.8.0/24", "RFC1918"),
        ("127.0.0.0/24", "Loopback"),
        ("169.254.1.0/24", "Link-local"),
        ("224.0.0.0/24", "Multicast"),
        ("fd00::/120", "IPv6"),
        ("not-a-cidr", "malformed"),
    ],
)
def test_scope_rejections_are_specific(target: str, message: str) -> None:
    scope = DiscoveryScope(**{**VALID_SCOPE, "target_cidr": target})
    with pytest.raises(ScopeValidationError, match=message):
        validate_scope(scope, DemoInterfaceProvider())


def test_selected_address_and_interface_must_be_current() -> None:
    with pytest.raises(ScopeValidationError, match="assigned"):
        validate_scope(
            DiscoveryScope(**{**VALID_SCOPE, "selected_ipv4_address": "192.168.50.11"}),
            DemoInterfaceProvider(),
        )
    with pytest.raises(ScopeValidationError, match="no longer exists"):
        validate_scope(
            DiscoveryScope(**{**VALID_SCOPE, "interface_id": "missing"}),
            DemoInterfaceProvider(),
        )


def test_local_metadata_can_validate_but_cannot_create_real_job(tmp_path: Path) -> None:
    provider = LocalFixtureProvider()
    payload = {
        "interface_id": "local0",
        "selected_ipv4_address": "192.168.50.10",
        "target_cidr": "192.168.50.0/24",
    }
    with TestClient(
        create_app(
            Settings(database_path=tmp_path / "db", interface_source="local_metadata"),
            interface_provider=provider,
        )
    ) as client:
        interfaces = client.get("/api/network/interfaces").json()
        response = client.post("/api/discovery/jobs", json=payload)

    assert interfaces[0]["source"] == "local_metadata"
    assert response.status_code == 409
    assert "Real discovery is unavailable" in response.json()["detail"]


def test_concurrent_submission_allows_only_one_active_job(tmp_path: Path) -> None:
    with TestClient(create_app(app_settings(tmp_path / "db"))) as client:
        with ThreadPoolExecutor(max_workers=6) as executor:
            responses = list(
                executor.map(
                    lambda _: client.post("/api/discovery/jobs", json=VALID_SCOPE),
                    range(6),
                )
            )
    assert [response.status_code for response in responses].count(201) == 1
    assert [response.status_code for response in responses].count(409) == 5


def test_atomic_claim_and_terminal_state_cannot_run_again(tmp_path: Path) -> None:
    app = create_app(app_settings(tmp_path / "db"))
    with TestClient(app) as client:
        job_id = client.post("/api/discovery/jobs", json=VALID_SCOPE).json()["id"]
        store = app.state.inventory_store
        with ThreadPoolExecutor(max_workers=4) as executor:
            claims = list(executor.map(lambda i: store.claim_discovery_job(f"w{i}", 30), range(4)))
        claimed = [job for job in claims if job is not None]
        assert len(claimed) == 1
        store.complete_discovery_job(job_id, claimed[0].worker_id, [])
        assert store.claim_discovery_job("later", 30) is None
        with pytest.raises(InvalidJobTransitionError):
            store.complete_discovery_job(job_id, claimed[0].worker_id, [])


def test_queued_and_running_cancellation_are_idempotent(tmp_path: Path) -> None:
    app = create_app(app_settings(tmp_path / "db"))
    with TestClient(app) as client:
        queued = client.post("/api/discovery/jobs", json=VALID_SCOPE).json()
        first = client.post(f"/api/discovery/jobs/{queued['id']}/cancel").json()
        second = client.post(f"/api/discovery/jobs/{queued['id']}/cancel").json()
        assert first["state"] == second["state"] == "cancelled"

        running = client.post("/api/discovery/jobs", json=VALID_SCOPE).json()
        claimed = app.state.inventory_store.claim_discovery_job("worker", 30)
        requested = client.post(f"/api/discovery/jobs/{running['id']}/cancel").json()
        assert requested["state"] == "running"
        assert requested["cancellation_requested"] is True
        final = app.state.inventory_store.cancel_claimed_discovery_job(
            running["id"], claimed.worker_id
        )
        assert final.state.value == "cancelled"


def test_worker_revalidates_fresh_metadata_before_execution(tmp_path: Path) -> None:
    provider = MutableInterfaceProvider()
    app = create_app(
        app_settings(tmp_path / "db"), interface_provider=provider
    )
    with TestClient(app) as client:
        job = client.post("/api/discovery/jobs", json=VALID_SCOPE).json()
        provider.interfaces = []
        worker = OfflineDiscoveryWorker(
            app.state.inventory_store, provider, FakeDiscoveryAdapter(), 30, "worker"
        )
        assert worker.process_one() is True
        failed = client.get(f"/api/discovery/jobs/{job['id']}").json()
    assert failed["state"] == "failed"
    assert failed["failure_code"] == "scope_changed"


def test_worker_completion_is_transactional_and_preserves_names_and_presence(
    tmp_path: Path,
) -> None:
    app = create_app(app_settings(tmp_path / "db"))
    with TestClient(app) as client:
        first = client.post("/api/discovery/jobs", json=VALID_SCOPE).json()
        worker = OfflineDiscoveryWorker(
            app.state.inventory_store,
            DemoInterfaceProvider(),
            FakeDiscoveryAdapter(),
            30,
            "worker-a",
        )
        worker.process_one()
        completed = client.get(f"/api/discovery/jobs/{first['id']}").json()
        discovered = [
            device
            for device in client.get("/api/devices").json()
            if device["data_source"] == "demo_discovery"
        ]
        target = discovered[0]
        client.patch(
            f"/api/devices/{target['id']}", json={"custom_name": "Kept name"}
        )

        second = client.post("/api/discovery/jobs", json=VALID_SCOPE).json()
        OfflineDiscoveryWorker(
            app.state.inventory_store,
            DemoInterfaceProvider(),
            EmptyAdapter(),
            30,
            "worker-b",
        ).process_one()
        after = client.get(f"/api/devices/{target['id']}").json()
        history = client.get(f"/api/devices/{target['id']}/history").json()

    assert completed["state"] == "completed"
    assert completed["progress_processed"] == 256
    assert completed["progress_discovered"] == 3
    assert after["custom_name"] == "Kept name"
    assert after["status"] == "online"
    assert history["total"] == 1
    assert second["state"] == "queued"


def test_adapter_failure_and_cancel_do_not_ingest_partial_results(tmp_path: Path) -> None:
    class PartialFailureAdapter:
        def discover(self, scope, progress, cancelled):  # type: ignore[no-untyped-def]
            progress(1, 1)
            raise RuntimeError("private path /tmp/secret")

    app = create_app(app_settings(tmp_path / "db"))
    with TestClient(app) as client:
        job = client.post("/api/discovery/jobs", json=VALID_SCOPE).json()
        OfflineDiscoveryWorker(
            app.state.inventory_store,
            DemoInterfaceProvider(),
            PartialFailureAdapter(),
            30,
            "worker",
        ).process_one()
        failed = client.get(f"/api/discovery/jobs/{job['id']}").json()
        devices = client.get("/api/devices").json()

    assert failed["state"] == "failed"
    assert failed["failure_message"] == "The offline discovery adapter failed."
    assert all(device["data_source"] != "demo_discovery" for device in devices)


def test_running_cancellation_discards_adapter_results(tmp_path: Path) -> None:
    app = create_app(app_settings(tmp_path / "db"))

    class CancellingAdapter:
        def discover(self, scope, progress, cancelled):  # type: ignore[no-untyped-def]
            progress(1, 1)
            running = app.state.inventory_store.list_discovery_jobs(1, 0).items[0]
            app.state.inventory_store.cancel_discovery_job(running.id)
            progress(2, 1)
            if cancelled():
                raise DiscoveryCancelled
            return []

    with TestClient(app) as client:
        job = client.post("/api/discovery/jobs", json=VALID_SCOPE).json()
        OfflineDiscoveryWorker(
            app.state.inventory_store,
            DemoInterfaceProvider(),
            CancellingAdapter(),
            30,
            "worker",
        ).process_one()
        cancelled = client.get(f"/api/discovery/jobs/{job['id']}").json()
        devices = client.get("/api/devices").json()

    assert cancelled["state"] == "cancelled"
    assert all(device["data_source"] != "demo_discovery" for device in devices)


def test_expired_worker_lease_fails_without_rerun(tmp_path: Path) -> None:
    clock = ManualClock()
    app = create_app(app_settings(tmp_path / "db"), clock=clock)
    with TestClient(app) as client:
        job = client.post("/api/discovery/jobs", json=VALID_SCOPE).json()
        claimed = app.state.inventory_store.claim_discovery_job("lost", 5)
        assert claimed is not None
        clock.advance(6)
        assert app.state.inventory_store.claim_discovery_job("replacement", 5) is None
        recovered = client.get(f"/api/discovery/jobs/{job['id']}").json()
    assert recovered["state"] == "failed"
    assert recovered["failure_code"] == "worker_lost"


def test_job_pagination_retention_and_request_protections(tmp_path: Path) -> None:
    app = create_app(app_settings(tmp_path / "db", retention=2))
    with TestClient(app) as client:
        for _ in range(3):
            job = client.post("/api/discovery/jobs", json=VALID_SCOPE).json()
            client.post(f"/api/discovery/jobs/{job['id']}/cancel")
        listing = client.get("/api/discovery/jobs?limit=1&offset=0").json()
        bad_origin = client.post(
            "/api/discovery/jobs",
            json=VALID_SCOPE,
            headers={"Origin": "http://attacker.invalid"},
        )
        no_origin = client.post("/api/discovery/jobs", json=VALID_SCOPE)
        bad_host = client.get("/api/health", headers={"Host": "attacker.invalid"})

    assert listing["total"] == 2
    assert len(listing["items"]) == 1
    assert listing["next_offset"] == 1
    assert bad_origin.status_code == 403
    assert no_origin.status_code == 201
    assert bad_host.status_code == 400


def test_worker_startup_imports_no_scapy_modules() -> None:
    before = {name for name in sys.modules if name == "scapy" or name.startswith("scapy.")}
    __import__("wifi_guard_api.worker")
    after = {name for name in sys.modules if name == "scapy" or name.startswith("scapy.")}
    assert after == before
