"""API key verification for the obsidian-rag FastAPI service.

Uses constant-time comparison (CWE-208) and returns consistent 401/500 errors.
Importing :mod:`infra.config` guarantees ``.env`` is loaded before lookup.
"""

import os
import secrets
from typing import Optional

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from infra import config  # noqa: F401  (side effect: loads .env)

__all__ = ["API_KEY_HEADER", "verify_api_key"]

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)) -> str:
    """Validate the ``X-API-Key`` header against the ``API_KEY`` environment variable.

    Raises:
        HTTPException: 500 if ``API_KEY`` is not configured on the server.
        HTTPException: 401 if the header is missing or does not match.

    Returns:
        The validated API key.
    """
    expected_api_key = os.getenv("API_KEY")
    if not expected_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key is not configured on the server.",
        )
    if not api_key or not secrets.compare_digest(api_key, expected_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )
    return api_key
