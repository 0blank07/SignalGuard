from target import update_health


def test_public_stays_healthy():
    state, changed = update_health("HEALTHY", consecutive_failures=0, consecutive_successes=5)
    assert state == "HEALTHY"
    assert changed is False


def test_verifier_single_failure_does_not_mark_down():
    # 1 failure with threshold=3 must become DEGRADED, NOT DOWN!
    state, changed = update_health(
        current_state="HEALTHY",
        consecutive_failures=1,
        consecutive_successes=0,
        failure_threshold=3,
    )
    assert state == "DEGRADED", f"Expected DEGRADED on 1 failure, got {state}!"
    assert changed is True


def test_verifier_reaches_down_only_at_threshold():
    state, _ = update_health(
        current_state="DEGRADED",
        consecutive_failures=2,
        consecutive_successes=0,
        failure_threshold=3,
    )
    assert state == "DEGRADED"

    state, changed = update_health(
        current_state="DEGRADED",
        consecutive_failures=3,
        consecutive_successes=0,
        failure_threshold=3,
    )
    assert state == "DOWN"
    assert changed is True


def test_verifier_recovery_requires_hysteresis():
    # 1 success after being DOWN must NOT immediately flip back to HEALTHY
    state, changed = update_health(
        current_state="DOWN",
        consecutive_failures=0,
        consecutive_successes=1,
        recovery_threshold=2,
    )
    assert state == "DEGRADED", f"Expected DEGRADED during partial recovery, got {state}!"

    # 2nd consecutive success reaches recovery threshold
    state, changed = update_health(
        current_state="DEGRADED",
        consecutive_failures=0,
        consecutive_successes=2,
        recovery_threshold=2,
    )
    assert state == "HEALTHY"
    assert changed is True
