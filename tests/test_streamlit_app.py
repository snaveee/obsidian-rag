"""Headless automated UI lifecycle tests for streamlit_app.py using AppTest."""

from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


def test_streamlit_app_renders_empty_state():
    app_path = Path(__file__).resolve().parent.parent / "streamlit_app.py"

    # Mock fetch_api_status returning None (backend offline or unindexed)
    with patch("streamlit_app.fetch_api_status", return_value=None):
        at = AppTest.from_file(str(app_path), default_timeout=10)
        at.run()

        # Check title and captions
        assert not at.exception
        assert "Personal Vault Knowledge Engine" in at.title[0].value


def test_streamlit_app_with_connected_backend():
    app_path = Path(__file__).resolve().parent.parent / "streamlit_app.py"

    mock_status = {
        "status": "online",
        "total_notes": 8,
        "total_chunks": 16,
        "last_indexed_at": "2026-11-09T12:00:00",
        "folders": ["daily"],
    }
    mock_history = [
        {"id": 1, "query": "What is RRF?", "results_count": 3, "answer_preview": "RRF combines...", "retrieval_mode": "hybrid"}
    ]

    with patch("streamlit_app.fetch_api_status", return_value=mock_status), \
         patch("streamlit_app.fetch_history", return_value=mock_history):
        at = AppTest.from_file(str(app_path), default_timeout=10)
        at.run()

        assert not at.exception
        # Input widget should exist
        assert len(at.text_input) >= 1

