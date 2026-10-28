# ADR 0003: Incident Deduplication Invariants and State Hysteresis

## Status
Accepted

## Context
Network jitter can cause transient probe failures. Naive incident management results in:
1. Alert flapping: Rapidly opening and closing incidents on single-packet loss.
2. Duplicate incidents: Concurrent probe failures racing to open separate active incidents for the same endpoint.

## Decision
1. Implement a 3-state finite state machine (`HEALTHY`, `DEGRADED`, `DOWN`).
2. Enforce hysteresis: Transition to `DOWN` requires $\ge 2$ consecutive failures. Recovery to `HEALTHY` requires $\ge 2$ consecutive successes.
3. Enforce the **Single-Active-Incident Invariant**: At most one active incident (`OPEN` or `ACKNOWLEDGED`) per endpoint at any given time.
4. When already `DOWN`, subsequent failed probes update `last_seen_at` and increment `failure_count` rather than spawning duplicate records.
5. Returning to `HEALTHY` automatically resolves any open incidents with an audit event log.

## Consequences
- **Positive:** Zero duplicate incidents; complete elimination of flapping alert storms; clear audit trail of outage duration.
- **Trade-off:** Recovery requires two consecutive successful polling cycles before marking healthy (desirable behavior in production SRE).
