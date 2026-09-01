# -*- coding: utf-8 -*-
"""OAuth2 SSO Plugin — zero core-code modification.

Pure plugin implementation that adds OAuth2 single sign-on to QwenPaw
without modifying any source files.

Supported providers: GitHub, Google, and any custom OAuth2 provider.

Environment variables
---------------------
OMATE_OAUTH2_PROVIDER       : "github" | "google" | "custom"  (default: github)
OMATE_OAUTH2_CLIENT_ID      : OAuth2 client ID   (required)
OMATE_OAUTH2_CLIENT_SECRET  : OAuth2 client secret (required)
OMATE_OAUTH2_REDIRECT_URI   : callback URL        (auto-detected if omitted)
OMATE_OAUTH2_AUTH_URL       : (custom only) authorization endpoint
OMATE_OAUTH2_TOKEN_URL      : (custom only) token endpoint
OMATE_OAUTH2_USERINFO_URL   : (custom only) userinfo endpoint
OMATE_OAUTH2_SCOPE          : (custom only) OAuth2 scope
OMATE_OAUTH2_USERNAME_FIELD : (custom only) JSON field name for username

Exported on successful login (for other plugins)
-------------------------------------------------
OMATE_USER_CODE             : authenticated username
OMATE_USER_NAME             : display name from provider

Note: OMATE_CONSOLE_TOKEN is NOT exported by this plugin.
It should be a manually configured API Key for service-to-service calls.

Usage
-----
    GET /api/oauth/login     → redirect to provider
    GET /api/oauth/callback  → handle callback (called by provider)
    GET /api/oauth/status    → check configuration status
"""

import logging
import os
import secrets
from typing import Any, Dict, Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from qwenpaw.plugins.api import PluginApi

logger = logging.getLogger("qwenpaw.oauth2_sso")

# ── Provider presets ──────────────────────────────────────────────────────

_PROVIDERS: Dict[str, Dict[str, str]] = {
    "github": {
        "auth_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "scope": "read:user user:email",
        "username_field": "login",
    },
    "google": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "scope": "openid email profile",
        "username_field": "email",
    },
}

# ── Internal helpers ──────────────────────────────────────────────────────


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _get_config() -> Dict[str, str]:
    """Build merged provider config from env vars + preset."""
    provider = _env("OMATE_OAUTH2_PROVIDER", "github").lower()
    preset = _PROVIDERS.get(provider, _PROVIDERS["github"])
    return {
        "provider": provider,
        "client_id": _env("OMATE_OAUTH2_CLIENT_ID"),
        "client_secret": _env("OMATE_OAUTH2_CLIENT_SECRET"),
        "redirect_uri": _env("OMATE_OAUTH2_REDIRECT_URI"),
        "auth_url": _env("OMATE_OAUTH2_AUTH_URL") or preset["auth_url"],
        "token_url": _env("OMATE_OAUTH2_TOKEN_URL") or preset["token_url"],
        "userinfo_url": (
            _env("OMATE_OAUTH2_USERINFO_URL") or preset["userinfo_url"]
        ),
        "scope": _env("OMATE_OAUTH2_SCOPE") or preset["scope"],
        "username_field": (
            _env("OMATE_OAUTH2_USERNAME_FIELD") or preset["username_field"]
        ),
    }


def _html_page(
    title: str,
    body: str,
    *,
    token: str = "",
    redirect: bool = False,
    status: str = "info",
) -> str:
    """Build a self-contained styled HTML response page."""
    icon = {"ok": "✅", "error": "❌", "info": "ℹ️", "wait": "⏳"}.get(
        status, "ℹ️"
    )
    color = {
        "ok": "#52c41a",
        "error": "#ff4d4f",
        "info": "#1677ff",
        "wait": "#1677ff",
    }.get(status, "#1677ff")

    token_script = ""
    if token:
        # Escape single quotes in token (shouldn't happen, but be safe)
        safe_token = token.replace("'", "\\'")
        token_script = f"""
    <script>
      (function() {{
        try {{
          localStorage.setItem("qwenpaw_auth_token", '{safe_token}');
          window.location.href = "/";
        }} catch(e) {{
          document.getElementById("status-text").innerText =
            "Token 已生成，但无法写入 localStorage: " + e.message;
        }}
      }})();
    </script>"""

    spinner = (
        '<div class="spinner"></div>'
        if redirect or bool(token)
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} — QwenPaw</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #f0f2f5;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
    }}
    .card {{
      background: #fff;
      border-radius: 16px;
      box-shadow: 0 4px 24px rgba(0,0,0,0.08);
      padding: 48px 40px;
      text-align: center;
      max-width: 420px;
      width: 90%;
    }}
    .icon {{ font-size: 48px; margin-bottom: 16px; }}
    h2 {{ color: #1a1a1a; font-size: 20px; font-weight: 600; margin-bottom: 12px; }}
    p {{ color: #666; font-size: 15px; line-height: 1.7; word-break: break-all; }}
    code {{ background: #f5f5f5; padding: 2px 6px; border-radius: 4px; font-size: 13px; }}
    .spinner {{
      border: 3px solid #f0f0f0;
      border-top: 3px solid {color};
      border-radius: 50%;
      width: 32px;
      height: 32px;
      animation: spin 0.8s linear infinite;
      margin: 20px auto 0;
    }}
    @keyframes spin {{ 0%{{transform:rotate(0deg)}} 100%{{transform:rotate(360deg)}} }}
    a {{ color: {color}; text-decoration: none; font-weight: 500; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">{icon}</div>
    <h2>{title}</h2>
    <p id="status-text">{body}</p>
    {spinner}
  </div>
  {token_script}
</body>
</html>"""


# ── Router ────────────────────────────────────────────────────────────────


def _build_router() -> APIRouter:
    router = APIRouter()

    @router.get("/login")
    async def oauth2_login(request: Request):
        """Initiate the OAuth2 authorization code flow."""
        cfg = _get_config()

        if not cfg["client_id"]:
            return HTMLResponse(
                _html_page(
                    "配置错误",
                    "请先设置环境变量 "
                    "<code>OMATE_OAUTH2_CLIENT_ID</code> 和 "
                    "<code>OMATE_OAUTH2_CLIENT_SECRET</code>",
                    status="error",
                ),
                status_code=500,
            )

        # Auto-detect redirect URI if not explicitly set
        redirect_uri = cfg["redirect_uri"]
        if not redirect_uri:
            # Build from the current request's origin
            base = str(request.base_url).rstrip("/")
            redirect_uri = f"{base}/api/oauth/callback"
            
        state = secrets.token_hex(16)
        params = {
            "client_id": cfg["client_id"],
            "redirect_uri": redirect_uri,
            "scope": cfg["scope"],
            "response_type": "code",
            "state": state,
        }

        # Provider-specific extras
        if "github" in cfg["auth_url"]:
            params["allow_signup"] = "true"
        elif "google" in cfg["auth_url"]:
            params["access_type"] = "offline"
            params["prompt"] = "consent"

        auth_url = f"{cfg['auth_url']}?{urlencode(params)}"
        logger.info("OAuth2 SSO: redirecting to %s", cfg["provider"])
        return RedirectResponse(url=auth_url, status_code=302)

    @router.get("/callback")
    async def oauth2_callback(
        request: Request,
        code: Optional[str] = None,
        error: Optional[str] = None,
        error_description: Optional[str] = None,
    ):
        """Handle the OAuth2 callback from the identity provider."""

        # ── Error from provider ──
        if error:
            msg = error_description or error
            logger.warning("OAuth2 SSO: provider returned error: %s", msg)
            return HTMLResponse(
                _html_page("授权失败", f"OAuth2 Provider 返回错误: <b>{msg}</b>", status="error"),
                status_code=400,
            )

        if not code:
            return HTMLResponse(
                _html_page("参数错误", "未收到授权码 (<code>code</code>)", status="error"),
                status_code=400,
            )

        cfg = _get_config()

        import httpx

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                # ── Step 1: exchange code for access token ──
                redirect_uri = cfg["redirect_uri"]
                if not redirect_uri:
                    base = str(request.base_url).rstrip("/")
                    redirect_uri = f"{base}/api/oauth/callback"
                    
                token_payload = {
                    "client_id": cfg["client_id"],
                    "client_secret": cfg["client_secret"],
                    "code": code,
                    "redirect_uri": redirect_uri,
                }

                token_headers = {"Accept": "application/json"}
                token_resp = await client.post(
                    cfg["token_url"],
                    data=token_payload,
                    headers=token_headers,
                )
                token_json = token_resp.json()

                access_token = token_json.get("access_token")
                if not access_token:
                    err_detail = token_json.get("error_description") or token_json.get("error") or str(token_json)
                    logger.error("OAuth2 SSO: no access_token: %s", token_json)
                    return HTMLResponse(
                        _html_page("获取 Token 失败", str(err_detail), status="error"),
                        status_code=500,
                    )

                # ── Step 2: fetch user info ──
                userinfo_headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                }
                userinfo_resp = await client.get(
                    cfg["userinfo_url"],
                    headers=userinfo_headers,
                )
                userinfo = userinfo_resp.json()

            logger.debug("OAuth2 SSO: userinfo = %s", userinfo)

            # ── Step 3: extract username ──
            username = userinfo.get(cfg["username_field"], "")
            if not username:
                # Fallback: try common fields
                for fallback in ("login", "email", "preferred_username", "sub", "name"):
                    username = userinfo.get(fallback, "")
                    if username:
                        break

            if not username:
                return HTMLResponse(
                    _html_page(
                        "用户信息异常",
                        f"无法从 Provider 响应中提取用户名 "
                        f"(field: <code>{cfg['username_field']}</code>)",
                        status="error",
                    ),
                    status_code=500,
                )

            # ── Step 4: create QwenPaw JWT ──
            from qwenpaw.app.auth import (
                create_token,
                has_registered_users,
                register_user,
            )

            if not has_registered_users():
                # First login ever: auto-register this OAuth2 user
                random_pw = secrets.token_hex(32)
                token = register_user(username, random_pw)
                if token:
                    logger.info(
                        "OAuth2 SSO: auto-registered first user '%s'",
                        username,
                    )
                else:
                    # Race condition fallback
                    token = create_token(username)
            else:
                token = create_token(username)

            if not token:
                return HTMLResponse(
                    _html_page(
                        "Token 创建失败",
                        "无法生成认证 Token，请检查系统配置",
                        status="error",
                    ),
                    status_code=500,
                )

            # ── Step 5: export user identity as env vars for other plugins ──
            # Note: OMATE_CONSOLE_TOKEN is NOT set here — it should be a
            # manually configured API Key (X-API-Key), not a session JWT.
            display_name = (
                userinfo.get("name")
                or userinfo.get("preferred_username")
                or username
            )
            os.environ["OMATE_USER_CODE"] = username
            os.environ["OMATE_USER_NAME"] = display_name
            logger.info(
                "OAuth2 SSO: exported OMATE_USER_CODE=%s, OMATE_USER_NAME=%s",
                username,
                display_name,
            )

            logger.info("OAuth2 SSO: login successful for '%s'", username)

            return HTMLResponse(
                _html_page(
                    "登录成功",
                    f"欢迎 <b>{username}</b>，正在跳转…",
                    token=token,
                    redirect=True,
                    status="ok",
                ),
            )

        except httpx.HTTPStatusError as exc:
            logger.error("OAuth2 SSO HTTP error: %s", exc, exc_info=True)
            return HTMLResponse(
                _html_page(
                    "网络请求失败",
                    f"HTTP {exc.response.status_code}: {exc}",
                    status="error",
                ),
                status_code=502,
            )
        except httpx.RequestError as exc:
            logger.error("OAuth2 SSO request error: %s", exc, exc_info=True)
            return HTMLResponse(
                _html_page("网络连接失败", f"无法连接 OAuth2 Provider: {exc}", status="error"),
                status_code=502,
            )
        except Exception as exc:
            logger.error("OAuth2 SSO unexpected error: %s", exc, exc_info=True)
            return HTMLResponse(
                _html_page("内部错误", f"未知错误: {exc}", status="error"),
                status_code=500,
            )

    @router.get("/status")
    async def oauth2_status() -> Dict[str, Any]:
        """Check whether OAuth2 SSO is configured and reachable."""
        cfg = _get_config()
        cid = cfg["client_id"]
        return {
            "plugin": "oauth2-sso",
            "configured": bool(cid and cfg["client_secret"]),
            "provider": cfg["provider"],
            "client_id_preview": f"{cid[:8]}…" if len(cid) > 8 else cid,
            "redirect_uri": cfg["redirect_uri"] or "(auto-detect)",
            "endpoints": {
                "login": "/api/oauth/login",
                "callback": "/api/oauth/callback",
                "status": "/api/oauth/status",
            },
        }

    return router


# ── Plugin entry point ────────────────────────────────────────────────────


class OAuth2SSOPlugin:
    """OAuth2 SSO — pure plugin, zero core-code changes."""

    def register(self, api: PluginApi) -> None:
        # 1) Mount HTTP routes
        router = _build_router()
        api.register_http_router(
            router,
            prefix="/oauth",
            tags=["OAuth2-SSO"],
        )

        # 2) Whitelist OAuth2 endpoints in AuthMiddleware at startup
        def _patch_public_prefixes():
            try:
                import qwenpaw.app.auth as auth_mod

                current = auth_mod._PUBLIC_PREFIXES
                new_prefix = "/api/oauth/"
                if not any(p == new_prefix for p in current):
                    auth_mod._PUBLIC_PREFIXES = current + (new_prefix,)
                    logger.info(
                        "OAuth2 SSO: added '%s' to _PUBLIC_PREFIXES",
                        new_prefix,
                    )
            except Exception as exc:
                logger.warning(
                    "OAuth2 SSO: could not patch _PUBLIC_PREFIXES: %s",
                    exc,
                )

        api.register_startup_hook(
            hook_name="oauth2_sso_whitelist",
            callback=_patch_public_prefixes,
            priority=99,
        )

        logger.info("OAuth2 SSO plugin registered → /api/oauth")


plugin = OAuth2SSOPlugin()
