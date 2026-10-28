import pytest
from pathlib import Path
from evaluation.common.types import TaskSpec, TestRunStatus, TaskEvaluationReport
from evaluation.runner import EvaluationRunner


def test_task_spec_creation():
    spec = TaskSpec(
        id="task_01_sample",
        title="Sample Task",
        description="A sample test task",
        category="security",
        difficulty="medium",
        timeout_seconds=10,
    )
    assert spec.id == "task_01_sample"
    assert spec.category == "security"


def test_evaluation_runner_discovery():
    runner = EvaluationRunner()
    tasks = runner.list_tasks()
    assert isinstance(tasks, list)


def test_evaluation_runner_dummy_task_execution(tmp_path):
    # Setup temporary dummy task
    task_dir = tmp_path / "dummy_task"
    task_dir.mkdir()

    (task_dir / "spec.json").write_text(
        '{"id": "dummy_task", "title": "Dummy", "description": "Test", "category": "logic", "difficulty": "easy"}'
    )
    (task_dir / "starter.py").write_text("def add(a, b): return a - b\n")
    (task_dir / "solution.py").write_text("def add(a, b): return a + b\n")
    (task_dir / "test_verifier.py").write_text(
        "import pytest\n"
        "from target import add\n"
        "def test_add(): assert add(2, 3) == 5\n"
    )

    runner = EvaluationRunner(tasks_dir=tmp_path)
    starter_report = runner.run_task("dummy_task", target="starter")
    assert starter_report.passed is False
    assert starter_report.failed_tests >= 1

    solution_report = runner.run_task("dummy_task", target="solution")
    assert solution_report.passed is True
    assert solution_report.failed_tests == 0
    assert solution_report.passed_tests == 1
