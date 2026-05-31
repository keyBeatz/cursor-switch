from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from cursor_switch.paths import ACCOUNTS_DIR, ACCOUNTS_FILE, ACTIVE_FILE, ensure_root


@dataclass
class AccountsConfig:
    default: str = "work"
    accounts: dict[str, dict[str, str]] = field(default_factory=dict)


def _parse_toml_simple(text: str) -> AccountsConfig:
    cfg = AccountsConfig()
    section: str | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            if section.startswith("accounts."):
                name = section.split(".", 1)[1]
                cfg.accounts.setdefault(name, {})
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if section is None and key == "default":
            cfg.default = value
        elif section and section.startswith("accounts."):
            name = section.split(".", 1)[1]
            cfg.accounts.setdefault(name, {})[key] = value
    return cfg


def _render_toml(cfg: AccountsConfig) -> str:
    lines = [f'default = "{cfg.default}"', ""]
    for name in sorted(cfg.accounts):
        lines.append(f"[accounts.{name}]")
        for key, value in sorted(cfg.accounts[name].items()):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{key} = "{escaped}"')
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def sync_accounts_from_dirs(cfg: AccountsConfig) -> bool:
    """Register account dirs missing from accounts.toml (e.g. after parser round-trip bug)."""
    changed = False
    if cfg.default and cfg.default not in cfg.accounts:
        cfg.accounts[cfg.default] = {}
        changed = True
    if not ACCOUNTS_DIR.is_dir():
        return changed
    for path in sorted(ACCOUNTS_DIR.iterdir()):
        if path.is_dir() and path.name not in cfg.accounts:
            cfg.accounts[path.name] = {}
            changed = True
    return changed


def load_accounts() -> AccountsConfig:
    if not ACCOUNTS_FILE.exists():
        cfg = AccountsConfig()
    else:
        cfg = _parse_toml_simple(ACCOUNTS_FILE.read_text(encoding="utf-8"))
    if sync_accounts_from_dirs(cfg):
        save_accounts(cfg)
    return cfg


def save_accounts(cfg: AccountsConfig) -> None:
    ensure_root()
    ACCOUNTS_FILE.write_text(_render_toml(cfg), encoding="utf-8")


def list_account_names(cfg: AccountsConfig) -> list[str]:
    return sorted(cfg.accounts)


def account_exists(cfg: AccountsConfig, name: str) -> bool:
    return name in cfg.accounts


def read_active() -> str | None:
    if not ACTIVE_FILE.exists():
        return None
    value = ACTIVE_FILE.read_text(encoding="utf-8").strip()
    return value or None


def write_active(name: str) -> None:
    ensure_root()
    ACTIVE_FILE.write_text(name + "\n", encoding="utf-8")


def validate_account_name(name: str) -> None:
    if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_-]{0,31}", name):
        raise ValueError(
            f"Invalid account name {name!r}. Use letters, digits, _ or - (max 32 chars)."
        )
