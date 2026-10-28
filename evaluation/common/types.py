import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


class TestRunStatus(str, enum.Enum):
    __test__ = False
    PASSED = "PASSED"
    FAILED = "FAILED"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


@dataclass
class TaskSpec:
    id: str
    title: str
    description: str
    category: str
    difficulty: str
    timeout_seconds: int = 15
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TestCaseResult:
    __test__ = False
    name: str
    status: TestRunStatus
    duration_seconds: float
    message: str | None = None


@dataclass
class TaskEvaluationReport:
    task_id: str
    target: str  # 'starter' or 'solution' or custom file
    passed: bool
    total_tests: int
    passed_tests: int
    failed_tests: int
    duration_seconds: float
    test_results: list[TestCaseResult] = field(default_factory=list)
    raw_stdout: str = ""
    raw_stderr: str = ""
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "target": self.target,
            "passed": self.passed,
            "score": round((self.passed_tests / self.total_tests) * 100.0, 1) if self.total_tests > 0 else 0.0,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "duration_seconds": round(self.duration_seconds, 3),
            "executed_at": self.executed_at.isoformat(),
            "tests": [
                {
                    "name": t.name,
                    "status": t.status.value,
                    "duration": round(t.duration_seconds, 3),
                    "message": t.message,
                }
                for t in self.test_results
            ],
        }
