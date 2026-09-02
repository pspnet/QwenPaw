# -*- coding: utf-8 -*-
"""Referral Plugin -- Invitation code, referral list and rewards.

Provides endpoints for:
- Viewing the current member's referral code and invitation link
- Listing people who accepted the invitation
- Viewing total rewards earned from referrals
- Accepting an invitation (for testing)
"""

import logging
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

from qwenpaw.plugins.api import PluginApi

logger = logging.getLogger("qwenpaw.referral")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_remote_config() -> Dict[str, str]:
    """Read remote connection config from environment variables."""
    return {
        "base_url": os.environ.get("OMATE_CONSOLE_URL", "").strip().rstrip("/"),
        "token": os.environ.get("OMATE_USER_TOKEN", "").strip(),
    }


def _build_headers(cfg: Dict[str, str]) -> Dict[str, str]:
    headers: Dict[str, str] = {"Content-Type": "application/json"}
    if cfg["token"]:
        headers["Authorization"] = f"Bearer {cfg['token']}"
    return headers


async def _remote_get(cfg: Dict[str, str], path: str, params: Optional[Dict] = None) -> Any:
    import httpx
    headers = _build_headers(cfg)
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{cfg['base_url']}{path}",
            params=params,
            headers=headers,
            timeout=15.0,
        )
        resp.raise_for_status()
        return resp.json()


async def _remote_post(cfg: Dict[str, str], path: str, json_data: Dict) -> Any:
    import httpx
    headers = _build_headers(cfg)
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{cfg['base_url']}{path}",
            json=json_data,
            headers=headers,
            timeout=15.0,
        )
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

def build_router() -> APIRouter:
    """Build and return the FastAPI router for referral endpoints."""
    router = APIRouter()

    @router.get("/me")
    async def get_me() -> Dict[str, Any]:
        """Get current member info including referral code."""
        cfg = _get_remote_config()
        if not cfg["base_url"]:
            raise HTTPException(status_code=400, detail="Set OMATE_CONSOLE_URL")

        try:
            data = await _remote_get(cfg, "/admin/v1/members/me")
            member = data.get("member", {})
            referral_count = data.get("referral_count", 0)
            return {
                "member": member,
                "referral_code": member.get("referral_code", ""),
                "referral_count": referral_count,
            }
        except Exception as e:
            logger.error("Failed to get member info: %s", e, exc_info=True)
            raise HTTPException(status_code=502, detail=str(e))

    @router.get("/records")
    async def list_records(page: int = 1, size: int = 20) -> Dict[str, Any]:
        """List referral records where current member is the referrer."""
        cfg = _get_remote_config()
        if not cfg["base_url"]:
            raise HTTPException(status_code=400, detail="Set OMATE_CONSOLE_URL")

        try:
            data = await _remote_get(
                cfg, "/admin/v1/referral-records",
                params={"page": page, "size": size},
            )
            return data
        except Exception as e:
            logger.error("Failed to fetch referral records: %s", e, exc_info=True)
            raise HTTPException(status_code=502, detail=str(e))

    @router.get("/rewards")
    async def get_rewards() -> Dict[str, Any]:
        """Get total referral rewards for current member."""
        cfg = _get_remote_config()
        if not cfg["base_url"]:
            raise HTTPException(status_code=400, detail="Set OMATE_CONSOLE_URL")

        try:
            # Fetch all records to calculate total (simple approach)
            data = await _remote_get(
                cfg, "/admin/v1/referral-records",
                params={"page": 1, "size": 1000},
            )
            items = data.get("items") or []
            total_count = data.get("total", 0)
            total_points = sum(r.get("referrer_points", 0) for r in items)
            return {
                "total_referrals": total_count,
                "total_rewards": total_points,
            }
        except Exception as e:
            logger.error("Failed to fetch rewards: %s", e, exc_info=True)
            raise HTTPException(status_code=502, detail=str(e))

    @router.post("/accept")
    async def accept_invitation(
        referral_code: str,
        nickname: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Accept an invitation (mainly for testing)."""
        cfg = _get_remote_config()
        if not cfg["base_url"]:
            raise HTTPException(status_code=400, detail="Set OMATE_CONSOLE_URL")

        try:
            result = await _remote_post(
                cfg, "/admin/v1/referral-records",
                json_data={
                    "referral_code": referral_code,
                    "nickname": nickname,
                    "user_id": user_id or "",
                },
            )
            return result
        except Exception as e:
            logger.error("Failed to accept invitation: %s", e, exc_info=True)
            raise HTTPException(status_code=502, detail=str(e))

    return router


# ---------------------------------------------------------------------------
# Plugin entry
# ---------------------------------------------------------------------------

class ReferralPlugin:
    """Plugin entry point for referral."""

    def register(self, api: PluginApi) -> None:
        router = build_router()
        api.register_http_router(
            router,
            prefix="/referral",
            tags=["Referral"],
        )
        logger.info("Referral plugin registered: /api/referral")


plugin = ReferralPlugin()
