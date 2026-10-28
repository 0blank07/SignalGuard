# ADR 0001: AsyncIO Prober Concurrency and Semaphore Bounds

## Status
Accepted

## Context
Monitoring hundreds of remote endpoints concurrently can cause socket exhaustion, event loop lag, and unbounded memory consumption if concurrency is unconstrained.

## Decision
We implemented a single-process AsyncIO event loop model using:
1. `asyncio.Semaphore` with a configurable ceiling (`MAX_CONCURRENT_CHECKS`, default 50).
2. Per-endpoint in-flight execution locking to prevent overlapping check stampedes.
3. Decoupling HTTP probing (network I/O) from database persistence to minimize database connection hold times.

## Consequences
- **Positive:** Bounded socket consumption; zero threat of thundering herd against local or remote resources.
- **Trade-off:** In a multi-worker cluster, distributed coordination would require Redis-based locks (Redlock or advisory locks). For single-node production, AsyncIO in-flight locking is deterministic, faster, and requires zero external daemon overhead.
