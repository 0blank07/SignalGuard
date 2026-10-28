# SignalGuard AI Code Evaluation & Verifier Laboratory

The **SignalGuard Code Evaluation Laboratory** (`evaluation/`) is a dedicated benchmark testing framework built to evaluate both AI coding agents and backend engineering candidates.

Rather than testing trivial syntax or relying on fragile AST regex matching, this laboratory evaluates **functional correctness, concurrency invariants, and adversarial edge cases**.

---

## 1. Laboratory Design & Evaluation Methodology

Each programming benchmark task follows an isolated evaluation contract:

```text
evaluation/tasks/<task_id>/
├── spec.json           # Machine-readable task metadata, timeout, and rubric
├── README.md           # Behavioral specifications & requirements
├── EXPLANATION.md      # Root-cause analysis, failure risks, and architectural reasoning
├── starter.py          # Buggy starter code or incomplete implementation
├── solution.py         # Ground-truth verified reference solution
├── test_public.py      # Informational unit tests explaining standard happy paths
└── test_verifier.py    # Hidden/adversarial boundary, race condition, & evasion test suite
```

### The Verifier Invariant
A valid evaluation benchmark must satisfy two conditions:
1. **The Buggy Starter MUST FAIL** one or more verifier tests.
2. **The Reference Solution MUST PASS** 100% of the verifier tests deterministically.

---

## 2. Benchmark Task Catalog

| Task ID | Domain | Category | Difficulty | Real-World Consequence |
|---|---|---|---|---|
| **`task_01_ssrf_protection`** | Security | Network Defense | Hard | Cloud metadata leak (`169.254.169.254`), octal IP bypass, VPC intranet port scanning |
| **`task_02_concurrent_incidents`** | Concurrency | Distributed Systems | Medium | Check-then-act race creates duplicate open incidents during network degradation |
| **`task_03_timeout_retry_backoff`** | Reliability | Resilience Engineering | Medium | Retry storms against failing APIs; 4xx client errors retried indefinitely |
| **`task_04_overlapping_check_lock`** | AsyncIO | Concurrency Control | Medium | Check stampedes: slow endpoints accumulate overlapping probe tasks, exhausting sockets |
| **`task_05_state_machine_flapping`** | State Machine | Observability | Medium | Zero-hysteresis alert storms: single-packet drops oscillate status between HEALTHY and DOWN |

---

## 3. Running the Verifier CLI

The evaluation runner operates completely decoupled from the production application runtime.

### List All Available Tasks
```bash
python -m evaluation.cli list
```

### Verify an Individual Task
```bash
# Verify that the reference solution passes all checks:
python -m evaluation.cli verify task_01_ssrf_protection --target solution

# Verify that the buggy starter is properly caught and rejected:
python -m evaluation.cli verify task_01_ssrf_protection --target starter
```

### Run the Full Benchmark Matrix
```bash
python -m evaluation.cli verify-all
```

**Output:**
```text
================ SignalGuard Evaluation Laboratory Matrix ================
Task ID                             Starter (Buggy)      Solution (Fix)     Verified?
-------------------------------------------------------------------------------------
task_01_ssrf_protection             [FAIL] (Expected)    [PASS] (Expected)  [VERIFIED]
task_02_concurrent_incidents        [FAIL] (Expected)    [PASS] (Expected)  [VERIFIED]
task_03_timeout_retry_backoff       [FAIL] (Expected)    [PASS] (Expected)  [VERIFIED]
task_04_overlapping_check_lock      [FAIL] (Expected)    [PASS] (Expected)  [VERIFIED]
task_05_state_machine_flapping      [FAIL] (Expected)    [PASS] (Expected)  [VERIFIED]
=====================================================================================
All evaluation tasks verified successfully! Deterministic benchmarks confirmed.
```

### Machine-Readable JSON Output
For integration into automated evaluation pipelines (e.g., OpenTrain AI evaluation harnesses):
```bash
python -m evaluation.cli verify-all --json
```
