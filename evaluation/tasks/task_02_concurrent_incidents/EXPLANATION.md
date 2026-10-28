# Explanation: Concurrency Race Condition in Incident Creation

## Root Cause

The starter code implemented incident tracking using a naive, non-synchronized check:
1. Thread A queries for an active incident: none exists.
2. Thread B queries for an active incident: none exists.
3. Thread A inserts Incident #1.
4. Thread B inserts Incident #2.

Both incidents remain in `OPEN` status, causing:
- Double alerts sent to on-call teams (pager fatigue).
- Fragmented timelines and disjointed metric reporting.
- Inconsistent resolution behavior (e.g. recovering resolves only one incident, leaving the orphaned duplicate open forever).

## Resolution

In `solution.py`, we implement:
1. Thread-safe synchronization using a per-endpoint or global re-entrant lock (`threading.Lock` / `RLock`).
2. Atomic check-and-upsert: under lock protection, inspect existing records, mutate the open incident if found, or atomically append the new open incident.
3. In production SQL databases, this is achieved via `SELECT ... FOR UPDATE` row-level locks or PostgreSQL partial unique indexes (`CREATE UNIQUE INDEX ON incidents (endpoint_id) WHERE status = 'OPEN'`).
