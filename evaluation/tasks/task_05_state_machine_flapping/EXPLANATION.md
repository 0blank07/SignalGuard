# Explanation: Alert Flapping and Hysteresis Design

## Root Cause

Zero-hysteresis state machines treat monitoring checks as point-in-time absolutes. In distributed systems, occasional network jitter (WiFi packet loss, TCP SYN drop, transient proxy timeout) is expected.

Toggling state on a single check causes **Alert Oscillation / Alert Fatigue**:
- Incident opened at 10:00:00 (1 fail)
- Incident closed at 10:00:30 (1 pass)
- Incident opened at 10:01:00 (1 fail)
- Incident closed at 10:01:30 (1 pass)

## Resolution

Introduce state hysteresis:
1. Require multiple consecutive failures ($N \ge 2$ or $3$) to declare an outage (`DOWN`).
2. Require multiple consecutive successes ($M \ge 2$) to declare full recovery (`HEALTHY`).
3. Introduce an intermediate `DEGRADED` state for transient disruptions, avoiding premature high-severity incident generation.
