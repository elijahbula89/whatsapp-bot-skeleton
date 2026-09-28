"""Server-wide settings, read from environment variables (see .env.example)."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    # Meta / WhatsApp
    verify_token: str  # any secret word; you type the same word into Meta's webhook setup
    app_secret: str  # from Meta app settings; used to check messages really came from Meta
    access_token: str  # Meta access token allowed to send messages
    graph_api_version: str
    # Claude
    anthropic_api_key: str
    model: str
    # Where the client folders live
    clients_dir: Path


def load_config() -> Config:
    return Config(
        verify_token=os.environ.get("WHATSAPP_VERIFY_TOKEN", ""),
        app_secret=os.environ.get("WHATSAPP_APP_SECRET", ""),
        access_token=os.environ.get("WHATSAPP_ACCESS_TOKEN", ""),
        graph_api_version=os.environ.get("WHATSAPP_GRAPH_VERSION", "v23.0"),
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        model=os.environ.get("CLAUDE_MODEL", "claude-sonnet-5"),
        clients_dir=Path(os.environ.get("CLIENTS_DIR", Path(__file__).resolve().parent.parent / "clients")),
    )
