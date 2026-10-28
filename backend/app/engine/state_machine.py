from backend.app.db.models.endpoint import EndpointStatus


def evaluate_health_transition(
    current_status: EndpointStatus,
    probe_success: bool,
    consecutive_failures: int,
    consecutive_successes: int,
    failure_threshold: int = 2,
    recovery_threshold: int = 2,
) -> tuple[EndpointStatus, bool]:
    """Evaluates state machine transition with hysteresis to prevent flapping.

    Returns:
        (new_status, has_changed)
    """
    if current_status == EndpointStatus.PAUSED:
        return EndpointStatus.PAUSED, False

    if probe_success:
        if current_status == EndpointStatus.HEALTHY:
            return EndpointStatus.HEALTHY, False

        # If previously DEGRADED or DOWN, check if recovery threshold met
        if consecutive_successes >= recovery_threshold:
            return EndpointStatus.HEALTHY, True
        else:
            # Partially recovering
            new_status = EndpointStatus.DEGRADED
            return new_status, (new_status != current_status)
    else:
        # Probe failed
        if consecutive_failures >= failure_threshold:
            new_status = EndpointStatus.DOWN
            return new_status, (new_status != current_status)
        else:
            # 1 failure but not yet at failure_threshold -> DEGRADED
            new_status = EndpointStatus.DEGRADED
            return new_status, (new_status != current_status)
