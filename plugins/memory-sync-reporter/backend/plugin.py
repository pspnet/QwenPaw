# -*- coding: utf-8 -*-
"""Memory Sync Reporter -- Bidirectional sync of user profiling data with remote.

Synced categories:
  - PROFILE   (single file: PROFILE.md)       — bidirectional
  - MEMORY    (single file: MEMORY.md)         — bidirectional
  - INTERESTS (single file: interests.yaml)    — bidirectional
  - DAILY     (directory bundle: memory/*.md)  — push
  - DIGEST    (directory bundle: digest/*.md)  — push
"""

import json
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from qwenpaw.plugins.api import PluginApi

logger = logging.getLogger("qwenpaw.memory_sync_reporter")

# ---------------------------------------------------------------------------
# Sync direction per category
# ---------------------------------------------------------------------------
CATEGORY_SYNC_DIRECTION: Dict[str, str] = {
    "PROFILE": "bidirectional",
    "MEMORY": "bidirectional",
    "INTERESTS": "bidirectional",
    "DAILY": "push",
    "DIGEST": "push",
}

# ---------------------------------------------------------------------------
# Dynamic config helpers (re-read env vars each time)
# ---------------------------------------------------------------------------

def _get_base_url() -> str:
    return os.environ.get("OMATE_CONSOLE_URL", "http://localhost:8080").rstrip("/")

def _get_remote_url() -> str:
    return f"{_get_base_url()}/admin/v1/memories"

def _get_interval() -> int:
    return int(os.environ.get("OMATE_MEMORY_SYNC_INTERVAL", "300"))

def _get_token() -> str:
    return os.environ.get("OMATE_CONSOLE_TOKEN", "")

def _get_user_code() -> str:
    return os.environ.get("OMATE_USER_CODE", "")

def _get_user_name() -> str:
    return os.environ.get("OMATE_USER_NAME", "")


# ---------------------------------------------------------------------------
# Local sync state (tracks last known remote version per category)
# ---------------------------------------------------------------------------

STATE_FILENAME = ".memory_sync_state.json"


def _load_sync_state(workspace: Path) -> Dict[str, Any]:
    """Load sync state from local JSON file.

    Structure: {"PROFILE": {"remote_id": "xxx", "version": 3, "local_hash": "abc"}, ...}
    """
    state_path = workspace / STATE_FILENAME
    if not state_path.is_file():
        return {}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_sync_state(workspace: Path, state: Dict[str, Any]) -> None:
    state_path = workspace / STATE_FILENAME
    try:
        state_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as exc:
        logger.warning("Failed to save sync state: %s", exc)


def _content_hash(text: str) -> str:
    """Simple hash to detect local content changes."""
    import hashlib
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Workspace helpers
# ---------------------------------------------------------------------------

def _resolve_workspace_dir() -> Path:
    """Resolve the active workspace directory.

    Priority:
    1. Context variable (set when called from inside an agent turn)
    2. First directory under ``WORKING_DIR / "workspaces"``
    3. ``WORKING_DIR`` itself (ultimate fallback)
    """
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


def _read_file(path: Path) -> Optional[str]:
    """Read a text file and return its content, or None if not found."""
    if not path.is_file():
        logger.debug("File not found: %s", path)
        return None
    try:
        content = path.read_text(encoding="utf-8").strip()
        return content if content else None
    except Exception as exc:
        logger.warning("Failed to read %s: %s", path, exc)
        return None


def _write_file(path: Path, content: str) -> None:
    """Write content to a text file."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        logger.info("Wrote local file: %s", path)
    except Exception as exc:
        logger.warning("Failed to write %s: %s", path, exc)


# ---------------------------------------------------------------------------
# Multi-file bundle helpers (for DAILY and DIGEST directories)
# ---------------------------------------------------------------------------

BUNDLE_FILE_PATTERN = re.compile(r'<!-- ===BUNDLE_FILE:(.+?)=== -->')


def _read_directory_bundle(directory: Path, max_days: int = 30) -> Optional[str]:
    """Read all .md files in a directory and merge into a single bundle string.

    Only includes files modified within *max_days* to keep bundle size bounded.
    Format:
        <!-- ===BUNDLE_FILE:2026-08-29.md=== -->

        (content)

        <!-- ===BUNDLE_FILE:2026-08-28.md=== -->

        (content)
    """
    if not directory.is_dir():
        return None
    md_files = sorted(directory.glob("*.md"), reverse=True)
    if not md_files:
        return None

    cutoff = time.time() - max_days * 86400
    parts: List[str] = []
    for f in md_files:
        try:
            if f.stat().st_mtime < cutoff:
                continue
        except OSError:
            continue
        content = _read_file(f)
        if content:
            parts.append(f"<!-- ===BUNDLE_FILE:{f.name}=== -->\n\n{content}")
    return "\n\n".join(parts) if parts else None


def _write_directory_bundle(directory: Path, bundle: str) -> None:
    """Split a bundle string back into individual .md files in the directory."""
    directory.mkdir(parents=True, exist_ok=True)
    segments = BUNDLE_FILE_PATTERN.split(bundle)
    # segments: ['preamble', 'file1.md', 'content1', 'file2.md', 'content2', ...]
    i = 1
    while i < len(segments) - 1:
        filename = segments[i].strip()
        content = segments[i + 1].strip()
        if filename and content:
            safe_name = Path(filename).name  # prevent path traversal
            _write_file(directory / safe_name, content)
        i += 2


# ---------------------------------------------------------------------------
# Local content readers per category
# ---------------------------------------------------------------------------

def _read_local_content(category: str, workspace: Path) -> Optional[str]:
    """Read local content for a given category."""
    if category == "PROFILE":
        return _read_file(workspace / "PROFILE.md")
    elif category == "MEMORY":
        return _read_file(workspace / "MEMORY.md")
    elif category == "INTERESTS":
        return _read_file(workspace / "interests.yaml")
    elif category == "DAILY":
        return _read_directory_bundle(workspace / "memory")
    elif category == "DIGEST":
        return _read_directory_bundle(workspace / "digest")
    return None


def _write_local_content(category: str, workspace: Path, content: str) -> None:
    """Write remote content to local files for a given category."""
    if category == "PROFILE":
        _write_file(workspace / "PROFILE.md", content)
    elif category == "MEMORY":
        _write_file(workspace / "MEMORY.md", content)
    elif category == "INTERESTS":
        _write_file(workspace / "interests.yaml", content)
    elif category == "DAILY":
        _write_directory_bundle(workspace / "memory", content)
    elif category == "DIGEST":
        _write_directory_bundle(workspace / "digest", content)


def _save_conflict_backup(category: str, workspace: Path, local_content: str) -> None:
    """Save a .conflict backup for single-file categories."""
    ext_map = {
        "PROFILE": ".md.conflict",
        "MEMORY": ".md.conflict",
        "INTERESTS": ".yaml.conflict",
    }
    suffix = ext_map.get(category)
    if not suffix:
        return
    name_map = {
        "PROFILE": "PROFILE.md",
        "MEMORY": "MEMORY.md",
        "INTERESTS": "interests.yaml",
    }
    base = name_map.get(category, category)
    conflict_path = workspace / (base + suffix)
    try:
        conflict_path.write_text(local_content, encoding="utf-8")
        logger.warning("Conflict on %s: local backup saved to %s", category, conflict_path)
    except Exception as exc:
        logger.warning("Failed to save conflict backup for %s: %s", category, exc)


# ---------------------------------------------------------------------------
# Bidirectional sync logic
# ---------------------------------------------------------------------------

def _sync_once(client: Any, headers: Dict[str, str], remote_url: str,
               user_code: str, user_name: str,
               workspace: Path) -> Dict[str, int]:
    """Perform one round of bidirectional sync.

    Returns stats dict: {"pushed": N, "pulled": N, "conflicts": N, "errors": N}
    """
    import httpx

    stats = {"pushed": 0, "pulled": 0, "conflicts": 0, "errors": 0}
    state = _load_sync_state(workspace)

    all_categories = list(CATEGORY_SYNC_DIRECTION.keys())

    # ── Step 1: Fetch all remote records ──────────────────────────────
    remote_map: Dict[str, Dict[str, Any]] = {}
    try:
        resp = client.get(
            remote_url,
            params={"userId": user_code, "page": 1, "size": 100},
            headers=headers,
            timeout=15.0,
        )
        resp.raise_for_status()
        for item in resp.json().get("items", []):
            cat = item.get("category", "")
            if cat:
                remote_map[cat] = item
    except Exception as exc:
        logger.warning("Failed to fetch remote memories: %s", exc)
        stats["errors"] += 1
        return stats

    # ── Step 2: Pull remote changes (remote -> local) ──────────────────
    # Only pull for bidirectional categories
    for category in all_categories:
        direction = CATEGORY_SYNC_DIRECTION[category]
        if direction == "push":
            continue  # push-only, skip pull

        remote_item = remote_map.get(category)
        if not remote_item:
            continue

        remote_version = remote_item.get("version", 1)
        remote_content = remote_item.get("content", "")
        remote_id = remote_item.get("id", "")
        local_state = state.get(category, {})
        known_version = local_state.get("version", 0)
        known_hash = local_state.get("local_hash", "")

        local_content = _read_local_content(category, workspace)
        local_hash = _content_hash(local_content) if local_content else ""

        if remote_version > known_version and local_hash == known_hash:
            # Pull: write remote content to local
            _write_local_content(category, workspace, remote_content)
            state[category] = {
                "remote_id": remote_id,
                "version": remote_version,
                "local_hash": _content_hash(remote_content),
            }
            stats["pulled"] += 1
            logger.info("Pulled %s: remote v%d -> local", category, remote_version)
        elif remote_version > known_version and local_hash != known_hash:
            # Conflict: remote wins, save local backup for single-file categories
            if local_content:
                _save_conflict_backup(category, workspace, local_content)
            _write_local_content(category, workspace, remote_content)
            state[category] = {
                "remote_id": remote_id,
                "version": remote_version,
                "local_hash": _content_hash(remote_content),
            }
            stats["conflicts"] += 1

    # ── Step 3: Push local changes (local -> remote) ──────────────────
    for category in all_categories:
        local_content = _read_local_content(category, workspace)
        if local_content is None:
            continue

        local_hash = _content_hash(local_content)
        local_state = state.get(category, {})
        known_hash = local_state.get("local_hash", "")
        known_version = local_state.get("version", 0)
        remote_id = local_state.get("remote_id", "")

        # Skip if local content hasn't changed since last sync
        if local_hash == known_hash and remote_id:
            continue

        sync_direction = CATEGORY_SYNC_DIRECTION[category]

        body: Dict[str, Any] = {
            "userId": user_code,
            "title": category,
            "content": local_content,
            "category": category,
            "source": "qwenpaw",
            "syncDirection": sync_direction,
            "tags": [],
        }

        remote_item = remote_map.get(category)
        if remote_item and remote_id:
            # Update existing record with optimistic lock
            body["version"] = known_version
            try:
                resp = client.put(
                    f"{remote_url}/{remote_id}",
                    json=body,
                    headers=headers,
                    timeout=15.0,
                )
                if resp.status_code == 409:
                    conflict_data = resp.json()
                    current_version = conflict_data.get("currentVersion", known_version)
                    logger.warning(
                        "Push conflict on %s: local v%d vs remote v%d, will retry next cycle",
                        category, known_version, current_version,
                    )
                    state[category]["version"] = current_version
                    state[category]["local_hash"] = ""
                    stats["conflicts"] += 1
                    continue
                resp.raise_for_status()
                updated = resp.json()
                state[category] = {
                    "remote_id": remote_id,
                    "version": updated.get("version", known_version + 1),
                    "local_hash": local_hash,
                }
                stats["pushed"] += 1
                logger.info("Pushed %s: v%d -> remote", category, known_version)
            except httpx.HTTPStatusError as exc:
                logger.warning("Push failed for %s: HTTP %d", category, exc.response.status_code)
                stats["errors"] += 1
            except Exception as exc:
                logger.warning("Push failed for %s: %s", category, exc)
                stats["errors"] += 1
        elif remote_item:
            # Found by category but no local remote_id yet
            remote_id = remote_item.get("id", "")
            body["version"] = remote_item.get("version", 1)
            try:
                resp = client.put(
                    f"{remote_url}/{remote_id}",
                    json=body,
                    headers=headers,
                    timeout=15.0,
                )
                resp.raise_for_status()
                updated = resp.json()
                state[category] = {
                    "remote_id": remote_id,
                    "version": updated.get("version", 2),
                    "local_hash": local_hash,
                }
                stats["pushed"] += 1
            except Exception as exc:
                logger.warning("Push (adopt) failed for %s: %s", category, exc)
                stats["errors"] += 1
        else:
            # Create new record
            try:
                resp = client.post(
                    remote_url,
                    json=body,
                    headers=headers,
                    timeout=15.0,
                )
                resp.raise_for_status()
                created = resp.json()
                state[category] = {
                    "remote_id": created.get("id", ""),
                    "version": created.get("version", 1),
                    "local_hash": local_hash,
                }
                stats["pushed"] += 1
                logger.info("Created %s on remote", category)
            except Exception as exc:
                logger.warning("Create failed for %s: %s", category, exc)
                stats["errors"] += 1

    _save_sync_state(workspace, state)
    return stats


def _sync_loop() -> None:
    import httpx

    while True:
        try:
            user_code = _get_user_code()
            user_name = _get_user_name()
            remote_url = _get_remote_url()
            token = _get_token()

            if not user_code:
                logger.warning("Memory sync skipped: OMATE_USER_CODE is empty")
                time.sleep(_get_interval())
                continue

            headers: Dict[str, str] = {"Content-Type": "application/json"}
            if token:
                headers["X-API-Key"] = token

            workspace = _resolve_workspace_dir()

            try:
                with httpx.Client() as client:
                    stats = _sync_once(
                        client, headers, remote_url,
                        user_code, user_name, workspace,
                    )
                    if stats["pushed"] or stats["pulled"] or stats["conflicts"]:
                        logger.info(
                            "Memory sync OK: user=%s(%s), pushed=%d pulled=%d conflicts=%d errors=%d",
                            user_name, user_code,
                            stats["pushed"], stats["pulled"],
                            stats["conflicts"], stats["errors"],
                        )
            except Exception as exc:
                logger.warning("Memory sync failed: %s", exc)

        except Exception as exc:
            logger.error("Unexpected error in memory sync loop: %s", exc)

        time.sleep(_get_interval())


# ---------------------------------------------------------------------------
# Plugin entry
# ---------------------------------------------------------------------------

class MemorySyncReporterPlugin:
    """Plugin entry point for memory-sync-reporter."""

    def register(self, api: PluginApi) -> None:
        # Register diagnostic HTTP endpoint
        try:
            from fastapi import APIRouter
            from fastapi.responses import JSONResponse

            router = APIRouter()

            @router.get("/status")
            async def status():
                ws = _resolve_workspace_dir()
                state = _load_sync_state(ws)
                return JSONResponse({
                    "plugin": "memory-sync-reporter",
                    "mode": "bidirectional",
                    "remote_url": _get_remote_url(),
                    "interval": _get_interval(),
                    "user_code": _get_user_code(),
                    "user_name": _get_user_name(),
                    "token_set": bool(_get_token()),
                    "workspace": str(ws),
                    "categories": {
                        cat: {
                            "syncDirection": direction,
                            "exists": _category_exists(cat, ws),
                            "synced": cat in state,
                        }
                        for cat, direction in CATEGORY_SYNC_DIRECTION.items()
                    },
                    "sync_state": state,
                })

            api.register_http_router(router, prefix="/memory-sync", tags=["Memory Sync"])
        except Exception as exc:
            logger.warning("Failed to register status endpoint: %s", exc)

        thread = threading.Thread(
            target=_sync_loop,
            name="memory-sync-reporter",
            daemon=True,
        )
        thread.start()
        logger.info(
            "Memory Sync Reporter started (user=%s, code=%s, interval=%ds, remote=%s)",
            _get_user_name(),
            _get_user_code(),
            _get_interval(),
            _get_remote_url(),
        )


def _category_exists(category: str, workspace: Path) -> bool:
    """Check if local data exists for a category."""
    if category == "PROFILE":
        return (workspace / "PROFILE.md").is_file()
    elif category == "MEMORY":
        return (workspace / "MEMORY.md").is_file()
    elif category == "INTERESTS":
        return (workspace / "interests.yaml").is_file()
    elif category == "DAILY":
        d = workspace / "memory"
        return d.is_dir() and any(d.glob("*.md"))
    elif category == "DIGEST":
        d = workspace / "digest"
        return d.is_dir() and any(d.glob("*.md"))
    return False


plugin = MemorySyncReporterPlugin()
