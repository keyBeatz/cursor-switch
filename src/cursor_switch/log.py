from __future__ import annotations

from datetime import datetime, timezone

from cursor_switch.paths import LOG_FILE, ensure_root


def log(message: str) -> None:
    ensure_root()
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[{stamp}] {message}\n"
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(line)
