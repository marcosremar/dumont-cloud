"""
Hosts API Endpoints - Host management and blacklist
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from datetime import datetime

from ..dependencies import get_current_user_email

router = APIRouter(prefix="/hosts", tags=["Hosts"])


class BlacklistedHost(BaseModel):
    machine_id: int
    reason: str
    added_at: str
    expires_at: Optional[str] = None


class BlacklistAddRequest(BaseModel):
    machine_id: int
    reason: str
    duration_hours: Optional[int] = None  # None = permanent


@router.get("/blacklist")
async def get_blacklist(
    user_email: str = Depends(get_current_user_email),
):
    """
    Get list of blacklisted hosts for current user
    """
    # In production, this would fetch from database
    return {
        "blacklist": [],
        "count": 0,
    }


@router.post("/blacklist")
async def add_to_blacklist(
    request: BlacklistAddRequest,
    user_email: str = Depends(get_current_user_email),
):
    """
    Add a host to the blacklist
    """
    expires_at = None
    if request.duration_hours:
        from datetime import timedelta
        expires_at = (datetime.utcnow() + timedelta(hours=request.duration_hours)).isoformat()

    return {
        "success": True,
        "host": BlacklistedHost(
            machine_id=request.machine_id,
            reason=request.reason,
            added_at=datetime.utcnow().isoformat(),
            expires_at=expires_at,
        ),
        "message": f"Host {request.machine_id} added to blacklist",
    }


@router.delete("/blacklist/{machine_id}")
async def remove_from_blacklist(
    machine_id: int,
    user_email: str = Depends(get_current_user_email),
):
    """
    Remove a host from the blacklist
    """
    return {
        "success": True,
        "machine_id": machine_id,
        "message": f"Host {machine_id} removed from blacklist",
    }


@router.get("/{machine_id}")
async def get_host_info(
    machine_id: int,
    user_email: str = Depends(get_current_user_email),
):
    """
    Get detailed info about a host
    """
    return {
        "machine_id": machine_id,
        "hostname": f"gpu-host-{machine_id}",
        "location": "US",
        "gpu_count": 4,
        "gpu_type": "RTX 4090",
        "reliability_score": 0.95,
        "uptime_percent": 99.0,
        "is_blacklisted": False,
    }
