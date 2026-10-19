"""
Lumi DICOM — API Key Authentication
Copyright © 2026 Lumi DICOM. All rights reserved.

API key authentication untuk Lumi DICOM Orchestrator.
Menggunakan header X-API-Key yang divalidasi terhadap daftar key valid.
"""

import logging

from fastapi import Header, HTTPException, Request, status

logger = logging.getLogger("lumi-dicom")


def verify_api_key(api_key: str, valid_keys: list[str]) -> bool:
    """Verify bahwa API key diberikan ada dalam daftar key valid.

    Args:
        api_key: API key dari header X-API-Key
        valid_keys: Daftar API key yang valid

    Returns:
        True jika valid, False jika tidak
    """
    if not api_key:
        return False
    return api_key in valid_keys


def get_api_key(
    request: Request,
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> str:
    """FastAPI dependency: validasi X-API-Key header.

    Reads valid API keys from app.state.api_keys (set by create_app).
    Raises HTTPException 401 jika key tidak ada atau tidak valid.

    Args:
        request: FastAPI Request object
        x_api_key: Nilai header X-API-Key

    Returns:
        API key yang valid

    Raises:
        HTTPException: 401 jika API key tidak ada atau tidak valid
    """
    # Get valid keys from app.state
    valid_keys: list[str] = getattr(request.app.state, "api_keys", [])

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not verify_api_key(x_api_key, valid_keys):
        logger.warning("Lumi DICOM: invalid API key attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return x_api_key


class APIKeyAuth:
    """API key authentication helper class.

    Provides a reusable interface for validating API keys
    against a configured list of valid keys.

    Usage::

        auth = APIKeyAuth(["key1", "key2"])
        if auth.is_valid("key1"):
            ...
    """

    def __init__(self, valid_keys: list[str]):
        """Initialize dengan daftar API key valid.

        Args:
            valid_keys: List of valid API key strings
        """
        self._valid_keys = valid_keys

    def is_valid(self, api_key: str) -> bool:
        """Check apakah API key valid."""
        return verify_api_key(api_key, self._valid_keys)

    def get_keys(self) -> list[str]:
        """Return copy dari daftar key valid."""
        return list(self._valid_keys)

    def add_key(self, api_key: str) -> None:
        """Tambah API key valid baru."""
        if api_key not in self._valid_keys:
            self._valid_keys.append(api_key)

    def remove_key(self, api_key: str) -> None:
        """Hapus API key dari daftar valid."""
        if api_key in self._valid_keys:
            self._valid_keys.remove(api_key)
