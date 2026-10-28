# BUGGY STARTER: Flapping zero-hysteresis state machine

def update_health(
    current_state: str,
    consecutive_failures: int,
    consecutive_successes: int,
    failure_threshold: int = 3,
    recovery_threshold: int = 2,
) -> tuple[str, bool]:
    # BUG: Flaps immediately between HEALTHY and DOWN on single check!
    if consecutive_failures > 0:
        new_state = "DOWN"
    else:
        new_state = "HEALTHY"

    return new_state, (new_state != current_state)
