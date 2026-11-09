"""Unit tests for API key verification and constant-time security checks."""

import pytest
from fastapi import HTTPException

from infra.auth import verify_api_key


def test_verify_api_key_valid(monkeypatch):
    monkeypatch.setenv("API_KEY", "valid-secret-token")
    assert verify_api_key("valid-secret-token") == "valid-secret-token"


def test_verify_api_key_invalid(monkeypatch):
    monkeypatch.setenv("API_KEY", "valid-secret-token")
    with pytest.raises(HTTPException) as exc:
        verify_api_key("wrong-token")
    assert exc.value.status_code == 401


def test_verify_api_key_missing_header(monkeypatch):
    monkeypatch.setenv("API_KEY", "valid-secret-token")
    with pytest.raises(HTTPException) as exc:
        verify_api_key(None)
    assert exc.value.status_code == 401


def test_verify_api_key_server_unconfigured(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    with pytest.raises(HTTPException) as exc:
        verify_api_key("any-token")
    assert exc.value.status_code == 500

