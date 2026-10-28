import time
from dataclasses import dataclass, field


@dataclass
class IncidentRecord:
    id: int
    endpoint_id: int
    status: str  # "OPEN" or "RESOLVED"
    error_message: str
    failure_count: int = 1
    started_at: float = field(default_factory=time.time)
    last_seen_at: float = field(default_factory=time.time)


class IncidentStore:
    def __init__(self) -> None:
        self.incidents: list[IncidentRecord] = []
        self._next_id = 1

    def get_active_incident(self, endpoint_id: int) -> IncidentRecord | None:
        for inc in self.incidents:
            if inc.endpoint_id == endpoint_id and inc.status == "OPEN":
                return inc
        return None

    def record_failure(self, endpoint_id: int, error_message: str) -> IncidentRecord:
        # BUG: Check-then-act race condition without lock!
        active = self.get_active_incident(endpoint_id)

        # Artificial context switch delay simulating DB network latency
        time.sleep(0.01)

        if active is not None:
            active.failure_count += 1
            active.last_seen_at = time.time()
            return active
        else:
            inc = IncidentRecord(
                id=self._next_id,
                endpoint_id=endpoint_id,
                status="OPEN",
                error_message=error_message,
                failure_count=1,
            )
            self._next_id += 1
            self.incidents.append(inc)
            return inc

    def resolve_incident(self, endpoint_id: int) -> bool:
        active = self.get_active_incident(endpoint_id)
        if active:
            active.status = "RESOLVED"
            return True
        return False
