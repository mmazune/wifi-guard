from collections.abc import Callable
from ipaddress import IPv4Network
from typing import Protocol

from .models import (
    ConnectionType,
    DataSource,
    DeviceStatus,
    DiscoveryScope,
    ProviderDevice,
)


class DiscoveryCancelled(RuntimeError):
    pass


class DiscoveryAdapter(Protocol):
    def discover(
        self,
        scope: DiscoveryScope,
        progress: Callable[[int, int], None],
        cancelled: Callable[[], bool],
    ) -> list[ProviderDevice]: ...


class FakeDiscoveryAdapter:
    """Deterministic offline adapter; it performs no network operations."""

    def discover(
        self,
        scope: DiscoveryScope,
        progress: Callable[[int, int], None],
        cancelled: Callable[[], bool],
    ) -> list[ProviderDevice]:
        network = IPv4Network(scope.target_cidr)
        selected_indexes = {
            index
            for index in (1, network.num_addresses // 2, network.num_addresses - 2)
            if 0 <= index < network.num_addresses
        }
        observations: list[ProviderDevice] = []
        for processed, address in enumerate(network, start=1):
            if cancelled():
                raise DiscoveryCancelled
            index = processed - 1
            if index in selected_indexes:
                address_value = int(address)
                observations.append(
                    ProviderDevice(
                        provider_identity=f"synthetic:{address}",
                        provider_name=f"Synthetic discovery device {len(observations) + 1}",
                        ipv4_address=str(address),
                        mac_address=(
                            "02:77:%02x:%02x:%02x:%02x"
                            % (
                                (address_value >> 24) & 255,
                                (address_value >> 16) & 255,
                                (address_value >> 8) & 255,
                                address_value & 255,
                            )
                        ),
                        status=DeviceStatus.ONLINE,
                        connection_type=ConnectionType.UNKNOWN,
                        data_source=DataSource.DEMO_DISCOVERY,
                    )
                )
            progress(processed, len(observations))
        return observations
