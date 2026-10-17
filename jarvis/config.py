"""Chargement de config.toml et de la clé API (.env)."""

import tomllib
from pathlib import Path

from dotenv import load_dotenv

RACINE = Path(__file__).resolve().parent.parent


def charger_config(chemin: Path | None = None) -> dict:
    load_dotenv(RACINE / ".env")
    chemin = chemin or RACINE / "config.toml"
    with open(chemin, "rb") as f:
        config = tomllib.load(f)

    # Les noms d'applis, de sites et de contacts sont comparés en minuscules.
    for section in ("applications", "sites"):
        config[section] = {k.lower(): v for k, v in config.get(section, {}).items()}
    discord = config.setdefault("discord", {})
    for section in ("contacts", "ids_bot"):
        discord[section] = {k.lower(): v for k, v in discord.get(section, {}).items()}
    return config
