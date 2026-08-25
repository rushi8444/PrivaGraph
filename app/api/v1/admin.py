"""Admin API endpoints — audit log, health, config."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.dependencies import get_state
from app.security.key_manager import KeyManager

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/audit-log")
async def get_audit_log(page: int = 1, limit: int = 50):
    """View the security audit trail."""
    state = get_state()
    entries = state.audit.read_entries(limit=limit)
    return {"entries": entries, "total": len(entries)}
