"""Persistent favorites manager for SofaTUI."""

from __future__ import annotations

import json
import os
from pathlib import Path


def _resolve_favorites_path() -> Path:
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg_config) if xdg_config and not xdg_config.startswith("/tmp") else (Path.home() / ".config")
    return base / "sofatui" / "favorites.json"


DEFAULT_FAVORITES_PATH = _resolve_favorites_path()
LEGACY_FAVORITES_PATH = Path(__file__).resolve().parents[2] / "data" / "favorites.json"


class FavoritesStore:
    """Stores starred match IDs, team IDs, and unique tournament IDs on persistent storage."""

    def __init__(self, path: Path = DEFAULT_FAVORITES_PATH) -> None:
        self.path = path
        self.match_ids: set[int] = set()
        self.team_ids: set[int] = set()
        self.tournament_ids: set[int] = {
            7,    # UEFA Champions League
            679,  # UEFA Europa League
            17,   # Premier League
            8,    # LaLiga
            23,   # Serie A
            35,   # Bundesliga
            34,   # Ligue 1
            238,  # Liga Portugal Betclic
        }
        self.load()

    def load(self) -> None:
        target = self.path
        if not target.exists() and target == DEFAULT_FAVORITES_PATH and LEGACY_FAVORITES_PATH.exists():
            target = LEGACY_FAVORITES_PATH
        if not target.exists():
            return
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
            self.match_ids = {int(x) for x in data.get("match_ids", [])}
            self.team_ids = {int(x) for x in data.get("team_ids", [])}
            if "tournament_ids" in data:
                self.tournament_ids = {int(x) for x in data["tournament_ids"]}
        except Exception:
            pass

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "match_ids": sorted(self.match_ids),
                "team_ids": sorted(self.team_ids),
                "tournament_ids": sorted(self.tournament_ids),
            }
            self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            pass

    def is_match_starred(self, match_id: int, home_team_id: int = 0, away_team_id: int = 0) -> bool:
        return (
            match_id in self.match_ids
            or home_team_id in self.team_ids
            or away_team_id in self.team_ids
        )

    def toggle_match(self, match_id: int) -> bool:
        if match_id in self.match_ids:
            self.match_ids.remove(match_id)
            self.save()
            return False
        self.match_ids.add(match_id)
        self.save()
        return True

    def toggle_team(self, team_id: int) -> bool:
        if team_id in self.team_ids:
            self.team_ids.remove(team_id)
            self.save()
            return False
        self.team_ids.add(team_id)
        self.save()
        return True
