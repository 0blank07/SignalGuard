from target import IncidentStore


def test_public_sequential_incident_lifecycle():
    store = IncidentStore()
    inc = store.record_failure(endpoint_id=1, error_message="Timeout")
    assert inc.status == "OPEN"
    assert inc.failure_count == 1

    # Second failure should aggregate
    inc2 = store.record_failure(endpoint_id=1, error_message="Timeout again")
    assert inc2.id == inc.id
    assert inc2.failure_count == 2

    # Resolve
    resolved = store.resolve_incident(endpoint_id=1)
    assert resolved is True
    assert store.get_active_incident(endpoint_id=1) is None
