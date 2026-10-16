import sqlite3
import threading
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from .models import (
    DataSource,
    Device,
    DeviceStatus,
    DiscoveryJob,
    DiscoveryJobList,
    DiscoveryJobState,
    DiscoveryScope,
    InterfaceSource,
    PresenceEvent,
    PresenceHistory,
    ProviderDevice,
    RefreshSummary,
)
from .providers import DeviceProvider


SCHEMA_VERSION = 2


class PersistenceError(RuntimeError):
    """An inventory operation failed without exposing storage internals."""


class DeviceNotFoundError(LookupError):
    pass


class DiscoveryJobNotFoundError(LookupError):
    pass


class ActiveDiscoveryJobError(RuntimeError):
    pass


class InvalidJobTransitionError(RuntimeError):
    pass


class InventoryStore:
    def __init__(
        self,
        database_path: Path,
        history_limit_per_device: int,
        clock: Callable[[], datetime] | None = None,
        job_retention_limit: int = 100,
    ) -> None:
        self.database_path = database_path
        self.history_limit_per_device = history_limit_per_device
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.job_retention_limit = job_retention_limit
        self._refresh_lock = threading.Lock()

    def close(self) -> None:
        """Connections are operation-scoped, so shutdown has nothing open to close."""

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version INTEGER PRIMARY KEY,
                        applied_at TEXT NOT NULL
                    )
                    """
                )
                current = connection.execute(
                    "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
                ).fetchone()[0]
                if current > SCHEMA_VERSION:
                    raise PersistenceError(
                        "The inventory schema is newer than this app."
                    )
                if current < 1:
                    connection.execute("BEGIN IMMEDIATE")
                    try:
                        self._migrate_v1(connection)
                        connection.execute(
                            """
                            INSERT INTO schema_migrations(version, applied_at)
                            VALUES (?, ?)
                            """,
                            (1, self._timestamp()),
                        )
                        connection.commit()
                    except Exception:
                        connection.rollback()
                        raise
                if current < 2:
                    connection.execute("BEGIN IMMEDIATE")
                    try:
                        self._migrate_v2(connection)
                        connection.execute(
                            "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                            (2, self._timestamp()),
                        )
                        connection.commit()
                    except Exception:
                        connection.rollback()
                        raise
        except PersistenceError:
            raise
        except (OSError, sqlite3.Error) as error:
            raise PersistenceError("Inventory storage is unavailable.") from error

    def _migrate_v1(self, connection: sqlite3.Connection) -> None:
        statements = (
            """
            CREATE TABLE devices (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                provider_identity TEXT NOT NULL,
                provider_name TEXT NOT NULL,
                custom_name TEXT,
                ipv4_address TEXT NOT NULL,
                mac_address TEXT NOT NULL,
                connection_type TEXT NOT NULL,
                status TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT,
                UNIQUE(source, provider_identity)
            )
            """,
            """
            CREATE TABLE presence_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
                previous_status TEXT,
                new_status TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                source TEXT NOT NULL
            )
            """,
            """
            CREATE INDEX presence_events_device_order
                ON presence_events(device_id, observed_at DESC, event_id DESC)
            """,
        )
        for statement in statements:
            connection.execute(statement)

    def _migrate_v2(self, connection: sqlite3.Connection) -> None:
        statements = (
            """
            CREATE TABLE discovery_jobs (
                id TEXT PRIMARY KEY,
                mode TEXT NOT NULL,
                source TEXT NOT NULL,
                interface_id TEXT NOT NULL,
                selected_ipv4_address TEXT NOT NULL,
                target_cidr TEXT NOT NULL,
                state TEXT NOT NULL CHECK(state IN (
                    'queued', 'running', 'completed', 'failed', 'cancelled'
                )),
                created_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                progress_total INTEGER NOT NULL CHECK(
                    progress_total BETWEEN 0 AND 256
                ),
                progress_processed INTEGER NOT NULL DEFAULT 0 CHECK(
                    progress_processed BETWEEN 0 AND 256
                ),
                progress_discovered INTEGER NOT NULL DEFAULT 0 CHECK(
                    progress_discovered BETWEEN 0 AND 256
                ),
                failure_code TEXT,
                failure_message TEXT,
                cancellation_requested INTEGER NOT NULL DEFAULT 0 CHECK(
                    cancellation_requested IN (0, 1)
                ),
                worker_id TEXT,
                lease_expires_at TEXT
            )
            """,
            """
            CREATE UNIQUE INDEX discovery_jobs_one_active
            ON discovery_jobs((1)) WHERE state IN ('queued', 'running')
            """,
            """
            CREATE INDEX discovery_jobs_order
            ON discovery_jobs(created_at DESC, id DESC)
            """,
        )
        for statement in statements:
            connection.execute(statement)

    def schema_version(self) -> int:
        try:
            with self._connect() as connection:
                return connection.execute(
                    "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
                ).fetchone()[0]
        except sqlite3.Error as error:
            raise PersistenceError("Inventory storage is unavailable.") from error

    def refresh(self, provider: DeviceProvider) -> RefreshSummary:
        with self._refresh_lock:
            observations = provider.list_devices()
            try:
                connection = self._connect()
                try:
                    connection.execute("BEGIN IMMEDIATE")
                    summary = self._apply_observations(connection, observations)
                    connection.commit()
                    return summary
                except Exception:
                    connection.rollback()
                    raise
                finally:
                    connection.close()
            except PersistenceError:
                raise
            except (OSError, sqlite3.Error) as error:
                raise PersistenceError("Inventory storage is unavailable.") from error

    def _apply_observations(
        self,
        connection: sqlite3.Connection,
        observations: list[ProviderDevice],
    ) -> RefreshSummary:
        observed_at = self._timestamp()
        created = 0
        updated = 0
        transitions = 0
        pruned_events = 0
        for observation in observations:
            event_added = False
            row = connection.execute(
                """
                SELECT id, status FROM devices
                WHERE source = ? AND provider_identity = ?
                """,
                (observation.data_source.value, observation.provider_identity),
            ).fetchone()
            if row is None:
                device_id = (
                    observation.provider_identity
                    if observation.data_source == DataSource.DEMO
                    else (
                        f"{observation.data_source.value}:"
                        f"{observation.provider_identity}"
                    )
                )
                connection.execute(
                    """
                    INSERT INTO devices(
                        id, source, provider_identity, provider_name, custom_name,
                        ipv4_address, mac_address, connection_type, status,
                        first_seen, last_seen
                    ) VALUES (?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        device_id,
                        observation.data_source.value,
                        observation.provider_identity,
                        observation.provider_name,
                        observation.ipv4_address,
                        observation.mac_address,
                        observation.connection_type.value,
                        observation.status.value,
                        observed_at,
                        (
                            observed_at
                            if observation.status == DeviceStatus.ONLINE
                            else None
                        ),
                    ),
                )
                self._insert_event(
                    connection, device_id, None, observation, observed_at
                )
                created += 1
                transitions += 1
                event_added = True
            else:
                device_id = row["id"]
                previous_status = DeviceStatus(row["status"])
                last_seen = (
                    observed_at if observation.status == DeviceStatus.ONLINE else None
                )
                connection.execute(
                    """
                    UPDATE devices
                    SET provider_name = ?, ipv4_address = ?, mac_address = ?,
                        connection_type = ?, status = ?,
                        last_seen = COALESCE(?, last_seen)
                    WHERE id = ?
                    """,
                    (
                        observation.provider_name,
                        observation.ipv4_address,
                        observation.mac_address,
                        observation.connection_type.value,
                        observation.status.value,
                        last_seen,
                        device_id,
                    ),
                )
                updated += 1
                if previous_status != observation.status:
                    self._insert_event(
                        connection,
                        device_id,
                        previous_status,
                        observation,
                        observed_at,
                    )
                    transitions += 1
                    event_added = True
            if event_added:
                pruned_events += self._prune_events(connection, device_id)
        source = observations[0].data_source if observations else DataSource.DEMO
        return RefreshSummary(
            source=source,
            observed=len(observations),
            created=created,
            updated=updated,
            transitions=transitions,
            pruned_events=pruned_events,
        )

    def _insert_event(
        self,
        connection: sqlite3.Connection,
        device_id: str,
        previous_status: DeviceStatus | None,
        observation: ProviderDevice,
        observed_at: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO presence_events(
                device_id, previous_status, new_status, observed_at, source
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                device_id,
                previous_status.value if previous_status else None,
                observation.status.value,
                observed_at,
                observation.data_source.value,
            ),
        )

    def _prune_events(self, connection: sqlite3.Connection, device_id: str) -> int:
        before = connection.total_changes
        connection.execute(
            """
            DELETE FROM presence_events
            WHERE device_id = ? AND event_id NOT IN (
                SELECT event_id FROM presence_events
                WHERE device_id = ?
                ORDER BY observed_at DESC, event_id DESC
                LIMIT ?
            )
            """,
            (device_id, device_id, self.history_limit_per_device),
        )
        return connection.total_changes - before

    def list_devices(self) -> list[Device]:
        try:
            with self._connect() as connection:
                rows = connection.execute(
                    "SELECT * FROM devices ORDER BY rowid"
                ).fetchall()
            return [self._device_from_row(row) for row in rows]
        except sqlite3.Error as error:
            raise PersistenceError("Inventory storage is unavailable.") from error

    def get_device(self, device_id: str) -> Device:
        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT * FROM devices WHERE id = ?", (device_id,)
                ).fetchone()
            if row is None:
                raise DeviceNotFoundError
            return self._device_from_row(row)
        except sqlite3.Error as error:
            raise PersistenceError("Inventory storage is unavailable.") from error

    def update_custom_name(self, device_id: str, custom_name: str | None) -> Device:
        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    "UPDATE devices SET custom_name = ? WHERE id = ?",
                    (custom_name, device_id),
                )
                if cursor.rowcount == 0:
                    raise DeviceNotFoundError
            return self.get_device(device_id)
        except sqlite3.Error as error:
            raise PersistenceError("Inventory storage is unavailable.") from error

    def history(self, device_id: str, limit: int, offset: int) -> PresenceHistory:
        try:
            with self._connect() as connection:
                exists = connection.execute(
                    "SELECT 1 FROM devices WHERE id = ?", (device_id,)
                ).fetchone()
                if exists is None:
                    raise DeviceNotFoundError
                total = connection.execute(
                    "SELECT COUNT(*) FROM presence_events WHERE device_id = ?",
                    (device_id,),
                ).fetchone()[0]
                rows = connection.execute(
                    """
                    SELECT * FROM presence_events WHERE device_id = ?
                    ORDER BY observed_at DESC, event_id DESC LIMIT ? OFFSET ?
                    """,
                    (device_id, limit, offset),
                ).fetchall()
            items = [PresenceEvent.model_validate(dict(row)) for row in rows]
            next_offset = offset + len(items) if offset + len(items) < total else None
            return PresenceHistory(
                items=items,
                limit=limit,
                offset=offset,
                total=total,
                next_offset=next_offset,
            )
        except sqlite3.Error as error:
            raise PersistenceError("Inventory storage is unavailable.") from error

    def _device_from_row(self, row: sqlite3.Row) -> Device:
        custom_name = row["custom_name"]
        return Device(
            id=row["id"],
            display_name=custom_name or row["provider_name"],
            provider_name=row["provider_name"],
            custom_name=custom_name,
            ipv4_address=row["ipv4_address"],
            mac_address=row["mac_address"],
            status=row["status"],
            connection_type=row["connection_type"],
            data_source=row["source"],
            first_seen=row["first_seen"],
            last_seen=row["last_seen"],
        )

    def create_discovery_job(
        self,
        source: InterfaceSource,
        scope: DiscoveryScope,
        progress_total: int,
    ) -> DiscoveryJob:
        job_id = str(uuid4())
        created_at = self._timestamp()
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                try:
                    self._expire_worker_leases(connection)
                    connection.execute(
                        """
                        INSERT INTO discovery_jobs(
                            id, mode, source, interface_id,
                            selected_ipv4_address, target_cidr, state,
                            created_at, progress_total
                        ) VALUES (?, 'demo', ?, ?, ?, ?, 'queued', ?, ?)
                        """,
                        (
                            job_id,
                            source.value,
                            scope.interface_id,
                            scope.selected_ipv4_address,
                            scope.target_cidr,
                            created_at,
                            progress_total,
                        ),
                    )
                    self._prune_terminal_jobs(connection)
                    connection.commit()
                except sqlite3.IntegrityError as error:
                    connection.rollback()
                    if "discovery_jobs_one_active" in str(error):
                        raise ActiveDiscoveryJobError from error
                    raise
            return self.get_discovery_job(job_id)
        except ActiveDiscoveryJobError:
            raise
        except sqlite3.Error as error:
            raise PersistenceError("Inventory storage is unavailable.") from error

    def get_discovery_job(self, job_id: str) -> DiscoveryJob:
        try:
            with self._connect() as connection:
                self._expire_worker_leases(connection)
                row = connection.execute(
                    "SELECT * FROM discovery_jobs WHERE id = ?", (job_id,)
                ).fetchone()
            if row is None:
                raise DiscoveryJobNotFoundError
            return self._job_from_row(row)
        except sqlite3.Error as error:
            raise PersistenceError("Inventory storage is unavailable.") from error

    def list_discovery_jobs(self, limit: int, offset: int) -> DiscoveryJobList:
        try:
            with self._connect() as connection:
                self._expire_worker_leases(connection)
                total = connection.execute(
                    "SELECT COUNT(*) FROM discovery_jobs"
                ).fetchone()[0]
                rows = connection.execute(
                    """
                    SELECT * FROM discovery_jobs
                    ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                ).fetchall()
            items = [self._job_from_row(row) for row in rows]
            next_offset = offset + len(items) if offset + len(items) < total else None
            return DiscoveryJobList(
                items=items,
                limit=limit,
                offset=offset,
                total=total,
                next_offset=next_offset,
            )
        except sqlite3.Error as error:
            raise PersistenceError("Inventory storage is unavailable.") from error

    def cancel_discovery_job(self, job_id: str) -> DiscoveryJob:
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT state FROM discovery_jobs WHERE id = ?", (job_id,)
                ).fetchone()
                if row is None:
                    raise DiscoveryJobNotFoundError
                state = DiscoveryJobState(row["state"])
                if state == DiscoveryJobState.QUEUED:
                    connection.execute(
                        """
                        UPDATE discovery_jobs
                        SET state = 'cancelled', cancellation_requested = 1,
                            finished_at = ?
                        WHERE id = ? AND state = 'queued'
                        """,
                        (self._timestamp(), job_id),
                    )
                    self._prune_terminal_jobs(connection)
                elif state == DiscoveryJobState.RUNNING:
                    connection.execute(
                        """
                        UPDATE discovery_jobs SET cancellation_requested = 1
                        WHERE id = ? AND state = 'running'
                        """,
                        (job_id,),
                    )
                connection.commit()
            return self.get_discovery_job(job_id)
        except DiscoveryJobNotFoundError:
            raise
        except sqlite3.Error as error:
            raise PersistenceError("Inventory storage is unavailable.") from error

    def claim_discovery_job(
        self, worker_id: str, lease_seconds: int
    ) -> DiscoveryJob | None:
        now = self._timestamp()
        lease = self._timestamp_after(lease_seconds)
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                self._expire_worker_leases(connection)
                row = connection.execute(
                    """
                    SELECT id FROM discovery_jobs WHERE state = 'queued'
                    ORDER BY created_at ASC, id ASC LIMIT 1
                    """
                ).fetchone()
                if row is None:
                    self._prune_terminal_jobs(connection)
                    connection.commit()
                    return None
                cursor = connection.execute(
                    """
                    UPDATE discovery_jobs
                    SET state = 'running', started_at = ?, worker_id = ?,
                        lease_expires_at = ?
                    WHERE id = ? AND state = 'queued'
                    """,
                    (now, worker_id, lease, row["id"]),
                )
                if cursor.rowcount != 1:
                    connection.rollback()
                    return None
                connection.commit()
                job_id = row["id"]
            return self.get_discovery_job(job_id)
        except sqlite3.Error as error:
            raise PersistenceError("Inventory storage is unavailable.") from error

    def update_discovery_progress(
        self,
        job_id: str,
        worker_id: str,
        processed: int,
        discovered: int,
        lease_seconds: int,
    ) -> bool:
        if not 0 <= discovered <= processed <= 256:
            raise ValueError("Discovery progress is outside its bounded range")
        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    """
                    UPDATE discovery_jobs
                    SET progress_processed = ?, progress_discovered = ?,
                        lease_expires_at = ?
                    WHERE id = ? AND state = 'running' AND worker_id = ?
                        AND progress_total >= ?
                    """,
                    (
                        processed,
                        discovered,
                        self._timestamp_after(lease_seconds),
                        job_id,
                        worker_id,
                        processed,
                    ),
                )
                if cursor.rowcount != 1:
                    raise InvalidJobTransitionError
                cancelled = connection.execute(
                    "SELECT cancellation_requested FROM discovery_jobs WHERE id = ?",
                    (job_id,),
                ).fetchone()[0]
            return bool(cancelled)
        except InvalidJobTransitionError:
            raise
        except sqlite3.Error as error:
            raise PersistenceError("Inventory storage is unavailable.") from error

    def complete_discovery_job(
        self,
        job_id: str,
        worker_id: str,
        observations: list[ProviderDevice],
    ) -> DiscoveryJob:
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    """
                    SELECT state, cancellation_requested, progress_total
                    FROM discovery_jobs WHERE id = ? AND worker_id = ?
                    """,
                    (job_id, worker_id),
                ).fetchone()
                if row is None or row["state"] != DiscoveryJobState.RUNNING.value:
                    raise InvalidJobTransitionError
                if row["cancellation_requested"]:
                    self._cancel_claimed_job(connection, job_id)
                else:
                    self._apply_observations(connection, observations)
                    connection.execute(
                        """
                        UPDATE discovery_jobs
                        SET state = 'completed', finished_at = ?,
                            progress_processed = progress_total,
                            progress_discovered = ?, worker_id = NULL,
                            lease_expires_at = NULL
                        WHERE id = ? AND state = 'running'
                        """,
                        (self._timestamp(), len(observations), job_id),
                    )
                self._prune_terminal_jobs(connection)
                connection.commit()
            return self.get_discovery_job(job_id)
        except InvalidJobTransitionError:
            raise
        except (OSError, sqlite3.Error) as error:
            raise PersistenceError("Inventory storage is unavailable.") from error

    def cancel_claimed_discovery_job(
        self, job_id: str, worker_id: str
    ) -> DiscoveryJob:
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT state FROM discovery_jobs WHERE id = ? AND worker_id = ?",
                    (job_id, worker_id),
                ).fetchone()
                if row is None or row["state"] != DiscoveryJobState.RUNNING.value:
                    raise InvalidJobTransitionError
                self._cancel_claimed_job(connection, job_id)
                self._prune_terminal_jobs(connection)
                connection.commit()
            return self.get_discovery_job(job_id)
        except InvalidJobTransitionError:
            raise
        except sqlite3.Error as error:
            raise PersistenceError("Inventory storage is unavailable.") from error

    def fail_discovery_job(
        self, job_id: str, worker_id: str, code: str, message: str
    ) -> DiscoveryJob:
        safe_code = code[:64]
        safe_message = message[:240]
        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    """
                    UPDATE discovery_jobs
                    SET state = 'failed', finished_at = ?, failure_code = ?,
                        failure_message = ?, worker_id = NULL,
                        lease_expires_at = NULL
                    WHERE id = ? AND state = 'running' AND worker_id = ?
                    """,
                    (self._timestamp(), safe_code, safe_message, job_id, worker_id),
                )
                if cursor.rowcount != 1:
                    raise InvalidJobTransitionError
                self._prune_terminal_jobs(connection)
            return self.get_discovery_job(job_id)
        except InvalidJobTransitionError:
            raise
        except sqlite3.Error as error:
            raise PersistenceError("Inventory storage is unavailable.") from error

    def _cancel_claimed_job(
        self, connection: sqlite3.Connection, job_id: str
    ) -> None:
        connection.execute(
            """
            UPDATE discovery_jobs
            SET state = 'cancelled', cancellation_requested = 1,
                finished_at = ?, worker_id = NULL, lease_expires_at = NULL
            WHERE id = ? AND state = 'running'
            """,
            (self._timestamp(), job_id),
        )

    def _prune_terminal_jobs(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            DELETE FROM discovery_jobs
            WHERE state IN ('completed', 'failed', 'cancelled') AND id NOT IN (
                SELECT id FROM discovery_jobs
                WHERE state IN ('completed', 'failed', 'cancelled')
                ORDER BY created_at DESC, id DESC LIMIT ?
            )
            """,
            (self.job_retention_limit,),
        )

    def _expire_worker_leases(self, connection: sqlite3.Connection) -> None:
        now = self._timestamp()
        connection.execute(
            """
            UPDATE discovery_jobs
            SET state = 'failed', finished_at = ?,
                failure_code = 'worker_lost',
                failure_message = 'The worker lease expired before completion.',
                worker_id = NULL, lease_expires_at = NULL
            WHERE state = 'running' AND lease_expires_at < ?
            """,
            (now, now),
        )

    def _job_from_row(self, row: sqlite3.Row) -> DiscoveryJob:
        return DiscoveryJob(
            id=row["id"],
            mode=row["mode"],
            source=row["source"],
            scope=DiscoveryScope(
                interface_id=row["interface_id"],
                selected_ipv4_address=row["selected_ipv4_address"],
                target_cidr=row["target_cidr"],
            ),
            state=row["state"],
            created_at=row["created_at"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
            progress_total=row["progress_total"],
            progress_processed=row["progress_processed"],
            progress_discovered=row["progress_discovered"],
            failure_code=row["failure_code"],
            failure_message=row["failure_message"],
            cancellation_requested=bool(row["cancellation_requested"]),
            worker_id=row["worker_id"],
            lease_expires_at=row["lease_expires_at"],
        )

    def _timestamp(self) -> str:
        current = self.clock()
        if current.tzinfo is None or current.utcoffset() is None:
            raise ValueError("Inventory clock must return a timezone-aware datetime")
        return current.astimezone(timezone.utc).isoformat()

    def _timestamp_after(self, seconds: int) -> str:
        current = self.clock()
        if current.tzinfo is None or current.utcoffset() is None:
            raise ValueError("Inventory clock must return a timezone-aware datetime")
        return (current.astimezone(timezone.utc) + timedelta(seconds=seconds)).isoformat()
