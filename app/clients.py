"""Loads each client's settings.yaml.

Every folder inside clients/ is one business. The bot knows which business a
message is for by the WhatsApp phone number ID it arrived on.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REQUIRED_FIELDS = ("business", "industry", "whatsapp_phone_number_id")


class ClientConfigError(ValueError):
    pass


@dataclass
class Client:
    slug: str  # folder name, e.g. "example-cafe"
    business: str
    industry: str
    phone_number_id: str
    staff_whatsapp: str | None
    data: dict[str, Any] = field(repr=False)  # the whole settings file


def load_client(folder: Path) -> Client:
    path = folder / "settings.yaml"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise ClientConfigError(f"{path}: not valid YAML ({e})") from e
    if not isinstance(data, dict):
        raise ClientConfigError(f"{path}: should be a list of 'name: value' settings")
    missing = [f for f in REQUIRED_FIELDS if not data.get(f)]
    if missing:
        raise ClientConfigError(f"{path}: missing {', '.join(missing)}")
    return Client(
        slug=folder.name,
        business=str(data["business"]),
        industry=str(data["industry"]),
        phone_number_id=str(data["whatsapp_phone_number_id"]),
        staff_whatsapp=str(data["staff_whatsapp"]) if data.get("staff_whatsapp") else None,
        data=data,
    )


def load_all_clients(clients_dir: Path) -> dict[str, Client]:
    """Returns clients keyed by WhatsApp phone number ID."""
    clients: dict[str, Client] = {}
    for folder in sorted(p for p in clients_dir.iterdir() if (p / "settings.yaml").is_file()):
        client = load_client(folder)
        if client.phone_number_id in clients:
            other = clients[client.phone_number_id].slug
            raise ClientConfigError(
                f"{client.slug} and {other} use the same whatsapp_phone_number_id"
            )
        clients[client.phone_number_id] = client
    return clients
