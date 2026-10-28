# SignalGuard API Reference

SignalGuard provides a RESTful API compliant with standard HTTP status codes, structured JSON error handling, and strict input validation.

Base URL: `http://localhost:8000/api/v1`

---

## Standard Error Response Format

All error responses return a structured payload:

```json
{
  "error": {
    "code": "SSRF_BLOCKED",
    "message": "Target IP address '127.0.0.1' is in a blocked or private network range.",
    "status_code": 400,
    "details": {
      "ip": "127.0.0.1",
      "blocked_type": "PRIVATE_OR_RESERVED"
    }
  }
}
```

---

## 1. Monitored Endpoints

### Register a Target Endpoint
`POST /api/v1/endpoints`

**Request Body:**
```json
{
  "name": "Auth Service Production",
  "url": "https://api.github.com/status",
  "method": "GET",
  "headers": {
    "Authorization": "Bearer secure-token"
  },
  "interval_seconds": 30,
  "timeout_seconds": 5,
  "expected_status": 200,
  "retry_count": 3
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "name": "Auth Service Production",
  "url": "https://api.github.com/status",
  "method": "GET",
  "headers": {"Authorization": "Bearer secure-token"},
  "body": null,
  "interval_seconds": 30,
  "timeout_seconds": 5,
  "expected_status": 200,
  "retry_count": 3,
  "is_active": true,
  "status": "HEALTHY",
  "last_checked_at": null,
  "next_check_due": "2026-10-28T12:00:00Z",
  "consecutive_failures": 0,
  "consecutive_successes": 0,
  "created_at": "2026-10-28T12:00:00Z",
  "updated_at": "2026-10-28T12:00:00Z"
}
```

### List Endpoints (Paginated)
`GET /api/v1/endpoints?page=1&page_size=20&status=HEALTHY&is_active=true`

### Trigger On-Demand Check
`POST /api/v1/endpoints/{id}/check`

Triggers an immediate probe outside the normal scheduled tick.

**Response (200 OK):**
```json
{
  "endpoint_id": 1,
  "is_success": true,
  "status_code": 200,
  "response_time_ms": 42.15,
  "error_type": null,
  "error_message": null,
  "attempts": 1
}
```

### Pause / Resume Endpoint
- `POST /api/v1/endpoints/{id}/pause`
- `POST /api/v1/endpoints/{id}/resume`

---

## 2. Check History & SLA Metrics

### Get Historical Check Results
`GET /api/v1/endpoints/{id}/history?page=1&page_size=50`

### Get Reliability & Latency SLA Metrics
`GET /api/v1/endpoints/{id}/metrics?limit=1000`

**Response (200 OK):**
```json
{
  "endpoint_id": 1,
  "endpoint_name": "Auth Service Production",
  "total_checks": 1440,
  "successful_checks": 1438,
  "failed_checks": 2,
  "uptime_percentage": 99.86,
  "avg_latency_ms": 52.4,
  "min_latency_ms": 38.1,
  "max_latency_ms": 312.0,
  "p50_latency_ms": 48.0,
  "p95_latency_ms": 94.5,
  "p99_latency_ms": 180.2,
  "last_checked_at": "2026-10-28T12:00:00Z"
}
```

---

## 3. Incident Management

### Query Incidents
`GET /api/v1/incidents?page=1&page_size=20&status=OPEN&endpoint_id=1`

### Acknowledge Incident
`POST /api/v1/incidents/{id}/acknowledge`

### Manually Resolve Incident
`POST /api/v1/incidents/{id}/resolve`

**Request Body:**
```json
{
  "message": "Resolved after rolling back payment proxy deploy."
}
```

---

## 4. System Health

`GET /health` or `GET /api/v1/health`

**Response (200 OK):**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "database": "connected",
  "scheduler": "running",
  "active_monitors": 12,
  "open_incidents": 0,
  "timestamp": "2026-10-28T12:00:00Z"
}
```
