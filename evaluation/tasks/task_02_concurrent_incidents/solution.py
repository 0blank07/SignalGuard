import threading
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
        self._lock = threading.Lock()

    def get_active_incident(self, endpoint_id: int) -> IncidentRecord | None:
        with self._lock:
            for inc in self.incidents:
                if inc.endpoint_id == endpoint_id and inc.status == "OPEN":
                    return inc
            return None

    def record_failure(self, endpoint_id: int, error_message: str) -> IncidentRecord:
        with self._lock:
            # Atomically inspect and upsert under lock protection
            active = None
            for inc in self.incidents:
                if inc.endpoint_id == endpoint_id and inc.status == "OPEN":
                    active = inc
                    break

            # Sleep inside lock safely or after acquisition
            time.sleep(0.005)

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
        with self._lock:
            for inc in self.incidents:
                if inc.endpoint_id == endpoint_id and inc.status == "OPEN":
                    inc.status = "RESOLVED"
                    return True
            return False
