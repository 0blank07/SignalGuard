# BUGGY STARTER: Does not track in-flight tasks; always allows execution

class ExecutionCoordinator:
    def __init__(self) -> None:
        self.in_flight_count = 0

    def acquire(self, endpoint_id: int) -> bool:
        # BUG: Always returns True, failing to prevent overlapping checks for the same endpoint!
        self.in_flight_count += 1
        return True

    def release(self, endpoint_id: int) -> None:
        if self.in_flight_count > 0:
            self.in_flight_count -= 1

    def is_in_flight(self, endpoint_id: int) -> bool:
        # BUG: Cannot track per-endpoint state
        return False
