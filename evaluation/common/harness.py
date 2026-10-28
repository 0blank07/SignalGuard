import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from evaluation.common.types import (
    TaskEvaluationReport,
    TestCaseResult,
    TestRunStatus,
)


class EvaluationHarness:
    def __init__(self, python_executable: str | None = None) -> None:
        self.python_executable = python_executable or sys.executable

    def execute_test_suite(
        self,
        task_dir: Path,
        target_file: Path,
        test_file: Path,
        timeout_seconds: int = 20,
    ) -> TaskEvaluationReport:
        """Executes pytest against target_file mapped as `target.py` in an isolated workspace."""
        start_time = time.perf_counter()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Copy target implementation as target.py
            shutil.copy2(target_file, temp_path / "target.py")

            # Copy test file
            temp_test = temp_path / test_file.name
            shutil.copy2(test_file, temp_test)

            # Also copy any helper files or specs present in task_dir
            for item in task_dir.iterdir():
                if item.is_file() and item.name not in ("starter.py", "solution.py", test_file.name):
                    try:
                        shutil.copy2(item, temp_path / item.name)
                    except Exception:
                        pass

            # Prepare environment
            env = os.environ.copy()
            repo_root = str(Path(__file__).resolve().parent.parent.parent)
            env["PYTHONPATH"] = f"{temp_dir}{os.pathsep}{repo_root}{os.pathsep}{env.get('PYTHONPATH', '')}"

            cmd = [
                self.python_executable,
                "-m",
                "pytest",
                str(temp_test),
                "-v",
                "--tb=short",
                "-o",
                "asyncio_default_fixture_loop_scope=function",
            ]

            try:
                proc = subprocess.run(
                    cmd,
                    cwd=temp_dir,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                )
                stdout = proc.stdout
                stderr = proc.stderr
                return_code = proc.returncode
            except subprocess.TimeoutExpired as e:
                stdout = e.stdout or ""
                stderr = f"Test execution timed out after {timeout_seconds} seconds."
                return_code = -1

            duration = time.perf_counter() - start_time

            # Parse pytest terminal output to extract test results
            test_results: list[TestCaseResult] = []
            passed_count = 0
            failed_count = 0

            for line in stdout.splitlines():
                line = line.strip()
                if " PASSED" in line:
                    test_name = line.split(" PASSED")[0].split("::")[-1]
                    test_results.append(TestCaseResult(name=test_name, status=TestRunStatus.PASSED, duration_seconds=0.0))
                    passed_count += 1
                elif " FAILED" in line:
                    test_name = line.split(" FAILED")[0].split("::")[-1]
                    test_results.append(TestCaseResult(name=test_name, status=TestRunStatus.FAILED, duration_seconds=0.0))
                    failed_count += 1
                elif " ERROR" in line:
                    test_name = line.split(" ERROR")[0].split("::")[-1]
                    test_results.append(TestCaseResult(name=test_name, status=TestRunStatus.ERROR, duration_seconds=0.0))
                    failed_count += 1

            total = passed_count + failed_count
            passed_overall = (return_code == 0 and failed_count == 0 and total > 0)

            return TaskEvaluationReport(
                task_id=task_dir.name,
                target=target_file.stem,
                passed=passed_overall,
                total_tests=total,
                passed_tests=passed_count,
                failed_tests=failed_count,
                duration_seconds=duration,
                test_results=test_results,
                raw_stdout=stdout,
                raw_stderr=stderr,
            )
