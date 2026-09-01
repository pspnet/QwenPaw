# -*- coding: utf-8 -*-
"""JWT Auth Interceptor Plugin.

Intercepts outgoing HTTP requests to a **specific external service**
(e.g. ``http://10.0.0.1:8080``) and injects an
``Authorization: Bearer <token>`` header using the JWT from the
``OMATE_USER_TOKEN`` environment variable.

LLM API calls (OpenAI, Anthropic, Gemini, ...) are **NOT** intercepted.
Only requests whose URL starts with one of the configured target
prefixes are modified.

How it works
------------
On startup the plugin monkey-patches ``httpx.AsyncClient.send`` and
``httpx.Client.send``.  Every outgoing httpx request is inspected: if
its URL matches a configured target prefix, the JWT bearer token is
added to the request headers before the original ``send`` proceeds.

On uninstall the original ``send`` methods are restored.

Environment variables
---------------------
OMATE_USER_TOKEN : JWT to include as ``Authorization: Bearer`` value.
    If unset or empty, the plugin logs a warning and does **not**
    patch anything.

OMATE_REMOTE_SERVICE_URL : Target service URL(s) to intercept.
    Comma-separated list of URL prefixes.  A request is intercepted
    only when its full URL starts with one of these prefixes.

    Example::

        OMATE_REMOTE_SERVICE_URL=http://10.0.0.1:8080

    or::

        OMATE_REMOTE_SERVICE_URL=http://10.0.0.1:8080,http://10.0.0.2:9090

    If unset or empty, the plugin logs a warning and does not intercept
    any request.
"""

import logging
import os
from typing import List

from qwenpaw.plugins.api import PluginApi

logger = logging.getLogger("qwenpaw.jwt_auth_interceptor")

# Module-level state for storing originals during patch.
_original_async_send = None
_original_sync_send = None


# ── Helpers ──────────────────────────────────────────────────────────────


def _normalize_prefixes(raw: str) -> List[str]:
    """Parse comma-separated URL prefixes, strip trailing slashes."""
    if not raw:
        return []
    prefixes = []
    for url in raw.split(","):
        url = url.strip().rstrip("/")
        if url:
            prefixes.append(url)
    return prefixes


def _url_matches(url_str: str, prefixes: List[str]) -> bool:
    """Return True if *url_str* starts with any of the *prefixes*."""
    for prefix in prefixes:
        if url_str.startswith(prefix):
            return True
    return False


def _make_async_send_wrapper(original_send, prefixes: List[str]):
    """Return a wrapper for ``httpx.AsyncClient.send`` that injects JWT."""

    async def _patched_async_send(self, request, **kwargs):
        url_str = str(request.url)
        if _url_matches(url_str, prefixes):
            token = os.environ.get("OMATE_USER_TOKEN", "").strip()
            if token and "Authorization" not in request.headers:
                request.headers["Authorization"] = f"Bearer {token}"
        return await original_send(self, request, **kwargs)

    _patched_async_send.__wrapped__ = original_send
    return _patched_async_send


def _make_sync_send_wrapper(original_send, prefixes: List[str]):
    """Return a wrapper for ``httpx.Client.send`` that injects JWT."""

    def _patched_sync_send(self, request, **kwargs):
        url_str = str(request.url)
        if _url_matches(url_str, prefixes):
            token = os.environ.get("OMATE_USER_TOKEN", "").strip()
            if token and "Authorization" not in request.headers:
                request.headers["Authorization"] = f"Bearer {token}"
        return original_send(self, request, **kwargs)

    _patched_sync_send.__wrapped__ = original_send
    return _patched_sync_send


# ── Plugin class ─────────────────────────────────────────────────────────


class JWTAuthInterceptorPlugin:
    """JWT Auth Interceptor — injects OMATE_USER_TOKEN into requests
    targeting a specific external service, identified by URL prefix."""

    def register(self, api: PluginApi) -> None:
        api.register_startup_hook(
            hook_name="jwt_auth_interceptor_patch",
            callback=self._on_startup,
            priority=10,  # Run early, before any HTTP call is made.
        )
        api.register_uninstall_hook(
            hook_name="jwt_auth_interceptor_unpatch",
            callback=self._on_uninstall,
            priority=10,
        )
        logger.info("JWT Auth Interceptor plugin registered")

    # ── Startup ──────────────────────────────────────────────────────

    async def _on_startup(self) -> None:
        """Patch httpx send methods to inject JWT for target URLs."""
        global _original_async_send, _original_sync_send

        token = os.environ.get("OMATE_USER_TOKEN", "").strip()
        if not token:
            logger.warning(
                "JWT Auth Interceptor: OMATE_USER_TOKEN is not set; "
                "no auth header will be injected",
            )
            return

        raw_url = os.environ.get("OMATE_REMOTE_SERVICE_URL", "").strip()
        prefixes = _normalize_prefixes(raw_url)
        if not prefixes:
            logger.warning(
                "JWT Auth Interceptor: OMATE_REMOTE_SERVICE_URL is not "
                "set; no requests will be intercepted. Set it to the "
                "target service URL (e.g. http://10.0.0.1:8080)",
            )
            return

        import httpx

        # Patch AsyncClient.send
        _original_async_send = httpx.AsyncClient.send
        httpx.AsyncClient.send = _make_async_send_wrapper(
            _original_async_send, prefixes,
        )

        # Patch Client.send (synchronous)
        _original_sync_send = httpx.Client.send
        httpx.Client.send = _make_sync_send_wrapper(
            _original_sync_send, prefixes,
        )

        logger.info(
            "JWT Auth Interceptor: patched httpx.AsyncClient.send and "
            "httpx.Client.send; requests to %s will include "
            "Authorization: Bearer header",
            prefixes,
        )

    # ── Uninstall ────────────────────────────────────────────────────

    async def _on_uninstall(
        self,
        *,
        plugin_id: str = "",
        delete_files: bool = False,
    ) -> None:
        """Restore original httpx send methods."""
        global _original_async_send, _original_sync_send

        import httpx

        if _original_async_send is not None:
            httpx.AsyncClient.send = _original_async_send
            _original_async_send = None
            logger.info(
                "JWT Auth Interceptor: restored httpx.AsyncClient.send",
            )

        if _original_sync_send is not None:
            httpx.Client.send = _original_sync_send
            _original_sync_send = None
            logger.info(
                "JWT Auth Interceptor: restored httpx.Client.send",
            )


# ── Module-level plugin entry point ──────────────────────────────────────

plugin = JWTAuthInterceptorPlugin()
