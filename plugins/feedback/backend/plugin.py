# -*- coding: utf-8 -*-
"""Feedback Plugin -- Submit user feedback to remote a-console.

Provides a single endpoint for submitting feedback that gets stored
in the remote a-console database, viewable at /ui/member/feedback.
"""

import logging
import os
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from qwenpaw.plugins.api import PluginApi

logger = logging.getLogger("qwenpaw.feedback")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class FeedbackCreate(BaseModel):
    title: str
    content: str
    category: str = "bug"  # bug, feature, question
    priority: str = "medium"  # low, medium, high, critical


# ---------------------------------------------------------------------------
# Remote API helpers
# ---------------------------------------------------------------------------

def _get_remote_config() -> Dict[str, str]:
    return {
        "base_url": os.environ.get("OMATE_CONSOLE_URL", "").strip().rstrip("/"),
        "token": os.environ.get("OMATE_CONSOLE_TOKEN", "").strip(),
        "user_code": os.environ.get("OMATE_USER_CODE", "").strip(),
        "user_name": os.environ.get("OMATE_USER_NAME", "").strip(),
    }


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

def build_router() -> APIRouter:
    router = APIRouter()

    @router.post("")
    async def create_feedback(payload: FeedbackCreate) -> Dict[str, Any]:
        """Submit a new feedback item to remote a-console."""
        cfg = _get_remote_config()
        if not cfg["base_url"]:
            raise HTTPException(status_code=503, detail="Remote feedback URL not configured")

        import httpx

        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if cfg["token"]:
            headers["Authorization"] = f"Bearer {cfg['token']}"

        data = {
            "title": payload.title,
            "content": payload.content,
            "category": payload.category,
            "priority": payload.priority,
            "status": "open",
            "user_id": cfg["user_code"],
            "user_name": cfg["user_name"],
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{cfg['base_url']}/admin/v1/feedback",
                    json=data,
                    headers=headers,
                    timeout=15.0,
                )
                resp.raise_for_status()
                result = resp.json()
                logger.info("Feedback submitted: %s", result.get("id", ""))
                return {"ok": True, "feedback": result}
        except httpx.HTTPStatusError as e:
            logger.warning("Remote feedback submit failed: %s", e)
            raise HTTPException(status_code=e.response.status_code, detail=str(e))
        except Exception as e:
            logger.warning("Remote feedback submit failed: %s", e)
            raise HTTPException(status_code=502, detail=str(e))

    return router


# ---------------------------------------------------------------------------
# Plugin entry
# ---------------------------------------------------------------------------

class FeedbackPlugin:
    """Plugin entry point for feedback."""

    def register(self, api: PluginApi) -> None:
        router = build_router()
        api.register_http_router(
            router,
            prefix="/feedback",
            tags=["Feedback"],
        )
        logger.info("Feedback plugin registered: /api/feedback")


plugin = FeedbackPlugin()
