# SignalGuard Production Backend & AI Evaluation Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build SignalGuard into a production-grade backend reliability and API observability platform with an autonomous monitoring engine, concurrency-safe incident management, hardened SSRF defense, comprehensive automated tests, and a dedicated 5-task AI code-evaluation laboratory with deterministic verifiers.

**Architecture:** A modular Python 3.12+ backend built on FastAPI and SQLAlchemy 2.0. The core engine runs an asynchronous probe worker using `asyncio` with bounded concurrency (`Semaphore`), per-endpoint execution locks, and an SSRF-hardened HTTP client. Incident state transitions follow an explicit finite state machine with database transaction isolation to eliminate duplicate incidents. A dedicated `evaluation/` laboratory provides isolated tasks, buggy starter code, reference solutions, public/hidden tests, and an evaluation CLI verifier for AI model and engineer benchmark assessment.

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy 2.0, Pydantic v2, HTTPX, SQLite/PostgreSQL, Alembic, pytest, pytest-asyncio, pytest-cov, Ruff, Docker & Docker Compose, GitHub Actions.

**Spec:** [USER_REQUEST] SignalGuard — Build a Production-Grade Backend Engineering & AI Evaluation Project.

---

## Global Constraints

- Python 3.12+ compatibility with strict type annotations across public interfaces.
- Zero committed secrets or API keys; use environment-based configuration with secure defaults.
- SSRF defense must block loopback (`127.0.0.0/8`, `::1`), private RFC 1918 subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), link-local (`169.254.0.0/16`, `fe80::/10`), IPv6 ULA (`fc00::/7`), and cloud metadata services (`169.254.169.254`), with DNS rebinding and redirect verification.
- Incident management must be concurrency-safe: at most one ACTIVE/OPEN incident per endpoint at any time.
- Monitoring prober must not block the event loop; concurrency must be strictly bounded via `asyncio.Semaphore`.
- Overlapping check stampedes must be prevented via per-endpoint in-flight execution tracking.
- Test suite must be 100% deterministic and runnable offline without external internet connectivity (using mock transport and local servers).
- Evaluation lab tasks must be completely decoupled from the production runtime, with automated deterministic verifiers producing structured JSON results.

---

## Review Focus

1. **DNS Rebinding & Redirect SSRF Bypass:** A monitoring endpoint URL points to a public DNS name that resolves to a public IP on initial check, but redirects or rebinds to `169.254.169.254` or `127.0.0.1`. Expected behavior: Transport verifies the actual connected IP address on every request and every redirect hop before sending HTTP payloads.
2. **Concurrent Duplicate Incidents Under Flapping Network:** Multiple concurrent probe failures for the same endpoint execute simultaneously. Expected behavior: Database transaction with lock or unique constraint ensures only one incident is created, while subsequent failures update `last_seen_at` without duplicate records.
3. **Check Stampede Under High Latency:** An endpoint has a 5-second polling interval, but target server takes 15 seconds to time out. Expected behavior: In-flight check tracking skips or postpones overlapping scheduled runs for that endpoint rather than spawning accumulating concurrent probe tasks.
4. **Response Payload Memory Exhaustion:** Monitored endpoint responds with a massive streaming payload (e.g. 500MB chunked body). Expected behavior: Prober reads at most a bounded response preview (e.g. 10KB) and closes the socket immediately to prevent out-of-memory crashes.
5. **Database Session Leaks Across Async Tasks:** Async worker spawning probe tasks fails to release SQLAlchemy sessions on unhandled network exceptions. Expected behavior: Context-managed sessions with guaranteed cleanup in `finally` blocks, preserving connection pool health.

---

## File Structure & Module Map

```text
SignalGuard/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                     # FastAPI application factory & lifespan
│   │   ├── config.py                   # Pydantic v2 settings & environment loading
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py                 # Dependency injection (DB session, auth)
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py           # V1 API router aggregation
│   │   │   │   ├── endpoints.py        # /api/v1/endpoints CRUD & pause/resume
│   │   │   │   ├── checks.py           # /api/v1/endpoints/{id}/history & /check
│   │   │   │   ├── incidents.py        # /api/v1/incidents & acknowledge/resolve
│   │   │   │   └── metrics.py          # /api/v1/endpoints/{id}/metrics & SLA
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── errors.py               # Standardized error classes & RFC-7807 handlers
│   │   │   ├── logging.py              # Structured JSON logging with credential redaction
│   │   │   └── security.py             # SSRF validator, IP resolver, redirect safety
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── session.py              # Engine, sessionmaker, transaction helpers
│   │   │   ├── base.py                 # DeclarativeBase with common mixins
│   │   │   └── models/
│   │   │       ├── __init__.py
│   │   │       ├── endpoint.py         # MonitoredEndpoint model
│   │   │       ├── check_result.py     # CheckResult model
│   │   │       └── incident.py         # Incident & IncidentEvent models
│   │   ├── engine/
│   │   │   ├── __init__.py
│   │   │   ├── prober.py               # Async HTTP prober with SSRF transport & retries
│   │   │   ├── state_machine.py        # Health state transition logic (HEALTHY, DEGRADED, DOWN)
│   │   │   ├── incident_manager.py     # Incident lifecycle, deduplication & resolution
│   │   │   ├── scheduler.py            # AsyncIO polling worker with semaphore & overlap locks
│   │   │   └── metrics_calculator.py   # Uptime SLA %, p50/p95 latency aggregation
│   │   └── schemas/
│   │       ├── __init__.py
│   │       ├── endpoint.py             # EndpointCreate, EndpointUpdate, EndpointResponse
│   │       ├── check.py                # CheckResultResponse, TriggerCheckRequest
│   │       ├── incident.py             # IncidentResponse, IncidentResolveRequest
│   │       ├── metrics.py              # EndpointMetricsResponse, HealthSummary
│   │       └── common.py               # PaginationParams, PaginatedResponse, ErrorResponse
│   ├── alembic/                        # Database migration scripts
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   ├── alembic.ini
│   └── Dockerfile
├── evaluation/                         # Dedicated Code Evaluation & Verifier Lab
│   ├── __init__.py
│   ├── cli.py                          # Verifier CLI: run, verify, verify-all
│   ├── runner.py                       # Deterministic task executor & report generator
│   ├── common/
│   │   ├── __init__.py
│   │   ├── types.py                    # TaskSpec, EvaluationResult, TestStatus
│   │   └── harness.py                  # Isolated test harness & timeout wrappers
│   └── tasks/
│       ├── task_01_ssrf_protection/
│       │   ├── spec.json
│       │   ├── README.md
│       │   ├── EXPLANATION.md
│       │   ├── starter.py
│       │   ├── solution.py
│       │   ├── test_public.py
│       │   └── test_verifier.py
│       ├── task_02_concurrent_incidents/
│       │   ├── spec.json
│       │   ├── README.md
│       │   ├── EXPLANATION.md
│       │   ├── starter.py
│       │   ├── solution.py
│       │   ├── test_public.py
│       │   └── test_verifier.py
│       ├── task_03_timeout_retry_backoff/
│       │   ├── spec.json
│       │   ├── README.md
│       │   ├── EXPLANATION.md
│       │   ├── starter.py
│       │   ├── solution.py
│       │   ├── test_public.py
│       │   └── test_verifier.py
│       ├── task_04_overlapping_check_lock/
│       │   ├── spec.json
│       │   ├── README.md
│       │   ├── EXPLANATION.md
│       │   ├── starter.py
│       │   ├── solution.py
│       │   ├── test_public.py
│       │   └── test_verifier.py
│       └── task_05_state_machine_flapping/
│           ├── spec.json
│           ├── README.md
│           ├── EXPLANATION.md
│           ├── starter.py
│           ├── solution.py
│           ├── test_public.py
│           └── test_verifier.py
├── tests/
│   ├── conftest.py                     # Fixtures, test database, mock servers
│   ├── unit/
│   │   ├── test_security_ssrf.py
│   │   ├── test_state_machine.py
│   │   ├── test_retry_policy.py
│   │   └── test_metrics_calculator.py
│   ├── integration/
│   │   ├── test_api_endpoints.py
│   │   ├── test_api_incidents.py
│   │   ├── test_api_metrics.py
│   │   └── test_prober_execution.py
│   ├── concurrency/
│   │   ├── test_concurrent_probes.py
│   │   └── test_incident_deduplication.py
│   └── security/
│       └── test_ssrf_attacks.py
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt
├── .github/
│   └── workflows/
│       └── ci.yml
└── docs/
    ├── architecture.md
    ├── api_reference.md
    ├── evaluation_framework.md
    └── adr/
        ├── 0001-async-prober-concurrency.md
        ├── 0002-ssrf-mitigation-strategy.md
        └── 0003-incident-deduplication-invariants.md
```

---

## Tasks

### Task 1: Environment, Dependencies & Configuration Architecture

**Files:**
- Create: `backend/app/config.py`
- Create: `backend/app/core/logging.py`
- Create: `backend/app/core/errors.py`
- Create: `pyproject.toml`
- Modify: `requirements.txt`
- Modify: `.gitignore`
- Test: `tests/unit/test_config.py`

**Interfaces:**
- Consumes: Environment variables via `pydantic-settings` / `os.environ`.
- Produces: `get_settings() -> Settings`, `configure_logging()`, `AppException`, `NotFoundError`, `ConflictError`, `ValidationError`.

- [ ] **Step 1: Write the failing test for configuration and structured logging**
  Write tests in `tests/unit/test_config.py` validating that `Settings` defaults to SQLite in dev, enforces reasonable probe limits (e.g., minimum polling interval 5s, timeout cap 60s), parses CORS origins, and loads environment variables properly.
- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/unit/test_config.py -v` -> Expected: FAIL.
- [ ] **Step 3: Implement `backend/app/config.py`, `backend/app/core/logging.py`, `backend/app/core/errors.py`**
  Implement Pydantic Settings with validated database URL, max concurrency limits, default timeout, and secure redaction formatter for logging.
- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/unit/test_config.py -v` -> Expected: PASS.
- [ ] **Step 5: Commit**
  `git add pyproject.toml requirements.txt backend/app/config.py backend/app/core/ tests/unit/test_config.py`
  `git commit -m "feat(core): setup environment configuration, errors and logging"`

---

### Task 2: Core Domain Models & Database Persistence Layer

**Files:**
- Create: `backend/app/db/base.py`
- Create: `backend/app/db/session.py`
- Create: `backend/app/db/models/endpoint.py`
- Create: `backend/app/db/models/check_result.py`
- Create: `backend/app/db/models/incident.py`
- Create: `backend/app/db/models/__init__.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/001_initial_schema.py`
- Test: `tests/unit/test_models.py`

**Interfaces:**
- Consumes: `Settings.database_url`.
- Produces: `Base`, `engine`, `SessionLocal`, `get_db()`, `MonitoredEndpoint`, `CheckResult`, `Incident`, `IncidentEvent`.

- [ ] **Step 1: Write the failing test for database models and session lifecycles**
  Write tests in `tests/unit/test_models.py` that create an endpoint, record check results, verify foreign keys, index structures, and verify the constraint that active incidents have `status in ('OPEN', 'ACKNOWLEDGED')`.
- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/unit/test_models.py -v` -> Expected: FAIL.
- [ ] **Step 3: Implement SQLAlchemy 2.0 models with proper constraints and indexes**
  Implement `MonitoredEndpoint` (id, name, url, method, headers, interval_seconds, timeout_seconds, expected_status, is_active, current_status, created_at, updated_at).
  Implement `CheckResult` (id, endpoint_id, timestamp, status_code, response_time_ms, is_success, error_type, error_message).
  Implement `Incident` (id, endpoint_id, status, error_type, root_cause, started_at, resolved_at, last_seen_at, failure_count).
  Implement `IncidentEvent` (id, incident_id, event_type, timestamp, message).
  Configure session generator with auto-rollback on exception.
- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/unit/test_models.py -v` -> Expected: PASS.
- [ ] **Step 5: Commit**
  `git add backend/app/db/ backend/alembic/ tests/unit/test_models.py`
  `git commit -m "feat(db): implement core database models and alembic migration"`

---

### Task 3: Security Hardening & SSRF Defense Layer

**Files:**
- Create: `backend/app/core/security.py`
- Test: `tests/unit/test_security_ssrf.py`
- Test: `tests/security/test_ssrf_attacks.py`

**Interfaces:**
- Consumes: URL string from user input or redirection response.
- Produces: `validate_target_url(url: str, allow_private: bool = False) -> ParsedURLValidationResult`, `resolve_and_verify_ip(hostname: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]`, `SSRFSecurityException`.

- [ ] **Step 1: Write the failing test for SSRF defense and IP resolution**
  Write unit tests verifying rejection of:
  - `http://localhost/` and `http://127.0.0.1/`
  - Decimal, octal, hex encoded IPs (e.g. `http://0177.0.0.1`, `http://2130706433`)
  - Cloud metadata addresses (`http://169.254.169.254/latest/meta-data/`)
  - Private subnets (`http://10.0.0.1/`, `http://192.168.1.1/`, `http://172.16.0.1/`)
  - IPv6 loopback (`http://[::1]/`) and unique-local addresses
  - Unsupported protocols (`file:///etc/passwd`, `ftp://`, `gopher://`)
  - Valid public URLs are accepted (`https://api.github.com/status`).
- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/unit/test_security_ssrf.py -v` -> Expected: FAIL.
- [ ] **Step 3: Implement comprehensive IP validation and DNS safety check**
  Implement URL parsing with scheme enforcement (`http`, `https`), canonical host extraction, standard socket `getaddrinfo` resolution with timeout, and strict exclusion of `is_private`, `is_loopback`, `is_link_local`, `is_reserved`, `is_multicast`, and AWS/GCP metadata ranges.
- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/unit/test_security_ssrf.py tests/security/test_ssrf_attacks.py -v` -> Expected: PASS.
- [ ] **Step 5: Commit**
  `git add backend/app/core/security.py tests/unit/test_security_ssrf.py tests/security/test_ssrf_attacks.py`
  `git commit -m "feat(security): implement strict ssrf defense and safe ip resolver"`

---

### Task 4: Reliable Monitoring Engine & Resilient HTTP Prober

**Files:**
- Create: `backend/app/engine/prober.py`
- Create: `backend/app/engine/retry.py`
- Test: `tests/unit/test_retry_policy.py`
- Test: `tests/integration/test_prober_execution.py`

**Interfaces:**
- Consumes: `MonitoredEndpoint`, `validate_target_url`, `Settings`.
- Produces: `execute_probe(endpoint: MonitoredEndpoint, client: httpx.AsyncClient | None = None) -> ProbeExecutionSummary`, `RetryPolicy`.

- [ ] **Step 1: Write the failing test for prober and retry logic**
  Write tests with mock transports simulating:
  - 200 OK fast response -> success with latency.
  - ConnectTimeout / ReadTimeout -> classified as TIMEOUT error.
  - DNS resolution failure -> classified as DNS_ERROR.
  - HTTP 500 / 503 -> classified as HTTP_ERROR.
  - Retry policy: 3 retries with backoff on 5xx or connection error, but immediate return on 4xx or SSRF block.
  - Max response body cutoff: prober does not read past 16KB.
- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/unit/test_retry_policy.py tests/integration/test_prober_execution.py -v` -> Expected: FAIL.
- [ ] **Step 3: Implement `execute_probe` and `RetryPolicy`**
  Implement async HTTP prober using `httpx.AsyncClient` with custom transport hook that re-checks destination IP on every hop, measures high-resolution duration with `time.perf_counter()`, safely truncates response snippets, and classifies network error variants into standardized error codes.
- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/unit/test_retry_policy.py tests/integration/test_prober_execution.py -v` -> Expected: PASS.
- [ ] **Step 5: Commit**
  `git add backend/app/engine/prober.py backend/app/engine/retry.py tests/unit/test_retry_policy.py tests/integration/test_prober_execution.py`
  `git commit -m "feat(engine): implement resilient async http prober and retry policy"`

---

### Task 5: Incident State Machine & Concurrency-Safe Incident Manager

**Files:**
- Create: `backend/app/engine/state_machine.py`
- Create: `backend/app/engine/incident_manager.py`
- Test: `tests/unit/test_state_machine.py`
- Test: `tests/concurrency/test_incident_deduplication.py`

**Interfaces:**
- Consumes: `ProbeExecutionSummary`, database `Session`, `MonitoredEndpoint`.
- Produces: `evaluate_health_transition(current_status, probe_success, consecutive_failures, consecutive_successes) -> (new_status, state_changed)`, `IncidentManager.record_probe_result(db, endpoint_id, probe_summary) -> IncidentUpdateResult`.

- [ ] **Step 1: Write the failing test for state machine transitions and incident deduplication**
  Write tests verifying:
  - Transition from HEALTHY to DOWN upon threshold failures.
  - Single incident opened when service goes DOWN.
  - Repeated failures while DOWN update `last_seen_at` and `failure_count` without creating duplicate incidents.
  - Recovery transition to HEALTHY automatically resolves the open incident and logs an `IncidentEvent(type="RESOLVED")`.
  - Concurrent failure events cannot create two open incidents for the same endpoint.
- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/unit/test_state_machine.py tests/concurrency/test_incident_deduplication.py -v` -> Expected: FAIL.
- [ ] **Step 3: Implement `StateMachine` and `IncidentManager` with transaction safety**
  Implement deterministic finite state machine (HEALTHY, DEGRADED, DOWN).
  Implement `IncidentManager` using database transactions with row-locking / check-or-create logic to guarantee idempotent incident creation and automated recovery resolution.
- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/unit/test_state_machine.py tests/concurrency/test_incident_deduplication.py -v` -> Expected: PASS.
- [ ] **Step 5: Commit**
  `git add backend/app/engine/state_machine.py backend/app/engine/incident_manager.py tests/unit/test_state_machine.py tests/concurrency/test_incident_deduplication.py`
  `git commit -m "feat(incident): implement state machine and concurrency-safe incident manager"`

---

### Task 6: Autonomous Async Scheduler & Concurrency Control

**Files:**
- Create: `backend/app/engine/scheduler.py`
- Test: `tests/concurrency/test_concurrent_probes.py`

**Interfaces:**
- Consumes: `MonitoredEndpoint` records, `execute_probe`, `IncidentManager`, `Settings.max_concurrent_checks`.
- Produces: `MonitoringScheduler.start()`, `MonitoringScheduler.stop()`, `MonitoringScheduler.schedule_check(endpoint_id)`.

- [ ] **Step 1: Write the failing test for the scheduler, semaphore bounds, and overlap prevention**
  Write tests verifying:
  - Bounded concurrency: with semaphore limit N, no more than N probe tasks run concurrently.
  - Overlap lock: if an endpoint check is already running when its next interval triggers, the scheduled check is skipped or deferred.
  - Graceful shutdown: scheduler stops background workers cleanly without leaving unhandled task exceptions.
- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/concurrency/test_concurrent_probes.py -v` -> Expected: FAIL.
- [ ] **Step 3: Implement `MonitoringScheduler`**
  Implement an asynchronous scheduler loop using `asyncio.Semaphore`, an in-flight check registry (`set[int]` with `asyncio.Lock`), and a periodic polling tick that fetches active endpoints whose `next_check_due <= now()`.
- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/concurrency/test_concurrent_probes.py -v` -> Expected: PASS.
- [ ] **Step 5: Commit**
  `git add backend/app/engine/scheduler.py tests/concurrency/test_concurrent_probes.py`
  `git commit -m "feat(scheduler): implement bounded async scheduler with overlap lock"`

---

### Task 7: Schemas, Metrics Calculator & REST API Endpoints

**Files:**
- Create: `backend/app/schemas/common.py`
- Create: `backend/app/schemas/endpoint.py`
- Create: `backend/app/schemas/check.py`
- Create: `backend/app/schemas/incident.py`
- Create: `backend/app/schemas/metrics.py`
- Create: `backend/app/engine/metrics_calculator.py`
- Create: `backend/app/api/deps.py`
- Create: `backend/app/api/v1/router.py`
- Create: `backend/app/api/v1/endpoints.py`
- Create: `backend/app/api/v1/checks.py`
- Create: `backend/app/api/v1/incidents.py`
- Create: `backend/app/api/v1/metrics.py`
- Modify: `backend/app/main.py`
- Test: `tests/integration/test_api_endpoints.py`
- Test: `tests/integration/test_api_incidents.py`
- Test: `tests/integration/test_api_metrics.py`

**Interfaces:**
- Consumes: SQLAlchemy session, DB models, `IncidentManager`, `MetricsCalculator`.
- Produces: FastAPI REST endpoints under `/api/v1`:
  - `POST /api/v1/endpoints` (with SSRF validation)
  - `GET /api/v1/endpoints` (paginated)
  - `GET /api/v1/endpoints/{id}`
  - `PATCH /api/v1/endpoints/{id}`
  - `DELETE /api/v1/endpoints/{id}`
  - `POST /api/v1/endpoints/{id}/pause` & `resume`
  - `POST /api/v1/endpoints/{id}/check` (immediate manual trigger)
  - `GET /api/v1/endpoints/{id}/history`
  - `GET /api/v1/endpoints/{id}/metrics` (uptime %, p50/p95 latency)
  - `GET /api/v1/incidents`
  - `GET /api/v1/incidents/{id}`
  - `POST /api/v1/incidents/{id}/acknowledge`
  - `POST /api/v1/incidents/{id}/resolve`
  - `GET /health` & `/api/v1/health`

- [ ] **Step 1: Write the failing tests for API endpoints**
  Write integration tests in `tests/integration/test_api_endpoints.py`, `test_api_incidents.py`, `test_api_metrics.py` covering endpoint CRUD, pagination, SSRF rejection on creation, pause/resume, on-demand check execution, incident queries, acknowledgment, and SLA uptime calculation.
- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/integration/test_api_endpoints.py -v` -> Expected: FAIL.
- [ ] **Step 3: Implement Pydantic schemas, metrics calculator, and FastAPI routes**
  Implement Pydantic v2 schemas with field validation.
  Implement `MetricsCalculator` aggregating uptime percentage over 24h/7d/30d and latency percentiles.
  Implement route controllers with RFC-7807 problem detail error responses and dependency injection.
- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/integration/test_api_endpoints.py tests/integration/test_api_incidents.py tests/integration/test_api_metrics.py -v` -> Expected: PASS.
- [ ] **Step 5: Commit**
  `git add backend/app/schemas/ backend/app/api/ backend/app/engine/metrics_calculator.py backend/app/main.py tests/integration/`
  `git commit -m "feat(api): implement v1 rest endpoints, schemas and metrics calculation"`

---

### Task 8: Evaluation Framework Core & Verifier Runner

**Files:**
- Create: `evaluation/__init__.py`
- Create: `evaluation/common/types.py`
- Create: `evaluation/common/harness.py`
- Create: `evaluation/runner.py`
- Create: `evaluation/cli.py`
- Test: `tests/unit/test_evaluation_runner.py`

**Interfaces:**
- Consumes: Task directories in `evaluation/tasks/`.
- Produces: `EvaluationRunner.run_task(task_id: str, candidate_target: str) -> TaskEvaluationReport`, `python -m evaluation.cli verify <task_id> [--target starter|solution]`, `python -m evaluation.cli verify-all`.

- [ ] **Step 1: Write the failing test for the evaluation harness and runner**
  Write tests in `tests/unit/test_evaluation_runner.py` asserting that the runner correctly discovers tasks, executes tests in isolated subprocesses with timeouts, captures stdout/stderr, and returns structured `EvaluationResult(passed=bool, score=float, test_results=list)`.
- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/unit/test_evaluation_runner.py -v` -> Expected: FAIL.
- [ ] **Step 3: Implement evaluation harness, runner, and CLI**
  Implement test runner using `pytest` runner wrapper in subprocess with timeout protection, JSON reporting format, and colorized CLI terminal summary.
- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/unit/test_evaluation_runner.py -v` -> Expected: PASS.
- [ ] **Step 5: Commit**
  `git add evaluation/__init__.py evaluation/common/ evaluation/runner.py evaluation/cli.py tests/unit/test_evaluation_runner.py`
  `git commit -m "feat(eval): implement evaluation harness, runner, and cli verifier"`

---

### Task 9: Evaluation Lab Tasks 1 to 5 (Specifications, Buggy Starters, Reference Solutions, Verifiers)

**Files:**
- Create: `evaluation/tasks/task_01_ssrf_protection/` (`spec.json`, `README.md`, `EXPLANATION.md`, `starter.py`, `solution.py`, `test_public.py`, `test_verifier.py`)
- Create: `evaluation/tasks/task_02_concurrent_incidents/` (`spec.json`, `README.md`, `EXPLANATION.md`, `starter.py`, `solution.py`, `test_public.py`, `test_verifier.py`)
- Create: `evaluation/tasks/task_03_timeout_retry_backoff/` (`spec.json`, `README.md`, `EXPLANATION.md`, `starter.py`, `solution.py`, `test_public.py`, `test_verifier.py`)
- Create: `evaluation/tasks/task_04_overlapping_check_lock/` (`spec.json`, `README.md`, `EXPLANATION.md`, `starter.py`, `solution.py`, `test_public.py`, `test_verifier.py`)
- Create: `evaluation/tasks/task_05_state_machine_flapping/` (`spec.json`, `README.md`, `EXPLANATION.md`, `starter.py`, `solution.py`, `test_public.py`, `test_verifier.py`)
- Test: `tests/integration/test_evaluation_suite.py`

**Tasks Overview:**
1. **Task 01 (SSRF Protection):**
   - *Bug:* Starter uses naive regex matching on hostname string, allowing octal/hex IP bypasses, DNS rebinding to 127.0.0.1, and link-local cloud metadata IPs.
   - *Fix:* Canonical resolution with standard IP address parsing, subnet membership tests, and redirect hop checking.
2. **Task 02 (Concurrent Incidents):**
   - *Bug:* Starter checks if an active incident exists with a SELECT then INSERTs without atomic lock or unique partial index, resulting in duplicate active incidents during race conditions.
   - *Fix:* Atomic database upsert / locking transaction ensuring single active incident invariant.
3. **Task 03 (Timeout & Bounded Retry Policy):**
   - *Bug:* Starter retries infinitely on 4xx client errors or resets backoff improperly, and fails to bound timeout duration.
   - *Fix:* Bounded exponential backoff with jitter, retry filtering (only transient 5xx/network errors, never 4xx), and strict timeout budgets.
4. **Task 04 (Overlapping Check Lock):**
   - *Bug:* Scheduler launches periodic checks via `create_task` unconditionally; when a check takes longer than the interval, duplicate checks accumulate and exhaust connections.
   - *Fix:* Async in-flight locking mechanism that drops or defers overlapping ticks for the same target.
5. **Task 05 (Flapping State Machine & Hysteresis):**
   - *Bug:* Starter flips endpoint state to DOWN on a single failed check and immediately back to HEALTHY on a single success, causing alert noise and flapping incidents under packet loss.
   - *Fix:* Multi-sample hysteresis state machine (e.g., 3 consecutive failures to mark DOWN, 2 consecutive successes to recover) with proper state transition invariants.

- [ ] **Step 1: Write the failing test for evaluation lab verification**
  Write `tests/integration/test_evaluation_suite.py` asserting that for every task 1..5:
  - `verify(task_id, target="starter")` produces FAILING test results.
  - `verify(task_id, target="solution")` produces 100% PASSING test results.
- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/integration/test_evaluation_suite.py -v` -> Expected: FAIL.
- [ ] **Step 3: Implement all 5 tasks with specs, buggy starter code, reference solutions, explanations, public and verifier tests**
  Write complete implementations for tasks 1-5 adhering to standard interfaces.
- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/integration/test_evaluation_suite.py -v` -> Expected: PASS.
  Run: `python -m evaluation.cli verify-all` -> Expected: All 5 starter fail, all 5 solutions pass.
- [ ] **Step 5: Commit**
  `git add evaluation/tasks/ tests/integration/test_evaluation_suite.py`
  `git commit -m "feat(eval): implement 5 production-grade evaluation tasks and verifiers"`

---

### Task 10: Docker, CI/CD, Static Analysis & Developer Tooling

**Files:**
- Create: `backend/Dockerfile`
- Create: `docker-compose.yml`
- Create: `.github/workflows/ci.yml`
- Modify: `pyproject.toml` (Ruff, pytest, coverage configurations)
- Create: `Makefile` or PowerShell dev runner `scripts/run_dev.ps1`
- Test: Local Ruff check and pytest coverage run

- [ ] **Step 1: Write GitHub Actions CI workflow**
  Configure CI pipeline in `.github/workflows/ci.yml` with steps:
  - Checkout & Python 3.12/3.14 setup
  - Install dependencies and cache
  - Ruff linting and formatting check
  - Database service setup (PostgreSQL)
  - Pytest with coverage gate
  - Evaluation CLI verify-all check
- [ ] **Step 2: Write Dockerfile and docker-compose.yml**
  Multi-stage Dockerfile for FastAPI backend with unprivileged user, healthcheck instruction, and docker-compose orchestration for PostgreSQL + SignalGuard backend.
- [ ] **Step 3: Run Ruff and Pytest locally to verify compliance**
  Run: `ruff check backend evaluation tests` -> Expected: 0 errors.
  Run: `pytest --cov=backend/app --cov-report=term-missing` -> Expected: 100% passing tests.
- [ ] **Step 4: Commit**
  `git add backend/Dockerfile docker-compose.yml .github/workflows/ci.yml pyproject.toml Makefile scripts/`
  `git commit -m "chore(ci): configure github actions, docker, compose and ruff"`

---

### Task 11: Production Documentation, Architecture Diagrams & Recruiter Portfolio Presentation

**Files:**
- Modify: `README.md`
- Create: `docs/architecture.md`
- Create: `docs/api_reference.md`
- Create: `docs/evaluation_framework.md`
- Create: `docs/adr/0001-async-prober-concurrency.md`
- Create: `docs/adr/0002-ssrf-mitigation-strategy.md`
- Create: `docs/adr/0003-incident-deduplication-invariants.md`

- [ ] **Step 1: Write comprehensive system architecture document and ADRs**
  Document the async concurrency model, SSRF defenses, and incident deduplication state machine with Mermaid sequence and state diagrams.
- [ ] **Step 2: Write API reference and evaluation laboratory guides**
  Document REST endpoints with request/response examples and cURL commands. Document the evaluation laboratory philosophy, benchmark harness, and task specifications.
- [ ] **Step 3: Write production-grade README.md**
  Craft an exceptional README highlighting product capabilities, architecture diagrams, quickstart with and without Docker, verification commands, and AI evaluation laboratory walkthrough for OpenTrain AI and technical interviewers.
- [ ] **Step 4: Verify all markdown links and documentation consistency**
  Check that all file links, commands, and code samples match the real codebase.
- [ ] **Step 5: Commit**
  `git add README.md docs/`
  `git commit -m "docs: add comprehensive system architecture, adrs and evaluation lab guide"`
