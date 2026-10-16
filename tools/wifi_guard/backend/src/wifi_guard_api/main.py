import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import __version__
from .config import Settings
from .interfaces import (
    DemoInterfaceProvider,
    InterfaceProvider,
    LocalMetadataInterfaceProvider,
    ScopeValidationError,
    validate_scope,
)
from .models import (
    CapabilitiesResponse,
    Capability,
    Device,
    DeviceNameUpdate,
    DiscoveryJob,
    DiscoveryJobList,
    DiscoveryScope,
    HealthResponse,
    NetworkInterface,
    PresenceHistory,
    RefreshSummary,
)
from .providers import DemoDeviceProvider, DeviceProvider
from .storage import (
    ActiveDiscoveryJobError,
    DeviceNotFoundError,
    DiscoveryJobNotFoundError,
    InventoryStore,
    PersistenceError,
)


def create_app(
    settings: Settings | None = None,
    provider: DeviceProvider | None = None,
    clock: Callable[[], datetime] | None = None,
    interface_provider: InterfaceProvider | None = None,
) -> FastAPI:
    resolved_settings = settings or Settings()
    resolved_provider = provider or DemoDeviceProvider()
    resolved_interface_provider = interface_provider or (
        DemoInterfaceProvider()
        if resolved_settings.interface_source == "demo"
        else LocalMetadataInterfaceProvider()
    )
    store = InventoryStore(
        resolved_settings.database_path,
        resolved_settings.history_limit_per_device,
        clock,
        resolved_settings.job_retention_limit,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await asyncio.to_thread(store.initialize)
        await asyncio.to_thread(store.refresh, resolved_provider)
        try:
            yield
        finally:
            store.close()

    app = FastAPI(
        title=resolved_settings.app_name,
        version=__version__,
        lifespan=lifespan,
    )
    app.state.inventory_store = store
    app.state.interface_provider = resolved_interface_provider
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "PATCH", "POST"],
        allow_headers=["Accept", "Content-Type"],
    )

    @app.middleware("http")
    async def protect_local_requests(request: Request, call_next: Callable):
        host = request.headers.get("host", "").rsplit(":", 1)[0].lower()
        if host not in {"127.0.0.1", "localhost"}:
            return JSONResponse(
                status_code=400,
                content={"detail": "Untrusted Host header."},
            )
        if request.method in {"POST", "PATCH", "PUT", "DELETE"}:
            origin = request.headers.get("origin")
            if origin is not None and origin not in resolved_settings.cors_origins:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Untrusted browser Origin."},
                )
        return await call_next(request)

    @app.exception_handler(PersistenceError)
    async def persistence_error(
        _: Request, __: PersistenceError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"detail": "Inventory storage is unavailable."},
        )

    @app.get("/api/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            application=resolved_settings.app_name,
            version=__version__,
            mode=resolved_settings.mode,
        )

    @app.get("/api/capabilities", response_model=CapabilitiesResponse)
    def capabilities() -> CapabilitiesResponse:
        unavailable = "Planned for a later milestone."
        return CapabilitiesResponse(
            demo_device_inventory=Capability(
                available=True,
                detail="Deterministic synthetic inventory is available.",
            ),
            demo_discovery_jobs=Capability(
                available=resolved_interface_provider.source.value == "demo",
                detail=(
                    "A separate unprivileged worker can run synthetic offline jobs."
                    if resolved_interface_provider.source.value == "demo"
                    else "Local metadata can be inspected, but real discovery is unavailable."
                ),
            ),
            live_discovery=Capability(available=False, detail=unavailable),
            traffic_capture=Capability(available=False, detail=unavailable),
            device_ip_enforcement=Capability(available=False, detail=unavailable),
            domain_enforcement=Capability(available=False, detail=unavailable),
            exact_url_enforcement=Capability(available=False, detail=unavailable),
        )

    @app.get("/api/network/interfaces", response_model=list[NetworkInterface])
    def network_interfaces() -> list[NetworkInterface]:
        return resolved_interface_provider.list_interfaces()

    @app.get("/api/devices", response_model=list[Device])
    def devices() -> list[Device]:
        return store.list_devices()

    @app.get("/api/devices/{device_id}", response_model=Device)
    def device(device_id: str) -> Device:
        try:
            return store.get_device(device_id)
        except DeviceNotFoundError as error:
            raise HTTPException(status_code=404, detail="Device not found.") from error

    @app.patch("/api/devices/{device_id}", response_model=Device)
    def update_device(device_id: str, update: DeviceNameUpdate) -> Device:
        try:
            return store.update_custom_name(device_id, update.custom_name)
        except DeviceNotFoundError as error:
            raise HTTPException(status_code=404, detail="Device not found.") from error

    @app.get("/api/devices/{device_id}/history", response_model=PresenceHistory)
    def device_history(
        device_id: str,
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0, le=1_000_000),
    ) -> PresenceHistory:
        try:
            return store.history(device_id, limit, offset)
        except DeviceNotFoundError as error:
            raise HTTPException(status_code=404, detail="Device not found.") from error

    @app.post("/api/inventory/refresh", response_model=RefreshSummary)
    def refresh_inventory() -> RefreshSummary:
        return store.refresh(resolved_provider)

    @app.post(
        "/api/discovery/jobs", response_model=DiscoveryJob, status_code=201
    )
    def create_discovery_job(scope: DiscoveryScope) -> DiscoveryJob:
        try:
            validated, selected_interface, target = validate_scope(
                scope, resolved_interface_provider
            )
        except ScopeValidationError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        if selected_interface.source.value != "demo":
            raise HTTPException(
                status_code=409,
                detail=(
                    "Real discovery is unavailable. Local interfaces are exposed "
                    "for metadata inspection and scope validation only."
                ),
            )
        try:
            return store.create_discovery_job(
                selected_interface.source, validated, target.num_addresses
            )
        except ActiveDiscoveryJobError as error:
            raise HTTPException(
                status_code=409,
                detail="Another discovery job is already queued or running.",
            ) from error

    @app.get("/api/discovery/jobs/{job_id}", response_model=DiscoveryJob)
    def discovery_job(job_id: str) -> DiscoveryJob:
        try:
            return store.get_discovery_job(job_id)
        except DiscoveryJobNotFoundError as error:
            raise HTTPException(status_code=404, detail="Discovery job not found.") from error

    @app.get("/api/discovery/jobs", response_model=DiscoveryJobList)
    def discovery_jobs(
        limit: int = Query(default=10, ge=1, le=100),
        offset: int = Query(default=0, ge=0, le=1_000_000),
    ) -> DiscoveryJobList:
        return store.list_discovery_jobs(limit, offset)

    @app.post("/api/discovery/jobs/{job_id}/cancel", response_model=DiscoveryJob)
    def cancel_discovery_job(job_id: str) -> DiscoveryJob:
        try:
            return store.cancel_discovery_job(job_id)
        except DiscoveryJobNotFoundError as error:
            raise HTTPException(status_code=404, detail="Discovery job not found.") from error

    return app


app = create_app()
