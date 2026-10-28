from backend.app.db.models.endpoint import EndpointStatus
from backend.app.engine.state_machine import evaluate_health_transition


def test_stays_healthy_on_success():
    new_status, changed = evaluate_health_transition(
        current_status=EndpointStatus.HEALTHY,
        probe_success=True,
        consecutive_failures=0,
        consecutive_successes=5,
        failure_threshold=2,
        recovery_threshold=2,
    )
    assert new_status == EndpointStatus.HEALTHY
    assert changed is False


def test_transitions_to_degraded_on_first_failure():
    # 1st failure under threshold of 2 -> DEGRADED
    new_status, changed = evaluate_health_transition(
        current_status=EndpointStatus.HEALTHY,
        probe_success=False,
        consecutive_failures=1,
        consecutive_successes=0,
        failure_threshold=2,
        recovery_threshold=2,
    )
    assert new_status == EndpointStatus.DEGRADED
    assert changed is True


def test_transitions_to_down_on_reaching_failure_threshold():
    # 2nd consecutive failure reaches threshold of 2 -> DOWN
    new_status, changed = evaluate_health_transition(
        current_status=EndpointStatus.DEGRADED,
        probe_success=False,
        consecutive_failures=2,
        consecutive_successes=0,
        failure_threshold=2,
        recovery_threshold=2,
    )
    assert new_status == EndpointStatus.DOWN
    assert changed is True


def test_recovery_hysteresis_requires_consecutive_successes():
    # Service is DOWN. 1st success is not enough (recovery_threshold=2) -> remains DOWN or DEGRADED
    new_status, changed = evaluate_health_transition(
        current_status=EndpointStatus.DOWN,
        probe_success=True,
        consecutive_failures=0,
        consecutive_successes=1,
        failure_threshold=2,
        recovery_threshold=2,
    )
    assert new_status == EndpointStatus.DEGRADED
    assert changed is True

    # 2nd success reaches threshold -> recovers to HEALTHY
    final_status, final_changed = evaluate_health_transition(
        current_status=EndpointStatus.DEGRADED,
        probe_success=True,
        consecutive_failures=0,
        consecutive_successes=2,
        failure_threshold=2,
        recovery_threshold=2,
    )
    assert final_status == EndpointStatus.HEALTHY
    assert final_changed is True
