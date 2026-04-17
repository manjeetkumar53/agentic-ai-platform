"""Tests for dashboard data-fetcher helpers (offline — no server needed)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestFetchHelpers:
    """Test fetch_* helpers in isolation using mock responses."""

    def _make_response(self, json_data: dict | list, status_code: int = 200) -> MagicMock:
        mock = MagicMock()
        mock.status_code = status_code
        mock.json.return_value = json_data
        mock.raise_for_status = MagicMock()
        return mock

    def test_fetch_health_ok(self):
        with patch("requests.get", return_value=self._make_response({"status": "ok"})):
            from dashboard.app import fetch_health
            fetch_health.clear()   # clear streamlit cache
            result = fetch_health("http://localhost:8000")
            assert result["status"] == "ok"

    def test_fetch_health_connection_error(self):
        with patch("requests.get", side_effect=ConnectionError("refused")):
            from dashboard.app import fetch_health
            fetch_health.clear()
            result = fetch_health("http://localhost:9999")
            assert result["status"] == "error"

    def test_fetch_summary_returns_dict(self):
        payload = {"request_count": 10, "avg_latency_ms": 42.0}
        with patch("requests.get", return_value=self._make_response(payload)):
            from dashboard.app import fetch_summary
            fetch_summary.clear()
            result = fetch_summary("http://localhost:8000")
            assert result["request_count"] == 10

    def test_fetch_events_returns_list(self):
        payload = {"events": [{"request_id": "abc", "latency_ms": 10}]}
        with patch("requests.get", return_value=self._make_response(payload)):
            from dashboard.app import fetch_events
            fetch_events.clear()
            result = fetch_events("http://localhost:8000", 100)
            assert isinstance(result, list)
            assert result[0]["request_id"] == "abc"

    def test_fetch_events_empty_on_error(self):
        with patch("requests.get", side_effect=Exception("timeout")):
            from dashboard.app import fetch_events
            fetch_events.clear()
            result = fetch_events("http://localhost:8999", 100)
            assert result == []

    def test_fetch_breaker_returns_dict(self):
        payload = {"state": "CLOSED"}
        with patch("requests.get", return_value=self._make_response(payload)):
            from dashboard.app import fetch_breaker
            fetch_breaker.clear()
            result = fetch_breaker("http://localhost:8000")
            assert result["state"] == "CLOSED"
