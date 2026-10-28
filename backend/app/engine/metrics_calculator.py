from sqlalchemy import desc
from sqlalchemy.orm import Session
from backend.app.db.models.check_result import CheckResult
from backend.app.db.models.endpoint import MonitoredEndpoint
from backend.app.schemas.metrics import EndpointMetricsResponse


class MetricsCalculator:
    @staticmethod
    def calculate_endpoint_metrics(
        db: Session,
        endpoint: MonitoredEndpoint,
        limit: int = 1000,
    ) -> EndpointMetricsResponse:
        results = (
            db.query(CheckResult)
            .filter(CheckResult.endpoint_id == endpoint.id)
            .order_by(desc(CheckResult.created_at))
            .limit(limit)
            .all()
        )

        total = len(results)
        if total == 0:
            return EndpointMetricsResponse(
                endpoint_id=endpoint.id,
                endpoint_name=endpoint.name,
                total_checks=0,
                successful_checks=0,
                failed_checks=0,
                uptime_percentage=100.0,
                avg_latency_ms=0.0,
                min_latency_ms=0.0,
                max_latency_ms=0.0,
                p50_latency_ms=0.0,
                p95_latency_ms=0.0,
                p99_latency_ms=0.0,
                last_checked_at=endpoint.last_checked_at,
            )

        successes = sum(1 for r in results if r.is_success)
        failures = total - successes
        uptime_pct = round((successes / total) * 100.0, 2)

        latencies = sorted(r.response_time_ms for r in results)
        avg_lat = round(sum(latencies) / total, 2)
        min_lat = round(latencies[0], 2)
        max_lat = round(latencies[-1], 2)

        # Percentile calculations without requiring heavy dependencies
        def percentile(data: list[float], p: float) -> float:
            if not data:
                return 0.0
            k = (len(data) - 1) * (p / 100.0)
            f = int(k)
            c = min(f + 1, len(data) - 1)
            d0 = data[f] * (c - k)
            d1 = data[c] * (k - f)
            return round(d0 + d1, 2)

        p50 = percentile(latencies, 50)
        p95 = percentile(latencies, 95)
        p99 = percentile(latencies, 99)

        return EndpointMetricsResponse(
            endpoint_id=endpoint.id,
            endpoint_name=endpoint.name,
            total_checks=total,
            successful_checks=successes,
            failed_checks=failures,
            uptime_percentage=uptime_pct,
            avg_latency_ms=avg_lat,
            min_latency_ms=min_lat,
            max_latency_ms=max_lat,
            p50_latency_ms=p50,
            p95_latency_ms=p95,
            p99_latency_ms=p99,
            last_checked_at=endpoint.last_checked_at,
        )
