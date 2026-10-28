import concurrent.futures

from target import ExecutionCoordinator


def test_public_acquire_and_release():
    coord = ExecutionCoordinator()
    assert coord.acquire(1) is True
    coord.release(1)


def test_verifier_duplicate_acquire_blocked():
    coord = ExecutionCoordinator()
    # First acquire succeeds
    assert coord.acquire(10) is True
    assert coord.is_in_flight(10) is True

    # Overlapping second acquire MUST return False
    assert coord.acquire(10) is False, "Expected overlapping acquire for same endpoint to be rejected!"

    # Release clears lock
    coord.release(10)
    assert coord.is_in_flight(10) is False

    # Now acquire should succeed again
    assert coord.acquire(10) is True
    coord.release(10)


def test_verifier_concurrent_acquisition_single_winner():
    coord = ExecutionCoordinator()
    endpoint_id = 99

    def attempt_acquire():
        return coord.acquire(endpoint_id)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(attempt_acquire) for _ in range(10)]
        results = [f.result() for f in futures]

    successes = sum(1 for r in results if r is True)
    assert successes == 1, f"Expected exactly 1 thread to acquire lock, but {successes} succeeded!"


def test_verifier_different_endpoints_independent():
    coord = ExecutionCoordinator()
    assert coord.acquire(1) is True
    assert coord.acquire(2) is True
    assert coord.acquire(3) is True

    assert coord.acquire(1) is False
    assert coord.acquire(2) is False

    coord.release(1)
    assert coord.acquire(1) is True
