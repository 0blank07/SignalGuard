import threading


class ExecutionCoordinator:
    def __init__(self) -> None:
        self._in_flight: set[int] = set()
        self._lock = threading.Lock()

    def acquire(self, endpoint_id: int) -> bool:
        with self._lock:
            if endpoint_id in self._in_flight:
                return False
            self._in_flight.add(endpoint_id)
            return True

    def release(self, endpoint_id: int) -> None:
        with self._lock:
            self._in_flight.discard(endpoint_id)

    def is_in_flight(self, endpoint_id: int) -> bool:
        with self._lock:
            return endpoint_id in self._in_flight
