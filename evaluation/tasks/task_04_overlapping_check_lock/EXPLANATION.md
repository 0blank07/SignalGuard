# Explanation: Check Stampedes and Concurrency Control

## Root Cause

Monitoring schedulers typically operate on tick loops (e.g. evaluating active monitors every second). When target endpoints suffer from high latency or degradation, response time can easily exceed the polling interval ($T_{latency} > T_{interval}$).

Without per-endpoint in-flight tracking, the scheduler commits the **accumulation anti-pattern**:
$$\text{Accumulated Tasks} \approx \frac{T_{timeout}}{T_{interval}}$$
For a 30s timeout and a 5s interval, up to 6 concurrent probe tasks accumulate against a single struggling endpoint, exacerbating the outage.

## Resolution

In `solution.py`, we implement:
1. An atomic in-flight registry (`set[int]` guarded by an `asyncio.Lock` or `threading.Lock`).
2. `acquire(endpoint_id)` checks if `endpoint_id in in_flight`:
   - If present: logs a skip metric and returns `False`.
   - If absent: adds `endpoint_id` and returns `True`.
3. `release(endpoint_id)` is invoked in a `finally` block of the task worker, guaranteeing socket and memory release.
