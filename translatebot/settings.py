"""Environment settings loaded from .env (SPEC section 2)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


class MissingConfigError(RuntimeError):
    """Raised when a required configuration value is missing or invalid."""


def _clean(value: str | None) -> str:
    return (value or "").strip()


@dataclass(frozen=True)
class Settings:
    """Validated bot configuration. Secrets are never printed by loaders."""

    discord_token: str = ""
    deepl_api_key: str = ""
    engine: str = "deepl"
    anthropic_api_key: str = ""
    claude_model: str = "claude-haiku-4-5"
    dev_guild_id: int | None = None
    allowed_guild_ids: tuple[int, ...] = ()
    data_dir: Path = Path("data")
    log_level: str = "INFO"


def _parse_int(value: str, name: str) -> int:
    try:
        return int(value)
    except ValueError:
        raise MissingConfigError(
            f"{name} must be an integer ID (found an invalid value). / "
            f"{name} bir tam sayi ID olmali (gecersiz deger bulundu)."
        ) from None


def load_settings(
    env_file: Path | str | None = None,
    *,
    require_token: bool = True,
    require_engine_keys: bool = True,
) -> Settings:
    """Read .env and validate it.

    Error messages are bilingual (EN/TR) and never echo secret values.
    ``require_token=False`` is used by ``bot.py --selftest``; it lets the
    self-test run without a Discord token. ``require_engine_keys=False``
    lets it run without translation API keys.
    """
    if env_file is None:
        env_file = Path(".env")
    load_dotenv(Path(env_file), override=False)

    token = _clean(os.getenv("DISCORD_TOKEN"))
    if require_token and not token:
        raise MissingConfigError(
            "DISCORD_TOKEN is missing in .env - paste the bot token from the "
            "Discord Developer Portal. / .env icinde DISCORD_TOKEN eksik - "
            "Developer Portal'daki bot token'ini yapistir."
        )

    engine = _clean(os.getenv("ENGINE")).lower() or "deepl"
    if engine not in ("deepl", "claude"):
        raise MissingConfigError(
            f"ENGINE must be 'deepl' or 'claude' (got '{engine}'). / "
            "ENGINE 'deepl' veya 'claude' olmali."
        )

    deepl_api_key = _clean(os.getenv("DEEPL_API_KEY"))
    if require_engine_keys and engine == "deepl" and not deepl_api_key:
        raise MissingConfigError(
            "DEEPL_API_KEY is missing in .env (required when ENGINE=deepl). / "
            "ENGINE=deepl iken .env icinde DEEPL_API_KEY zorunludur."
        )

    anthropic_api_key = _clean(os.getenv("ANTHROPIC_API_KEY"))
    if require_engine_keys and engine == "claude" and not anthropic_api_key:
        raise MissingConfigError(
            "ANTHROPIC_API_KEY is missing in .env (required when ENGINE=claude). / "
            "ENGINE=claude iken .env icinde ANTHROPIC_API_KEY zorunludur."
        )

    claude_model = _clean(os.getenv("CLAUDE_MODEL")) or "claude-haiku-4-5"

    dev_guild_id: int | None = None
    raw_dev = _clean(os.getenv("DEV_GUILD_ID"))
    if raw_dev:
        dev_guild_id = _parse_int(raw_dev, "DEV_GUILD_ID")

    allowed: list[int] = []
    raw_allowed = _clean(os.getenv("ALLOWED_GUILD_IDS"))
    if raw_allowed:
        for part in raw_allowed.split(","):
            part = part.strip()
            if part:
                allowed.append(_parse_int(part, "ALLOWED_GUILD_IDS"))

    data_dir = Path(_clean(os.getenv("DATA_DIR")) or "data")
    log_level = _clean(os.getenv("LOG_LEVEL")).upper() or "INFO"

    return Settings(
        discord_token=token,
        deepl_api_key=deepl_api_key,
        engine=engine,
        anthropic_api_key=anthropic_api_key,
        claude_model=claude_model,
        dev_guild_id=dev_guild_id,
        allowed_guild_ids=tuple(allowed),
        data_dir=data_dir,
        log_level=log_level,
    )
