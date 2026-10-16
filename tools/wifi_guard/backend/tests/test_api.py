import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient as FastAPITestClient
from pydantic import ValidationError

from wifi_guard_api.config import Settings
from wifi_guard_api.main import create_app
from wifi_guard_api.models import DeviceStatus, ProviderDevice
from wifi_guard_api.storage import SCHEMA_VERSION


class TestClient(FastAPITestClient):
    def __init__(self, *args: object, **kwargs: object) -> None:
        kwargs.setdefault("base_url", "http://127.0.0.1")
        super().__init__(*args, **kwargs)


class ManualClock:
    def __init__(self) -> None:
        self.value = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.value

    def advance(self) -> None:
        self.value += timedelta(minutes=1)


class MutableProvider:
    def __init__(self, status: DeviceStatus = DeviceStatus.ONLINE) -> None:
        self.status = status
        self.name = "Provider laptop"

    def list_devices(self) -> list[ProviderDevice]:
        return [
            ProviderDevice(
                provider_identity="demo-test-01",
                provider_name=self.name,
                ipv4_address="192.168.50.99",
                mac_address="02:00:00:00:99:01",
                status=self.status,
                connection_type="wifi",
                data_source="demo",
            )
        ]


def settings(database_path: Path, history_limit: int = 100) -> Settings:
    return Settings(
        database_path=database_path,
        history_limit_per_device=history_limit,
    )


def test_health_and_capabilities_are_truthful(tmp_path: Path) -> None:
    with TestClient(create_app(settings(tmp_path / "inventory.db"))) as client:
        health = client.get("/api/health")
        capabilities = client.get("/api/capabilities").json()

    assert health.json() == {
        "application": "WiFi Guard",
        "version": "0.3.0",
        "mode": "demo",
    }
    assert capabilities["demo_device_inventory"]["available"] is True
    assert all(
        capability["available"] is False
        for name, capability in capabilities.items()
        if name not in {"demo_device_inventory", "demo_discovery_jobs"}
    )


def test_fresh_database_has_schema_and_seeded_inventory(tmp_path: Path) -> None:
    database_path = tmp_path / "nested" / "inventory.db"
    with TestClient(create_app(settings(database_path))) as client:
        devices = client.get("/api/devices").json()

    assert database_path.exists()
    assert [device["id"] for device in devices] == [
        "demo-laptop-01",
        "demo-tv-01",
        "demo-phone-01",
        "demo-sensor-01",
    ]
    assert all(device["data_source"] == "demo" for device in devices)
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT MAX(version) FROM schema_migrations"
        ).fetchone()[0] == SCHEMA_VERSION


def test_startup_is_idempotent_and_records_survive_restart(tmp_path: Path) -> None:
    database_path = tmp_path / "inventory.db"
    with TestClient(create_app(settings(database_path))) as client:
        renamed = client.patch(
            "/api/devices/demo-laptop-01", json={"custom_name": "Moses laptop"}
        )
        assert renamed.status_code == 200

    with TestClient(create_app(settings(database_path))) as client:
        device = client.get("/api/devices/demo-laptop-01").json()
        history = client.get("/api/devices/demo-laptop-01/history").json()

    assert device["custom_name"] == "Moses laptop"
    assert device["display_name"] == "Moses laptop"
    assert history["total"] == 1


def test_v1_database_migrates_without_losing_inventory(tmp_path: Path) -> None:
    database_path = tmp_path / "inventory.db"
    with TestClient(create_app(settings(database_path))) as client:
        client.patch(
            "/api/devices/demo-laptop-01", json={"custom_name": "Preserved"}
        )
    with sqlite3.connect(database_path) as connection:
        connection.execute("DROP TABLE discovery_jobs")
        connection.execute("DELETE FROM schema_migrations WHERE version = 2")

    with TestClient(create_app(settings(database_path))) as client:
        device = client.get("/api/devices/demo-laptop-01").json()
        jobs = client.get("/api/discovery/jobs").json()

    assert device["custom_name"] == "Preserved"
    assert jobs["items"] == []
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT MAX(version) FROM schema_migrations"
        ).fetchone()[0] == 2


def test_custom_name_survives_refresh_and_can_be_cleared(tmp_path: Path) -> None:
    provider = MutableProvider()
    with TestClient(
        create_app(settings(tmp_path / "inventory.db"), provider=provider)
    ) as client:
        response = client.patch(
            "/api/devices/demo-test-01", json={"custom_name": "Desk machine"}
        )
        assert response.json()["display_name"] == "Desk machine"
        provider.name = "Renamed by provider"
        client.post("/api/inventory/refresh")
        refreshed = client.get("/api/devices/demo-test-01").json()
        cleared = client.patch(
            "/api/devices/demo-test-01", json={"custom_name": None}
        ).json()

    assert refreshed["provider_name"] == "Renamed by provider"
    assert refreshed["display_name"] == "Desk machine"
    assert cleared["custom_name"] is None
    assert cleared["display_name"] == "Renamed by provider"


@pytest.mark.parametrize(
    "payload",
    [
        {"custom_name": "   "},
        {"custom_name": "x" * 81},
        {"custom_name": "valid", "status": "offline"},
        {},
    ],
)
def test_invalid_name_updates_are_rejected(
    tmp_path: Path, payload: dict[str, str | None]
) -> None:
    with TestClient(create_app(settings(tmp_path / "inventory.db"))) as client:
        response = client.patch("/api/devices/demo-laptop-01", json=payload)

    assert response.status_code == 422


def test_unknown_devices_return_404(tmp_path: Path) -> None:
    with TestClient(create_app(settings(tmp_path / "inventory.db"))) as client:
        assert client.get("/api/devices/missing").status_code == 404
        assert client.patch(
            "/api/devices/missing", json={"custom_name": "Name"}
        ).status_code == 404
        assert client.get("/api/devices/missing/history").status_code == 404


def test_unchanged_status_has_no_duplicate_event_and_refresh_is_accurate(
    tmp_path: Path,
) -> None:
    provider = MutableProvider()
    with TestClient(
        create_app(settings(tmp_path / "inventory.db"), provider=provider)
    ) as client:
        summary = client.post("/api/inventory/refresh").json()
        history = client.get("/api/devices/demo-test-01/history").json()

    assert summary == {
        "source": "demo",
        "observed": 1,
        "created": 0,
        "updated": 1,
        "transitions": 0,
        "pruned_events": 0,
    }
    assert history["total"] == 1


def test_transitions_and_offline_last_seen_semantics(tmp_path: Path) -> None:
    provider = MutableProvider()
    clock = ManualClock()
    with TestClient(
        create_app(settings(tmp_path / "inventory.db"), provider, clock)
    ) as client:
        original = client.get("/api/devices/demo-test-01").json()
        clock.advance()
        provider.status = DeviceStatus.OFFLINE
        summary = client.post("/api/inventory/refresh").json()
        offline = client.get("/api/devices/demo-test-01").json()
        events = client.get("/api/devices/demo-test-01/history").json()["items"]

    assert summary["transitions"] == 1
    assert offline["last_seen"] == original["last_seen"]
    assert events[0]["previous_status"] == "online"
    assert events[0]["new_status"] == "offline"


def test_history_pagination_and_retention(tmp_path: Path) -> None:
    provider = MutableProvider()
    clock = ManualClock()
    with TestClient(
        create_app(
            settings(tmp_path / "inventory.db", history_limit=3), provider, clock
        )
    ) as client:
        for status in [
            DeviceStatus.OFFLINE,
            DeviceStatus.ONLINE,
            DeviceStatus.OFFLINE,
            DeviceStatus.ONLINE,
        ]:
            clock.advance()
            provider.status = status
            client.post("/api/inventory/refresh")
        first = client.get(
            "/api/devices/demo-test-01/history", params={"limit": 2, "offset": 0}
        ).json()
        second = client.get(
            "/api/devices/demo-test-01/history", params={"limit": 2, "offset": 2}
        ).json()
        invalid = client.get(
            "/api/devices/demo-test-01/history", params={"limit": 101}
        )

    assert first["total"] == 3
    assert len(first["items"]) == 2
    assert first["next_offset"] == 2
    assert len(second["items"]) == 1
    assert second["next_offset"] is None
    assert invalid.status_code == 422
    timestamps = [item["observed_at"] for item in first["items"] + second["items"]]
    assert timestamps == sorted(timestamps, reverse=True)


def test_overlapping_refreshes_create_one_transition(tmp_path: Path) -> None:
    provider = MutableProvider(DeviceStatus.OFFLINE)
    app = create_app(settings(tmp_path / "inventory.db"), provider)
    with TestClient(app) as client:
        provider.status = DeviceStatus.ONLINE
        with ThreadPoolExecutor(max_workers=4) as executor:
            responses = list(
                executor.map(lambda _: client.post("/api/inventory/refresh"), range(4))
            )
        history = client.get("/api/devices/demo-test-01/history").json()

    assert all(response.status_code == 200 for response in responses)
    assert sum(response.json()["transitions"] for response in responses) == 1
    assert history["total"] == 2


def test_failed_refresh_rolls_back_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = MutableProvider(DeviceStatus.ONLINE)
    app = create_app(settings(tmp_path / "inventory.db"), provider)
    with TestClient(app, raise_server_exceptions=False) as client:
        before = client.get("/api/devices/demo-test-01").json()
        provider.status = DeviceStatus.OFFLINE

        def fail_insert(*_: object) -> None:
            raise sqlite3.OperationalError("synthetic transaction failure")

        monkeypatch.setattr(app.state.inventory_store, "_insert_event", fail_insert)
        response = client.post("/api/inventory/refresh")
        after = client.get("/api/devices/demo-test-01").json()

    assert response.status_code == 503
    assert response.json() == {"detail": "Inventory storage is unavailable."}
    assert after == before
    assert str(tmp_path) not in response.text


def test_live_mode_is_rejected_before_app_creation() -> None:
    with pytest.raises(ValidationError, match="live mode is not supported"):
        create_app(Settings(mode="live"))


def test_api_startup_imports_no_scapy_modules(tmp_path: Path) -> None:
    import sys

    before = {
        name
        for name in sys.modules
        if name == "scapy" or name.startswith("scapy.")
    }
    with TestClient(create_app(settings(tmp_path / "inventory.db"))):
        pass
    after = {
        name
        for name in sys.modules
        if name == "scapy" or name.startswith("scapy.")
    }

    assert after == before
