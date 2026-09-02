# -*- coding: utf-8 -*-
"""Check-in Plugin -- Personal daily check-in.

Local check-in tracking with optional remote sync to a-console.
After each local checkin, the record is pushed to the remote
POST /admin/v1/checkin-records endpoint so it appears in the
a-console checkin page.
"""

import json
import logging
import os
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from qwenpaw.plugins.api import PluginApi

logger = logging.getLogger("qwenpaw.checkin")

LOCAL_FILE = "checkin_local.json"


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class CheckinRecord(BaseModel):
    """A locally recorded checkin."""
    date: str = Field(default_factory=lambda: date.today().isoformat())
    points_earned: int = 0
    consecutive_days: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------

def _resolve_workspace_dir() -> Path:
    """Best-effort resolution of the active workspace directory."""
    try:
        from qwenpaw.config.context import get_current_workspace_dir
        ws_dir = get_current_workspace_dir()
        if ws_dir is not None:
            return Path(ws_dir)
    except Exception:
        pass

    from qwenpaw.constant import WORKING_DIR
    workspaces_root = WORKING_DIR / "workspaces"
    if workspaces_root.is_dir():
        candidates = sorted(d for d in workspaces_root.iterdir() if d.is_dir())
        if candidates:
            return candidates[0]
    return WORKING_DIR


def _get_local_path() -> Path:
    return _resolve_workspace_dir() / LOCAL_FILE


def _load_local() -> List[Dict[str, Any]]:
    path = _get_local_path()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_local(records: List[Dict[str, Any]]) -> None:
    path = _get_local_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _get_remote_config() -> Dict[str, str]:
    """Read remote connection config from environment variables."""
    return {
        "base_url": os.environ.get("OMATE_CONSOLE_URL", "").strip().rstrip("/"),
        "token": os.environ.get("OMATE_USER_TOKEN", "").strip(),
    }


async def _sync_to_remote(
    checkin_date: str,
    points_earned: int,
    consecutive_days: int,
) -> Optional[Dict[str, Any]]:
    """Push checkin record to remote a-console API.

    Calls POST /admin/v1/checkin-records. Returns the remote response
    or None on failure (non-blocking, logged as warning).
    User identity is extracted from the JWT by the server.
    """
    cfg = _get_remote_config()
    if not cfg["base_url"]:
        logger.debug("Remote sync skipped: no remote URL configured")
        return None

    import httpx
    headers: Dict[str, str] = {"Content-Type": "application/json"}
    if cfg["token"]:
        headers["Authorization"] = f"Bearer {cfg['token']}"

    payload = {
        "checkin_date": checkin_date,
        "points_earned": points_earned,
        "consecutive_days": consecutive_days,
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{cfg['base_url']}/admin/v1/checkin-records",
                json=payload,
                headers=headers,
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info("Remote sync OK: %s", data)
            return data
    except Exception as e:
        logger.warning("Remote sync failed (non-blocking): %s", e)
        return None


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

def build_router() -> APIRouter:
    """Build and return the FastAPI router for checkin endpoints."""
    router = APIRouter()

    @router.get("/today")
    async def check_today() -> Dict[str, Any]:
        """Check if user has checked in today."""
        today_str = date.today().isoformat()
        records = _load_local()
        today_record = next(
            (r for r in records if r.get("date") == today_str),
            None,
        )
        return {
            "checked_in": today_record is not None,
            "record": today_record,
            "date": today_str,
        }

    @router.post("/today")
    async def do_checkin() -> Dict[str, Any]:
        """Record today's checkin (idempotent)."""
        today_str = date.today().isoformat()
        records = _load_local()

        # Check if already checked in today
        existing = next(
            (r for r in records if r.get("date") == today_str),
            None,
        )
        if existing:
            return {"ok": True, "already": True, "record": existing}

        # Calculate consecutive days
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        yesterday_record = next(
            (r for r in records if r.get("date") == yesterday),
            None,
        )
        consecutive = (yesterday_record.get("consecutive_days", 0) + 1) if yesterday_record else 1

        # Points: base 10 + bonus 20 if consecutive >= 7
        points = 10 + (20 if consecutive >= 7 else 0)

        record = CheckinRecord(
            date=today_str,
            points_earned=points,
            consecutive_days=consecutive,
        )
        records.append(record.model_dump())
        _save_local(records)

        logger.info("Checkin recorded: %s (day %d, +%d pts)", today_str, consecutive, points)

        # Sync to remote a-console (non-blocking)
        remote_result = await _sync_to_remote(
            checkin_date=today_str,
            points_earned=points,
            consecutive_days=consecutive,
        )

        resp: Dict[str, Any] = {"ok": True, "already": False, "record": record.model_dump()}
        if remote_result:
            resp["synced"] = True
        return resp

    @router.get("/history")
    async def get_history(page: int = 1, size: int = 20) -> Dict[str, Any]:
        """Get local checkin history (newest first)."""
        records = _load_local()
        records.sort(key=lambda r: r.get("date", ""), reverse=True)
        total = len(records)
        start = (page - 1) * size
        items = records[start: start + size]
        return {"items": items, "total": total, "page": page, "size": size}

    return router


# ---------------------------------------------------------------------------
# Plugin entry
# ---------------------------------------------------------------------------

class CheckinPlugin:
    """Plugin entry point for checkin."""

    def register(self, api: PluginApi) -> None:
        router = build_router()
        api.register_http_router(
            router,
            prefix="/checkin",
            tags=["Checkin"],
        )
        logger.info("Checkin plugin registered: /api/checkin")


plugin = CheckinPlugin()
