# SignalGuard — System Architecture & Engineering Design

SignalGuard is an enterprise-grade backend reliability observability platform coupled with a deterministic software verification laboratory.

---

## 1. High-Level Component Topology

```mermaid
flowchart TD
    Client["Client / External Consumer"] -->|REST API over HTTP/S| FastAPI["FastAPI Application"]
    FastAPI --> Auth["Auth & Rate Limiting"]
    Auth --> Router["API Routers (/endpoints, /incidents, /metrics)"]
    
    subgraph DatabaseLayer ["Persistence Layer"]
        DB[(PostgreSQL / SQLite)]
        ORM["SQLAlchemy 2.0 ORM"]
        Migrations["Alembic Migrations"]
        ORM --> DB
        Migrations --> DB
    end

    Router --> ORM

    subgraph MonitoringEngine ["Autonomous Monitoring Engine"]
        Scheduler["AsyncIO Scheduler Loop"]
        Coord["Execution Coordinator (In-Flight Mutex)"]
        Sem["AsyncIO Semaphore (Concurrency Bound)"]
        Prober["Resilient Async Prober"]
        SSRF["SSRF Defense Layer (DNS & CIDR Filter)"]
        SM["Hysteresis State Machine"]
        IncMgr["Incident Manager"]

        Scheduler -->|Every Tick| Coord
        Coord -->|Acquire Lock| Sem
        Sem --> Prober
        Prober -->|Target URL Validation| SSRF
        Prober -->|Execute HTTP Probe| ExternalTarget["Monitored Target APIs"]
        Prober -->|ProbeExecutionSummary| IncMgr
        IncMgr --> SM
        IncMgr -->|Idempotent Upsert & Resolve| ORM
    end

    subgraph EvaluationLaboratory ["AI Code Evaluation Laboratory"]
        EvalCLI["Evaluation CLI (verify-all)"]
        Runner["Evaluation Runner"]
        Harness["Isolated Subprocess Harness"]
        TaskSuite["5 Deterministic Tasks"]
        
        EvalCLI --> Runner
        Runner --> Harness
        Harness --> TaskSuite
    end
```

---

## 2. Asynchronous Prober Execution & Overlap Prevention

When target response times exceed polling intervals ($T_{\text{latency}} > T_{\text{interval}}$), naive schedulers spawn accumulating concurrent probe tasks against struggling services (**check stampedes**).

SignalGuard prevents this via a per-endpoint in-flight execution lock:

```mermaid
sequenceDiagram
    autonumber
    participant S as Scheduler Tick
    participant C as Execution Coordinator
    participant Sem as AsyncIO Semaphore
    participant P as HTTP Prober
    participant T as Target API
    participant M as Incident Manager
    participant DB as Database

    S->>C: acquire(endpoint_id=42)
    alt Lock Already Held (Check in-flight)
        C-->>S: False (Skip / Postpone)
    else Lock Free
        C-->>S: True (Acquired)
        S->>Sem: acquire slot
        Sem->>P: execute_probe(endpoint_42)
        P->>P: validate_target_url (SSRF & DNS rebind check)
        P->>T: GET /health (timeout=10s)
        T-->>P: 200 OK (latency=42ms)
        P-->>Sem: release slot
        P->>M: record_probe_result(summary)
        M->>DB: persist CheckResult & evaluate state transition
        P->>C: release(endpoint_id=42)
    end
```

---

## 3. Finite State Machine with Hysteresis (Flapping Suppression)

To eliminate alert fatigue caused by single transient packet drops, the state machine requires multi-sample confirmation:
- **HEALTHY $\rightarrow$ DOWN:** requires $N$ consecutive failures (default 2 or 3). An initial failure moves the state to intermediate **DEGRADED**.
- **DOWN $\rightarrow$ HEALTHY:** requires $M$ consecutive successes (default 2).

```mermaid
stateDiagram-v2
    [*] --> HEALTHY
    
    HEALTHY --> DEGRADED: Single Probe Failure
    HEALTHY --> HEALTHY: Probe Success

    DEGRADED --> HEALTHY: Recovery Threshold Met (consecutive successes >= 2)
    DEGRADED --> DOWN: Failure Threshold Met (consecutive failures >= 2)
    DEGRADED --> DEGRADED: Continued partial flapping

    DOWN --> DEGRADED: First successful probe
    DOWN --> DOWN: Probe Failure (updates failure_count & last_seen_at)

    HEALTHY --> PAUSED: Operator pause
    DEGRADED --> PAUSED: Operator pause
    DOWN --> PAUSED: Operator pause
    PAUSED --> HEALTHY: Operator resume
```

---

## 4. Single-Active-Incident Invariant

SignalGuard guarantees that for any endpoint $E$, there is at most **one active incident** ($\text{status} \in \{\text{OPEN}, \text{ACKNOWLEDGED}\}$) at any point in time:

```mermaid
flowchart TD
    ProbeFailed["Probe Failed Threshold -> Status: DOWN"] --> QueryActive{"Active Incident Exists for Endpoint?"}
    QueryActive -->|Yes| UpdateExisting["Update existing incident: failure_count += 1, last_seen_at = now()"]
    QueryActive -->|No| CreateNew["Atomic INSERT: status='OPEN', severity='HIGH', event='TRIGGERED'"]
    
    ProbeSuccess["Probe Success -> Status: HEALTHY"] --> QueryOpen{"Active Incident Exists?"}
    QueryOpen -->|Yes| AutoResolve["Atomic UPDATE: status='RESOLVED', resolved_at=now(), event='RESOLVED'"]
    QueryOpen -->|No| NoOp["Maintain HEALTHY status"]
```
