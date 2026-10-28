import concurrent.futures

from target import IncidentStore


def test_public_sequential_incident_lifecycle():
    store = IncidentStore()
    inc = store.record_failure(endpoint_id=1, error_message="Timeout")
    assert inc.status == "OPEN"
    assert inc.failure_count == 1


def test_verifier_concurrent_failures_single_incident():
    store = IncidentStore()
    endpoint_id = 42
    concurrency = 10

    def worker(i: int):
        return store.record_failure(endpoint_id, f"Error from worker {i}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(worker, i) for i in range(concurrency)]
        for f in futures:
            f.result()

    # Verify how many OPEN incidents exist for this endpoint
    open_incidents = [
        inc for inc in store.incidents
        if inc.endpoint_id == endpoint_id and inc.status == "OPEN"
    ]

    assert len(open_incidents) == 1, (
        f"Concurrency violation: Expected exactly 1 active incident, but found {len(open_incidents)}! "
        f"Race condition in check-then-act."
    )
    assert open_incidents[0].failure_count == concurrency


def test_verifier_multiple_endpoints_isolated():
    store = IncidentStore()

    def worker(eid: int):
        store.record_failure(eid, f"Error for {eid}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(worker, i % 4) for i in range(16)]
        for f in futures:
            f.result()

    for eid in range(4):
        open_incs = [inc for inc in store.incidents if inc.endpoint_id == eid and inc.status == "OPEN"]
        assert len(open_incs) == 1
        assert open_incs[0].failure_count == 4
