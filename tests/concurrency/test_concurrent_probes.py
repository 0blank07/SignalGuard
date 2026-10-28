import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.base import Base
from backend.app.engine.scheduler import MonitoringScheduler


@pytest.fixture
def db_session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session


@pytest.mark.asyncio
async def test_scheduler_overlap_lock_prevents_duplicate_in_flight(db_session_factory):
    scheduler = MonitoringScheduler(
        session_factory=db_session_factory,
        max_concurrent_checks=5,
        tick_interval_seconds=0.05,
    )

    # Simulate an endpoint running in-flight
    assert scheduler.is_endpoint_in_flight(1) is False

    acquired = await scheduler.acquire_endpoint_run_lock(1)
    assert acquired is True
    assert scheduler.is_endpoint_in_flight(1) is True

    # Second concurrent attempt to acquire lock for same endpoint must fail / return False
    second_attempt = await scheduler.acquire_endpoint_run_lock(1)
    assert second_attempt is False

    # Releasing the lock clears the in-flight state
    await scheduler.release_endpoint_run_lock(1)
    assert scheduler.is_endpoint_in_flight(1) is False


@pytest.mark.asyncio
async def test_scheduler_semaphore_bounds_concurrency(db_session_factory):
    max_concurrency = 3
    scheduler = MonitoringScheduler(
        session_factory=db_session_factory,
        max_concurrent_checks=max_concurrency,
        tick_interval_seconds=0.05,
    )

    current_concurrent = 0
    max_observed_concurrency = 0

    async def mock_probe_task(endpoint_id: int):
        nonlocal current_concurrent, max_observed_concurrency
        async with scheduler.semaphore:
            current_concurrent += 1
            max_observed_concurrency = max(max_observed_concurrency, current_concurrent)
            await asyncio.sleep(0.05)
            current_concurrent -= 1

    # Launch 10 simultaneous tasks
    tasks = [asyncio.create_task(mock_probe_task(i)) for i in range(10)]
    await asyncio.gather(*tasks)

    assert max_observed_concurrency <= max_concurrency
