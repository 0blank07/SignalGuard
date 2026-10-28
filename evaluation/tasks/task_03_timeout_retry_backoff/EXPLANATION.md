# Explanation: Retry Storms and Jittered Backoff

## Root Cause

1. **Retrying Non-Idempotent / Deterministic Errors:** Retrying 404 or 401 will never result in success. Retrying it 3 times just triples load on an already stressed API.
2. **Unbounded Exponential Explosion:** Without a `max_delay` cap, exponential growth ($2^{10} = 1024$s) locks worker coroutines and exhausts queue capacities.
3. **Synchronized Retries (Thundering Herd):** If 500 monitoring tasks experience a brief network blip at $T=0$, all 500 tasks will retry at exactly $T=1.0$, $T=2.0$, and $T=4.0$. This synchronized pulse can knock the recovering service back offline.

## Resolution

1. Strictly partition error classifications:
   - Transient: Network partition, TCP timeout, DNS transient failure, 5xx.
   - Permanent: 4xx, authentication, SSRF block.
2. Apply Full Jitter: randomize delay uniformly between $0.5 \times delay$ and $delay$, smearing retry traffic across a wider window.
3. Cap delay explicitly with `min(delay, max_delay)`.
