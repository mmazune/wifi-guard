from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConnectionType(StrEnum):
    WIFI = "wifi"
    WIRED = "wired"
    UNKNOWN = "unknown"


class DeviceStatus(StrEnum):
    ONLINE = "online"
    OFFLINE = "offline"


class DataSource(StrEnum):
    DEMO = "demo"
    DEMO_DISCOVERY = "demo_discovery"


class InterfaceSource(StrEnum):
    DEMO = "demo"
    LOCAL_METADATA = "local_metadata"


class InterfaceIPv4(BaseModel):
    address: str
    netmask: str
    network: str


class NetworkInterface(BaseModel):
    id: str
    name: str
    ipv4_addresses: list[InterfaceIPv4]
    connected_ipv4_networks: list[str]
    is_up: bool | None
    is_loopback: bool
    connection_type: ConnectionType = ConnectionType.UNKNOWN
    source: InterfaceSource
    eligible: bool
    ineligible_reason: str | None


class DiscoveryScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interface_id: str = Field(min_length=1, max_length=255)
    selected_ipv4_address: str = Field(min_length=1, max_length=45)
    target_cidr: str = Field(min_length=1, max_length=50)


class DiscoveryJobState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DiscoveryJob(BaseModel):
    id: str
    mode: str
    source: InterfaceSource
    scope: DiscoveryScope
    state: DiscoveryJobState
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    progress_total: int = Field(ge=0, le=256)
    progress_processed: int = Field(ge=0, le=256)
    progress_discovered: int = Field(ge=0, le=256)
    failure_code: str | None
    failure_message: str | None
    cancellation_requested: bool
    worker_id: str | None
    lease_expires_at: datetime | None


class DiscoveryJobList(BaseModel):
    items: list[DiscoveryJob]
    limit: int
    offset: int
    total: int
    next_offset: int | None


class Device(BaseModel):
    id: str
    display_name: str
    ipv4_address: str
    mac_address: str
    status: DeviceStatus
    connection_type: ConnectionType
    data_source: DataSource
    provider_name: str
    custom_name: str | None
    first_seen: datetime
    last_seen: datetime | None


class ProviderDevice(BaseModel):
    provider_identity: str
    provider_name: str
    ipv4_address: str
    mac_address: str
    status: DeviceStatus
    connection_type: ConnectionType
    data_source: DataSource


class DeviceNameUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    custom_name: str | None = Field(max_length=80)

    @field_validator("custom_name")
    @classmethod
    def validate_custom_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("custom_name must not be blank")
        return trimmed


class PresenceEvent(BaseModel):
    event_id: int
    device_id: str
    previous_status: DeviceStatus | None
    new_status: DeviceStatus
    observed_at: datetime
    source: DataSource


class PresenceHistory(BaseModel):
    items: list[PresenceEvent]
    limit: int
    offset: int
    total: int
    next_offset: int | None


class RefreshSummary(BaseModel):
    source: DataSource
    observed: int
    created: int
    updated: int
    transitions: int
    pruned_events: int


class HealthResponse(BaseModel):
    application: str
    version: str
    mode: str


class Capability(BaseModel):
    available: bool
    detail: str


class CapabilitiesResponse(BaseModel):
    demo_device_inventory: Capability
    demo_discovery_jobs: Capability
    live_discovery: Capability
    traffic_capture: Capability
    device_ip_enforcement: Capability
    domain_enforcement: Capability
    exact_url_enforcement: Capability
