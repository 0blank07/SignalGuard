import pytest

from evaluation.runner import EvaluationRunner


@pytest.fixture(scope="module")
def eval_runner():
    return EvaluationRunner()


def test_discovered_five_tasks(eval_runner):
    tasks = eval_runner.list_tasks()
    task_ids = [t.id for t in tasks]
    expected_tasks = [
        "task_01_ssrf_protection",
        "task_02_concurrent_incidents",
        "task_03_timeout_retry_backoff",
        "task_04_overlapping_check_lock",
        "task_05_state_machine_flapping",
    ]
    for expected in expected_tasks:
        assert expected in task_ids, f"Expected task {expected} was not discovered."


@pytest.mark.parametrize(
    "task_id",
    [
        "task_01_ssrf_protection",
        "task_02_concurrent_incidents",
        "task_03_timeout_retry_backoff",
        "task_04_overlapping_check_lock",
        "task_05_state_machine_flapping",
    ],
)
def test_evaluation_task_deterministic_verification(eval_runner, task_id):
    # 1. Buggy Starter MUST FAIL verifier tests
    starter_report = eval_runner.run_task(task_id, target="starter")
    assert starter_report.passed is False, (
        f"Task {task_id}: Buggy starter unexpectedly passed the verifier! "
        f"Verifier must catch the starter's bug."
    )
    assert starter_report.failed_tests >= 1

    # 2. Reference Solution MUST PASS verifier tests
    solution_report = eval_runner.run_task(task_id, target="solution")
    assert solution_report.passed is True, (
        f"Task {task_id}: Reference solution failed verification! "
        f"Stdout:\n{solution_report.raw_stdout}\nStderr:\n{solution_report.raw_stderr}"
    )
    assert solution_report.failed_tests == 0
    assert solution_report.passed_tests > 0
