import json
from pathlib import Path

from evaluation.common.harness import EvaluationHarness
from evaluation.common.types import TaskEvaluationReport, TaskSpec


class EvaluationRunner:
    def __init__(self, tasks_dir: Path | str | None = None) -> None:
        if tasks_dir is None:
            self.tasks_dir = Path(__file__).resolve().parent / "tasks"
        else:
            self.tasks_dir = Path(tasks_dir)
        self.harness = EvaluationHarness()

    def list_tasks(self) -> list[TaskSpec]:
        """Discovers all task specifications."""
        if not self.tasks_dir.exists():
            return []

        specs: list[TaskSpec] = []
        for d in sorted(self.tasks_dir.iterdir()):
            if d.is_dir() and (d / "spec.json").exists():
                try:
                    data = json.loads((d / "spec.json").read_text(encoding="utf-8"))
                    specs.append(
                        TaskSpec(
                            id=data["id"],
                            title=data["title"],
                            description=data["description"],
                            category=data.get("category", "general"),
                            difficulty=data.get("difficulty", "medium"),
                            timeout_seconds=data.get("timeout_seconds", 15),
                            metadata=data.get("metadata", {}),
                        )
                    )
                except Exception:
                    pass
        return specs

    def run_task(
        self,
        task_id: str,
        target: str = "solution",
        use_verifier: bool = True,
    ) -> TaskEvaluationReport:
        """Runs evaluation for a specific task against target ('starter' or 'solution' or custom file path)."""
        task_dir = self.tasks_dir / task_id
        if not task_dir.exists():
            raise FileNotFoundError(f"Task directory '{task_id}' not found in {self.tasks_dir}")

        # Determine target implementation file
        if target == "starter":
            target_file = task_dir / "starter.py"
        elif target == "solution":
            target_file = task_dir / "solution.py"
        else:
            target_file = Path(target)
            if not target_file.is_absolute():
                target_file = task_dir / target

        if not target_file.exists():
            raise FileNotFoundError(f"Target implementation file not found: {target_file}")

        # Determine test file (verifier or public)
        test_file = task_dir / ("test_verifier.py" if use_verifier else "test_public.py")
        if not test_file.exists():
            # Fallback to test_verifier.py or whatever test file is there
            test_file = task_dir / "test_verifier.py"

        # Read timeout from spec if available
        timeout = 20
        spec_file = task_dir / "spec.json"
        if spec_file.exists():
            try:
                spec_data = json.loads(spec_file.read_text(encoding="utf-8"))
                timeout = spec_data.get("timeout_seconds", 20)
            except Exception:
                pass

        return self.harness.execute_test_suite(
            task_dir=task_dir,
            target_file=target_file,
            test_file=test_file,
            timeout_seconds=timeout,
        )

    def verify_all(self) -> dict[str, dict[str, TaskEvaluationReport]]:
        """Evaluates all discovered tasks against BOTH starter and solution implementations."""
        results: dict[str, dict[str, TaskEvaluationReport]] = {}
        for spec in self.list_tasks():
            starter_res = self.run_task(spec.id, target="starter")
            solution_res = self.run_task(spec.id, target="solution")
            results[spec.id] = {
                "starter": starter_res,
                "solution": solution_res,
            }
        return results
