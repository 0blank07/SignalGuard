import asyncio
import logging

from sqlalchemy.orm import sessionmaker

from backend.app.config import get_settings
from backend.app.db.base import utc_now
from backend.app.db.models.endpoint import EndpointStatus, MonitoredEndpoint
from backend.app.engine.incident_manager import IncidentManager
from backend.app.engine.prober import execute_probe

logger = logging.getLogger("signalguard.scheduler")


class MonitoringScheduler:
    def __init__(
        self,
        session_factory: sessionmaker,
        max_concurrent_checks: int | None = None,
        tick_interval_seconds: float = 1.0,
    ) -> None:
        settings = get_settings()
        self.session_factory = session_factory
        self.max_concurrent_checks = (
            max_concurrent_checks or settings.MAX_CONCURRENT_CHECKS
        )
        self.tick_interval_seconds = tick_interval_seconds
        self.semaphore = asyncio.Semaphore(self.max_concurrent_checks)

        self._in_flight: set[int] = set()
        self._lock = asyncio.Lock()
        self._stop_event = asyncio.Event()
        self._loop_task: asyncio.Task | None = None
        self._incident_manager = IncidentManager()

    def is_endpoint_in_flight(self, endpoint_id: int) -> bool:
        return endpoint_id in self._in_flight

    async def acquire_endpoint_run_lock(self, endpoint_id: int) -> bool:
        """Atomically acquires the execution lock for an endpoint.

        Returns True if acquired; False if a check is already in-flight (overlap prevention).
        """
        async with self._lock:
            if endpoint_id in self._in_flight:
                return False
            self._in_flight.add(endpoint_id)
            return True

    async def release_endpoint_run_lock(self, endpoint_id: int) -> None:
        """Releases the execution lock for an endpoint."""
        async with self._lock:
            self._in_flight.discard(endpoint_id)

    async def execute_endpoint_check(self, endpoint_id: int) -> None:
        """Executes a single check bounded by semaphore and overlap lock."""
        acquired = await self.acquire_endpoint_run_lock(endpoint_id)
        if not acquired:
            logger.info("Skipping overlapping check for endpoint %d (already in flight)", endpoint_id)
            return

        try:
            async with self.semaphore:
                # Run database probe work in worker session
                with self.session_factory() as db:
                    endpoint = (
                        db.query(MonitoredEndpoint)
                        .filter(MonitoredEndpoint.id == endpoint_id)
                        .first()
                    )
                    if not endpoint or not endpoint.is_active or endpoint.status == EndpointStatus.PAUSED:
                        return

                    # Detach endpoint attributes for probe
                    endpoint_copy = MonitoredEndpoint(
                        id=endpoint.id,
                        name=endpoint.name,
                        url=endpoint.url,
                        method=endpoint.method,
                        headers=endpoint.headers,
                        body=endpoint.body,
                        timeout_seconds=endpoint.timeout_seconds,
                        expected_status=endpoint.expected_status,
                        retry_count=endpoint.retry_count,
                    )

                # Execute network probe outside DB lock
                summary = await execute_probe(endpoint=endpoint_copy)

                # Record result and update state machine
                with self.session_factory() as db:
                    self._incident_manager.record_probe_result(
                        db=db,
                        endpoint_id=endpoint_id,
                        summary=summary,
                    )
                    db.commit()

        except Exception as e:
            logger.exception("Unexpected error while checking endpoint %d: %s", endpoint_id, e)
        finally:
            await self.release_endpoint_run_lock(endpoint_id)

    async def _tick(self) -> None:
        """Queries for due endpoints and launches tasks."""
        now = utc_now()
        due_endpoint_ids: list[int] = []

        try:
            with self.session_factory() as db:
                due_endpoints = (
                    db.query(MonitoredEndpoint.id)
                    .filter(
                        MonitoredEndpoint.is_active.is_(True),
                        MonitoredEndpoint.status != EndpointStatus.PAUSED,
                        MonitoredEndpoint.next_check_due <= now,
                    )
                    .all()
                )
                due_endpoint_ids = [row[0] for row in due_endpoints]
        except Exception as e:
            logger.error("Failed to query due endpoints: %s", e)
            return

        for eid in due_endpoint_ids:
            if not self.is_endpoint_in_flight(eid):
                asyncio.create_task(self.execute_endpoint_check(eid))

    async def _run_loop(self) -> None:
        logger.info("MonitoringScheduler loop started.")
        while not self._stop_event.is_set():
            await self._tick()
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.tick_interval_seconds,
                )
            except TimeoutError:
                pass
        logger.info("MonitoringScheduler loop terminated.")

    def start(self) -> None:
        if self._loop_task is None or self._loop_task.done():
            self._stop_event.clear()
            self._loop_task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        if self._loop_task and not self._loop_task.done():
            self._stop_event.set()
            try:
                await asyncio.wait_for(self._loop_task, timeout=5.0)
            except TimeoutError:
                self._loop_task.cancel()
