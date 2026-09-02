# -*- coding: utf-8 -*-
"""Console API Client.

Structured async client for the a-console gateway admin API.
Supports auto-login (username/password → JWT) and token refresh.

Usage from within a QwenPaw plugin::

    from jwt_auth_interceptor.backend.console_client import get_console_client

    client = get_console_client()
    me = await client.me()
    servers = await client.list_mcp_servers()
"""

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger("qwenpaw.jwt_auth_interceptor.console")

# ── Singleton ────────────────────────────────────────────────────────────

_client: Optional["ConsoleClient"] = None


def get_console_client() -> "ConsoleClient":
    """Return the singleton ConsoleClient (created on first call)."""
    global _client
    if _client is None:
        _client = ConsoleClient()
    return _client


def reset_console_client() -> None:
    """Reset the singleton (used on uninstall)."""
    global _client
    _client = None


# ── Client ───────────────────────────────────────────────────────────────


class ConsoleClient:
    """Async HTTP client for a-console admin API.

    Reads connection settings from environment variables:

    - ``OMATE_CONSOLE_URL`` — base URL (e.g. ``http://localhost:8080``)
    - ``OMATE_USER_TOKEN`` — JWT token (always present)
    """

    def __init__(
        self,
        base_url: str = "",
        token: str = "",
    ):
        self._base_url = (
            base_url
            or os.environ.get("OMATE_CONSOLE_URL", "").strip().rstrip("/")
        )
        self._token = (
            token or os.environ.get("OMATE_USER_TOKEN", "").strip()
        )

    # ── Properties ───────────────────────────────────────────────────

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def token(self) -> str:
        return self._token

    @property
    def has_credentials(self) -> bool:
        """True when enough config is present to make API calls."""
        return bool(self._base_url) and bool(self._token)

    # ── HTTP helpers ─────────────────────────────────────────────────

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Make an authenticated request to a-console."""
        if not self._base_url:
            raise RuntimeError("OMATE_CONSOLE_URL is not set")

        import httpx

        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        url = f"{self._base_url}{path}"

        async with httpx.AsyncClient() as client:
            resp = await client.request(
                method,
                url,
                json=json,
                params=params,
                headers=headers,
                timeout=30.0,
            )
            resp.raise_for_status()

            if resp.status_code == 204:
                return None

            return resp.json()

    async def _get(self, path: str, **kwargs: Any) -> Any:
        return await self._request("GET", path, **kwargs)

    async def _post(self, path: str, **kwargs: Any) -> Any:
        return await self._request("POST", path, **kwargs)

    async def _put(self, path: str, **kwargs: Any) -> Any:
        return await self._request("PUT", path, **kwargs)

    async def _delete(self, path: str, **kwargs: Any) -> Any:
        return await self._request("DELETE", path, **kwargs)

    # ── Auth / User ──────────────────────────────────────────────────

    async def me(self) -> Dict[str, Any]:
        """GET /admin/v1/me — current user info from JWT."""
        return await self._get("/admin/v1/me")

    # ── MCP Servers ──────────────────────────────────────────────────

    async def list_mcp_servers(self) -> List[Dict[str, Any]]:
        """GET /admin/v1/mcp-servers."""
        return await self._get("/admin/v1/mcp-servers")

    async def get_mcp_server(self, server_id: str) -> Dict[str, Any]:
        """GET /admin/v1/mcp-servers/:id."""
        return await self._get(f"/admin/v1/mcp-servers/{server_id}")

    async def create_mcp_server(
        self, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """POST /admin/v1/mcp-servers."""
        return await self._post("/admin/v1/mcp-servers", json=data)

    async def update_mcp_server(
        self, server_id: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """PUT /admin/v1/mcp-servers/:id."""
        return await self._put(f"/admin/v1/mcp-servers/{server_id}", json=data)

    async def delete_mcp_server(self, server_id: str) -> None:
        """DELETE /admin/v1/mcp-servers/:id."""
        await self._delete(f"/admin/v1/mcp-servers/{server_id}")

    async def list_mcp_tools(self, server_id: str) -> List[Dict[str, Any]]:
        """GET /admin/v1/mcp-servers/:id/tools."""
        return await self._get(f"/admin/v1/mcp-servers/{server_id}/tools")

    async def sync_mcp_tools(self, server_id: str) -> Dict[str, Any]:
        """POST /admin/v1/mcp-servers/:id/sync-tools."""
        return await self._post(
            f"/admin/v1/mcp-servers/{server_id}/sync-tools"
        )

    # ── API Keys ─────────────────────────────────────────────────────

    async def list_api_keys(self) -> List[Dict[str, Any]]:
        """GET /admin/v1/api-keys."""
        return await self._get("/admin/v1/api-keys")

    async def create_api_key(
        self, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """POST /admin/v1/api-keys."""
        return await self._post("/admin/v1/api-keys", json=data)

    async def delete_api_key(self, key_id: str) -> None:
        """DELETE /admin/v1/api-keys/:id."""
        await self._delete(f"/admin/v1/api-keys/{key_id}")

    async def rotate_api_key(self, key_id: str) -> Dict[str, Any]:
        """POST /admin/v1/api-keys/:id/rotate."""
        return await self._post(f"/admin/v1/api-keys/{key_id}/rotate")

    # ── Policies ─────────────────────────────────────────────────────

    async def reload_policies(self) -> Dict[str, Any]:
        """POST /admin/v1/policies/reload."""
        return await self._post("/admin/v1/policies/reload")

    async def list_policies(self) -> List[Dict[str, Any]]:
        """GET /admin/v1/policies."""
        return await self._get("/admin/v1/policies")

    # ── Clients ──────────────────────────────────────────────────────

    async def list_clients(self) -> List[Dict[str, Any]]:
        """GET /admin/v1/clients."""
        return await self._get("/admin/v1/clients")

    async def create_client(
        self, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """POST /admin/v1/clients."""
        return await self._post("/admin/v1/clients", json=data)

    # ── Users / Roles ────────────────────────────────────────────────

    async def list_users(self) -> List[Dict[str, Any]]:
        """GET /admin/v1/users."""
        return await self._get("/admin/v1/users")

    async def list_roles(self) -> List[Dict[str, Any]]:
        """GET /admin/v1/roles."""
        return await self._get("/admin/v1/roles")

    # ── Audit ────────────────────────────────────────────────────────

    async def list_audit_logs(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """GET /admin/v1/audit-logs."""
        return await self._get(
            "/admin/v1/audit-logs",
            params={"limit": limit, "offset": offset},
        )

    # ── User Memory ──────────────────────────────────────────────────

    async def list_memories(self) -> List[Dict[str, Any]]:
        """GET /admin/v1/memories."""
        return await self._get("/admin/v1/memories")

    async def create_memory(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """POST /admin/v1/memories."""
        return await self._post("/admin/v1/memories", json=data)

    async def update_memory(
        self, memory_id: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """PUT /admin/v1/memories/:id."""
        return await self._put(f"/admin/v1/memories/{memory_id}", json=data)

    async def delete_memory(self, memory_id: str) -> None:
        """DELETE /admin/v1/memories/:id."""
        await self._delete(f"/admin/v1/memories/{memory_id}")

    # ── Skills ───────────────────────────────────────────────────────

    async def list_skills(self) -> List[Dict[str, Any]]:
        """GET /admin/v1/skills."""
        return await self._get("/admin/v1/skills")

    # ── Prompts ──────────────────────────────────────────────────────

    async def list_prompts(self) -> List[Dict[str, Any]]:
        """GET /admin/v1/prompts."""
        return await self._get("/admin/v1/prompts")

    # ── Feedback ─────────────────────────────────────────────────────

    async def create_feedback(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """POST /admin/v1/feedback."""
        return await self._post("/admin/v1/feedback", json=data)

    # ── OAuth2 Providers ─────────────────────────────────────────────

    async def list_oauth_providers(self) -> List[Dict[str, Any]]:
        """GET /admin/v1/oauth-providers."""
        return await self._get("/admin/v1/oauth-providers")

    async def create_oauth_provider(
        self, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """POST /admin/v1/oauth-providers."""
        return await self._post("/admin/v1/oauth-providers", json=data)

    # ── Settings ─────────────────────────────────────────────────────

    async def list_settings(self) -> List[Dict[str, Any]]:
        """GET /admin/v1/settings."""
        return await self._get("/admin/v1/settings")

    # ── Members ──────────────────────────────────────────────────────

    async def get_member_me(self) -> Dict[str, Any]:
        """GET /admin/v1/members/me — current user's member info."""
        return await self._get("/admin/v1/members/me")

    async def get_member(self, member_id: str) -> Dict[str, Any]:
        """GET /admin/v1/members/:id."""
        return await self._get(f"/admin/v1/members/{member_id}")

    async def list_members(
        self, *, q: str = "", page: int = 1, size: int = 20
    ) -> Dict[str, Any]:
        """GET /admin/v1/members."""
        return await self._get(
            "/admin/v1/members", params={"q": q, "page": page, "size": size}
        )

    # ── Checkin ──────────────────────────────────────────────────────

    async def create_checkin(
        self,
        *,
        points_earned: int = 0,
        consecutive_days: int = 0,
        checkin_date: str = "",
    ) -> Dict[str, Any]:
        """POST /admin/v1/checkin-records — member resolved from JWT."""
        payload: Dict[str, Any] = {
            "points_earned": points_earned,
            "consecutive_days": consecutive_days,
        }
        if checkin_date:
            payload["checkin_date"] = checkin_date
        return await self._post("/admin/v1/checkin-records", json=payload)

    async def list_checkin_records(
        self, *, page: int = 1, size: int = 20
    ) -> Dict[str, Any]:
        """GET /admin/v1/checkin-records."""
        return await self._get(
            "/admin/v1/checkin-records", params={"page": page, "size": size}
        )

    # ── Referral ─────────────────────────────────────────────────────

    async def list_referral_records(
        self, *, status: str = "", page: int = 1, size: int = 20
    ) -> Dict[str, Any]:
        """GET /admin/v1/referral-records — member resolved from JWT."""
        params: Dict[str, Any] = {"page": page, "size": size}
        if status:
            params["status"] = status
        return await self._get("/admin/v1/referral-records", params=params)

    async def accept_referral(
        self, referral_code: str, nickname: str, user_id: str = ""
    ) -> Dict[str, Any]:
        """POST /admin/v1/referral-records."""
        return await self._post(
            "/admin/v1/referral-records",
            json={
                "referral_code": referral_code,
                "nickname": nickname,
                "user_id": user_id,
            },
        )

    # ── Generic request (escape hatch) ──────────────────────────────

    async def request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Any:
        """Make any authenticated request to a-console.

        Use this for endpoints not covered by convenience methods.
        """
        return await self._request(method, path, **kwargs)
