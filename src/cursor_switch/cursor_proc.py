from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import time
import urllib.parse
from pathlib import Path

from cursor_switch.log import log
from cursor_switch.paths import CODE_LOCK, STORAGE_JSON, resolve_cursor_binary


def _pgrep_matches(pattern: str) -> bool:
    try:
        result = subprocess.run(
            ["pgrep", "-f", pattern],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def cursor_agent_running() -> bool:
    return _pgrep_matches(r"cursor-agent")


def cursor_running() -> bool:
    if CODE_LOCK.exists():
        return True
    return _pgrep_matches(r"/usr/share/cursor/cursor")


def wait_for_cursor_exit(timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not cursor_running() and not CODE_LOCK.exists():
            return True
        time.sleep(0.25)
    return not cursor_running() and not CODE_LOCK.exists()


def wait_for_cursor_agent_exit(timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not cursor_agent_running():
            return True
        time.sleep(0.25)
    return not cursor_agent_running()


def quit_cursor_agent(timeout: float = 15.0) -> None:
    if not cursor_agent_running():
        return
    log("Stopping cursor-agent (Cursor CLI)")
    subprocess.run(["pkill", "-TERM", "-f", r"cursor-agent"], check=False)
    if not wait_for_cursor_agent_exit(timeout):
        log("cursor-agent still running; sending SIGKILL")
        subprocess.run(["pkill", "-KILL", "-f", r"cursor-agent"], check=False)
        if not wait_for_cursor_agent_exit(5.0):
            raise RuntimeError(
                "cursor-agent (Cursor CLI) is still running. Stop it, then retry."
            )


def quit_cursor(timeout: float = 30.0) -> None:
    quit_cursor_agent()
    if not cursor_running() and not CODE_LOCK.exists():
        return
    log("Sending SIGTERM to Cursor processes")
    subprocess.run(["pkill", "-TERM", "-f", r"/usr/share/cursor/cursor"], check=False)
    if not wait_for_cursor_exit(timeout):
        log("Cursor still running; sending SIGKILL")
        subprocess.run(["pkill", "-KILL", "-f", r"/usr/share/cursor/cursor"], check=False)
        if not wait_for_cursor_exit(10.0):
            raise RuntimeError(
                "Cursor is still running. Close it manually, then retry."
            )


def db_has_open_handles(db_path: Path) -> bool:
    db_path = db_path.resolve()
    targets = {
        str(db_path),
        str(Path(f"{db_path}-wal").resolve()),
        str(Path(f"{db_path}-shm").resolve()),
    }
    proc_root = Path("/proc")
    if not proc_root.is_dir():
        return False
    for pid_dir in proc_root.iterdir():
        if not pid_dir.name.isdigit():
            continue
        fd_dir = pid_dir / "fd"
        try:
            for fd in fd_dir.iterdir():
                try:
                    if os.readlink(fd) in targets:
                        return True
                except OSError:
                    continue
        except OSError:
            continue
    return False


def _checkpoint_wal(db_path: Path) -> bool:
    try:
        conn = sqlite3.connect(db_path, timeout=1.0)
    except sqlite3.OperationalError:
        return False
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        return True
    except sqlite3.OperationalError:
        return False
    finally:
        conn.close()


def wal_idle(db_path: Path, timeout: float = 10.0) -> bool:
    """Return True when the SQLite DB can be safely copied or patched."""
    wal = Path(f"{db_path}-wal")
    shm = Path(f"{db_path}-shm")
    deadline = time.time() + timeout
    while time.time() < deadline:
        if db_has_open_handles(db_path):
            time.sleep(0.25)
            continue
        if _checkpoint_wal(db_path):
            return not wal.exists() and not shm.exists()
        if not wal.exists() and not shm.exists():
            return True
        time.sleep(0.25)
    if db_has_open_handles(db_path):
        return False
    if _checkpoint_wal(db_path):
        return not wal.exists() and not shm.exists()
    return not wal.exists() and not shm.exists()


def folder_uri_to_path(uri: str) -> str | None:
    if not uri.startswith("file://"):
        return None
    parsed = urllib.parse.urlparse(uri)
    return urllib.parse.unquote(parsed.path)


def save_session(session_file: Path) -> list[str]:
    folders: list[str] = []
    if not STORAGE_JSON.exists():
        session_file.write_text(json.dumps({"folders": []}, indent=2) + "\n", encoding="utf-8")
        return folders
    data = json.loads(STORAGE_JSON.read_text(encoding="utf-8"))
    seen: set[str] = set()
    for entry in data.get("backupWorkspaces", {}).get("folders", []):
        uri = entry.get("folderUri")
        if not uri:
            continue
        path = folder_uri_to_path(uri)
        if path and path not in seen:
            seen.add(path)
            folders.append(path)
    for window in data.get("windowsState", {}).get("openedWindows", []):
        uri = window.get("folder")
        if not uri:
            continue
        path = folder_uri_to_path(uri)
        if path and path not in seen:
            seen.add(path)
            folders.append(path)
    session_file.write_text(
        json.dumps({"folders": folders}, indent=2) + "\n",
        encoding="utf-8",
    )
    return folders


def load_session_folders(session_file: Path) -> list[str]:
    if not session_file.exists():
        return []
    data = json.loads(session_file.read_text(encoding="utf-8"))
    return list(data.get("folders", []))


def launch_cursor(
    user_data_dir: Path,
    extensions_dir: Path,
    folders: list[str] | None = None,
) -> None:
    cmd = [
        resolve_cursor_binary(),
        f"--user-data-dir={user_data_dir}",
        f"--extensions-dir={extensions_dir}",
        "-r",
    ]
    if folders:
        cmd.extend(folders)
    log(f"Launching: {' '.join(cmd)}")
    subprocess.Popen(cmd, start_new_session=True)
