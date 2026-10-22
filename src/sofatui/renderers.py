"""Rich terminal renderers for SofaTUI: Scoreboard, Attack Momentum, Timeline, Stats, Tactical Pitch, Lineups, Commentary, and Standings."""

from __future__ import annotations

import datetime
import time
from typing import Any

from rich.align import Align
from rich.columns import Columns
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from sofatui.models import (
    CommentItem,
    FullMatchBundle,
    H2HInfo,
    IncidentItem,
    MatchEvent,
    MatchLineups,
    MomentumPoint,
    PeriodStats,
    PlayerLineup,
    StandingRow,
    TeamInfo,
    TeamLineup,
)


def _normalize_hex(hex_str: str, default: str = "#38bdf8") -> str:
    s = (hex_str or "").strip().lstrip("#")
    if len(s) == 6:
        try:
            int(s, 16)
            return f"#{s.lower()}"
        except ValueError:
            pass
    return default


def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    h = _normalize_hex(hex_str).lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{max(0, min(255, r)):02x}{max(0, min(255, g)):02x}{max(0, min(255, b)):02x}"


def _ensure_dark_bg_contrast(hex_str: str, min_luma: float = 95.0) -> str:
    """Ensure a club jersey color is vivid and legible against the dark #0b0e14 TUI background."""
    r, g, b = _hex_to_rgb(hex_str)
    luma = 0.299 * r + 0.587 * g + 0.114 * b
    if luma >= min_luma:
        return _rgb_to_hex(r, g, b)
    # If near-black/achromatic dark, lift to crisp silver-blue
    if max(r, g, b) - min(r, g, b) < 18:
        return "#cbd5e1"
    # Scale RGB channels while preserving hue saturation
    peak = max(r, g, b, 1)
    scale = max(1.4, min(3.2, 215.0 / peak))
    nr = min(255, int(r * scale + 18))
    ng = min(255, int(g * scale + 18))
    nb = min(255, int(b * scale + 18))
    return _rgb_to_hex(nr, ng, nb)


def _color_distance(hex1: str, hex2: str) -> float:
    r1, g1, b1 = _hex_to_rgb(hex1)
    r2, g2, b2 = _hex_to_rgb(hex2)
    return ((r1 - r2) ** 2 * 0.30 + (g1 - g2) ** 2 * 0.59 + (b1 - b2) ** 2 * 0.11) ** 0.5


def resolve_match_kit_colors(home: TeamInfo, away: TeamInfo) -> tuple[str, str]:
    """Return (home_color, away_color) matching club jerseys with dark-theme contrast and clash resolution."""
    h_col = _ensure_dark_bg_contrast(home.color_primary, min_luma=95.0)
    a_col = _ensure_dark_bg_contrast(away.color_primary, min_luma=95.0)
    if _color_distance(h_col, a_col) < 62.0:
        # Away kit clash resolution: try away secondary color, then away trim color, then fallback
        alt_sec = _ensure_dark_bg_contrast(away.color_secondary, min_luma=105.0)
        if _color_distance(h_col, alt_sec) >= 62.0:
            a_col = alt_sec
        else:
            alt_trim = _ensure_dark_bg_contrast(away.color_trim, min_luma=105.0)
            if _color_distance(h_col, alt_trim) >= 62.0:
                a_col = alt_trim
            else:
                a_col = "#ffd166" if _color_distance(h_col, "#ffd166") >= 62.0 else "#38bdf8"
    return (h_col, a_col)


def render_club_crest(team: TeamInfo) -> Text:
    """Render a zero-overhead 3-row x 5-col (6x5 sub-pixel) heraldic shield in the club's authentic colors."""
    c1 = _ensure_dark_bg_contrast(team.color_primary, min_luma=70.0)
    c2 = _normalize_hex(team.color_secondary, "#ffffff")
    if _color_distance(c1, c2) < 35.0:
        c2 = "#ffffff" if _color_distance(c1, "#ffffff") > 60.0 else "#ffd166"
    c3 = _normalize_hex(team.color_trim, "#ffd166")
    pat = (team.crest_pattern or "stripes").lower()

    # 6x5 pointed heraldic shield mask
    mask = [
        [1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1],
        [0, 1, 1, 1, 0],
        [0, 0, 1, 0, 0],
    ]

    def _px_color(y: int, x: int) -> str | None:
        if not mask[y][x]:
            return None
        if pat == "stripes":
            if y == 0 and x in (1, 3):
                return c3
            return c1 if (x % 2 == 0) else c2
        if pat == "hoops":
            if y == 0 and x == 2:
                return c3
            return c1 if (y % 2 == 0) else c2
        if pat == "center_stripe":
            if x == 2:
                return c2
            if x in (1, 3):
                return c3 if y == 0 else c1
            return c1
        if pat == "sash":
            if y == 0 and x in (1, 2, 3):
                return c3
            if x == y - 1 or (y == 4 and x == 3):
                return c2
            return c1
        if pat == "halves":
            if y == 0:
                return c3
            if x < 2:
                return c1
            if x > 2:
                return c2
            return c3 if y in (1, 2) else c1
        if pat == "sleeves":
            if y == 0 and x == 2:
                return c3
            if x in (0, 4) and y in (1, 2, 3):
                return c2
            return c1
        # "emblem"
        if y == 0:
            return c3
        if (y in (2, 3) and x == 2) or (y == 2 and x in (1, 3)):
            return c2
        return c1

    crest = Text(no_wrap=True)
    for row in range(3):
        if row > 0:
            crest.append("\n")
        for col in range(5):
            top = _px_color(row * 2, col)
            bot = _px_color(row * 2 + 1, col)
            if top is None and bot is None:
                crest.append(" ")
            elif top is not None and bot is None:
                crest.append("▀", style=top)
            elif top is None and bot is not None:
                crest.append("▄", style=bot)
            elif top == bot:
                crest.append("█", style=top)
            else:
                crest.append("▀", style=f"{top} on {bot}")
    return crest


def rating_style(rating: float | None) -> str:
    """Return SofaScore-authentic badge style for a player/team rating."""
    if rating is None or rating <= 0:
        return "dim white on #2a2e39"
    if rating >= 9.0:
        return "bold #ffffff on #0284c7"  # SofaScore Electric Blue (9.0 - 10.0)
    if rating >= 8.0:
        return "bold #000000 on #00e676"  # SofaScore Bright Emerald (8.0 - 8.9)
    if rating >= 7.0:
        return "bold #000000 on #84cc16"  # SofaScore Lime Green (7.0 - 7.9)
    if rating >= 6.5:
        return "bold #000000 on #facc15"  # SofaScore Yellow/Amber (6.5 - 6.9)
    if rating >= 6.0:
        return "bold #000000 on #fb923c"  # SofaScore Orange (6.0 - 6.4)
    return "bold #ffffff on #e11d48"      # SofaScore Red (< 6.0)


def format_rating_badge(rating: float | None, is_motm: bool = False) -> Text:
    """Render a compact colored SofaScore rating pill."""
    if rating is None or rating <= 0:
        return Text(" -.- ", style="dim on #1e222d")
    star = "★" if is_motm else ""
    return Text(f" {rating:.1f}{star} ", style=rating_style(rating))


def format_form_badges(form: list[str]) -> Text:
    """Render W / D / L pregame form badges like SofaScore."""
    out = Text()
    if not form:
        out.append("No recent form", style="dim")
        return out
    for idx, ch in enumerate(form[:5]):
        if idx > 0:
            out.append(" ")
        u = ch.upper()
        if u == "W":
            out.append(" W ", style="bold #0b132b on #00e676")
        elif u == "D":
            out.append(" D ", style="bold #0b132b on #ffd166")
        elif u == "L":
            out.append(" L ", style="bold #ffffff on #ef476f")
        else:
            out.append(f" {u} ", style="bold white on #4a5568")
    return out


def _extract_xg(bundle: FullMatchBundle) -> tuple[str, str] | None:
    for p in bundle.statistics:
        if p.period == "ALL":
            for g in p.groups:
                for it in g.items:
                    if it.key == "expectedGoals" or "expected goals" in it.name.lower():
                        return (it.home_str, it.away_str)
    return None


def _coach_title(name: str) -> str:
    """Return 'Manager' exclusively for Ruben Amorim, and 'Coach' for everyone else."""
    n = (name or "").lower()
    if "amorim" in n and ("ruben" in n or "rúben" in n or n.strip() == "amorim"):
        return "Manager"
    return "Coach"


def render_scoreboard_banner(bundle: FullMatchBundle, is_starred: bool = False) -> Panel:
    """Render the top SofaScore match center scoreboard header."""
    ev = bundle.event
    now_ts = time.time()
    clock_str = ev.live_minute_str(now_ts)
    h_kit_color, a_kit_color = resolve_match_kit_colors(ev.home_team, ev.away_team)

    # Top tournament line with competition, round, and leg
    dt_str = datetime.datetime.fromtimestamp(ev.start_timestamp).strftime("%a %d %b %Y • %H:%M")
    star_icon = "★ PINNED  " if is_starred else ""
    header_line = Text()
    if star_icon:
        header_line.append(star_icon, style="bold #ffd166")
    header_line.append(f"🏆 {ev.tournament.category_name} • {ev.tournament.name}", style="bold #38bdf8")
    if ev.tournament.round_info:
        header_line.append(f"  •  {ev.tournament.round_info}", style="bold #ffd166")
    if ev.leg_info:
        header_line.append("  ")
        header_line.append(f" {ev.leg_info} ", style="bold #0b132b on #38bdf8")
    header_line.append(f"   •   {dt_str}", style="dim #94a3b8")

    # Main 3-column scoreboard grid
    grid = Table.grid(expand=True, padding=(0, 1))
    grid.add_column(justify="right", ratio=5)
    grid.add_column(justify="center", ratio=2)
    grid.add_column(justify="left", ratio=5)

    # Home team column: [Home Text (Name + Country + Formation), Low-Res Club Crest]
    home_txt = Text(justify="right", no_wrap=True)
    if ev.home_team.red_cards > 0:
        home_txt.append("■ " * ev.home_team.red_cards, style="bold #ff1744")
    home_style = "bold #ffffff" if ev.winner_code != 2 else "#cbd5e1"
    home_txt.append(ev.home_team.name, style=home_style)
    if ev.home_team.country_display:
        home_txt.append(f"\n{ev.home_team.country_display}", style=f"bold {h_kit_color}")
    meta_h: list[str] = []
    if bundle.lineups and bundle.lineups.home.formation:
        meta_h.append(f"[{bundle.lineups.home.formation}]")
    if ev.home_manager:
        meta_h.append(f"{_coach_title(ev.home_manager)}: {ev.home_manager}")
    if meta_h:
        home_txt.append(f"\n{' • '.join(meta_h)}", style="dim #94a3b8")

    home_sub = Table.grid(padding=(0, 1))
    home_sub.add_column(justify="right")
    home_sub.add_column(justify="center", width=5)
    home_sub.add_row(home_txt, render_club_crest(ev.home_team))

    # Center score & status column
    center_txt = Text(justify="center")
    h_sc = ev.home_score.display if ev.home_score.display is not None else ev.home_score.current
    a_sc = ev.away_score.display if ev.away_score.display is not None else ev.away_score.current

    if ev.is_upcoming and h_sc is None:
        center_txt.append("  vs  \n", style="bold #94a3b8")
        center_txt.append(f" ◆ {clock_str} ", style="bold #0b132b on #38bdf8")
    else:
        h_str = str(h_sc if h_sc is not None else 0)
        a_str = str(a_sc if a_sc is not None else 0)
        score_style = "bold #00e676" if ev.is_live else "bold #f8fafc"
        center_txt.append(f" {h_str}  -  {a_str} \n", style=score_style)
        if ev.is_live:
            live_lbl = " ● LIVE " if clock_str.upper() == "LIVE" else f" ● LIVE {clock_str} "
            center_txt.append(live_lbl, style="bold #ffffff on #e11d48")
        elif ev.is_finished:
            center_txt.append(f" {clock_str} ({ev.status_description}) ", style="bold #e2e8f0 on #334155")
        else:
            center_txt.append(f" {clock_str} ", style="bold #e2e8f0 on #334155")

        sub_scores: list[str] = []
        if ev.home_score.period1 is not None and ev.away_score.period1 is not None:
            sub_scores.append(f"HT {ev.home_score.period1}-{ev.away_score.period1}")
        if ev.home_score.penalties is not None and ev.away_score.penalties is not None:
            sub_scores.append(f"PEN {ev.home_score.penalties}-{ev.away_score.penalties}")
        if ev.injury_time_1 > 0 or ev.injury_time_2 > 0:
            it_parts: list[str] = []
            if ev.injury_time_1 > 0:
                it_parts.append(f"1H +{ev.injury_time_1}'")
            if ev.injury_time_2 > 0:
                it_parts.append(f"2H +{ev.injury_time_2}'")
            sub_scores.append(" / ".join(it_parts))
        if sub_scores:
            center_txt.append(f"\n({' • '.join(sub_scores)})", style="dim #94a3b8")

    # Aggregate & Past Leg Result display (for two-legged ties)
    if (
        (ev.home_score.aggregated is not None and ev.away_score.aggregated is not None)
        or ev.prev_leg_score
        or ev.series_note
    ):
        center_txt.append("\n")
        if ev.home_score.aggregated is not None and ev.away_score.aggregated is not None:
            center_txt.append(
                f" AGG: {ev.home_score.aggregated} - {ev.away_score.aggregated} ",
                style="bold #0b132b on #ffd166",
            )
            if ev.prev_leg_score:
                center_txt.append(f"  ({ev.prev_leg_score})", style="bold #cbd5e1")
        elif ev.prev_leg_score:
            center_txt.append(f" {ev.prev_leg_score} ", style="bold #cbd5e1 on #1e293b")
        if ev.series_note:
            center_txt.append(f"\n{ev.series_note}", style="italic #38bdf8")

    # Away team column: [Low-Res Club Crest, Away Text (Name + Country + Formation)]
    away_txt = Text(justify="left", no_wrap=True)
    away_style = "bold #ffffff" if ev.winner_code != 1 else "#cbd5e1"
    away_txt.append(ev.away_team.name, style=away_style)
    if ev.away_team.red_cards > 0:
        away_txt.append(" " + "■" * ev.away_team.red_cards, style="bold #ff1744")
    if ev.away_team.country_display:
        away_txt.append(f"\n{ev.away_team.country_display}", style=f"bold {a_kit_color}")
    meta_a: list[str] = []
    if bundle.lineups and bundle.lineups.away.formation:
        meta_a.append(f"[{bundle.lineups.away.formation}]")
    if ev.away_manager:
        meta_a.append(f"{_coach_title(ev.away_manager)}: {ev.away_manager}")
    if meta_a:
        away_txt.append(f"\n{' • '.join(meta_a)}", style="dim #94a3b8")

    away_sub = Table.grid(padding=(0, 1))
    away_sub.add_column(justify="center", width=5)
    away_sub.add_column(justify="left")
    away_sub.add_row(render_club_crest(ev.away_team), away_txt)

    grid.add_row(Align.right(home_sub), center_txt, Align.left(away_sub))

    # Goal scorers summary row under teams
    home_goals: list[str] = []
    away_goals: list[str] = []
    for inc in sorted(bundle.incidents, key=lambda x: (x.time, x.added_time)):
        if inc.incident_type == "goal":
            tag = ""
            if inc.incident_class == "penalty":
                tag = " (P)"
            elif inc.incident_class == "ownGoal":
                tag = " (OG)"
            assist = f" [{inc.assist_name}]" if inc.assist_name else ""
            entry = f"⚽ {inc.minute_label} {inc.player_short or inc.player_name}{tag}{assist}"
            if inc.is_home:
                home_goals.append(entry)
            else:
                away_goals.append(entry)

    xg_pair = _extract_xg(bundle)
    if home_goals or away_goals or xg_pair:
        xg_center = Text(justify="center")
        if xg_pair:
            xg_center.append(f"xG: {xg_pair[0]}  —  {xg_pair[1]}", style="bold #ffd166")
        grid.add_row(
            Text("\n".join(home_goals), style="#a7f3d0", justify="right"),
            xg_center,
            Text("\n".join(away_goals), style="#bae6fd", justify="left"),
        )

    # Metadata footer (stadium + country, referee + nationality, round/leg, attendance)
    meta_parts: list[str] = []
    if ev.venue_name:
        loc = f"{ev.venue_name}, {ev.venue_city}" if ev.venue_city else ev.venue_name
        if ev.venue_country and ev.venue_country.lower() not in loc.lower():
            loc = f"{loc} ({ev.venue_country})"
        meta_parts.append(f"◆ Venue: {loc}")
    if ev.referee_name:
        ref_str = (
            f"{ev.referee_name} ({ev.referee_country})"
            if ev.referee_country
            else ev.referee_name
        )
        meta_parts.append(f"⚖ Ref: {ref_str}")
    if ev.tournament.round_info:
        rnd_str = f"{ev.tournament.round_info} • {ev.leg_info}" if ev.leg_info else ev.tournament.round_info
        meta_parts.append(f"✦ Stage: {rnd_str}")
    if ev.attendance:
        meta_parts.append(f"★ Att: {ev.attendance:,}")

    elements: list[RenderableType] = [
        Align.center(header_line),
        Rule(style="#1e293b"),
        grid,
    ]
    if meta_parts:
        elements.append(Rule(style="#1e293b"))
        elements.append(Align.center(Text("   •   ".join(meta_parts), style="dim #94a3b8")))

    border_color = "#e11d48" if ev.is_live else "#3b82f6"
    return Panel(
        Group(*elements),
        border_style=border_color,
        padding=(0, 2),
    )


def render_momentum_graph(bundle: FullMatchBundle, width: int = 104) -> Panel:
    """Render SofaScore's signature Attack Momentum graph across the full panel width in club jersey colors."""
    pts = bundle.momentum
    ev = bundle.event
    if not pts:
        return Panel(
            Align.center(Text("Attack Momentum graph not available for this match.", style="dim #64748b")),
            title="[bold #38bdf8]⚡ SofaScore Attack Momentum[/]",
            border_style="#1e293b",
        )

    home_color, away_color = resolve_match_kit_colors(ev.home_team, ev.away_team)

    width = max(48, min(168, width))
    max_min = max(90, int(max((p.minute for p in pts), default=90)))
    raw_buckets: list[float] = []
    for col in range(width):
        m_start = 1.0 + (col / width) * max_min
        m_end = 1.0 + ((col + 1) / width) * max_min
        in_bucket = [p.value for p in pts if m_start <= p.minute <= m_end + 0.6]
        if not in_bucket:
            nearest = min(pts, key=lambda p: abs(p.minute - (m_start + m_end) / 2.0))
            val = nearest.value if abs(nearest.minute - (m_start + m_end) / 2.0) <= 2.5 else 0.0
        else:
            val = max(in_bucket, key=lambda v: abs(v))
        raw_buckets.append(val)

    peak = max(55.0, max((abs(v) for v in raw_buckets), default=80.0))
    bucket_vals = [(v / peak) * 98.0 for v in raw_buckets]

    # Map goal & red card minutes to columns
    home_markers: list[tuple[str, str]] = [(" ", "")] * width
    away_markers: list[tuple[str, str]] = [(" ", "")] * width
    for inc in bundle.incidents:
        if inc.time <= 0:
            continue
        col = min(width - 1, max(0, int(((inc.time - 1) / max(1, max_min)) * width)))
        if inc.incident_type == "goal":
            if inc.is_home:
                home_markers[col] = ("⚽", f"bold {home_color}")
            else:
                away_markers[col] = ("⚽", f"bold {away_color}")
        elif inc.incident_type == "card" and "red" in inc.incident_class.lower():
            if inc.is_home:
                home_markers[col] = ("■", "bold #ff1744")
            else:
                away_markers[col] = ("■", "bold #ff1744")

    up_blocks = " ▁▂▃▄▅▆▇█"
    ht_col = int((45.0 / max_min) * width)
    tick_cols = {
        int((m / max_min) * width): f"{m}'"
        for m in (15, 30, 45, 60, 75)
        if m < max_min
    }

    rows_text: list[RenderableType] = []

    # Home incident marker strip
    hm_line = Text(f" {ev.home_team.name_code:>4} │ ", style=f"bold {home_color}", no_wrap=True)
    skip_next = False
    for col, (ch, st) in enumerate(home_markers):
        if skip_next:
            skip_next = False
            continue
        if ch != " ":
            hm_line.append(ch, style=st)
            if ch == "⚽":
                skip_next = True
        elif col == ht_col:
            hm_line.append("┆", style="dim #334155")
        else:
            hm_line.append(" ")
    rows_text.append(Align.center(hm_line))

    # 4 tiers above axis (Home momentum: 0..100, 25 units per tier, colored in Home Jersey Color)
    for tier in (3, 2, 1, 0):
        label = "  ▲   │ " if tier == 1 else "      │ "
        line = Text(label, style="dim #64748b", no_wrap=True)
        for col, val in enumerate(bucket_vals):
            if val <= 0:
                line.append("┆" if col == ht_col else " ", style="dim #334155" if col == ht_col else "")
            else:
                norm = min(100.0, val) - tier * 25.0
                if norm <= 0:
                    line.append("┆" if col == ht_col else " ", style="dim #334155" if col == ht_col else "")
                elif norm >= 25.0:
                    line.append("█", style=f"bold {home_color}")
                else:
                    idx = max(1, min(8, int((norm / 25.0) * 8)))
                    line.append(up_blocks[idx], style=home_color)
        rows_text.append(Align.center(line))

    # Center timeline axis
    axis_line = Text("  0'  ┼─", style="dim #475569", no_wrap=True)
    for col in range(width):
        if col == ht_col:
            axis_line.append("┼", style="bold #ffd166")
        elif col in tick_cols:
            axis_line.append("┼", style="dim #94a3b8")
        else:
            axis_line.append("─", style="dim #475569")
    rows_text.append(Align.center(axis_line))

    # 4 tiers below axis (Away momentum: 0..-100, growing downward, colored in Away Jersey Color)
    for tier in (0, 1, 2, 3):
        label = "  ▼   │ " if tier == 1 else "      │ "
        line = Text(label, style="dim #64748b", no_wrap=True)
        for col, val in enumerate(bucket_vals):
            if val >= 0:
                line.append("┆" if col == ht_col else " ", style="dim #334155" if col == ht_col else "")
            else:
                abs_v = min(100.0, abs(val)) - tier * 25.0
                if abs_v <= 0:
                    line.append("┆" if col == ht_col else " ", style="dim #334155" if col == ht_col else "")
                elif abs_v >= 25.0:
                    line.append("█", style=f"bold {away_color}")
                elif abs_v >= 12.5:
                    line.append("▀", style=away_color)
                else:
                    line.append("▔", style=f"dim {away_color}")
        rows_text.append(Align.center(line))

    # Away incident marker strip
    am_line = Text(f" {ev.away_team.name_code:>4} │ ", style=f"bold {away_color}", no_wrap=True)
    skip_next = False
    for col, (ch, st) in enumerate(away_markers):
        if skip_next:
            skip_next = False
            continue
        if ch != " ":
            am_line.append(ch, style=st)
            if ch == "⚽":
                skip_next = True
        elif col == ht_col:
            am_line.append("┆", style="dim #334155")
        else:
            am_line.append(" ")
    rows_text.append(Align.center(am_line))

    # Full-width minute scale row aligned with ticks
    ht_lbl = f"HT 45+{ev.injury_time_1}'" if ev.injury_time_1 > 0 else "HT 45'"
    ft_lbl = f"FT 90+{ev.injury_time_2}'" if ev.injury_time_2 > 0 else f"FT {max_min}'"
    scale_chars = [" "] * (width + 8)
    anchors: list[tuple[int, str]] = [
        (8, "1'"),
        (8 + int((15.0 / max_min) * width) - 1, "15'"),
        (8 + int((30.0 / max_min) * width) - 1, "30'"),
        (8 + ht_col - len(ht_lbl) // 2, ht_lbl),
        (8 + int((60.0 / max_min) * width) - 1, "60'"),
        (8 + int((75.0 / max_min) * width) - 1, "75'"),
        (max(8, 8 + width - len(ft_lbl)), ft_lbl),
    ]
    for pos_idx, lbl in anchors:
        for i, ch in enumerate(lbl):
            if 0 <= pos_idx + i < len(scale_chars):
                scale_chars[pos_idx + i] = ch
    rows_text.append(Align.center(Text("".join(scale_chars), style="dim #94a3b8", no_wrap=True)))

    legend = Text()
    legend.append(f"■ {ev.home_team.short_name}", style=f"bold {home_color}")
    legend.append("     •     ", style="dim #64748b")
    legend.append(f"■ {ev.away_team.short_name}", style=f"bold {away_color}")

    return Panel(
        Group(Align.center(legend), *rows_text),
        title="[bold #38bdf8]⚡ SofaScore Attack Momentum[/]",
        border_style="#1e293b",
        padding=(0, 1),
    )


def _format_incident_cell(inc: IncidentItem) -> Text:
    txt = Text()
    it = inc.incident_type
    ic = inc.incident_class.lower()

    if it == "goal":
        tag = ""
        if ic == "penalty":
            tag = " (Penalty)"
        elif ic == "owngoal":
            tag = " (Own Goal)"
        score_pill = f" [{inc.home_score} - {inc.away_score}]" if inc.home_score is not None else ""
        txt.append(f"⚽ GOAL!{score_pill} ", style="bold #00e676")
        txt.append(inc.player_name or inc.player_short, style="bold #ffffff")
        if tag:
            txt.append(tag, style="bold #ffd166")
        if inc.assist_name:
            txt.append(f" (Assist: {inc.assist_name})", style="dim #94a3b8")
        if inc.xg is not None:
            txt.append(f" [xG {inc.xg:.2f}]", style="italic #38bdf8")
    elif it == "card":
        if "red" in ic:
            if ic == "red":
                txt.append("■ ", style="bold #ff1744")
            else:
                txt.append("■", style="bold #ffea00")
                txt.append("■ ", style="bold #ff1744")
        else:
            txt.append("■ ", style="bold #ffea00")
        txt.append(inc.player_name or inc.player_short or "Team Official", style="bold #e2e8f0")
        if inc.reason:
            txt.append(f" ({inc.reason})", style="dim #94a3b8")
    elif it == "substitution":
        if inc.is_injury_sub:
            txt.append(" ✚ INJ ", style="bold #ffffff on #e11d48")
            txt.append(" ▲ IN: ", style="bold #00e676")
            txt.append(inc.player_in_name or "Sub", style="bold #f8fafc")
            txt.append("  •  ", style="dim #64748b")
            txt.append("✚▼ OUT: ", style="bold #ff1744")
            txt.append(f"{inc.player_out_name or 'Player'} (Injured)", style="bold #fca5a5")
        else:
            txt.append("▲ IN: ", style="bold #00e676")
            txt.append(inc.player_in_name or "Sub", style="#f8fafc")
            txt.append("  •  ", style="dim #64748b")
            txt.append("▼ OUT: ", style="bold #f87171")
            txt.append(inc.player_out_name or "Player", style="dim #94a3b8")
    elif it == "varDecision":
        txt.append("⊞ VAR: ", style="bold #c084fc")
        txt.append(f"{inc.player_name} — {inc.text or inc.incident_class}", style="#e2e8f0")
    elif it == "inGamePenalty":
        txt.append("✖ Missed Penalty: ", style="bold #ff1744")
        txt.append(inc.player_name or inc.player_short, style="bold #f8fafc")
    else:
        txt.append(f"• {inc.text or inc.incident_type}", style="dim #94a3b8")
    return txt


def render_overview_tab(bundle: FullMatchBundle, width: int = 104) -> RenderableType:
    """Render Tab 1: Attack Momentum + Chronological Match Incidents + Form & H2H."""
    parts: list[RenderableType] = []
    ev = bundle.event

    # 1. Attack Momentum Graph (if present)
    if bundle.momentum:
        parts.append(render_momentum_graph(bundle, width=width))

    # 2. Match Timeline (Incidents)
    inc_table = Table(
        expand=True,
        box=None,
        show_header=True,
        header_style="bold #94a3b8",
        padding=(0, 1),
    )
    inc_table.add_column(ev.home_team.short_name, justify="right", ratio=5)
    inc_table.add_column("Min", justify="center", width=9, style="bold #ffd166")
    inc_table.add_column(ev.away_team.short_name, justify="left", ratio=5)

    # Sort incidents chronologically (SofaScore returns reverse-chronological)
    chron_incidents = list(reversed(bundle.incidents))
    has_p1_injury = any(i.incident_type == "injuryTime" and i.time <= 45 for i in chron_incidents)
    has_p2_injury = any(i.incident_type == "injuryTime" and i.time > 45 for i in chron_incidents)

    has_rows = False
    for inc in chron_incidents:
        if inc.incident_type == "period":
            p_label = inc.text or "HT"
            # Synthesize injuryTime row before HT/FT if event has injury_time_1/2 but no incident item
            if p_label == "HT" and not has_p1_injury and ev.injury_time_1 > 0:
                has_p1_injury = True
                inc_table.add_row(
                    Text("┄┄┄ Additional Time (1st Half) ┄┄┄", style="italic #ffd166"),
                    Text(f" +{ev.injury_time_1}' ", style="bold #0b132b on #ffd166"),
                    Text(f"┄┄┄ +{ev.injury_time_1} min stoppage time ┄┄┄", style="italic #ffd166"),
                )
            elif p_label == "FT" and not has_p2_injury and ev.injury_time_2 > 0:
                has_p2_injury = True
                inc_table.add_row(
                    Text("┄┄┄ Additional Time (2nd Half) ┄┄┄", style="italic #ffd166"),
                    Text(f" +{ev.injury_time_2}' ", style="bold #0b132b on #ffd166"),
                    Text(f"┄┄┄ +{ev.injury_time_2} min stoppage time ┄┄┄", style="italic #ffd166"),
                )

            added_n = inc.added_time or (ev.injury_time_1 if p_label == "HT" else (ev.injury_time_2 if p_label == "FT" else 0))
            p_tag = f"{p_label} ({inc.time}+{added_n}')" if added_n > 0 and inc.time > 0 else p_label
            score_str = f"{inc.home_score} - {inc.away_score}" if inc.home_score is not None else p_label
            inc_table.add_row(
                Text(f"────── {p_tag} ──────", style="dim #38bdf8"),
                Text(score_str, style="bold #38bdf8"),
                Text(f"────── {p_tag} ──────", style="dim #38bdf8"),
            )
            has_rows = True
            continue
        if inc.incident_type == "injuryTime":
            if inc.length > 0:
                half_lbl = "1st Half" if inc.time <= 45 else "2nd Half"
                inc_table.add_row(
                    Text(f"┄┄┄ Additional Time ({half_lbl}) ┄┄┄", style="italic #ffd166"),
                    Text(f" +{inc.length}' ", style="bold #0b132b on #ffd166"),
                    Text(f"┄┄┄ +{inc.length} min stoppage time ┄┄┄", style="italic #ffd166"),
                )
                has_rows = True
            continue

        cell = _format_incident_cell(inc)
        min_badge = Text(inc.minute_label, style="bold #ffd166")
        if inc.is_home is True:
            inc_table.add_row(cell, min_badge, Text(""))
        elif inc.is_home is False:
            inc_table.add_row(Text(""), min_badge, cell)
        else:
            inc_table.add_row(cell, min_badge, Text(""))
        has_rows = True

    if not has_rows:
        inc_panel = Panel(
            Align.center(Text("No match incidents recorded yet.", style="dim #64748b")),
            title="[bold #38bdf8]⚡ Match Timeline & Key Events[/]",
            border_style="#1e293b",
        )
    else:
        inc_panel = Panel(
            inc_table,
            title="[bold #38bdf8]⚡ Match Timeline & Key Events[/]",
            border_style="#1e293b",
            padding=(0, 1),
        )
    parts.append(inc_panel)

    # 3. Pre-match Form & H2H Summary Card
    h2h = bundle.h2h
    if h2h.home_form or h2h.away_form or (h2h.home_wins + h2h.draws + h2h.away_wins) > 0:
        f_grid = Table.grid(expand=True, padding=(0, 2))
        f_grid.add_column(justify="left", ratio=4)
        f_grid.add_column(justify="center", ratio=3)
        f_grid.add_column(justify="right", ratio=4)

        h_form_txt = Text()
        h_form_txt.append(f"{bundle.event.home_team.short_name} Form: ", style="bold #e2e8f0")
        h_form_txt.append_text(format_form_badges(h2h.home_form))
        if h2h.home_avg_rating:
            h_form_txt.append(f"  Avg: {h2h.home_avg_rating}", style="dim #94a3b8")

        a_form_txt = Text()
        if h2h.away_avg_rating:
            a_form_txt.append(f"Avg: {h2h.away_avg_rating}  ", style="dim #94a3b8")
        a_form_txt.append_text(format_form_badges(h2h.away_form))
        a_form_txt.append(f" :{bundle.event.away_team.short_name} Form", style="bold #e2e8f0")

        duel_txt = Text(justify="center")
        total_h2h = h2h.home_wins + h2h.draws + h2h.away_wins
        if total_h2h > 0:
            duel_txt.append(f"H2H ({total_h2h}): ", style="bold #94a3b8")
            duel_txt.append(f"{h2h.home_wins}W ", style="bold #00e676")
            duel_txt.append(f"• {h2h.draws}D • ", style="bold #ffd166")
            duel_txt.append(f"{h2h.away_wins}W", style="bold #38bdf8")

        f_grid.add_row(h_form_txt, duel_txt, a_form_txt)
        parts.append(
            Panel(
                f_grid,
                title="[bold #38bdf8]▤ Team Form & Head-to-Head[/]",
                border_style="#1e293b",
            )
        )

    return Group(*parts)


def render_statistics_tab(bundle: FullMatchBundle, period: str = "ALL", width: int = 92) -> RenderableType:
    """Render Tab 2: SofaScore Dual-Bar Match Statistics across ALL / 1ST / 2ND periods."""
    if not bundle.statistics:
        return Panel(
            Align.center(Text("Detailed statistics are not yet available for this match.", style="dim #64748b")),
            title="[bold #38bdf8]▤ Match Statistics[/]",
            border_style="#1e293b",
        )

    available_periods = [p.period for p in bundle.statistics]
    chosen_period = period if period in available_periods else available_periods[0]
    p_stats: PeriodStats = next(
        (p for p in bundle.statistics if p.period == chosen_period),
        bundle.statistics[0],
    )

    ev = bundle.event
    home_color, away_color = resolve_match_kit_colors(ev.home_team, ev.away_team)
    hr, hg, hb = _hex_to_rgb(home_color)
    ar, ag, ab = _hex_to_rgb(away_color)
    home_Sub_color = _rgb_to_hex(int(hr * 0.78), int(hg * 0.78), int(hb * 0.78))
    away_sub_color = _rgb_to_hex(int(ar * 0.78), int(ag * 0.78), int(ab * 0.78))

    # Period switcher bar
    p_bar = Text("Period [press 'p' or click to switch]: ", style="dim #94a3b8")
    for per in available_periods:
        span_start = len(p_bar)
        if per == chosen_period:
            p_bar.append(f" [{per}] ", style="bold #000000 on #00e676")
        else:
            p_bar.append(f"  {per}  ", style="bold #94a3b8 on #1e293b")
        p_bar.apply_meta({"period": per}, span_start, len(p_bar))
        p_bar.append(" ")

    panels: list[RenderableType] = [Align.center(p_bar)]
    bar_width = max(16, min(34, (width - 60) // 2))

    for grp in p_stats.groups:
        tbl = Table(expand=True, box=None, show_header=False, padding=(0, 1))
        tbl.add_column("HomeVal", justify="right", width=12)
        tbl.add_column("HomeBar", justify="right", width=bar_width)
        tbl.add_column("Metric", justify="center", ratio=1, min_width=24)
        tbl.add_column("AwayBar", justify="left", width=bar_width)
        tbl.add_column("AwayVal", justify="left", width=12)

        for item in grp.items:
            h_win = item.compare_code == 1
            a_win = item.compare_code == 2

            h_val_style = f"bold {home_color}" if h_win else "#e2e8f0"
            a_val_style = f"bold {away_color}" if a_win else "#e2e8f0"

            total = max(0.001, abs(item.home_val) + abs(item.away_val))
            h_ratio = min(1.0, max(0.0, abs(item.home_val) / total))
            a_ratio = min(1.0, max(0.0, abs(item.away_val) / total))

            h_fill = int(round(h_ratio * bar_width))
            a_fill = int(round(a_ratio * bar_width))

            h_bar = Text()
            h_bar.append("░" * (bar_width - h_fill), style="dim #1e293b")
            h_bar.append("█" * h_fill, style=home_color if h_win else home_Sub_color)

            a_bar = Text()
            a_bar.append("█" * a_fill, style=away_color if a_win else away_sub_color)
            a_bar.append("░" * (bar_width - a_fill), style="dim #1e293b")

            tbl.add_row(
                Text(item.home_str, style=h_val_style),
                h_bar,
                Text(item.name, style="bold #cbd5e1"),
                a_bar,
                Text(item.away_str, style=a_val_style),
            )

        panels.append(
            Panel(
                tbl,
                title=f"[bold #38bdf8]{grp.group_name}[/]",
                border_style="#1e293b",
                padding=(0, 1),
            )
        )

    return Group(*panels)


def _split_formation_rows(starters: list[PlayerLineup], formation: str) -> list[tuple[str, list[PlayerLineup]]]:
    """Arrange 11 starters into labeled tactical lines (GK + formation rows, e.g. 4-2-3-1)."""
    if not starters:
        return []

    # Ensure starters are sorted by tactical depth if not already
    pos_depth = {"G": 0.0, "D": 1.0, "M": 2.0, "F": 3.0}
    ordered = list(starters[:11])
    if any("_depth" in p.stats for p in ordered):
        ordered.sort(key=lambda p: float(p.stats.get("_depth", pos_depth.get(p.position, 2.0))))
    elif len(ordered) > 1:
        # Keep GK first, sort outfield by D -> M -> F if out of order
        gk_first = [p for p in ordered if p.position == "G"] or [ordered[0]]
        rest = [p for p in ordered if p.id != gk_first[0].id]
        ordered = [gk_first[0]] + rest

    gk = [ordered[0]]
    outfield = ordered[1:11]
    parts = [int(x) for x in formation.split("-") if x.strip().isdigit()]
    if not parts or sum(parts) != len(outfield):
        parts = [4, 3, 3] if len(outfield) == 10 else [len(outfield)]

    n_lines = len(parts)
    if n_lines == 3:
        labels = ["DEF", "MID", "FWD"]
    elif n_lines == 4:
        r2_lbl = "DM" if parts[1] <= 2 else "MID"
        r3_lbl = "AM" if parts[3] <= 2 else "MID"
        labels = ["DEF", r2_lbl, r3_lbl, "FWD"]
    else:
        labels = ["DEF"] + ["MID"] * max(0, n_lines - 2) + ["FWD"]

    rows: list[tuple[str, list[PlayerLineup]]] = [("GK", gk)]
    idx = 0
    for line_idx, count in enumerate(parts):
        r_slice = list(outfield[idx : idx + count])
        if any("_lat" in p.stats for p in r_slice):
            r_slice.sort(key=lambda p: float(p.stats.get("_lat", 0.0)))
        lbl = labels[line_idx] if line_idx < len(labels) else "MID"
        rows.append((lbl, r_slice))
        idx += count
    if idx < len(outfield):
        rows[-1][1].extend(outfield[idx:])
    return rows


def _format_pitch_player(p: PlayerLineup, motm_id: int, selected_id: int) -> Text:
    t = Text(justify="center")
    is_sel = p.id == selected_id
    role = str(p.stats.get("tacticalRole") or p.position or "")
    if is_sel:
        t.append("▶", style="bold #ffd166")
    if role:
        t.append(f"[{role}] ", style="dim #94a3b8")
    short = p.short_name[:13]
    name_style = "bold #ffd166" if is_sel else "bold #f8fafc"
    t.append(f"#{p.shirt_number} {short}", style=name_style)
    if p.captain:
        t.append(" (C)", style="bold #ffd166")
    if p.goals > 0:
        t.append(" " + "⚽" * min(3, p.goals), style="bold #00e676")
    if p.assists > 0:
        t.append(" ✦" * min(2, p.assists), style="bold #38bdf8")
    if p.red_cards > 0:
        t.append(" ■", style="bold #ff1744")
    elif p.yellow_cards > 0:
        t.append(" ■", style="bold #ffea00")
    if p.subbed_out is not None:
        if p.subbed_out_injured:
            t.append(" ✚▼", style="bold #ff1744")
        else:
            t.append(" ▼", style="bold #f87171")
    t.append(" ")
    t.append_text(format_rating_badge(p.rating, is_motm=(p.id == motm_id and (p.rating or 0) >= 7.0)))
    if p.id:
        t.apply_meta({"player_id": p.id}, 0, len(t))
    return t


def _build_pitch_row(
    line_label: str,
    r_players: list[PlayerLineup],
    side_color: str,
    motm_id: int,
    selected_player_id: int,
) -> Table:
    """Build one tactical line row with exact symmetric horizontal spacing across the pitch."""
    row_tbl = Table(box=None, expand=True, show_header=False, show_edge=False, padding=(0, 0))
    row_tbl.add_column(width=6, justify="left")
    n = len(r_players)
    cells: list[RenderableType] = [Text(f" {line_label:<3} │", style=f"bold {side_color}")]
    p_nodes = [_format_pitch_player(p, motm_id, selected_player_id) for p in r_players]

    if n == 1:
        row_tbl.add_column(ratio=1, justify="center")
        cells.append(Align.center(p_nodes[0]))
    elif n == 2:
        row_tbl.add_column(ratio=1)
        row_tbl.add_column(justify="center", ratio=3)
        row_tbl.add_column(justify="center", ratio=3)
        row_tbl.add_column(ratio=1)
        cells.extend([Text(""), Align.center(p_nodes[0]), Align.center(p_nodes[1]), Text("")])
    elif n == 3:
        row_tbl.add_column(ratio=1, justify="center")
        row_tbl.add_column(ratio=1, justify="center")
        row_tbl.add_column(ratio=1, justify="center")
        cells.extend([Align.center(p_nodes[0]), Align.center(p_nodes[1]), Align.center(p_nodes[2])])
    else:
        for p_node in p_nodes:
            row_tbl.add_column(justify="center", ratio=1)
            cells.append(Align.center(p_node))

    row_tbl.add_column(width=2, justify="right")
    cells.append(Text("│", style=f"dim {side_color}"))
    row_tbl.add_row(*cells)
    return row_tbl


def _build_pitch_marking_row(
    side_color: str,
    center_art: str,
    art_style: str = "#15803d",
    left_border: str = "     │",
    right_border: str = "│",
) -> Table:
    """Render a centered pitch geometry line (penalty box or center circle arc) aligned with the sidelines."""
    sp = Table(box=None, expand=True, show_header=False, show_edge=False, padding=(0, 0))
    sp.add_column(width=6, justify="left")
    sp.add_column(ratio=1, justify="center")
    sp.add_column(width=2, justify="right")
    sp.add_row(
        Text(left_border, style=f"dim {side_color}"),
        Align.center(Text(center_art, style=art_style)),
        Text(right_border, style=f"dim {side_color}"),
    )
    return sp


def _build_pitch_full_line(
    side_color: str,
    left_corner: str,
    right_corner: str,
    center_piece: str = "",
) -> Table:
    """Render a full-width horizontal pitch boundary or halfway line between the left and right touchlines."""
    sp = Table(box=None, expand=True, show_header=False, show_edge=False, padding=(0, 0))
    sp.add_column(width=6, justify="left")
    sp.add_column(ratio=1, justify="center")
    sp.add_column(width=2, justify="right")
    if center_piece:
        mid: RenderableType = Rule(title=f"[bold {side_color}]{center_piece}[/]", style=f"dim {side_color}", characters="─")
    else:
        mid = Rule(style=f"dim {side_color}", characters="─")
    sp.add_row(
        Text(f"     {left_corner}", style=f"dim {side_color}"),
        mid,
        Text(right_corner, style=f"dim {side_color}"),
    )
    return sp


def render_tactical_pitch(
    bundle: FullMatchBundle,
    motm_id: int = 0,
    selected_player_id: int = 0,
) -> Panel:
    """Render a 2D tactical football pitch with Home & Away formations and SofaScore ratings."""
    lu = bundle.lineups
    if not lu or (not lu.home.starters and not lu.away.starters):
        return Panel(
            Align.center(Text("Tactical lineups not available for this match.", style="dim #64748b")),
            title="[bold #00e676]⊞ Tactical Pitch & Formations[/]",
            border_style="#1e293b",
        )

    ev = bundle.event
    h_color, a_color = resolve_match_kit_colors(ev.home_team, ev.away_team)
    home_rows = _split_formation_rows(lu.home.starters, lu.home.formation)
    away_rows = [
        (lbl, list(reversed(r_players)))
        for lbl, r_players in reversed(_split_formation_rows(lu.away.starters, lu.away.formation))
    ]

    pitch_lines: list[RenderableType] = []

    # Home Team Header (outside the pitch boundary, zero text inside pitch lines)
    h_hdr = Text()
    h_hdr.append(f"■ {ev.home_team.name}", style=f"bold {h_color}")
    if lu.home.formation:
        h_hdr.append(f"  •  {lu.home.formation}", style="bold #cbd5e1")
    if lu.home.average_age is not None:
        h_hdr.append(f"  •  Avg Age: {lu.home.average_age:.1f} yrs", style="#94a3b8")
    if ev.home_manager:
        h_hdr.append(f"  •  {_coach_title(ev.home_manager)}: {ev.home_manager}", style="#94a3b8")
    pitch_lines.append(Align.center(h_hdr))

    # Top Goal Line (closed rectangle top border with goal mouth in center)
    pitch_lines.append(_build_pitch_full_line("#22c55e", "┌", "┐", "┬───────────┬"))

    for r_idx, (line_lbl, r_players) in enumerate(home_rows):
        pitch_lines.append(_build_pitch_row(line_lbl, r_players, "#22c55e", motm_id, selected_player_id))
        if r_idx == 0:
            pitch_lines.append(_build_pitch_marking_row("#22c55e", "└───────────────────────┘", "#15803d"))
        elif r_idx < len(home_rows) - 1:
            pitch_lines.append(_build_pitch_marking_row("#22c55e", " ", "#15803d"))

    # Halfway Line & Center Circle (connected to touchlines with ├ and ┤)
    pitch_lines.append(_build_pitch_marking_row("#22c55e", "╭───────╮", "#15803d"))
    pitch_lines.append(_build_pitch_full_line("#22c55e", "├", "┤", "◯"))
    pitch_lines.append(_build_pitch_marking_row("#22c55e", "╰───────╯", "#15803d"))

    for r_idx, (line_lbl, r_players) in enumerate(away_rows):
        if r_idx == len(away_rows) - 1 and len(away_rows) > 1:
            pitch_lines.append(_build_pitch_marking_row("#22c55e", "┌───────────────────────┐", "#15803d"))
        elif r_idx > 0:
            pitch_lines.append(_build_pitch_marking_row("#22c55e", " ", "#15803d"))
        pitch_lines.append(_build_pitch_row(line_lbl, r_players, "#22c55e", motm_id, selected_player_id))

    # Bottom Goal Line (closed rectangle bottom border with goal mouth in center)
    pitch_lines.append(_build_pitch_full_line("#22c55e", "└", "┘", "┴───────────┴"))

    # Away Team Header (outside the pitch boundary, zero text inside pitch lines)
    a_hdr = Text()
    a_hdr.append(f"■ {ev.away_team.name}", style=f"bold {a_color}")
    if lu.away.formation:
        a_hdr.append(f"  •  {lu.away.formation}", style="bold #cbd5e1")
    if lu.away.average_age is not None:
        a_hdr.append(f"  •  Avg Age: {lu.away.average_age:.1f} yrs", style="#94a3b8")
    if ev.away_manager:
        a_hdr.append(f"  •  {_coach_title(ev.away_manager)}: {ev.away_manager}", style="#94a3b8")
    pitch_lines.append(Align.center(a_hdr))

    status_tag = "Confirmed Lineups" if lu.confirmed else "Predicted / Preliminary Lineups"
    return Panel(
        Group(*pitch_lines),
        title=f"[bold #00e676]⊞ SofaScore Tactical Pitch ({status_tag})[/]",
        subtitle="[dim]Press 'n' / 'N' to inspect individual player match statistics[/]",
        border_style="#15803d",
        padding=(0, 1),
    )


def render_player_inspector(player: PlayerLineup | None, team_name: str, is_motm: bool = False) -> Panel:
    """Render deep-dive SofaScore individual player statistics card."""
    if not player:
        return Panel(
            Text("Select a player with 'n' / 'N' to view individual match statistics.", style="dim"),
            title="[bold #ffd166]★ Player Match Stats Inspector[/]",
            border_style="#1e293b",
        )

    st = player.stats
    role = str(st.get("tacticalRole") or player.position)
    hdr = Text()
    hdr.append(f"#{player.shirt_number} {player.name} ", style="bold #ffffff")
    if player.country_display:
        hdr.append(f"[{player.country_display}] ", style="bold #38bdf8")
    age_part = f" • Age {player.age}" if player.age else ""
    hdr.append(f"({role} • {team_name}{age_part})  ", style="#94a3b8")
    if player.captain:
        hdr.append("[C] ", style="bold #ffd166")
    hdr.append_text(format_rating_badge(player.rating, is_motm=is_motm))
    if is_motm:
        hdr.append("  🏆 Player of the Match", style="bold #ffd166")
    elif st.get("isAvgRating"):
        hdr.append("  (Season Avg)", style="dim #94a3b8")
    if player.subbed_out_injured:
        hdr.append("  ✚ Subbed off injured", style="bold #ff1744")

    stat_pairs: list[tuple[str, Any]] = [
        ("Minutes Played", f"{player.minutes_played}'"),
        ("Goals / Assists", f"{player.goals} / {player.assists}"),
        ("Expected Goals (xG)", f"{float(st['expectedGoals']):.2f}" if "expectedGoals" in st else "-"),
        ("Expected Assists (xA)", f"{float(st['expectedAssists']):.2f}" if "expectedAssists" in st else "-"),
        ("Shots (On Target)", f"{st.get('totalScoringAttempt', 0)} ({st.get('onTargetScoringAttempt', 0)})"),
        ("Touches", st.get("touches", "-")),
        ("Accurate Passes", f"{st.get('accuratePass', 0)}/{st.get('totalPass', 0)}"),
        ("Key Passes", st.get("keyPass", 0)),
        ("Crosses (Acc)", f"{st.get('totalCross', 0)} ({st.get('accurateCross', 0)})"),
        ("Long Balls (Acc)", f"{st.get('totalLongBalls', 0)} ({st.get('accurateLongBalls', 0)})"),
        ("Dribbles (Won)", f"{st.get('totalContest', 0)} ({st.get('wonContest', 0)})"),
        ("Ground Duels Won", f"{st.get('duelWon', 0)}/{ (st.get('duelWon', 0) or 0) + (st.get('duelLost', 0) or 0) }"),
        ("Tackles / Interceptions", f"{st.get('totalTackle', 0)} / {st.get('interceptionWon', 0)}"),
        ("Clearances / Blocks", f"{st.get('totalClearance', 0)} / {st.get('outfielderBlock', 0)}"),
        ("Fouls / Was Fouled", f"{st.get('fouls', 0)} / {st.get('wasFouled', 0)}"),
        ("Saves (GK)", st.get("saves", "-")),
    ]

    grid = Table.grid(expand=True, padding=(0, 2))
    for _ in range(4):
        grid.add_column(ratio=1)

    cells: list[Text] = []
    for label, val in stat_pairs:
        c = Text()
        c.append(f"{label}: ", style="dim #94a3b8")
        c.append(str(val), style="bold #f8fafc")
        cells.append(c)

    for i in range(0, len(cells), 4):
        row = cells[i : i + 4]
        while len(row) < 4:
            row.append(Text(""))
        grid.add_row(*row)

    return Panel(
        Group(hdr, Rule(style="#1e293b"), grid),
        title="[bold #ffd166]★ SofaScore Player Performance Inspector (n/N to cycle)[/]",
        border_style="#ffd166",
        padding=(0, 1),
    )


def _format_squad_row(p: PlayerLineup, motm_id: int, selected_id: int) -> Text:
    line = Text()
    if p.id == selected_id:
        line.append("▶ ", style="bold #ffd166")
    else:
        line.append("  ")
    line.append_text(format_rating_badge(p.rating, is_motm=(p.id == motm_id and (p.rating or 0) >= 7.0)))
    line.append(f" #{p.shirt_number:>2} ", style="dim #94a3b8")
    role = str(p.stats.get("tacticalRole") or p.position)
    line.append(f"({role:<3}) ", style="dim #64748b")
    name_style = "bold #ffd166" if p.id == selected_id else "bold #e2e8f0"
    line.append(p.short_name, style=name_style)
    if p.captain:
        line.append(" (C)", style="bold #ffd166")
    if p.goals > 0:
        line.append(" " + "⚽" * p.goals, style="bold #00e676")
    if p.assists > 0:
        line.append(f" ✦×{p.assists}" if p.assists > 1 else " ✦", style="bold #38bdf8")
    if p.red_cards > 0:
        line.append(" ■", style="bold #ff1744")
    elif p.yellow_cards > 0:
        line.append(" ■", style="bold #ffea00")
    if p.subbed_in is not None:
        line.append(f" ▲{p.subbed_in}'", style="bold #00e676")
    if p.subbed_out is not None:
        if p.subbed_out_injured:
            line.append(f" ✚▼{p.subbed_out}' (Inj)", style="bold #ff1744")
        else:
            line.append(f" ▼{p.subbed_out}'", style="bold #f87171")
    if p.id:
        line.apply_meta({"player_id": p.id}, 0, len(line))
    return line


def render_lineups_tab(bundle: FullMatchBundle, selected_player_idx: int = 0) -> RenderableType:
    """Render Tab 3: Tactical Pitch + Player Stats Inspector + Starting XI, Bench & Missing Players."""
    lu = bundle.lineups
    if not lu or (not lu.home.players and not lu.away.players):
        return Panel(
            Align.center(Text("Lineups and player ratings are not yet available.", style="dim #64748b")),
            title="[bold #38bdf8]⊞ Lineups & SofaScore Ratings[/]",
            border_style="#1e293b",
        )

    # Identify Player of the Match (only for live/finished matches with actual match ratings)
    all_players: list[tuple[PlayerLineup, str]] = [
        (p, bundle.event.home_team.short_name) for p in lu.home.players
    ] + [
        (p, bundle.event.away_team.short_name) for p in lu.away.players
    ]
    motm_id = 0
    if bundle.event.is_live or bundle.event.is_finished:
        motm_candidates = [
            p
            for p, _ in all_players
            if p.rating is not None
            and p.rating >= 7.0
            and not p.stats.get("isAvgRating")
            and p.minutes_played > 0
        ]
        if motm_candidates:
            motm_id = max(motm_candidates, key=lambda x: x.rating or 0.0).id

    sel_player: PlayerLineup | None = None
    sel_team = ""
    if all_players:
        idx = selected_player_idx % len(all_players)
        sel_player, sel_team = all_players[idx]
    sel_id = sel_player.id if sel_player else 0

    pitch_panel = render_tactical_pitch(bundle, motm_id=motm_id, selected_player_id=sel_id)
    inspector_panel = render_player_inspector(
        sel_player,
        sel_team,
        is_motm=(sel_id == motm_id and motm_id != 0),
    )

    # Side-by-side Starting XI & Substitutes table
    h_age_str = f" • Avg {lu.home.average_age:.1f}y" if lu.home.average_age is not None else ""
    a_age_str = f" • Avg {lu.away.average_age:.1f}y" if lu.away.average_age is not None else ""
    squad_tbl = Table(expand=True, box=None, show_header=True, header_style="bold #38bdf8", padding=(0, 1))
    squad_tbl.add_column(f"▶ [HOME] {bundle.event.home_team.name} ({lu.home.formation or 'XI'}{h_age_str})", justify="left", no_wrap=True)
    squad_tbl.add_column("", ratio=1)
    squad_tbl.add_column(f"▶ [AWAY] {bundle.event.away_team.name} ({lu.away.formation or 'XI'}{a_age_str})", justify="left", no_wrap=True)

    if bundle.event.home_manager or bundle.event.away_manager:
        hm_txt = Text()
        if bundle.event.home_manager:
            hm_txt.append(f"  ◆ {_coach_title(bundle.event.home_manager)}: ", style="bold #ffd166")
            hm_txt.append(f"{bundle.event.home_manager}\n", style="bold #f8fafc")
        am_txt = Text()
        if bundle.event.away_manager:
            am_txt.append(f"  ◆ {_coach_title(bundle.event.away_manager)}: ", style="bold #ffd166")
            am_txt.append(f"{bundle.event.away_manager}\n", style="bold #f8fafc")
        squad_tbl.add_row(hm_txt, Text(""), am_txt)

    h_starters = lu.home.starters
    a_starters = lu.away.starters
    for i in range(max(len(h_starters), len(a_starters))):
        h_cell = _format_squad_row(h_starters[i], motm_id, sel_id) if i < len(h_starters) else Text("")
        a_cell = _format_squad_row(a_starters[i], motm_id, sel_id) if i < len(a_starters) else Text("")
        squad_tbl.add_row(h_cell, Text(""), a_cell)

    # Bench / Substitutes section
    squad_tbl.add_row(
        Text("\n── Substitutes ──", style="bold #94a3b8"),
        Text(""),
        Text("\n── Substitutes ──", style="bold #94a3b8"),
    )
    h_subs = lu.home.substitutes
    a_subs = lu.away.substitutes
    for i in range(max(len(h_subs), len(a_subs))):
        h_cell = _format_squad_row(h_subs[i], motm_id, sel_id) if i < len(h_subs) else Text("")
        a_cell = _format_squad_row(a_subs[i], motm_id, sel_id) if i < len(a_subs) else Text("")
        squad_tbl.add_row(h_cell, Text(""), a_cell)

    # Missing / Injured players
    if lu.home.missing_players or lu.away.missing_players:
        squad_tbl.add_row(
            Text("\n── Missing / Injured ──", style="bold #f87171"),
            Text(""),
            Text("\n── Missing / Injured ──", style="bold #f87171"),
        )
        hm = lu.home.missing_players
        am = lu.away.missing_players
        for i in range(max(len(hm), len(am))):
            hc = Text(f"  ✖ {hm[i].short_name} ({hm[i].reason})", style="dim #fca5a5") if i < len(hm) else Text("")
            ac = Text(f"  ✖ {am[i].short_name} ({am[i].reason})", style="dim #fca5a5") if i < len(am) else Text("")
            squad_tbl.add_row(hc, Text(""), ac)

    squad_panel = Panel(
        squad_tbl,
        title="[bold #38bdf8]▤ Full Squads, Substitutions & SofaScore Player Ratings[/]",
        border_style="#1e293b",
    )

    return Group(pitch_panel, inspector_panel, squad_panel)


COMMENT_BADGE_MAP: dict[str, tuple[str, str]] = {
    "goal": ("⚽ GOAL!", "bold #0b132b on #00e676"),
    "scoreChange": ("⚽ GOAL!", "bold #0b132b on #00e676"),
    "ownGoal": ("⚽ OWN GOAL", "bold #ffffff on #ef4444"),
    "penaltyGoal": ("⚽ PENALTY", "bold #0b132b on #00e676"),
    "penaltyMissed": ("✖ PEN MISSED", "bold #ffffff on #ef4444"),
    "penaltySaved": ("◈ PEN SAVED", "bold #0b132b on #ffd166"),
    "yellowCard": ("■ YELLOW", "bold #0b132b on #ffea00"),
    "redCard": ("■ RED CARD", "bold #ffffff on #ff1744"),
    "yellowRedCard": ("■■ 2ND YELLOW", "bold #ffffff on #ff1744"),
    "substitution": ("▲▼ SUB", "bold #0b132b on #38bdf8"),
    "injurySubstitution": ("✚ INJURY SUB", "bold #ffffff on #e11d48"),
    "injuryDelay": ("✚ INJURY", "bold #fca5a5 on #450a0a"),
    "attemptSaved": ("◈ SAVED", "bold #ffffff on #0284c7"),
    "attemptMissed": ("◎ MISS", "dim #cbd5e1 on #334155"),
    "attemptBlocked": ("▬ BLOCKED", "dim #cbd5e1 on #334155"),
    "post": ("╬ POST!", "bold #0b132b on #f59e0b"),
    "corner": ("⚑ CORNER", "dim #94a3b8"),
    "offside": ("⚑ OFFSIDE", "dim #94a3b8"),
    "freeKickWon": ("⚡ FREE KICK", "dim #94a3b8"),
    "foul": ("! FOUL", "dim #94a3b8"),
    "varDecision": ("⊞ VAR", "bold #ffffff on #9333ea"),
    "matchEnded": ("★ FULL TIME", "bold #0b132b on #e2e8f0"),
    "periodEnd": ("• HALF END", "bold #0b132b on #cbd5e1"),
    "periodStart": ("▶ KICKOFF", "bold #0b132b on #38bdf8"),
}


def render_commentary_tab(bundle: FullMatchBundle, key_only: bool = False) -> RenderableType:
    """Render Tab 4: Live Play-by-Play Text Commentary with event badges."""
    comments = bundle.comments
    if not comments:
        return Panel(
            Align.center(Text("Live play-by-play text commentary is not available for this match.", style="dim #64748b")),
            title="[bold #38bdf8]» Live Match Commentary[/]",
            border_style="#1e293b",
        )

    key_types = {
        "goal", "scoreChange", "ownGoal", "penaltyGoal", "penaltyMissed", "penaltySaved",
        "yellowCard", "redCard", "yellowRedCard", "substitution", "injurySubstitution",
        "injuryDelay", "post", "attemptSaved", "varDecision", "matchEnded", "periodEnd",
    }

    filtered = [c for c in comments if (not key_only or c.type in key_types)]

    tbl = Table(expand=True, box=None, show_header=True, header_style="bold #94a3b8", padding=(0, 1))
    tbl.add_column("Min", justify="right", width=8, style="bold #ffd166")
    tbl.add_column("Event", justify="center", width=16)
    tbl.add_column("Play-by-Play Commentary", ratio=1)

    for c in filtered[:120]:
        label, badge_style = COMMENT_BADGE_MAP.get(c.type, ("» PLAY", "dim #94a3b8"))
        badge = Text(f" {label} ", style=badge_style)
        body_style = "bold #ffffff" if c.type in ("goal", "penaltyGoal", "redCard", "post", "injurySubstitution") else "#e2e8f0"
        body = Text(c.text, style=body_style)
        tbl.add_row(c.minute_label, badge, body)

    filter_label = "Key Highlights Only" if key_only else f"All Play-by-Play ({len(comments)} entries)"
    return Panel(
        tbl,
        title=f"[bold #38bdf8]» Live Play-by-Play Commentary — {filter_label}[/]",
        subtitle="[dim]Press 'k' to toggle Key Commentary Highlights vs All[/]",
        border_style="#1e293b",
    )


def render_standings_tab(bundle: FullMatchBundle) -> RenderableType:
    """Render Tab 5: Live Tournament Standings + Head-to-Head + Pre-Match Form."""
    parts: list[RenderableType] = []

    if bundle.standings:
        tbl = Table(
            expand=True,
            box=None,
            show_header=True,
            header_style="bold #38bdf8",
            padding=(0, 1),
        )
        tbl.add_column("#", justify="right", width=4)
        tbl.add_column("Club", ratio=4)
        tbl.add_column("P", justify="right", width=4)
        tbl.add_column("W", justify="right", width=4)
        tbl.add_column("D", justify="right", width=4)
        tbl.add_column("L", justify="right", width=4)
        tbl.add_column("Goals", justify="right", width=8)
        tbl.add_column("GD", justify="right", width=5)
        tbl.add_column("PTS", justify="right", width=5, style="bold #ffd166")
        tbl.add_column("Qualification / Zone", ratio=3)

        home_id = bundle.event.home_team.id
        away_id = bundle.event.away_team.id
        h_short = bundle.event.home_team.short_name.lower()
        a_short = bundle.event.away_team.short_name.lower()

        for r in bundle.standings:
            rn_lower = r.team_name.lower()
            is_home = (r.team_id == home_id and home_id != 0) or (len(h_short) >= 3 and h_short in rn_lower)
            is_away = (r.team_id == away_id and away_id != 0) or (len(a_short) >= 3 and a_short in rn_lower)
            row_style = ""
            marker = ""
            if is_home:
                row_style = "bold #00e676 on #0f291e"
                marker = " ◀ HOME"
            elif is_away:
                row_style = "bold #38bdf8 on #0c2438"
                marker = " ◀ AWAY"

            promo_lower = r.promotion_text.lower()
            pos_style = "bold #e2e8f0"
            if "champions league" in promo_lower or "promotion" in promo_lower or "playoff" in promo_lower:
                pos_style = "bold #00e676"
            elif "europa" in promo_lower or "conference" in promo_lower:
                pos_style = "bold #38bdf8"
            elif "relegation" in promo_lower:
                pos_style = "bold #ef4444"

            tbl.add_row(
                Text(str(r.position), style=pos_style),
                Text(f"{r.team_name}{marker}"),
                str(r.matches),
                str(r.wins),
                str(r.draws),
                str(r.losses),
                f"{r.scores_for}:{r.scores_against}",
                r.score_diff,
                str(r.points),
                Text(r.promotion_text, style="dim #94a3b8"),
                style=row_style,
            )

        parts.append(
            Panel(
                tbl,
                title=f"[bold #38bdf8]🏆 {bundle.standings_name or bundle.event.tournament.name} Standings[/]",
                border_style="#1e293b",
            )
        )
    else:
        parts.append(
            Panel(
                Align.center(Text("League standings not applicable or unavailable for this competition.", style="dim #64748b")),
                title="[bold #38bdf8]🏆 Standings[/]",
                border_style="#1e293b",
            )
        )

    # Head-to-Head & Pre-game Form Comparison
    h2h = bundle.h2h
    home_color, away_color = resolve_match_kit_colors(bundle.event.home_team, bundle.event.away_team)
    h2h_tbl = Table.grid(expand=True, padding=(0, 2))
    h2h_tbl.add_column(justify="center", ratio=1)
    h2h_tbl.add_column(justify="center", ratio=1)
    h2h_tbl.add_column(justify="center", ratio=1)

    h2h_tbl.add_row(
        Text(f"{bundle.event.home_team.name}\n{h2h.home_wins} Wins", style=f"bold {home_color}"),
        Text(f"Draws\n{h2h.draws}", style="bold #ffd166"),
        Text(f"{bundle.event.away_team.name}\n{h2h.away_wins} Wins", style=f"bold {away_color}"),
    )
    h2h_tbl.add_row(
        format_form_badges(h2h.home_form),
        Text("Recent Form", style="dim #94a3b8"),
        format_form_badges(h2h.away_form),
    )
    parts.append(
        Panel(
            h2h_tbl,
            title="[bold #38bdf8]⚔ Head-to-Head & Pre-Match Form[/]",
            border_style="#1e293b",
        )
    )

    return Group(*parts)
