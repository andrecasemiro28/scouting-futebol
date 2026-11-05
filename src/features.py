"""Transforma eventos da StatsBomb em métricas por 90 minutos por jogador."""
from __future__ import annotations

from collections import Counter, defaultdict
from math import hypot

import pandas as pd

from src.download import COMPETITIONS, download_all, get_events, get_lineups

GOAL = (120.0, 40.0)  # campo StatsBomb: 120 x 80, ataque sempre para a direita
SET_PIECES = {"Corner", "Free Kick", "Throw-in", "Goal Kick", "Kick Off"}

POSITION_GROUPS = {
    "Goalkeeper": "GOL",
    "Right Center Back": "ZAG", "Left Center Back": "ZAG", "Center Back": "ZAG",
    "Right Back": "LAT", "Left Back": "LAT", "Right Wing Back": "LAT", "Left Wing Back": "LAT",
    "Right Defensive Midfield": "VOL", "Left Defensive Midfield": "VOL", "Center Defensive Midfield": "VOL",
    "Right Center Midfield": "MEI", "Left Center Midfield": "MEI", "Center Midfield": "MEI",
    "Right Attacking Midfield": "MEI", "Left Attacking Midfield": "MEI", "Center Attacking Midfield": "MEI",
    "Right Midfield": "PON", "Left Midfield": "PON", "Right Wing": "PON", "Left Wing": "PON",
    "Right Center Forward": "ATA", "Left Center Forward": "ATA", "Center Forward": "ATA",
    "Secondary Striker": "ATA",
}


def _dist_to_goal(loc) -> float:
    return hypot(GOAL[0] - loc[0], GOAL[1] - loc[1])


def is_progressive(start, end) -> bool:
    """Ação que aproxima a bola pelo menos 25% do gol adversário,
    começando fora do terço defensivo (definição usual em scouting)."""
    if start is None or end is None or start[0] < 40:
        return False
    return _dist_to_goal(end) <= 0.75 * _dist_to_goal(start)


def in_box(loc) -> bool:
    return loc is not None and loc[0] >= 102 and 18 <= loc[1] <= 62


def _elapsed(ev, period_start, period_offset) -> float:
    t = ev["minute"] + ev["second"] / 60
    return period_offset[ev["period"]] + (t - period_start[ev["period"]])


def match_minutes(events: list[dict]) -> dict[int, float]:
    """Minutos jogados por jogador numa partida (ignora disputa de pênaltis)."""
    evs = [e for e in events if e["period"] <= 4]
    period_start, period_end = {}, {}
    for e in evs:
        t = e["minute"] + e["second"] / 60
        p = e["period"]
        period_start[p] = min(period_start.get(p, t), t)
        period_end[p] = max(period_end.get(p, t), t)
    period_offset, acc = {}, 0.0
    for p in sorted(period_start):
        period_offset[p] = acc
        acc += period_end[p] - period_start[p]
    match_end = acc

    on, off = {}, {}
    for e in evs:
        typ = e["type"]["name"]
        if typ == "Starting XI":
            for pl in e["tactics"]["lineup"]:
                on[pl["player"]["id"]] = 0.0
        elif typ == "Substitution":
            t = _elapsed(e, period_start, period_offset)
            off[e["player"]["id"]] = t
            on[e["substitution"]["replacement"]["id"]] = t
        elif typ in ("Foul Committed", "Bad Behaviour"):
            card = (e.get("foul_committed") or e.get("bad_behaviour") or {}).get("card", {})
            if card.get("name") in ("Red Card", "Second Yellow"):
                off[e["player"]["id"]] = _elapsed(e, period_start, period_offset)
    return {pid: max(off.get(pid, match_end) - start, 0.0) for pid, start in on.items()}


def player_names(lineups: list[dict]) -> dict[int, tuple[str, str]]:
    """id -> (nome curto, seleção)."""
    out = {}
    for team in lineups:
        for p in team["lineup"]:
            out[p["player_id"]] = (p.get("player_nickname") or p["player_name"], team["team_name"])
    return out


def build_player_table(min_minutes: float = 0.0) -> pd.DataFrame:
    """Agrega todas as partidas e devolve uma linha por jogador com métricas por 90."""
    matches = download_all(COMPETITIONS)
    tot = defaultdict(Counter)
    positions = defaultdict(Counter)
    info, comps = {}, defaultdict(set)

    for m in matches:
        mid = m["match_id"]
        events = get_events(mid)
        info.update(player_names(get_lineups(mid)))
        for pid, mins in match_minutes(events).items():
            tot[pid]["minutes"] += mins
            if mins > 0:
                tot[pid]["matches"] += 1
                comps[pid].add(m["competition_label"])

        xg_by_shot = {e["id"]: e["shot"]["statsbomb_xg"] for e in events if e["type"]["name"] == "Shot"}

        for e in events:
            if e["period"] == 5 or "player" not in e:
                continue
            pid, typ, loc = e["player"]["id"], e["type"]["name"], e.get("location")
            c = tot[pid]
            if "position" in e:
                positions[pid][e["position"]["name"]] += 1
            if loc is not None and typ not in ("Pressure",):
                c["touches"] += 1
                c["touches_box"] += in_box(loc)

            if typ == "Pass":
                p = e["pass"]
                complete = "outcome" not in p
                open_play = p.get("type", {}).get("name") not in SET_PIECES
                c["passes"] += 1
                c["passes_completed"] += complete
                if p.get("shot_assist") or p.get("goal_assist"):
                    c["key_passes"] += 1
                    c["xa"] += xg_by_shot.get(p.get("assisted_shot_id"), 0.0)
                c["assists"] += bool(p.get("goal_assist"))
                if complete and open_play:
                    end = p["end_location"]
                    c["prog_passes"] += is_progressive(loc, end)
                    c["passes_final_third"] += (loc[0] < 80 <= end[0])
                    c["passes_into_box"] += (in_box(end) and not in_box(loc))
                if p.get("cross") and open_play:
                    c["crosses"] += 1
                    c["crosses_completed"] += complete
            elif typ == "Carry":
                end = e["carry"]["end_location"]
                c["prog_carries"] += is_progressive(loc, end)
                c["carries_into_box"] += (in_box(end) and not in_box(loc))
            elif typ == "Shot":
                s = e["shot"]
                if s["type"]["name"] == "Penalty":
                    continue
                c["np_shots"] += 1
                c["np_xg"] += s["statsbomb_xg"]
                c["np_goals"] += s["outcome"]["name"] == "Goal"
            elif typ == "Dribble":
                c["dribbles"] += 1
                c["dribbles_completed"] += e["dribble"]["outcome"]["name"] == "Complete"
            elif typ == "Duel" and e["duel"]["type"]["name"] == "Tackle":
                c["tackles"] += 1
                c["tackles_won"] += e["duel"].get("outcome", {}).get("name") in ("Won", "Success In Play", "Success Out")
            elif typ == "Interception":
                c["interceptions"] += 1
            elif typ == "Pressure":
                c["pressures"] += 1
                c["pressures_att_third"] += loc[0] >= 80
            elif typ == "Ball Recovery" and not e.get("ball_recovery", {}).get("recovery_failure"):
                c["recoveries"] += 1
            elif typ == "Clearance":
                c["clearances"] += 1
            elif typ == "Dispossessed" or (typ == "Miscontrol"):
                c["turnovers"] += 1

    rows = []
    for pid, c in tot.items():
        if c["minutes"] <= 0 or pid not in info:
            continue
        name, team = info[pid]
        pos = positions[pid].most_common(1)[0][0] if positions[pid] else None
        row = {"player_id": pid, "player": name, "team": team, "position": pos,
               "group": POSITION_GROUPS.get(pos), "competitions": ", ".join(sorted(comps[pid]))}
        row.update(c)
        rows.append(row)

    df = pd.DataFrame(rows).fillna(0)
    df = df[df["minutes"] >= min_minutes].copy()

    # --- métricas por 90 e taxas ---
    p90 = df["minutes"] / 90
    per90_cols = ["np_goals", "np_xg", "np_shots", "assists", "xa", "key_passes",
                  "prog_passes", "prog_carries", "passes_final_third", "passes_into_box",
                  "carries_into_box", "crosses_completed", "dribbles_completed",
                  "touches_box", "tackles_won", "interceptions", "pressures",
                  "pressures_att_third", "recoveries", "clearances", "turnovers", "passes"]
    for col in per90_cols:
        df[f"{col}_p90"] = df[col] / p90
    df["pass_pct"] = df["passes_completed"] / df["passes"].where(df["passes"] > 0)
    df["dribble_pct"] = df["dribbles_completed"] / df["dribbles"].where(df["dribbles"] > 0)
    df["np_xg_per_shot"] = df["np_xg"] / df["np_shots"].where(df["np_shots"] > 0)
    df[["pass_pct", "dribble_pct", "np_xg_per_shot"]] = df[["pass_pct", "dribble_pct", "np_xg_per_shot"]].fillna(0)
    df["minutes"] = df["minutes"].round(0).astype(int)
    return df.sort_values("minutes", ascending=False).reset_index(drop=True)


if __name__ == "__main__":
    from pathlib import Path
    out = Path(__file__).resolve().parents[1] / "data" / "processed" / "player_stats.csv"
    table = build_player_table()
    table.round(4).to_csv(out, index=False)
    print(f"{len(table)} jogadores salvos em {out}")
