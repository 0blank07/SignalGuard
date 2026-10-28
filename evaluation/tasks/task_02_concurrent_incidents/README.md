# Task 02: Concurrency-Safe Incident Deduplication

## Problem Statement

When an API monitor experiences downtime, multiple background checks or alerts may trigger concurrently. 

In `target.py`, `IncidentStore.record_failure(endpoint_id: int, error_message: str)` is responsible for creating an incident when a service goes down, or updating `failure_count` and `last_seen_at` if an incident is already open.

Currently, the implementation exhibits a classic **check-then-act race condition**:
```python
active = self.get_active_incident(endpoint_id)
if active is None:
    # Context switch occurs here!
    self.create_incident(...)
```
When multiple threads or coroutines invoke `record_failure` concurrently, multiple active incidents are inserted for the same endpoint!

## Invariants to Enforce

1. **Single Active Incident Invariant:** For any given `endpoint_id`, there must NEVER be more than one incident with `status == "OPEN"` at any point in time.
2. **Failure Aggregation:** When an incident is already OPEN, subsequent failure records must increment `failure_count` and update `last_seen_at` without creating a duplicate record.
3. **Resolution:** `resolve_incident(endpoint_id: int)` sets status to `"RESOLVED"`.
