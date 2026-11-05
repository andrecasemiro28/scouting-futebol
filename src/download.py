"""Download (com cache local) dos dados abertos da StatsBomb.

Fonte: https://github.com/statsbomb/open-data (licença de uso não comercial da StatsBomb).
"""
from __future__ import annotations

import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE_URL = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

# Competições de seleções entre 2022 e 2024 (competition_id, season_id, nome)
COMPETITIONS = [
    (43, 106, "Copa do Mundo 2022"),
    (55, 282, "Euro 2024"),
    (223, 282, "Copa América 2024"),
    (1267, 107, "Copa Africana 2023"),
]


def _get_json(rel_path: str) -> list | dict:
    """Lê do cache em data/raw; se não existir, baixa e salva."""
    local = RAW_DIR / rel_path
    if local.exists():
        return json.loads(local.read_text(encoding="utf-8"))
    local.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(f"{BASE_URL}/{rel_path}", timeout=60) as resp:
        data = resp.read()
    local.write_bytes(data)
    return json.loads(data)


def get_matches(competition_id: int, season_id: int) -> list[dict]:
    return _get_json(f"matches/{competition_id}/{season_id}.json")


def get_events(match_id: int) -> list[dict]:
    return _get_json(f"events/{match_id}.json")


def get_lineups(match_id: int) -> list[dict]:
    return _get_json(f"lineups/{match_id}.json")


def download_all(competitions=COMPETITIONS, workers: int = 8) -> list[dict]:
    """Baixa partidas, eventos e escalações de todas as competições.

    Retorna a lista de partidas com o nome da competição anexado.
    """
    matches = []
    for comp_id, season_id, name in competitions:
        for m in get_matches(comp_id, season_id):
            m["competition_label"] = name
            matches.append(m)

    def fetch(match):
        get_events(match["match_id"])
        get_lineups(match["match_id"])

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(fetch, matches))
    return matches


if __name__ == "__main__":
    ms = download_all()
    print(f"{len(ms)} partidas baixadas em {RAW_DIR}")
