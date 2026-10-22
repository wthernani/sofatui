"""Comprehensive unit, rendering, and live SofaScore integration tests for SofaTUI."""

from __future__ import annotations

from pathlib import Path
from rich.console import Console

from sofatui.api import SofaScoreClient, resolve_a_fast
from sofatui.favorites import FavoritesStore
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
    StatGroup,
    StatItem,
    TeamLineup,
)
from sofatui.renderers import (
    format_rating_badge,
    render_commentary_tab,
    render_lineups_tab,
    render_momentum_graph,
    render_overview_tab,
    render_scoreboard_banner,
    render_standings_tab,
    render_statistics_tab,
)


def _render_to_str(renderable) -> str:
    console = Console(width=110, force_terminal=False, color_system=None)
    with console.capture() as cap:
        console.print(renderable)
    return cap.get()


def test_fast_dns_resolver() -> None:
    ip = resolve_a_fast("www.sofascore.com")
    parts = ip.split(".")
    assert len(parts) == 4
    assert all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)


def test_favorites_persistence(tmp_path: Path) -> None:
    fav_file = tmp_path / "favorites.json"
    store = FavoritesStore(path=fav_file)
    assert not store.is_match_starred(12345)
    assert store.toggle_match(12345) is True
    assert store.is_match_starred(12345)

    reloaded = FavoritesStore(path=fav_file)
    assert reloaded.is_match_starred(12345)
    assert reloaded.toggle_match(12345) is False
    assert not reloaded.is_match_starred(12345)


def test_all_renderers_produce_rich_output() -> None:
    ev = MatchEvent.from_dict(
        {
            "id": 999,
            "slug": "arsenal-real-madrid",
            "startTimestamp": 1760980000,
            "status": {"code": 100, "description": "Ended", "type": "finished"},
            "homeTeam": {"id": 42, "name": "Arsenal", "shortName": "Arsenal", "nameCode": "ARS"},
            "awayTeam": {"id": 2829, "name": "Real Madrid", "shortName": "Real Madrid", "nameCode": "RMA"},
            "homeScore": {"current": 2, "display": 2, "period1": 1},
            "awayScore": {"current": 1, "display": 1, "period1": 0},
            "tournament": {
                "id": 7,
                "name": "UEFA Champions League",
                "uniqueTournament": {"id": 7, "name": "UEFA Champions League"},
                "category": {"id": 1465, "name": "Europe"},
            },
            "season": {"id": 76953},
            "roundInfo": {"round": 3},
            "venue": {"stadium": {"name": "Emirates Stadium"}, "city": {"name": "London"}},
            "referee": {"name": "Clement Turpin"},
            "attendance": 60383,
            "winnerCode": 1,
        }
    )

    incidents = [
        IncidentItem(
            incident_type="goal",
            incident_class="regular",
            time=80,
            is_home=True,
            player_name="Bukayo Saka",
            player_short="B. Saka",
            assist_name="D. Rice",
            home_score=2,
            away_score=1,
            xg=0.42,
        ),
        IncidentItem(
            incident_type="period",
            incident_class="regular",
            time=45,
            text="HT",
            home_score=1,
            away_score=0,
        ),
    ]

    stats = [
        PeriodStats(
            period="ALL",
            groups=[
                StatGroup(
                    group_name="Match overview",
                    items=[
                        StatItem("ballPossession", "Ball possession", "58%", "42%", 58, 42, 1),
                        StatItem("expectedGoals", "Expected goals", "2.14", "0.89", 2.14, 0.89, 1),
                    ],
                )
            ],
        )
    ]

    players_home = [
        PlayerLineup(
            id=i,
            name=f"HomePlayer{i}",
            short_name=f"H. Player{i}",
            shirt_number=str(i),
            position="G" if i == 1 else "M",
            substitute=False,
            captain=(i == 8),
            rating=7.0 + (i * 0.15),
            minutes_played=90,
            goals=1 if i == 7 else 0,
            assists=1 if i == 8 else 0,
            stats={"accuratePass": 45, "totalPass": 50, "touches": 64, "keyPass": 3},
        )
        for i in range(1, 12)
    ]
    players_away = [
        PlayerLineup(
            id=100 + i,
            name=f"AwayPlayer{i}",
            short_name=f"A. Player{i}",
            shirt_number=str(i),
            position="G" if i == 1 else "F",
            substitute=False,
            captain=(i == 10),
            rating=6.5 + (i * 0.1),
            minutes_played=90,
            goals=1 if i == 9 else 0,
            assists=0,
            stats={"accuratePass": 30, "totalPass": 38, "touches": 48},
        )
        for i in range(1, 12)
    ]
    lineups = MatchLineups(
        confirmed=True,
        home=TeamLineup(formation="4-3-3", players=players_home),
        away=TeamLineup(formation="4-2-3-1", players=players_away),
    )

    momentum = [MomentumPoint(minute=m, value=(40.0 if m % 2 == 0 else -35.0)) for m in range(1, 91)]
    comments = [
        CommentItem(id=1, type="goal", text="Goal! Arsenal 2, Real Madrid 1. Bukayo Saka scores!", time=80),
        CommentItem(id=2, type="corner", text="Corner, Arsenal.", time=42),
    ]
    standings = [
        StandingRow(1, 42, "Arsenal", "Arsenal", 3, 3, 0, 0, 8, 2, "+6", 9, "Champions League"),
        StandingRow(2, 2829, "Real Madrid", "Real Madrid", 3, 2, 0, 1, 6, 3, "+3", 6, "Champions League"),
    ]
    bundle = FullMatchBundle(
        event=ev,
        incidents=incidents,
        statistics=stats,
        comments=comments,
        lineups=lineups,
        momentum=momentum,
        standings=standings,
        standings_name="UEFA Champions League",
        h2h=H2HInfo(home_wins=2, draws=1, away_wins=0, home_form=["W", "W", "D", "W", "W"], away_form=["W", "L", "W", "W", "D"]),
    )

    sb_txt = _render_to_str(render_scoreboard_banner(bundle, is_starred=True))
    assert "Arsenal" in sb_txt and "Real Madrid" in sb_txt
    assert "2  -  1" in sb_txt
    assert "xG: 2.14" in sb_txt

    ov_txt = _render_to_str(render_overview_tab(bundle))
    assert "SofaScore Attack Momentum" in ov_txt
    assert "Bukayo Saka" in ov_txt

    st_txt = _render_to_str(render_statistics_tab(bundle, period="ALL"))
    assert "Ball possession" in st_txt
    assert "58%" in st_txt

    lu_txt = _render_to_str(render_lineups_tab(bundle, selected_player_idx=6))
    assert "SofaScore Tactical Pitch" in lu_txt
    assert "Player Performance Inspector" in lu_txt

    cm_txt = _render_to_str(render_commentary_tab(bundle, key_only=True))
    assert "GOAL" in cm_txt
    assert "Corner" not in cm_txt

    tb_txt = _render_to_str(render_standings_tab(bundle))
    assert "HOME" in tb_txt and "AWAY" in tb_txt

    # Upcoming match with pre-match avgRating must NOT mark any player as Player of the Match
    upcoming_ev = MatchEvent.from_dict(
        {
            "id": 1000,
            "slug": "bournemouth-ac-milan",
            "startTimestamp": 1792695600,
            "status": {"code": 0, "description": "Not started", "type": "notstarted"},
            "homeTeam": {"id": 60, "name": "Bournemouth", "shortName": "Bournemouth", "nameCode": "BOU"},
            "awayTeam": {"id": 2692, "name": "AC Milan", "shortName": "Milan", "nameCode": "ACM"},
            "tournament": {"id": 679, "name": "UEFA Europa League", "category": {"name": "Europe"}},
        }
    )
    cisse = PlayerLineup.from_dict(
        {
            "player": {
                "id": 70,
                "name": "Alphadjo Cisse",
                "shortName": "A. Cisse",
                "country": {"alpha2": "IT", "alpha3": "ITA", "name": "Italy"},
            },
            "shirtNumber": 70,
            "position": "F",
            "substitute": False,
            "avgRating": 8.0,
            "statistics": {},
        }
    )
    assert cisse.rating == 8.0
    assert cisse.country_display == "ITA • Italy"
    assert cisse.stats.get("isAvgRating") is True
    upcoming_bundle = FullMatchBundle(
        event=upcoming_ev,
        lineups=MatchLineups(
            confirmed=False,
            home=TeamLineup(formation="4-2-3-1", players=players_home),
            away=TeamLineup(formation="3-4-2-1", players=[cisse]),
        ),
    )
    upcoming_lu_txt = _render_to_str(render_lineups_tab(upcoming_bundle, selected_player_idx=len(players_home)))
    assert "Player of the Match" not in upcoming_lu_txt
    assert "8.0★" not in upcoming_lu_txt
    assert "[ITA • Italy]" in upcoming_lu_txt
    assert "8.0" in upcoming_lu_txt


def test_live_sofascore_client_integration() -> None:
    client = SofaScoreClient()
    # Test PSG vs Barcelona (401915399) and cross-provider failover
    bundle = client.get_full_match_bundle(401915399)
    assert bundle is not None
    assert "Paris" in bundle.event.home_team.name
    assert "Barcelona" in bundle.event.away_team.name
    assert len(bundle.incidents) > 0
    assert len(bundle.statistics) >= 1
    assert bundle.lineups is not None
    assert len(bundle.lineups.home.starters) == 11
    assert len(bundle.momentum) >= 50
    assert len(bundle.standings) >= 10


def test_rich_metadata_crests_legs_referee_and_stoppage_time() -> None:
    from sofatui.renderers import render_club_crest, resolve_match_kit_colors

    client = SofaScoreClient()
    # 1. FC Porto vs PSV (Champions League League Stage)
    b1 = client.get_full_match_bundle(401915398)
    assert b1 is not None
    assert b1.event.home_team.country_code == "POR"
    assert b1.event.away_team.country_code == "NED"
    assert b1.event.referee_name != ""
    assert b1.event.referee_country not in ("", "POR", "NED")
    assert b1.event.injury_time_1 > 0 or b1.event.injury_time_2 > 0

    crest_txt = _render_to_str(render_club_crest(b1.event.home_team))
    assert "▀" in crest_txt or "█" in crest_txt

    h_col, a_col = resolve_match_kit_colors(b1.event.home_team, b1.event.away_team)
    assert h_col.startswith("#") and a_col.startswith("#")
    assert h_col != a_col

    sb1 = _render_to_str(render_scoreboard_banner(b1))
    assert "POR • Portugal" in sb1
    assert "NED • Netherlands" in sb1
    assert f"({b1.event.referee_country})" in sb1

    ov1 = _render_to_str(render_overview_tab(b1))
    assert "Additional Time" in ov1
    assert "stoppage time" in ov1
    assert "✚ INJ" in ov1
    assert "✚▼ OUT: Filip" in ov1
    assert "(Injured)" in ov1

    lu1 = _render_to_str(render_lineups_tab(b1))
    assert "✚▼88' (Inj)" in lu1
    assert "✚▼" in lu1

    cm1 = _render_to_str(render_commentary_tab(b1))
    assert "✚ INJURY SUB" in cm1
    assert "✚ INJURY" in cm1

    # 2. Vasco da Gama vs Boca Juniors (CONMEBOL Sudamericana Semifinals 2nd Leg)
    b2 = client.get_full_match_bundle(401913957)
    assert b2 is not None
    assert b2.event.leg_info == "2nd Leg"
    assert b2.event.home_score.aggregated == 2
    assert b2.event.away_score.aggregated == 3
    assert "1st Leg: 1 - 0" in b2.event.prev_leg_score

    sb2 = _render_to_str(render_scoreboard_banner(b2))
    assert "Semifinals" in sb2
    assert "2nd Leg" in sb2
    assert "AGG: 2 - 3" in sb2
    assert "1st Leg: 1 - 0" in sb2
    assert "BRA • Brazil" in sb2
    assert "ARG • Argentina" in sb2


def test_textual_tui_headless_navigation_and_refresh() -> None:
    import asyncio
    import datetime
    from sofatui.app import SofaTuiApp
    from sofatui.models import sanitize_hex_color

    assert sanitize_hex_color("#7755kk", "#ffffff") == "#ffffff"
    assert sanitize_hex_color("7755kk", "#ffffff") == "#ffffff"
    assert sanitize_hex_color("8A8D8F", "#ffffff") == "#8a8d8f"

    async def _run() -> None:
        app = SofaTuiApp(
            initial_date=datetime.date(2026, 10, 21),
        )
        async with app.run_test(size=(237, 65)) as pilot:
            for _ in range(25):
                if len(app._all_matches) > 0:
                    break
                await pilot.pause(0.25)
            assert len(app._all_matches) > 0
            # Press 'h' (previous day 2026-10-20), 'v' (live filter -> 0 matches), 'a' (all), and cycle tabs
            await pilot.press("h")
            await pilot.pause(0.5)
            await pilot.press("v")
            await pilot.pause(0.2)
            assert len(app._displayed_matches) == sum(1 for m in app._all_matches if m.is_live)
            await pilot.press("a")
            await pilot.pause(0.2)
            assert len(app._displayed_matches) == len(app._all_matches)
            for key in ("3", "r", "2", "p", "3", "n", "4", "k", "5", "r", "1"):
                await pilot.press(key)
                await pilot.pause(0.25)

            # Test mouse clicks on all 5 Match Center tabs (#tabs-bar)
            tabs_widget = app.query_one("#tabs-bar")
            pad_left = max(0, (tabs_widget.size.width - app._tabs_bar_cell_len) // 2)
            for start, end, idx in list(app._tab_hit_ranges):
                click_x = pad_left + (start + end) // 2
                await pilot.click("#tabs-bar", offset=(click_x, 0))
                await pilot.pause(0.1)
                assert app.active_tab == idx

            # Also test clicking row 1 (border line) of #tabs-bar and #filter-strip
            s2, e2, _ = app._tab_hit_ranges[1]
            await pilot.click("#tabs-bar", offset=(pad_left + (s2 + e2) // 2, 1))
            await pilot.pause(0.1)
            assert app.active_tab == 2

            fs_widget = app.query_one("#filter-strip")
            fs_line = "".join(seg.text for seg in fs_widget.render_line(0))
            assert "[s]★" in fs_line

            fs_start, fs_end, _ = app._filter_hit_ranges[2]  # finished
            await pilot.click("#filter-strip", offset=(1 + (fs_start + fs_end) // 2, 0))
            await pilot.pause(0.1)
            assert app.active_filter == "finished"

            fa_start, fa_end, _ = app._filter_hit_ranges[0]  # all
            await pilot.click("#filter-strip", offset=(1 + (fa_start + fa_end) // 2, 0))
            await pilot.pause(0.1)
            assert app.active_filter == "all"

            await pilot.pause(0.5)
            assert len(app._all_matches) > 0
            assert app._current_bundle is not None

    asyncio.run(_run())

