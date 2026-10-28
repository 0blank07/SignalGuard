from target import update_health


def test_public_stays_healthy():
    state, changed = update_health("HEALTHY", consecutive_failures=0, consecutive_successes=5)
    assert state == "HEALTHY"
    assert changed is False
