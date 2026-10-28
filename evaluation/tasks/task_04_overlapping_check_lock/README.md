# Task 04: Preventing Overlapping Probe Stampedes

## Problem Statement

In an async monitoring engine, each endpoint has a configured `interval_seconds` (e.g. 5 seconds) and a `timeout_seconds` (e.g. 15 seconds). 

If an external service begins hanging or degrading, a probe request may take 14 seconds before timing out. If the scheduler ticks every 5 seconds and launches probe tasks unconditionally:
- Tick 1 (T=0s): Probe #1 starts (runs until T=14s)
- Tick 2 (T=5s): Probe #2 starts while #1 is still running!
- Tick 3 (T=10s): Probe #3 starts while #1 and #2 are still running!

This causes a **Check Stampede**: probe tasks pile up, exhaust socket file descriptors, overwhelm the event loop, and exacerbate downtime on the target service.

## Requirements

Implement in `target.py` an `ExecutionCoordinator`:
- `acquire(endpoint_id: int) -> bool`:
  - Returns `True` and marks the endpoint as in-flight if no probe is currently running.
  - Returns `False` if a probe is already running for this endpoint.
- `release(endpoint_id: int) -> None`:
  - Clears the in-flight state for the endpoint.
- `is_in_flight(endpoint_id: int) -> bool`:
  - Returns whether an endpoint currently has an active probe running.
- Must be thread-safe / async-safe against concurrent calls.
