from __future__ import annotations

from sp_core.models import Competition

from . import openligadb, thesportsdb

ALL_COMPETITIONS: dict[str, Competition] = {
    **openligadb.COMPETITIONS,
    **thesportsdb.COMPETITIONS,
}

SPORTS: list[str] = ["futbol", "baloncesto", "tenis"]
"""Sports with at least one verified, working free data source. "Otros
deportes" (motorsport, etc.) is intentionally left out: TheSportsDB likely
supports it through the same generic adapter, but it wasn't live-verified
before shipping this version — see docs/DATA_SOURCES.md. Don't add a sport
here without testing its real endpoints first."""


def competitions_for_sport(sport: str) -> list[Competition]:
    return [c for c in ALL_COMPETITIONS.values() if c.sport == sport]
