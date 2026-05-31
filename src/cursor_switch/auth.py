from __future__ import annotations

import base64
import json
import shutil
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from cursor_switch.cli_config import clear_cli_config, export_cli_config, import_cli_config
from cursor_switch.log import log
from cursor_switch.paths import (
    APPLICATION_USER_KEY,
    CLI_CONFIG,
    STATE_DB,
    STATSIG_CACHE,
    session_bundle_dir,
)

META_FILE = "meta.json"
STATE_KEYS_FILE = "state-keys.json"


def _auth_where_clause() -> str:
    return (
        "key LIKE 'cursorAuth/%' "
        "OR key LIKE 'glass.%' "
        f"OR key = '{APPLICATION_USER_KEY}'"
    )


def export_state_keys(conn: sqlite3.Connection) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    query = f"SELECT key, value FROM ItemTable WHERE {_auth_where_clause()}"
    for key, value in conn.execute(query):
        if value is None:
            continue
        if isinstance(value, memoryview):
            value = value.tobytes()
        if isinstance(value, bytes):
            encoded = base64.b64encode(value).decode("ascii")
            rows.append({"key": key, "value_b64": encoded, "encoding": "base64"})
        else:
            rows.append({"key": key, "value_b64": str(value), "encoding": "text"})
    return rows


def _decode_row(row: dict[str, str]) -> tuple[str, bytes | str]:
    key = row["key"]
    if row.get("encoding") == "text":
        return key, row["value_b64"]
    return key, base64.b64decode(row["value_b64"])


def import_state_keys(conn: sqlite3.Connection, rows: list[dict[str, str]]) -> None:
    conn.execute(f"DELETE FROM ItemTable WHERE {_auth_where_clause()}")
    for row in rows:
        key, value = _decode_row(row)
        conn.execute(
            "INSERT INTO ItemTable (key, value) VALUES (?, ?)",
            (key, value),
        )


def integrity_check(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        result = conn.execute("PRAGMA integrity_check").fetchone()
        if not result or result[0] != "ok":
            raise RuntimeError(f"SQLite integrity check failed: {result}")
    finally:
        conn.close()


def export_session_bundle(
    account: str,
    *,
    email_hint: str | None = None,
) -> Path:
    bundle = session_bundle_dir(account)
    bundle.mkdir(parents=True, exist_ok=True)

    if not STATE_DB.exists():
        raise FileNotFoundError(f"State database not found: {STATE_DB}")

    conn = sqlite3.connect(STATE_DB)
    try:
        rows = export_state_keys(conn)
    finally:
        conn.close()

    (bundle / STATE_KEYS_FILE).write_text(
        json.dumps(rows, indent=2) + "\n",
        encoding="utf-8",
    )

    if CLI_CONFIG.exists():
        shutil.copy2(CLI_CONFIG, bundle / "cli-config.json")
    if STATSIG_CACHE.exists():
        shutil.copy2(STATSIG_CACHE, bundle / "statsig-cache.json")

    cli_files = export_cli_config(bundle)

    email = email_hint
    for row in rows:
        if row["key"] == "cursorAuth/cachedEmail" and row.get("encoding") == "text":
            email = row["value_b64"]
            break

    meta = {
        "account": account,
        "email": email,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "key_count": len(rows),
        "cli_files": cli_files,
    }
    (bundle / META_FILE).write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    log(f"Exported session bundle for {account} ({len(rows)} keys)")
    return bundle


def has_session_bundle(account: str) -> bool:
    return (session_bundle_dir(account) / STATE_KEYS_FILE).is_file()


def clear_session_auth() -> None:
    """Remove auth tokens from shared state so Cursor prompts for login."""
    if not STATE_DB.exists():
        raise FileNotFoundError(f"State database not found: {STATE_DB}")

    with tempfile.TemporaryDirectory(prefix="cursor-switch-") as tmp:
        tmp_db = Path(tmp) / "state.vscdb"
        shutil.copy2(STATE_DB, tmp_db)
        for suffix in ("-wal", "-shm"):
            sidecar = Path(f"{STATE_DB}{suffix}")
            if sidecar.exists():
                shutil.copy2(sidecar, Path(f"{tmp_db}{suffix}"))

        conn = sqlite3.connect(tmp_db)
        try:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            conn.execute(f"DELETE FROM ItemTable WHERE {_auth_where_clause()}")
            conn.commit()
        finally:
            conn.close()

        integrity_check(tmp_db)

        shutil.copy2(tmp_db, STATE_DB)
        for suffix in ("-wal", "-shm"):
            sidecar = Path(f"{tmp_db}{suffix}")
            if sidecar.exists():
                shutil.copy2(sidecar, Path(f"{STATE_DB}{suffix}"))

    if CLI_CONFIG.exists():
        CLI_CONFIG.unlink()
    if STATSIG_CACHE.exists():
        STATSIG_CACHE.unlink()

    clear_cli_config()
    log("Cleared auth tokens for fresh login")


def import_session_bundle(account: str) -> None:
    bundle = session_bundle_dir(account)
    keys_file = bundle / STATE_KEYS_FILE
    if not keys_file.exists():
        raise FileNotFoundError(
            f"No session bundle for account {account!r}. "
            f"Log in once, then run: cursor-switch export-auth {account}"
        )

    rows = json.loads(keys_file.read_text(encoding="utf-8"))
    if not rows:
        raise RuntimeError(f"Session bundle for {account!r} is empty.")

    with tempfile.TemporaryDirectory(prefix="cursor-switch-") as tmp:
        tmp_db = Path(tmp) / "state.vscdb"
        shutil.copy2(STATE_DB, tmp_db)
        for suffix in ("-wal", "-shm"):
            sidecar = Path(f"{STATE_DB}{suffix}")
            if sidecar.exists():
                shutil.copy2(sidecar, Path(f"{tmp_db}{suffix}"))

        conn = sqlite3.connect(tmp_db)
        try:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            import_state_keys(conn, rows)
            conn.commit()
        finally:
            conn.close()

        integrity_check(tmp_db)

        shutil.copy2(tmp_db, STATE_DB)
        for suffix in ("-wal", "-shm"):
            sidecar = Path(f"{tmp_db}{suffix}")
            if sidecar.exists():
                shutil.copy2(sidecar, Path(f"{STATE_DB}{suffix}"))

    cli_src = bundle / "cli-config.json"
    if cli_src.exists():
        shutil.copy2(cli_src, CLI_CONFIG)

    statsig_src = bundle / "statsig-cache.json"
    if statsig_src.exists():
        shutil.copy2(statsig_src, STATSIG_CACHE)

    import_cli_config(bundle)

    log(f"Imported session bundle for {account} ({len(rows)} keys)")
