import socket
from ipaddress import IPv4Address, IPv4Network, ip_address, ip_network
from typing import Protocol

import psutil

from .models import (
    ConnectionType,
    DiscoveryScope,
    InterfaceIPv4,
    InterfaceSource,
    NetworkInterface,
)


RFC1918_NETWORKS = (
    IPv4Network("10.0.0.0/8"),
    IPv4Network("172.16.0.0/12"),
    IPv4Network("192.168.0.0/16"),
)


class ScopeValidationError(ValueError):
    pass


class InterfaceProvider(Protocol):
    source: InterfaceSource

    def list_interfaces(self) -> list[NetworkInterface]: ...


def _interface(
    identifier: str,
    name: str,
    source: InterfaceSource,
    addresses: list[tuple[str, str]],
    is_up: bool | None,
    is_loopback: bool,
) -> NetworkInterface:
    ipv4_addresses: list[InterfaceIPv4] = []
    networks: list[str] = []
    for address, netmask in addresses:
        network = ip_network(f"{address}/{netmask}", strict=False)
        if not isinstance(network, IPv4Network):
            continue
        network_text = str(network)
        ipv4_addresses.append(
            InterfaceIPv4(
                address=address,
                netmask=netmask,
                network=network_text,
            )
        )
        if network_text not in networks:
            networks.append(network_text)

    reason: str | None = None
    if is_loopback:
        reason = "Loopback interfaces are not eligible for discovery."
    elif is_up is False:
        reason = "The interface is down."
    elif not ipv4_addresses:
        reason = "The interface has no IPv4 address."
    elif not any(
        network.subnet_of(private)
        for network in map(IPv4Network, networks)
        for private in RFC1918_NETWORKS
    ):
        reason = "The interface has no directly connected private IPv4 network."

    return NetworkInterface(
        id=identifier,
        name=name,
        ipv4_addresses=ipv4_addresses,
        connected_ipv4_networks=networks,
        is_up=is_up,
        is_loopback=is_loopback,
        connection_type=ConnectionType.UNKNOWN,
        source=source,
        eligible=reason is None,
        ineligible_reason=reason,
    )


class DemoInterfaceProvider:
    source = InterfaceSource.DEMO

    def list_interfaces(self) -> list[NetworkInterface]:
        return [
            _interface(
                "demo-private-1",
                "Synthetic private LAN",
                self.source,
                [("192.168.50.10", "255.255.255.0")],
                True,
                False,
            ),
            _interface(
                "demo-private-2",
                "Synthetic workshop LAN",
                self.source,
                [("10.20.0.10", "255.255.255.0")],
                True,
                False,
            ),
            _interface(
                "demo-down",
                "Synthetic unavailable interface",
                self.source,
                [("172.20.0.10", "255.255.255.0")],
                False,
                False,
            ),
        ]


class LocalMetadataInterfaceProvider:
    source = InterfaceSource.LOCAL_METADATA

    def list_interfaces(self) -> list[NetworkInterface]:
        addresses = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        interfaces: list[NetworkInterface] = []
        for name in sorted(set(addresses) | set(stats)):
            ipv4 = [
                (item.address, item.netmask)
                for item in addresses.get(name, [])
                if item.family == socket.AF_INET and item.netmask
            ]
            is_loopback = bool(ipv4) and all(
                ip_address(address).is_loopback for address, _ in ipv4
            )
            state = stats.get(name)
            flags = getattr(state, "flags", "") if state is not None else ""
            if "loopback" in {flag.strip() for flag in flags.split(",")}:
                is_loopback = True
            interfaces.append(
                _interface(
                    name,
                    name,
                    self.source,
                    ipv4,
                    state.isup if state is not None else None,
                    is_loopback,
                )
            )
        return interfaces


def validate_scope(
    scope: DiscoveryScope, provider: InterfaceProvider
) -> tuple[DiscoveryScope, NetworkInterface, IPv4Network]:
    interfaces = provider.list_interfaces()
    matching = [item for item in interfaces if item.id == scope.interface_id]
    if not matching:
        raise ScopeValidationError("The selected interface no longer exists.")
    selected_interface = matching[0]
    if not selected_interface.eligible:
        raise ScopeValidationError(
            selected_interface.ineligible_reason
            or "The selected interface is not eligible."
        )
    if selected_interface.is_up is False:
        raise ScopeValidationError("The selected interface is down.")

    try:
        selected_address = ip_address(scope.selected_ipv4_address)
    except ValueError as error:
        raise ScopeValidationError(
            "The selected interface address is not a valid IPv4 address."
        ) from error
    if not isinstance(selected_address, IPv4Address):
        raise ScopeValidationError("IPv6 discovery is not supported.")

    address_records = [
        item
        for item in selected_interface.ipv4_addresses
        if item.address == str(selected_address)
    ]
    if len(address_records) != 1:
        raise ScopeValidationError(
            "Select exactly one IPv4 address currently assigned to the interface."
        )

    try:
        target = ip_network(scope.target_cidr, strict=True)
    except ValueError as error:
        message = str(error)
        if ":" in scope.target_cidr:
            raise ScopeValidationError("IPv6 discovery is not supported.") from error
        if "host bits set" in message:
            raise ScopeValidationError(
                "Target CIDR must be a canonical network address."
            ) from error
        raise ScopeValidationError("Target CIDR is malformed.") from error
    if not isinstance(target, IPv4Network):
        raise ScopeValidationError("IPv6 discovery is not supported.")
    if target.num_addresses > 256:
        raise ScopeValidationError("Target CIDR may contain at most 256 addresses.")
    if target.is_loopback:
        raise ScopeValidationError("Loopback targets are not allowed.")
    if target.is_link_local:
        raise ScopeValidationError("Link-local targets are not allowed.")
    if target.is_multicast:
        raise ScopeValidationError("Multicast targets are not allowed.")
    if not any(target.subnet_of(network) for network in RFC1918_NETWORKS):
        raise ScopeValidationError("Target CIDR must be entirely within RFC1918 space.")

    connected = IPv4Network(address_records[0].network)
    if not target.subnet_of(connected):
        raise ScopeValidationError(
            "Target CIDR must fit entirely within the selected directly connected network."
        )
    return (
        DiscoveryScope(
            interface_id=selected_interface.id,
            selected_ipv4_address=str(selected_address),
            target_cidr=str(target),
        ),
        selected_interface,
        target,
    )
