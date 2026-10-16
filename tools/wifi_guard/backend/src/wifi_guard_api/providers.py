from typing import Protocol

from .models import ConnectionType, DataSource, DeviceStatus, ProviderDevice


class DeviceProvider(Protocol):
    def list_devices(self) -> list[ProviderDevice]: ...


class DemoDeviceProvider:
    _DEVICES = (
        ProviderDevice(
            provider_identity="demo-laptop-01",
            provider_name="Studio laptop",
            ipv4_address="192.168.50.12",
            mac_address="02:00:00:00:10:01",
            status=DeviceStatus.ONLINE,
            connection_type=ConnectionType.WIFI,
            data_source=DataSource.DEMO,
        ),
        ProviderDevice(
            provider_identity="demo-tv-01",
            provider_name="Living room TV",
            ipv4_address="192.168.50.24",
            mac_address="02:00:00:00:10:02",
            status=DeviceStatus.ONLINE,
            connection_type=ConnectionType.WIRED,
            data_source=DataSource.DEMO,
        ),
        ProviderDevice(
            provider_identity="demo-phone-01",
            provider_name="Guest phone",
            ipv4_address="192.168.50.37",
            mac_address="02:00:00:00:10:03",
            status=DeviceStatus.OFFLINE,
            connection_type=ConnectionType.WIFI,
            data_source=DataSource.DEMO,
        ),
        ProviderDevice(
            provider_identity="demo-sensor-01",
            provider_name="Workshop sensor",
            ipv4_address="10.20.0.18",
            mac_address="02:00:00:00:20:01",
            status=DeviceStatus.ONLINE,
            connection_type=ConnectionType.UNKNOWN,
            data_source=DataSource.DEMO,
        ),
    )

    def list_devices(self) -> list[ProviderDevice]:
        return [device.model_copy() for device in self._DEVICES]
