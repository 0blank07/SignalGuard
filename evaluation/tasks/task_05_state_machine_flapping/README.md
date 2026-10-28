# Task 05: Health State Machine & Flapping Suppression

## Problem Statement

Networks inherently suffer from minor, transient packet loss. If a monitoring platform marks an API as `DOWN` on a single failed check and marks it `HEALTHY` on a single successful check, an endpoint with 5% packet loss will toggle its state dozens of times an hour (**flapping**).

Every flip triggers notifications, opens incidents, resolves incidents, and floods on-call channels with noise.

The starter code in `target.py` implements a zero-hysteresis state machine:
```python
if is_success:
    return "HEALTHY"
else:
    return "DOWN"
```

## Requirements

Implement a robust hysteresis state machine in `target.py`:
- States: `"HEALTHY"`, `"DEGRADED"`, `"DOWN"`.
- `update_health(current_state: str, consecutive_failures: int, consecutive_successes: int, failure_threshold: int = 3, recovery_threshold: int = 2) -> tuple[str, bool]`:
  - Returns `(new_state, state_changed)`
  - Transition to `DOWN` only occurs when `consecutive_failures >= failure_threshold`.
  - Single failure while `HEALTHY` moves state to `DEGRADED` (not `DOWN`).
  - While `DOWN`, a single success moves state to `DEGRADED`, but requires `consecutive_successes >= recovery_threshold` to return to `HEALTHY`.
  - While `HEALTHY`, any success keeps it `HEALTHY` (`state_changed=False`).
