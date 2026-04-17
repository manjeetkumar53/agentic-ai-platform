"""
Planner quality evaluation harness.

Usage:
    python -m evaluation.run [--prompts evaluation/prompts.json] [--output evaluation/report.json]

Metrics produced per category and overall:
  - precision  = TP / (TP + FP)   — of selected tools, how many were correct?
  - recall     = TP / (TP + FN)   — of expected tools, how many were selected?
  - f1         = harmonic mean of precision and recall
  - exact_match= fraction of prompts where selected tools == expected tools exactly
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

# Allow running as `python -m evaluation.run` from repo root.
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from app.orchestration import PlannerAgent  # noqa: E402


# ---------------------------------------------------------------------------
# Metrics helpers
# ---------------------------------------------------------------------------

def _compute_metrics(results: list[dict]) -> dict:
    tp = fp = fn = exact = 0
    for r in results:
        expected = set(r["expected_tools"])
        selected = set(r["selected_tools"])
        tp += len(expected & selected)
        fp += len(selected - expected)
        fn += len(expected - selected)
        exact += int(expected == selected)

    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall    = tp / (tp + fn) if (tp + fn) else 1.0
    f1        = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "precision":    round(precision, 4),
        "recall":       round(recall, 4),
        "f1":           round(f1, 4),
        "exact_match":  round(exact / len(results), 4) if results else 0.0,
        "sample_count": len(results),
    }


def _group_by_category(results: list[dict]) -> dict[str, dict]:
    categories: dict[str, list] = {}
    for r in results:
        categories.setdefault(r["category"], []).append(r)
    return {cat: _compute_metrics(items) for cat, items in categories.items()}


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_evaluation(prompts_path: Path) -> dict[str, Any]:
    planner = PlannerAgent()
    dataset: list[dict] = json.loads(prompts_path.read_text())

    results: list[dict] = []
    t0 = time.perf_counter()

    for item in dataset:
        plan = planner.plan(item["prompt"])
        results.append({
            "id":             item["id"],
            "category":       item["category"],
            "prompt":         item["prompt"],
            "expected_tools": item["expected_tools"],
            "selected_tools": plan.tools,
            "reasoning":      plan.reasoning,
            "exact_match":    set(plan.tools) == set(item["expected_tools"]),
        })

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

    report = {
        "elapsed_ms":   elapsed_ms,
        "overall":      _compute_metrics(results),
        "by_category":  _group_by_category(results),
        "detail":       results,
    }
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_report(report: dict) -> None:
    print("\n=== Planner Evaluation Report ===")
    print(f"Elapsed: {report['elapsed_ms']} ms  |  Samples: {report['overall']['sample_count']}")
    print()
    print("Overall:")
    for k, v in report["overall"].items():
        if k != "sample_count":
            print(f"  {k:<15} {v:.4f}")
    print()
    print("By category:")
    for cat, metrics in report["by_category"].items():
        exact = metrics["exact_match"]
        f1    = metrics["f1"]
        n     = metrics["sample_count"]
        print(f"  {cat:<14} exact={exact:.2f}  f1={f1:.2f}  n={n}")
    print()

    failures = [r for r in report["detail"] if not r["exact_match"]]
    if failures:
        print(f"Mismatches ({len(failures)}):")
        for r in failures:
            print(f"  [{r['id']}] expected={r['expected_tools']}  got={r['selected_tools']}")
            print(f"         prompt: {r['prompt'][:80]}")
    else:
        print("All prompts matched exactly — perfect score!")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run planner evaluation harness")
    parser.add_argument(
        "--prompts",
        type=Path,
        default=ROOT / "evaluation" / "prompts.json",
        help="Path to labeled prompt dataset (JSON)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write JSON report",
    )
    args = parser.parse_args()

    report = run_evaluation(args.prompts)
    _print_report(report)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2))
        print(f"Report written to {args.output}")

    overall = report["overall"]
    # Exit non-zero if f1 drops below 0.80 so CI can gate on it.
    if overall["f1"] < 0.80:
        print(f"FAIL: f1={overall['f1']} < 0.80 threshold", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
