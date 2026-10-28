import argparse
import json
import sys
from evaluation.runner import EvaluationRunner


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="signalguard-eval",
        description="SignalGuard AI Code Evaluation & Verifier Laboratory CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    subparsers.add_parser("list", help="List all evaluation benchmark tasks")

    # verify
    verify_parser = subparsers.add_parser("verify", help="Run verifier for a specific task")
    verify_parser.add_argument("task_id", help="Task ID (e.g., task_01_ssrf_protection)")
    verify_parser.add_argument(
        "--target",
        default="solution",
        choices=["starter", "solution"],
        help="Target implementation to evaluate",
    )
    verify_parser.add_argument("--json", action="store_true", help="Output JSON format")

    # verify-all
    verify_all_parser = subparsers.add_parser(
        "verify-all",
        help="Verify all tasks against both starter and solution implementations",
    )
    verify_all_parser.add_argument("--json", action="store_true", help="Output JSON format")

    args = parser.parse_args()
    runner = EvaluationRunner()

    if args.command == "list":
        tasks = runner.list_tasks()
        print(f"\nDiscovered {len(tasks)} Evaluation Tasks:")
        print("-" * 75)
        print(f"{'ID':<32} {'Difficulty':<12} {'Category':<15} {'Title'}")
        print("-" * 75)
        for t in tasks:
            print(f"{t.id:<32} {t.difficulty:<12} {t.category:<15} {t.title}")
        print("-" * 75)

    elif args.command == "verify":
        report = runner.run_task(args.task_id, target=args.target)
        if args.json:
            print(json.dumps(report.to_dict(), indent=2))
        else:
            status_symbol = "✓ PASS" if report.passed else "✗ FAIL"
            print("\n" + "=" * 60)
            print(f"Task:    {report.task_id} [{report.target}]")
            print(f"Outcome: {status_symbol}")
            print(f"Tests:   {report.passed_tests}/{report.total_tests} passed ({report.failed_tests} failed)")
            print(f"Time:    {report.duration_seconds:.2f}s")
            print("=" * 60)
            if not report.passed:
                print("\nDetailed Test Failures:")
                for test in report.test_results:
                    if test.status != "PASSED":
                        print(f"  ✗ {test.name}")
                if report.raw_stdout:
                    print("\nPytest Output:\n" + report.raw_stdout)
        sys.exit(0 if report.passed else 1)

    elif args.command == "verify-all":
        results = runner.verify_all()
        if args.json:
            json_data = {
                task_id: {
                    "starter": res["starter"].to_dict(),
                    "solution": res["solution"].to_dict(),
                }
                for task_id, res in results.items()
            }
            print(json.dumps(json_data, indent=2))
        else:
            print("\n================ SignalGuard Evaluation Laboratory Matrix ================")
            print(f"{'Task ID':<35} {'Starter (Buggy)':<18} {'Solution (Fix)':<18} {'Verified?'}")
            print("-" * 80)
            all_verified = True
            for task_id, res in results.items():
                starter_passed = res["starter"].passed
                solution_passed = res["solution"].passed
                # In a deterministic verifier: starter MUST FAIL, solution MUST PASS
                verified = (not starter_passed) and solution_passed
                if not verified:
                    all_verified = False

                starter_str = "✗ FAIL (Expected)" if not starter_passed else "! PASS (Unexpected)"
                solution_str = "✓ PASS (Expected)" if solution_passed else "✗ FAIL (Unexpected)"
                verified_str = "✓ VERIFIED" if verified else "✗ FAILED"

                print(f"{task_id:<35} {starter_str:<18} {solution_str:<18} {verified_str}")
            print("=" * 80)

            if all_verified and len(results) > 0:
                print("All evaluation tasks verified successfully! Deterministic benchmarks confirmed.\n")
                sys.exit(0)
            else:
                print("Verification failed on one or more tasks.\n")
                sys.exit(1)


if __name__ == "__main__":
    main()
