from __future__ import annotations

import os
from pathlib import Path

APPLICATION_USER_KEY = (
    "src.vs.platform.reactivestorage.browser.reactiveStorageServiceImpl"
    ".persistentStorage.applicationUser"
)

DEFAULT_CURSOR_CONFIG = Path.home() / ".config" / "Cursor"
DEFAULT_CURSOR_HOME = Path.home() / ".cursor"
DEFAULT_CURSOR_CLI = Path.home() / ".config" / "cursor"
ROOT = Path.home() / ".config" / "cursor-accounts"

SHARED_CONFIG = ROOT / "shared" / "config"
SHARED_CURSOR_HOME = ROOT / "shared" / "cursor-home"
SHARED_EXTENSIONS = SHARED_CURSOR_HOME / "extensions"
ACCOUNTS_DIR = ROOT / "accounts"
ACTIVE_FILE = ROOT / "active"
SESSION_FILE = ROOT / "session.json"
ACCOUNTS_FILE = ROOT / "accounts.toml"
LOG_FILE = ROOT / "switch.log"

STATE_DB = SHARED_CONFIG / "User" / "globalStorage" / "state.vscdb"
STORAGE_JSON = SHARED_CONFIG / "User" / "globalStorage" / "storage.json"
CODE_LOCK = SHARED_CONFIG / "code.lock"
CLI_CONFIG = SHARED_CURSOR_HOME / "cli-config.json"
STATSIG_CACHE = SHARED_CURSOR_HOME / "statsig-cache.json"
CLI_AUTH_JSON = DEFAULT_CURSOR_CLI / "auth.json"
CLI_PROMPT_HISTORY = DEFAULT_CURSOR_CLI / "prompt_history.json"

# Not swapped — cache / install artifacts (documented in docs/data-locations.md)
CURSOR_AGENT_DIR = Path.home() / ".local" / "share" / "cursor-agent"
CURSOR_SERVER_DIR = Path.home() / ".cursor-server"
CURSOR_COMPILE_CACHE = Path.home() / ".cache" / "cursor-compile-cache"


def session_bundle_dir(account: str) -> Path:
    return ACCOUNTS_DIR / account / "session-bundle"


def is_initialized() -> bool:
    return SHARED_CONFIG.is_dir() and ACCOUNTS_FILE.exists()


def ensure_root() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    ACCOUNTS_DIR.mkdir(parents=True, exist_ok=True)


def resolve_cursor_binary() -> str:
    for candidate in (
        os.environ.get("CURSOR_SWITCH_CURSOR_BIN"),
        "/usr/share/cursor/bin/cursor",
        str(Path.home() / ".local/bin/cursor"),
    ):
        if candidate and Path(candidate).is_file():
            return candidate
    return "cursor"
