"""Tests for the planner evaluation harness."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation.run import _compute_metrics, _group_by_category, run_evaluation

PROMPTS_PATH = Path(__file__).parent.parent / "evaluation" / "prompts.json"


# ---------------------------------------------------------------------------
# Unit: metric helpers
# ---------------------------------------------------------------------------

class TestComputeMetrics:
    def test_perfect_score(self):
        results = [
            {"expected_tools": ["calculator"], "selected_tools": ["calculator"]},
            {"expected_tools": [], "selected_tools": []},
        ]
        m = _compute_metrics(results)
        assert m["precision"] == 1.0
        assert m["recall"] == 1.0
        assert m["f1"] == 1.0
        assert m["exact_match"] == 1.0

    def test_zero_score(self):
        results = [
            {"expected_tools": ["calculator"], "selected_tools": []},
        ]
        m = _compute_metrics(results)
        assert m["recall"] == 0.0
        assert m["exact_match"] == 0.0

    def test_partial_precision(self):
        # selected 2 tools but only 1 expected → precision < 1
        results = [
            {"expected_tools": ["calculator"], "selected_tools": ["calculator", "search_docs"]},
        ]
        m = _compute_metrics(results)
        assert m["precision"] == pytest.approx(0.5, abs=0.01)
        assert m["recall"] == 1.0

    def test_empty_results(self):
        m = _compute_metrics([])
        assert m["sample_count"] == 0

    def test_group_by_category(self):
        results = [
            {"category": "arithmetic", "expected_tools": ["calculator"], "selected_tools": ["calculator"]},
            {"category": "docs",       "expected_tools": ["search_docs"], "selected_tools": ["search_docs"]},
        ]
        grouped = _group_by_category(results)
        assert "arithmetic" in grouped
        assert "docs" in grouped
        assert grouped["arithmetic"]["f1"] == 1.0


# ---------------------------------------------------------------------------
# Integration: run against real prompt dataset
# ---------------------------------------------------------------------------

class TestRunEvaluation:
    def test_report_structure(self):
        report = run_evaluation(PROMPTS_PATH)
        assert "overall" in report
        assert "by_category" in report
        assert "detail" in report
        assert "elapsed_ms" in report

    def test_overall_keys(self):
        report = run_evaluation(PROMPTS_PATH)
        for key in ("precision", "recall", "f1", "exact_match", "sample_count"):
            assert key in report["overall"]

    def test_sample_count_matches_dataset(self):
        dataset = json.loads(PROMPTS_PATH.read_text())
        report = run_evaluation(PROMPTS_PATH)
        assert report["overall"]["sample_count"] == len(dataset)

    def test_categories_covered(self):
        report = run_evaluation(PROMPTS_PATH)
        assert set(report["by_category"].keys()) >= {"arithmetic", "docs", "direct"}

    def test_arithmetic_perfect_recall(self):
        """Calculator prompts all contain digits — recall should be 1.0."""
        report = run_evaluation(PROMPTS_PATH)
        assert report["by_category"]["arithmetic"]["recall"] == 1.0

    def test_direct_prompts_no_tools(self):
        """Direct prompts have no expected tools; precision should be perfect."""
        report = run_evaluation(PROMPTS_PATH)
        assert report["by_category"]["direct"]["precision"] == 1.0

    def test_detail_has_required_fields(self):
        report = run_evaluation(PROMPTS_PATH)
        for item in report["detail"]:
            for field in ("id", "category", "prompt", "expected_tools", "selected_tools", "exact_match"):
                assert field in item

    def test_f1_above_floor(self):
        """Overall F1 must be at least 0.70 with the reference dataset."""
        report = run_evaluation(PROMPTS_PATH)
        assert report["overall"]["f1"] >= 0.70, f"F1 too low: {report['overall']['f1']}"
