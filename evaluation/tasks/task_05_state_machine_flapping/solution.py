def update_health(
    current_state: str,
    consecutive_failures: int,
    consecutive_successes: int,
    failure_threshold: int = 3,
    recovery_threshold: int = 2,
) -> tuple[str, bool]:
    if consecutive_failures > 0:
        # Service experienced failure(s)
        if consecutive_failures >= failure_threshold:
            new_state = "DOWN"
        else:
            # Under threshold: mark as DEGRADED instead of immediately DOWN
            new_state = "DEGRADED"
    else:
        # Service experienced success(es)
        if current_state == "HEALTHY":
            new_state = "HEALTHY"
        elif consecutive_successes >= recovery_threshold:
            new_state = "HEALTHY"
        else:
            # Partially recovering
            new_state = "DEGRADED"

    return new_state, (new_state != current_state)
