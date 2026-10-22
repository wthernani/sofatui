"""ESPN Soccer API adapter for SofaTUI — provides 1-request global scoreboards and full match centers with zero WAF blocks."""

from __future__ import annotations

import datetime
import math
import re
import unicodedata
from typing import Any

from sofatui.models import (
    COUNTRY_ALPHA3_MAP,
    CommentItem,
    FullMatchBundle,
    H2HInfo,
    IncidentItem,
    MatchEvent,
    MatchLineups,
    MomentumPoint,
    PeriodStats,
    PlayerLineup,
    ScoreInfo,
    StandingRow,
    StatGroup,
    StatItem,
    TeamInfo,
    TeamLineup,
    TournamentInfo,
    enrich_team_identity,
    sanitize_hex_color,
)


# ESPN League ID (from uid 's:600~l:<id>~e:...') -> (Category Name, League Name, Priority)
ESPN_LEAGUE_CATALOG: dict[int, tuple[str, str, int]] = {
    # UEFA & FIFA International / Continental
    775: ("Europe", "UEFA Champions League", 10000),
    776: ("Europe", "UEFA Europa League", 9600),
    780: ("Europe", "UEFA Europa League", 9600),
    20296: ("Europe", "UEFA Conference League", 9400),
    2395: ("Europe", "UEFA Nations League", 9350),
    19483: ("Europe", "UEFA Women's Champions League", 8500),
    24079: ("Europe", "UEFA Women's Europa Cup", 8450),
    20649: ("Europe", "FIFA Women's World Cup Qualifying (UEFA)", 8200),
    # Top 5 + Major European Domestic Leagues
    700: ("England", "Premier League", 9200),
    740: ("Spain", "LaLiga", 9000),
    730: ("Italy", "Serie A", 8900),
    720: ("Germany", "Bundesliga", 8800),
    710: ("France", "Ligue 1", 8700),
    715: ("Portugal", "Liga Portugal Betclic", 8600),
    725: ("Netherlands", "Eredivisie", 8400),
    # CONMEBOL & Major Americas
    783: ("South America", "CONMEBOL Libertadores", 8350),
    5453: ("South America", "CONMEBOL Libertadores", 8350),
    5454: ("South America", "CONMEBOL Sudamericana", 8250),
    630: ("Brazil", "Brasileirão Série A", 8300),
    745: ("Argentina", "Liga Profesional", 8150),
    655: ("Argentina", "Liga Profesional", 8150),
    # Major Domestic Cups
    702: ("England", "FA Cup", 8100),
    23480: ("England", "FA Cup Qualifying", 6400),
    3920: ("England", "EFL Carabao Cup", 8050),
    704: ("England", "EFL Carabao Cup", 8050),
    18481: ("England", "EFL Trophy", 6650),
    742: ("Spain", "Copa del Rey", 8000),
    20381: ("Spain", "Copa de la Reina", 6950),
    732: ("Italy", "Coppa Italia", 7950),
    3954: ("Germany", "DFB-Pokal", 7900),
    722: ("Germany", "DFB-Pokal", 7900),
    20922: ("Portugal", "Taça de Portugal", 7880),
    3957: ("Netherlands", "KNVB Beker", 7850),
    20115: ("Netherlands", "KNVB Beker Vrouwen", 6300),
    3959: ("Scotland", "Scottish Cup", 7150),
    5331: ("Scotland", "SPFL Challenge Cup", 6250),
    8107: ("Argentina", "Copa Argentina", 7280),
    5337: ("USA", "U.S. Open Cup", 7100),
    # Other European 1st & 2nd Divisions
    3914: ("England", "Championship", 7800),
    3946: ("Turkey", "Trendyol Süper Lig", 7650),
    755: ("Turkey", "Trendyol Süper Lig", 7650),
    735: ("Scotland", "Premiership", 7600),
    3901: ("Belgium", "Pro League", 7580),
    3907: ("Austria", "Bundesliga", 7560),
    3955: ("Greece", "Super League", 7540),
    3913: ("Denmark", "Superliga", 7520),
    3960: ("Norway", "Eliteserien", 7480),
    3945: ("Sweden", "Allsvenskan", 7460),
    3939: ("Russia", "Premier League", 7420),
    3927: ("Germany", "2. Bundesliga", 7380),
    3921: ("Spain", "LaLiga 2", 7360),
    3931: ("Italy", "Serie B", 7340),
    3926: ("France", "Ligue 2", 7320),
    3933: ("Netherlands", "Keuken Kampioen Divisie", 7120),
    3940: ("Scotland", "Championship", 6900),
    3915: ("England", "League One", 6850),
    3916: ("England", "League Two", 6750),
    3917: ("England", "National League", 6600),
    # Middle East, Asia, Africa & Oceania
    21231: ("Saudi Arabia", "Saudi Pro League", 7500),
    3902: ("Asia", "AFC Champions League Elite", 7490),
    2466: ("Asia", "AFC Champions League Two", 7180),
    750: ("Japan", "J1 League", 7450),
    2391: ("Africa", "CAF Champions League", 7440),
    18000: ("Africa", "CAF Confederation Cup", 7160),
    8376: ("China", "Chinese Super League", 6980),
    3906: ("Australia", "A-League Men", 6960),
    3937: ("South Africa", "Premiership", 6920),
    8316: ("India", "Indian Super League", 6880),
    18505: ("India", "I-League", 6200),
    # Americas (North, Central & South)
    770: ("USA", "MLS", 7400),
    760: ("Mexico", "Liga MX", 7350),
    4007: ("Brazil", "Brasileirão Série B", 6700),
    650: ("Colombia", "Primera A", 6680),
    8313: ("Colombia", "Copa Colombia", 6480),
    640: ("Chile", "Primera División", 6660),
    8312: ("Chile", "Copa Chile", 6460),
    680: ("Uruguay", "Liga AUF Uruguaya", 6640),
    670: ("Peru", "Liga 1", 6620),
    660: ("Ecuador", "LigaPro", 6610),
    3934: ("Paraguay", "Primera División", 6580),
    3949: ("Venezuela", "Liga FUTVE", 6560),
    620: ("Bolivia", "Liga Profesional", 6540),
    23284: ("Bolivia", "Copa Bolivia", 6380),
    19267: ("CONCACAF", "Nations League", 7250),
    22947: ("CONCACAF", "Central American Cup", 6520),
    4005: ("Costa Rica", "Liga FPD", 6440),
    3928: ("Guatemala", "Liga Nacional", 6420),
    3929: ("Honduras", "Liga Nacional", 6410),
    3943: ("El Salvador", "Primera División", 6405),
    3932: ("Mexico", "Liga de Expansión MX", 6500),
    3903: ("Argentina", "Primera Nacional", 6490),
    3904: ("Argentina", "Primera B Metropolitana", 6150),
    4002: ("USA", "USL Championship", 6450),
    19915: ("USA", "USL League One", 6180),
    22059: ("USA", "USL Cup", 6170),
    # Women's & Youth / Collegiate / Friendlies
    8097: ("England", "Women's Super League", 7050),
    20226: ("England", "Women's FA Cup", 6360),
    23390: ("England", "WSL League Cup", 6350),
    8301: ("USA", "NWSL", 7040),
    23633: ("USA", "USL Super League", 6340),
    20956: ("Spain", "Liga F", 7020),
    20955: ("France", "Première Ligue", 7010),
    19945: ("Netherlands", "Vrouwen Eredivisie", 6330),
    23541: ("Mexico", "Liga MX Femenil", 6320),
    18992: ("Australia", "A-League Women", 6310),
    23286: ("Canada", "Northern Super League", 6305),
    24081: ("World", "FIFA Women's Champions Cup", 7080),
    20865: ("World", "FIFA U-17 Women's World Cup", 7060),
    3922: ("World", "International Friendly", 7200),
    3923: ("World", "Women's International Friendly", 6800),
    19834: ("World", "Club Friendly", 6100),
    5487: ("USA", "NCAA Men's Soccer", 5800),
    5499: ("USA", "NCAA Women's Soccer", 5750),
}

DEMONYM_TO_COUNTRY: dict[str, str] = {
    "English": "England",
    "Spanish": "Spain",
    "Italian": "Italy",
    "German": "Germany",
    "French": "France",
    "Portuguese": "Portugal",
    "Dutch": "Netherlands",
    "Brazilian": "Brazil",
    "Argentine": "Argentina",
    "Scottish": "Scotland",
    "Mexican": "Mexico",
    "Japanese": "Japan",
    "Turkish": "Turkey",
    "Belgian": "Belgium",
    "Austrian": "Austria",
    "Danish": "Denmark",
    "Swedish": "Sweden",
    "Norwegian": "Norway",
    "Greek": "Greece",
    "Russian": "Russia",
    "Chinese": "China",
    "Indian": "India",
    "Australian": "Australia",
    "Colombian": "Colombia",
    "Chilean": "Chile",
    "Peruvian": "Peru",
    "Paraguayan": "Paraguay",
    "Venezuelan": "Venezuela",
    "Bolivian": "Bolivia",
    "Uruguayan": "Uruguay",
    "Costa Rican": "Costa Rica",
    "Guatemalan": "Guatemala",
    "Honduran": "Honduras",
    "Salvadoran": "El Salvador",
    "South African": "South Africa",
}


def _parse_iso_timestamp(iso_str: str) -> int:
    if not iso_str:
        return int(datetime.datetime.now().timestamp())
    try:
        s = iso_str.replace("Z", "+00:00")
        return int(datetime.datetime.fromisoformat(s).timestamp())
    except Exception:
        return int(datetime.datetime.now().timestamp())


def _extract_league_id(uid: str) -> int:
    m = re.search(r"~l:(\d+)~", uid or "")
    return int(m.group(1)) if m else 0


def _parse_minute_str(clock_display: str) -> tuple[int, int]:
    """Parse '45'+2'' or '80'' into (minute, added_time)."""
    if not clock_display:
        return (0, 0)
    cleaned = clock_display.replace("'", "").strip()
    if "+" in cleaned:
        parts = cleaned.split("+", 1)
        try:
            return (int(parts[0]), int(parts[1]))
        except ValueError:
            return (0, 0)
    try:
        return (int(float(cleaned)), 0)
    except ValueError:
        return (0, 0)


# FIFA / UEFA / CONMEBOL / Domestic Elite Referees & Nationalities
COMPETITION_REFEREES: dict[str, list[tuple[str, str]]] = {
    "Europe": [
        ("Clément Turpin", "FRA"),
        ("Szymon Marciniak", "POL"),
        ("Daniele Orsato", "ITA"),
        ("Slavko Vinčić", "SVN"),
        ("François Letexier", "FRA"),
        ("István Kovács", "ROU"),
        ("Felix Zwayer", "GER"),
        ("Michael Oliver", "ENG"),
        ("Jesús Gil Manzano", "ESP"),
        ("Danny Makkelie", "NED"),
        ("Artur Soares Dias", "POR"),
        ("Glenn Nyberg", "SWE"),
    ],
    "South America": [
        ("Wilton Sampaio", "BRA"),
        ("Darío Herrera", "ARG"),
        ("Jesús Valenzuela", "VEN"),
        ("Andrés Matonte", "URU"),
        ("Facundo Tello", "ARG"),
        ("Raphael Claus", "BRA"),
        ("Piero Maza", "CHI"),
        ("Wilmar Roldán", "COL"),
    ],
    "England": [
        ("Michael Oliver", "ENG"),
        ("Anthony Taylor", "ENG"),
        ("Paul Tierney", "ENG"),
        ("Simon Hooper", "ENG"),
        ("Chris Kavanagh", "ENG"),
        ("John Brooks", "ENG"),
    ],
    "Spain": [
        ("Jesús Gil Manzano", "ESP"),
        ("José María Sánchez Martínez", "ESP"),
        ("Alejandro Hernández Hernández", "ESP"),
        ("César Soto Grado", "ESP"),
    ],
    "Italy": [
        ("Daniele Orsato", "ITA"),
        ("Marco Guida", "ITA"),
        ("Davide Massa", "ITA"),
        ("Maurizio Mariani", "ITA"),
    ],
    "Germany": [
        ("Felix Zwayer", "GER"),
        ("Daniel Siebert", "GER"),
        ("Tobias Stieler", "GER"),
        ("Sascha Stegemann", "GER"),
    ],
    "France": [
        ("Clément Turpin", "FRA"),
        ("François Letexier", "FRA"),
        ("Benoît Bastien", "FRA"),
    ],
    "Portugal": [
        ("Artur Soares Dias", "POR"),
        ("João Pinheiro", "POR"),
        ("Luís Godinho", "POR"),
    ],
    "Netherlands": [
        ("Danny Makkelie", "NED"),
        ("Serdar Gözübüyük", "NED"),
        ("Allard Lindhout", "NED"),
    ],
    "Brazil": [
        ("Wilton Sampaio", "BRA"),
        ("Raphael Claus", "BRA"),
        ("Anderson Daronco", "BRA"),
    ],
    "Argentina": [
        ("Facundo Tello", "ARG"),
        ("Darío Herrera", "ARG"),
        ("Yael Falcón Pérez", "ARG"),
    ],
}

KNOWN_REFEREE_COUNTRIES: dict[str, str] = {
    name.lower(): nat
    for pool in COMPETITION_REFEREES.values()
    for name, nat in pool
}


def _select_match_referee(
    eid: int,
    cat_name: str,
    home_country_code: str,
    away_country_code: str,
    raw_name: str = "",
    raw_country: str = "",
) -> tuple[str, str]:
    """Return (referee_name, referee_country_alpha3) strictly from official match data."""
    if not raw_name:
        return ("", "")
    nat = raw_country
    if not nat:
        nat = KNOWN_REFEREE_COUNTRIES.get(raw_name.lower().strip(), "")
    if not nat and cat_name not in ("Europe", "South America", "World", "International"):
        nat = COUNTRY_ALPHA3_MAP.get(cat_name.lower(), cat_name[:3].upper())
    elif nat and len(nat) > 3:
        nat = COUNTRY_ALPHA3_MAP.get(nat.lower(), nat[:3].upper())
    return (raw_name, nat or "INT")


def parse_espn_scoreboard_event(ev: dict[str, Any], league_override: tuple[str, str] | None = None) -> MatchEvent | None:
    comps = ev.get("competitions") or []
    if not comps:
        return None
    comp = comps[0]
    competitors = comp.get("competitors") or []
    if len(competitors) < 2:
        return None

    home_c = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
    away_c = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])

    ht_raw = home_c.get("team") or {}
    at_raw = away_c.get("team") or {}

    # Count red cards from details if present
    details = comp.get("details") or []
    home_tid = str(ht_raw.get("id") or home_c.get("id") or "0")
    away_tid = str(at_raw.get("id") or away_c.get("id") or "0")
    home_red = sum(1 for d in details if d.get("redCard") and str((d.get("team") or {}).get("id")) == home_tid)
    away_red = sum(1 for d in details if d.get("redCard") and str((d.get("team") or {}).get("id")) == away_tid)

    home_team = TeamInfo(
        id=int(home_tid) if home_tid.isdigit() else 0,
        name=str(ht_raw.get("displayName") or ht_raw.get("name") or "Home"),
        short_name=str(ht_raw.get("shortDisplayName") or ht_raw.get("name") or "Home"),
        name_code=str(ht_raw.get("abbreviation") or (ht_raw.get("name") or "HOM")[:3].upper()),
        color_primary=sanitize_hex_color(ht_raw.get("color"), "#374df5"),
        color_secondary=sanitize_hex_color(ht_raw.get("alternateColor"), "#ffffff"),
        red_cards=home_red,
    )
    away_team = TeamInfo(
        id=int(away_tid) if away_tid.isdigit() else 0,
        name=str(at_raw.get("displayName") or at_raw.get("name") or "Away"),
        short_name=str(at_raw.get("shortDisplayName") or at_raw.get("name") or "Away"),
        name_code=str(at_raw.get("abbreviation") or (at_raw.get("name") or "AWY")[:3].upper()),
        color_primary=sanitize_hex_color(at_raw.get("color"), "#38bdf8"),
        color_secondary=sanitize_hex_color(at_raw.get("alternateColor"), "#ffffff"),
        red_cards=away_red,
    )

    st_raw = comp.get("status") or ev.get("status") or {}
    st_type = st_raw.get("type") or {}
    state = str(st_type.get("state") or "pre").lower()
    if state == "in":
        status_type = "inprogress"
    elif state == "post":
        status_type = "finished"
    else:
        status_type = "notstarted"

    status_desc = str(st_type.get("shortDetail") or st_type.get("description") or "")

    # Scores & halftime score estimation from details
    def _to_int(v: Any) -> int | None:
        if isinstance(v, dict):
            v = v.get("value") if v.get("value") is not None else v.get("displayValue")
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return None

    h_cur = _to_int(home_c.get("score")) if status_type != "notstarted" else None
    a_cur = _to_int(away_c.get("score")) if status_type != "notstarted" else None

    h_ht: int | None = None
    a_ht: int | None = None
    p1_max_added = 0
    p2_max_added = 0
    cur_period = int(st_raw.get("period") or 1)
    reached_ht = (
        status_type == "finished"
        or cur_period >= 2
        or "ht" in status_desc.lower()
        or "half" in status_desc.lower()
    )
    if status_type in ("inprogress", "finished") and details:
        if reached_ht:
            h_ht = 0
            a_ht = 0
        for d in details:
            mn, added = _parse_minute_str(str((d.get("clock") or {}).get("displayValue") or ""))
            if mn == 45 and added > p1_max_added:
                p1_max_added = added
            elif mn == 90 and added > p2_max_added:
                p2_max_added = added
            if reached_ht and d.get("scoringPlay") and not d.get("shootout"):
                if 0 < mn <= 45:
                    if str((d.get("team") or {}).get("id")) == home_tid:
                        h_ht = (h_ht or 0) + 1
                    elif str((d.get("team") or {}).get("id")) == away_tid:
                        a_ht = (a_ht or 0) + 1

    h_pen = _to_int(home_c.get("shootoutScore"))
    a_pen = _to_int(away_c.get("shootoutScore"))

    # Parse 2-legged series, aggregate score, leg number, and past leg result
    series_raw_any = comp.get("series") or {}
    if isinstance(series_raw_any, list):
        series_raw: dict[str, Any] = next(
            (s for s in series_raw_any if isinstance(s, dict) and s.get("type") == "series"),
            series_raw_any[0] if series_raw_any and isinstance(series_raw_any[0], dict) else {},
        )
    elif isinstance(series_raw_any, dict):
        series_raw = series_raw_any
    else:
        series_raw = {}
    leg_raw = comp.get("leg") or {}
    notes_raw = comp.get("notes") or []

    leg_disp = str(leg_raw.get("displayValue") or "").strip()
    leg_val = _to_int(leg_raw.get("value")) or 0
    if not leg_disp and leg_val in (1, 2):
        leg_disp = "1st Leg" if leg_val == 1 else "2nd Leg"

    h_agg: int | None = _to_int(home_c.get("aggregateScore"))
    a_agg: int | None = _to_int(away_c.get("aggregateScore"))
    series_comps = series_raw.get("competitors") or []
    if (h_agg is None or a_agg is None) and len(series_comps) >= 2:
        for sc in series_comps:
            sc_id = str(sc.get("id") or (sc.get("team") or {}).get("id") or "")
            sc_agg = _to_int(sc.get("aggregateScore"))
            if sc_id == home_tid and sc_agg is not None:
                h_agg = sc_agg
            elif sc_id == away_tid and sc_agg is not None:
                a_agg = sc_agg

    series_note = ""
    if notes_raw and isinstance(notes_raw[0], dict):
        series_note = str(notes_raw[0].get("text") or notes_raw[0].get("headline") or "").strip()
        if not leg_disp:
            if "1st leg" in series_note.lower():
                leg_disp = "1st Leg"
                leg_val = 1
            elif "2nd leg" in series_note.lower():
                leg_disp = "2nd Leg"
                leg_val = 2

    prev_leg_score = ""
    if h_agg is not None and a_agg is not None:
        if not leg_disp:
            leg_disp = "2nd Leg"
            leg_val = 2
        if leg_val == 2 and h_cur is not None and a_cur is not None:
            prev_h = h_agg - h_cur
            prev_a = a_agg - a_cur
            if prev_h >= 0 and prev_a >= 0:
                prev_leg_score = f"1st Leg: {prev_h} - {prev_a}"

    home_score = ScoreInfo(current=h_cur, display=h_cur, period1=h_ht, penalties=h_pen, aggregated=h_agg)
    away_score = ScoreInfo(current=a_cur, display=a_cur, period1=a_ht, penalties=a_pen, aggregated=a_agg)

    winner_code = 0
    if home_c.get("winner") is True or (h_cur is not None and a_cur is not None and h_cur > a_cur):
        winner_code = 1
    elif away_c.get("winner") is True or (h_cur is not None and a_cur is not None and a_cur > h_cur):
        winner_code = 2

    venue_raw = comp.get("venue") or ev.get("venue") or {}
    venue_name = str(venue_raw.get("fullName") or "")
    venue_addr = venue_raw.get("address") or {}
    venue_city = str(venue_addr.get("city") or "")
    venue_country = str(venue_addr.get("country") or "")
    attendance = _to_int(comp.get("attendance"))

    lid = _extract_league_id(str(ev.get("uid") or comp.get("uid") or ""))
    if lid in ESPN_LEAGUE_CATALOG:
        cat_name, lg_name, prio = ESPN_LEAGUE_CATALOG[lid]
    else:
        cat_name = venue_country if venue_country else "International"
        lg_name = f"{venue_country} League" if venue_country else f"Competition #{lid}"
        prio = 500
    if league_override:
        cat_name, lg_name = league_override

    enrich_team_identity(home_team, cat_name, venue_country)
    enrich_team_identity(away_team, cat_name)

    season_raw = ev.get("season") or {}
    slug_round = str(season_raw.get("slug") or "").replace("-", " ").title()
    series_title = str(series_raw.get("title") or "").strip()
    round_info = series_title or (slug_round if slug_round and slug_round != "Regular Season" else "League Stage")
    round_info = round_info.replace("Round Of ", "Round of ")

    tournament = TournamentInfo(
        id=lid,
        unique_id=lid,
        name=lg_name,
        category_id=lid,
        category_name=cat_name,
        season_id=int(season_raw.get("year") or 2026),
        round_info=round_info,
        priority=prio,
    )

    start_ts = _parse_iso_timestamp(str(comp.get("date") or ev.get("date") or ""))
    eid = int(ev.get("id") or comp.get("id") or 0)
    ref_name, ref_country = _select_match_referee(
        eid, cat_name, home_team.country_code, away_team.country_code
    )

    return MatchEvent(
        id=eid,
        slug=f"{home_team.short_name}-{away_team.short_name}".lower().replace(" ", "-"),
        start_timestamp=start_ts,
        status_type=status_type,
        status_description=status_desc,
        status_code=100 if status_type == "finished" else (6 if status_type == "inprogress" else 0),
        home_team=home_team,
        away_team=away_team,
        home_score=home_score,
        away_score=away_score,
        tournament=tournament,
        injury_time_1=p1_max_added,
        injury_time_2=p2_max_added,
        winner_code=winner_code,
        venue_name=venue_name,
        venue_city=venue_city,
        venue_country=venue_country,
        referee_name=ref_name,
        referee_country=ref_country,
        leg_info=leg_disp,
        prev_leg_score=prev_leg_score,
        series_note=series_note,
        attendance=attendance,
    )


def _classify_comment_type(text: str, raw_type: str = "") -> str:
    tl = text.lower()
    rl = raw_type.lower()
    if "goal!" in tl or "scores" in tl or "goal" in rl:
        if "own goal" in tl:
            return "ownGoal"
        if "penalty" in tl and "converts" in tl:
            return "penaltyGoal"
        return "goal"
    if "yellow card" in tl or "yellow" in rl:
        return "yellowCard"
    if "red card" in tl or "second yellow" in tl or "red" in rl:
        return "redCard"
    if "substitution" in tl or "replaces" in tl or "sub" in rl:
        if "injur" in tl:
            return "injurySubstitution"
        return "substitution"
    if "delay in match" in tl and "injur" in tl:
        return "injuryDelay"
    if "saved" in tl:
        return "attemptSaved"
    if "hits the" in tl and ("post" in tl or "crossbar" in tl or "woodwork" in tl):
        return "post"
    if "attempt blocked" in tl:
        return "attemptBlocked"
    if "attempt missed" in tl:
        return "attemptMissed"
    if "corner," in tl or "corner " in tl:
        return "corner"
    if "offside" in tl:
        return "offside"
    if "var " in tl or "video assistant" in tl:
        return "varDecision"
    if "foul by" in tl:
        return "foul"
    if "free kick" in tl:
        return "freeKickWon"
    if "match ends" in tl or "second half ends" in tl:
        return "matchEnded"
    if "first half ends" in tl or "half time" in tl:
        return "periodEnd"
    if "begins" in tl or "kickoff" in rl:
        return "periodStart"
    return "comment"


def _compute_player_rating(
    stats_map: dict[str, float],
    pos_abbr: str,
    starter: bool,
    sub_in: bool,
    team_won: bool,
    team_drew: bool,
    goals_conceded: int,
) -> float | None:
    """Calculate a realistic SofaScore-style 5.0 - 10.0 rating from individual player match statistics."""
    apps = stats_map.get("appearances", 0.0)
    if apps <= 0 and not starter and not sub_in:
        return None

    rating = 6.65 if starter else 6.45
    goals = stats_map.get("totalGoals", 0.0)
    assists = stats_map.get("goalAssists", 0.0)
    sot = stats_map.get("shotsOnTarget", 0.0)
    shots = stats_map.get("totalShots", 0.0)
    saves = stats_map.get("saves", 0.0)
    fc = stats_map.get("foulsCommitted", 0.0)
    fs = stats_map.get("foulsSuffered", 0.0)
    yc = stats_map.get("yellowCards", 0.0)
    rc = stats_map.get("redCards", 0.0)
    og = stats_map.get("ownGoals", 0.0)

    rating += goals * 1.05
    rating += assists * 0.70
    rating += sot * 0.25
    rating += max(0.0, shots - sot) * 0.07
    rating += fs * 0.12
    rating -= fc * 0.10
    rating -= yc * 0.35
    rating -= rc * 1.40
    rating -= og * 1.00

    if pos_abbr == "G":
        rating += saves * 0.32
        if goals_conceded == 0:
            rating += 0.55
        else:
            rating -= min(1.2, goals_conceded * 0.28)
    elif pos_abbr in ("D", "CB", "LB", "RB", "CD", "LD", "RD"):
        if goals_conceded == 0:
            rating += 0.40
        else:
            rating -= min(0.8, goals_conceded * 0.16)

    if team_won:
        rating += 0.25
    elif team_drew:
        rating += 0.05
    else:
        rating -= 0.15

    return round(min(9.9, max(4.8, rating)), 1)


def parse_espn_summary_bundle(summary: dict[str, Any]) -> FullMatchBundle | None:
    """Convert an ESPN /summary JSON payload into a complete SofaTUI FullMatchBundle."""
    header = summary.get("header") or {}
    comps = header.get("competitions") or []
    if not comps:
        return None
    comp = comps[0]

    uid_str = str(header.get("uid") or comp.get("uid") or "")
    lid = _extract_league_id(uid_str)
    lg_raw = header.get("league") or {}
    lg_name = str(lg_raw.get("name") or "")

    if lid in ESPN_LEAGUE_CATALOG:
        cat_name, lg_name, _ = ESPN_LEAGUE_CATALOG[lid]
    else:
        cat_name = "International"
        if "UEFA" in lg_name:
            cat_name = "Europe"
        elif "CONMEBOL" in lg_name or "Libertadores" in lg_name or "Sudamericana" in lg_name:
            cat_name = "South America"
        elif "CAF" in lg_name:
            cat_name = "Africa"
        elif "AFC" in lg_name:
            cat_name = "Asia"
        elif "Concacaf" in lg_name or "CONCACAF" in lg_name:
            cat_name = "CONCACAF"
        elif "FIFA" in lg_name or "Friendly" in lg_name:
            cat_name = "World"
        else:
            for dem, country_name in DEMONYM_TO_COUNTRY.items():
                if lg_name.startswith(f"{dem} "):
                    cat_name = country_name
                    lg_name = lg_name[len(dem) + 1 :]
                    break
            else:
                cat_name = lg_name.split(" ")[0] if " " in lg_name else "International"
        if lid and lg_name:
            ESPN_LEAGUE_CATALOG[lid] = (cat_name, lg_name, 6000)

    fake_sb_ev = {
        "id": comp.get("id") or header.get("id"),
        "uid": uid_str,
        "date": comp.get("date"),
        "season": header.get("season") or {},
        "competitions": [comp],
    }
    match_event = parse_espn_scoreboard_event(
        fake_sb_ev,
        league_override=(cat_name, lg_name) if lg_name else None,
    )
    if not match_event:
        return None

    # Enrich venue & attendance & referee from gameInfo
    game_info = summary.get("gameInfo") or {}
    venue_raw = game_info.get("venue") or {}
    venue_addr = venue_raw.get("address") or {}
    if venue_raw.get("fullName"):
        match_event.venue_name = str(venue_raw["fullName"])
    if venue_addr.get("city"):
        match_event.venue_city = str(venue_addr["city"])
    if venue_addr.get("country"):
        match_event.venue_country = str(venue_addr["country"])

    enrich_team_identity(
        match_event.home_team,
        match_event.tournament.category_name,
        match_event.venue_country,
    )
    enrich_team_identity(
        match_event.away_team,
        match_event.tournament.category_name,
    )

    if game_info.get("attendance"):
        try:
            match_event.attendance = int(game_info["attendance"])
        except (TypeError, ValueError):
            pass

    officials = game_info.get("officials") or []
    raw_ref_name = ""
    raw_ref_country = ""
    if officials and isinstance(officials[0], dict):
        off0 = officials[0]
        raw_ref_name = str(off0.get("displayName") or off0.get("fullName") or "")
        cit = off0.get("citizenship") or off0.get("country") or (off0.get("birthPlace") or {}).get("country") or ""
        if isinstance(cit, dict):
            raw_ref_country = str(cit.get("abbreviation") or cit.get("name") or "")
        else:
            raw_ref_country = str(cit or "")
    ref_name, ref_country = _select_match_referee(
        match_event.id,
        match_event.tournament.category_name,
        match_event.home_team.country_code,
        match_event.away_team.country_code,
        raw_name=raw_ref_name,
        raw_country=raw_ref_country,
    )
    match_event.referee_name = ref_name
    match_event.referee_country = ref_country

    home_name = match_event.home_team.name
    away_name = match_event.away_team.name
    home_id = match_event.home_team.id
    away_id = match_event.away_team.id

    # Pre-scan commentary & keyEvents for 1st-half and 2nd-half stoppage/additional time & injury substitutions
    p1_announced = 0
    p2_announced = 0
    p1_max_clock = match_event.injury_time_1
    p2_max_clock = match_event.injury_time_2
    injury_sub_texts: list[str] = []

    for c_raw in summary.get("commentary") or []:
        txt = str(c_raw.get("text") or "")
        tl = txt.lower()
        if "replaces" in tl and "injur" in tl:
            injury_sub_texts.append(tl)
        t_disp = str((c_raw.get("time") or {}).get("displayValue") or "")
        mn, added = _parse_minute_str(t_disp)
        if mn == 45 and added > p1_max_clock:
            p1_max_clock = added
        elif mn == 90 and added > p2_max_clock:
            p2_max_clock = added
        m_add = re.search(r"announced\s+(\d+)\s+minutes?\s+of\s+added\s+time", txt, re.IGNORECASE)
        if m_add:
            mins_val = int(m_add.group(1))
            if mn <= 50:
                p1_announced = mins_val
            else:
                p2_announced = mins_val

    for ke in summary.get("keyEvents") or []:
        clock_disp = str((ke.get("clock") or {}).get("displayValue") or "")
        mn, added = _parse_minute_str(clock_disp)
        if mn == 45 and added > p1_max_clock:
            p1_max_clock = added
        elif mn == 90 and added > p2_max_clock:
            p2_max_clock = added

    p1_added = p1_announced if p1_announced > 0 else p1_max_clock
    p2_added = p2_announced if p2_announced > 0 else p2_max_clock
    match_event.injury_time_1 = p1_added
    match_event.injury_time_2 = p2_added

    # 1. Parse Incidents from keyEvents
    incidents_chron: list[IncidentItem] = []
    h_running = 0
    a_running = 0
    ht_inserted = False
    p1_injury_inserted = False

    def _insert_ht_markers() -> None:
        nonlocal ht_inserted, p1_injury_inserted
        if not p1_injury_inserted and p1_added > 0:
            p1_injury_inserted = True
            incidents_chron.append(
                IncidentItem(
                    incident_type="injuryTime",
                    incident_class="regular",
                    time=45,
                    length=p1_added,
                    text=f"+{p1_added}'",
                )
            )
        if not ht_inserted:
            ht_inserted = True
            incidents_chron.append(
                IncidentItem(
                    incident_type="period",
                    incident_class="regular",
                    time=45,
                    added_time=p1_added,
                    text="HT",
                    home_score=h_running,
                    away_score=a_running,
                )
            )

    for ke in summary.get("keyEvents") or []:
        ktype_raw = (ke.get("type") or {}).get("text") or ""
        ktype_lower = ktype_raw.lower()
        clock_disp = str((ke.get("clock") or {}).get("displayValue") or "")
        mn, added = _parse_minute_str(clock_disp)
        period_num = int((ke.get("period") or {}).get("number") or 1)

        if period_num >= 2 and not ht_inserted and mn >= 45:
            _insert_ht_markers()

        t_obj = ke.get("team") or {}
        t_disp = str(t_obj.get("displayName") or "")
        t_id = int(t_obj.get("id") or 0) if str(t_obj.get("id") or "").isdigit() else 0
        is_home: bool | None = None
        if t_id and t_id == home_id:
            is_home = True
        elif t_id and t_id == away_id:
            is_home = False
        elif t_disp:
            is_home = (t_disp.lower() in home_name.lower() or home_name.lower() in t_disp.lower())

        participants = [
            str((p.get("athlete") or {}).get("shortName") or (p.get("athlete") or {}).get("displayName") or "")
            for p in (ke.get("participants") or [])
        ]
        p_full = [
            str((p.get("athlete") or {}).get("displayName") or "")
            for p in (ke.get("participants") or [])
        ]

        if "goal" in ktype_lower or ke.get("scoringPlay"):
            if is_home is True:
                h_running += 1
            elif is_home is False:
                a_running += 1
            iclass = "regular"
            if "penalty" in ktype_lower:
                iclass = "penalty"
            elif "own goal" in ktype_lower:
                iclass = "ownGoal"
            incidents_chron.append(
                IncidentItem(
                    incident_type="goal",
                    incident_class=iclass,
                    time=mn,
                    added_time=added,
                    is_home=is_home,
                    player_name=p_full[0] if p_full else "Scorer",
                    player_short=participants[0] if participants else "Scorer",
                    assist_name=participants[1] if len(participants) > 1 else "",
                    home_score=h_running,
                    away_score=a_running,
                )
            )
        elif "yellow card" in ktype_lower or "red card" in ktype_lower or "second yellow" in ktype_lower:
            iclass = "red" if "red" in ktype_lower else "yellow"
            incidents_chron.append(
                IncidentItem(
                    incident_type="card",
                    incident_class=iclass,
                    time=mn,
                    added_time=added,
                    is_home=is_home,
                    player_name=p_full[0] if p_full else "",
                    player_short=participants[0] if participants else "",
                )
            )
        elif "substitution" in ktype_lower:
            p_in_str = participants[0] if participants else "Sub In"
            p_out_str = participants[1] if len(participants) > 1 else "Sub Out"
            ke_txt_lower = str(ke.get("text") or "").lower()
            is_inj_sub = ("injur" in ke_txt_lower) or any(
                (len(p_out_str) >= 2 and p_out_str.lower() in itxt)
                and (len(p_in_str) >= 2 and p_in_str.lower() in itxt)
                for itxt in injury_sub_texts
            )
            incidents_chron.append(
                IncidentItem(
                    incident_type="substitution",
                    incident_class="injury" if is_inj_sub else "regular",
                    time=mn,
                    added_time=added,
                    is_home=is_home,
                    player_in_name=p_in_str,
                    player_out_name=p_out_str,
                    reason="Injury" if is_inj_sub else "",
                )
            )
        elif "halftime" in ktype_lower or "half time" in ktype_lower:
            _insert_ht_markers()

    if not ht_inserted and (match_event.is_finished or "2nd" in match_event.status_description.lower() or "ht" in match_event.status_description.lower()):
        _insert_ht_markers()

    if p2_added > 0:
        incidents_chron.append(
            IncidentItem(
                incident_type="injuryTime",
                incident_class="regular",
                time=90,
                length=p2_added,
                text=f"+{p2_added}'",
            )
        )

    if match_event.is_finished:
        incidents_chron.append(
            IncidentItem(
                incident_type="period",
                incident_class="regular",
                time=90,
                added_time=p2_added,
                text="FT",
                home_score=match_event.home_score.current or h_running,
                away_score=match_event.away_score.current or a_running,
            )
        )

    # SofaScore stores incidents reverse-chronologically
    incidents = list(reversed(incidents_chron))

    # 2. Parse Boxscore Team Statistics & Estimate xG
    box_teams = (summary.get("boxscore") or {}).get("teams") or []
    h_stats_raw: dict[str, str] = {}
    a_stats_raw: dict[str, str] = {}
    if len(box_teams) >= 2:
        for bt in box_teams:
            bt_id = int((bt.get("team") or {}).get("id") or 0)
            target_map = h_stats_raw if bt_id == home_id else a_stats_raw
            for st in bt.get("statistics") or []:
                target_map[str(st.get("name") or "")] = str(st.get("displayValue") or "0")

    def _fval(m: dict[str, str], k: str) -> float:
        try:
            return float(m.get(k, "0").replace("%", ""))
        except ValueError:
            return 0.0

    # Estimate realistic xG from shots on target, total shots, penalties, and goals
    h_shots = _fval(h_stats_raw, "totalShots")
    a_shots = _fval(a_stats_raw, "totalShots")
    h_sot = _fval(h_stats_raw, "shotsOnTarget")
    a_sot = _fval(a_stats_raw, "shotsOnTarget")
    h_pen_s = _fval(h_stats_raw, "penaltyKickShots")
    a_pen_s = _fval(a_stats_raw, "penaltyKickShots")
    h_goals_n = float(match_event.home_score.current or 0)
    a_goals_n = float(match_event.away_score.current or 0)

    h_xg = round(max(0.05 * h_shots, (h_sot * 0.19) + max(0.0, h_shots - h_sot) * 0.045 + h_pen_s * 0.58 + h_goals_n * 0.18), 2)
    a_xg = round(max(0.05 * a_shots, (a_sot * 0.19) + max(0.0, a_shots - a_sot) * 0.045 + a_pen_s * 0.58 + a_goals_n * 0.18), 2)

    def _mk_stat(
        key: str,
        label: str,
        hv: float,
        av: float,
        h_disp: str | None = None,
        a_disp: str | None = None,
        lower_better: bool = False,
    ) -> StatItem:
        hs = h_disp if h_disp is not None else (f"{int(hv)}" if hv.is_integer() else f"{hv:.2f}")
        as_ = a_disp if a_disp is not None else (f"{int(av)}" if av.is_integer() else f"{av:.2f}")
        if abs(hv - av) < 1e-6:
            cc = 3
        elif (hv > av and not lower_better) or (hv < av and lower_better):
            cc = 1
        else:
            cc = 2
        return StatItem(key=key, name=label, home_str=hs, away_str=as_, home_val=hv, away_val=av, compare_code=cc)

    overview_items = [
        _mk_stat("ballPossession", "Ball possession", _fval(h_stats_raw, "possessionPct"), _fval(a_stats_raw, "possessionPct"), f"{_fval(h_stats_raw, 'possessionPct'):.0f}%", f"{_fval(a_stats_raw, 'possessionPct'):.0f}%"),
        _mk_stat("expectedGoals", "Expected goals (xG)", h_xg, a_xg, f"{h_xg:.2f}", f"{a_xg:.2f}"),
        _mk_stat("totalShots", "Total shots", h_shots, a_shots),
        _mk_stat("shotsOnGoal", "Shots on target", h_sot, a_sot),
        _mk_stat("goalkeeperSaves", "Goalkeeper saves", _fval(h_stats_raw, "saves"), _fval(a_stats_raw, "saves")),
        _mk_stat("cornerKicks", "Corner kicks", _fval(h_stats_raw, "wonCorners"), _fval(a_stats_raw, "wonCorners")),
        _mk_stat("totalPasses", "Total passes", _fval(h_stats_raw, "totalPasses"), _fval(a_stats_raw, "totalPasses")),
        _mk_stat("accuratePasses", "Accurate passes", _fval(h_stats_raw, "accuratePasses"), _fval(a_stats_raw, "accuratePasses")),
        _mk_stat("totalTackles", "Tackles", _fval(h_stats_raw, "totalTackles"), _fval(a_stats_raw, "totalTackles")),
        _mk_stat("fouls", "Fouls", _fval(h_stats_raw, "foulsCommitted"), _fval(a_stats_raw, "foulsCommitted"), lower_better=True),
        _mk_stat("offsides", "Offsides", _fval(h_stats_raw, "offsides"), _fval(a_stats_raw, "offsides"), lower_better=True),
        _mk_stat("yellowCards", "Yellow cards", _fval(h_stats_raw, "yellowCards"), _fval(a_stats_raw, "yellowCards"), lower_better=True),
    ]
    shots_Passes_items = [
        _mk_stat("blockedShots", "Blocked shots", _fval(h_stats_raw, "blockedShots"), _fval(a_stats_raw, "blockedShots")),
        _mk_stat("accurateCrosses", "Accurate crosses", _fval(h_stats_raw, "accurateCrosses"), _fval(a_stats_raw, "accurateCrosses")),
        _mk_stat("totalCrosses", "Total crosses", _fval(h_stats_raw, "totalCrosses"), _fval(a_stats_raw, "totalCrosses")),
        _mk_stat("accurateLongBalls", "Accurate long balls", _fval(h_stats_raw, "accurateLongBalls"), _fval(a_stats_raw, "accurateLongBalls")),
        _mk_stat("totalLongBalls", "Total long balls", _fval(h_stats_raw, "totalLongBalls"), _fval(a_stats_raw, "totalLongBalls")),
    ]
    defending_items = [
        _mk_stat("effectiveTackles", "Effective tackles", _fval(h_stats_raw, "effectiveTackles"), _fval(a_stats_raw, "effectiveTackles")),
        _mk_stat("interceptions", "Interceptions", _fval(h_stats_raw, "interceptions"), _fval(a_stats_raw, "interceptions")),
        _mk_stat("clearances", "Clearances", _fval(h_stats_raw, "totalClearance"), _fval(a_stats_raw, "totalClearance")),
    ]
    period_stats = (
        []
        if match_event.is_upcoming and not h_stats_raw and not a_stats_raw
        else [
            PeriodStats(
                period="ALL",
                groups=[
                    StatGroup("Match overview", overview_items),
                    StatGroup("Attacking & Passing", shots_Passes_items),
                    StatGroup("Defending", defending_items),
                ],
            )
        ]
    )

    # 3. Parse Play-by-Play Commentary & Synthesize Attack Momentum Graph
    comments_chron: list[CommentItem] = []
    momentum_map: dict[int, float] = {m: 0.0 for m in range(1, 91)}

    def _norm_team(s: str) -> str:
        s_ascii = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
        return re.sub(r"[^a-z0-9]+", " ", s_ascii.lower()).strip()

    def _team_words(s: str) -> set[str]:
        stop = {"fc", "sc", "cf", "ac", "afc", "bk", "fk", "sk", "if", "cd", "ud", "sd", "rc", "rcd", "real", "club", "de", "the"}
        return {w for w in _norm_team(s).split() if len(w) >= 3 and w not in stop}

    h_norms = {_norm_team(home_name), _norm_team(match_event.home_team.short_name), _norm_team(match_event.home_team.name_code)} - {""}
    a_norms = {_norm_team(away_name), _norm_team(match_event.away_team.short_name), _norm_team(match_event.away_team.name_code)} - {""}
    h_words = _team_words(home_name) | _team_words(match_event.home_team.short_name)
    a_words = _team_words(away_name) | _team_words(match_event.away_team.short_name)

    def _resolve_acting_side(team_label: str) -> int:
        nt = _norm_team(team_label)
        if not nt:
            return 0
        h_hit = any(nt == hn or (len(hn) >= 4 and (hn in nt or nt in hn)) for hn in h_norms)
        a_hit = any(nt == an or (len(an) >= 4 and (an in nt or nt in an)) for an in a_norms)
        if h_hit and not a_hit:
            return 1
        if a_hit and not h_hit:
            return -1
        tw = _team_words(team_label)
        h_ov = len(tw & h_words)
        a_ov = len(tw & a_words)
        if h_ov > a_ov:
            return 1
        if a_ov > h_ov:
            return -1
        return 0

    def _extract_attack_impulse(txt: str, ctype: str) -> tuple[int, float]:
        tl = txt.lower()
        if ctype in ("foul", "yellowCard", "redCard", "substitution", "matchEnded", "comment"):
            return 0, 0.0
        if ctype == "freeKickWon":
            if "defensive half" in tl:
                return 0, 0.0
            weight = 20.0
        elif ctype in ("goal", "penaltyGoal"):
            weight = 65.0
        elif ctype == "post":
            weight = 50.0
        elif ctype == "attemptSaved":
            weight = 42.0
        elif ctype in ("attemptMissed", "attemptBlocked", "corner"):
            weight = 28.0
        elif ctype == "offside":
            weight = 14.0
        else:
            return 0, 0.0

        # 1. "Corner, <Team>." or "Offside, <Team>."
        m_prefix = re.match(r"^(?:Corner|Offside),\s*([^.]+)\.", txt, re.IGNORECASE)
        if m_prefix:
            return _resolve_acting_side(m_prefix.group(1)), weight

        # 2. "Own Goal by <Player> (<DefendingTeam>), ..."
        if tl.startswith("own goal by"):
            m_paren = re.search(r"\(([^)]+)\)", txt)
            if m_paren:
                return -_resolve_acting_side(m_paren.group(1)), weight

        # 3. Strip "Goal! TeamA X, TeamB Y." prefix so the first (<Team>) is the acting player's team
        body = re.sub(r"^Goal!.*?\.\s*", "", txt, flags=re.IGNORECASE)
        m_paren = re.search(r"\(([^)]+)\)", body)
        if m_paren:
            return _resolve_acting_side(m_paren.group(1)), weight

        return 0, 0.0

    for idx, c_raw in enumerate(summary.get("commentary") or []):
        txt = str(c_raw.get("text") or "").strip()
        if not txt:
            continue
        t_disp = str((c_raw.get("time") or {}).get("displayValue") or "")
        mn, added = _parse_minute_str(t_disp)
        play_type = str(((c_raw.get("play") or {}).get("type") or {}).get("text") or "")
        ctype = _classify_comment_type(txt, play_type)

        comments_chron.append(
            CommentItem(
                id=idx + 1,
                type=ctype,
                text=txt,
                time=mn,
                added_time=added,
            )
        )

        # Momentum contribution based strictly on the acting team of attacking plays
        if 1 <= mn <= 120:
            b_min = min(90, mn)
            side, weight = _extract_attack_impulse(txt, ctype)
            if side == 1:
                momentum_map[b_min] = min(95.0, momentum_map.get(b_min, 0.0) + weight)
            elif side == -1:
                momentum_map[b_min] = max(-95.0, momentum_map.get(b_min, 0.0) - weight)

    comments = list(reversed(comments_chron))

    # Build Attack Momentum strictly when real play-by-play coverage exists (no fake sine-wave on limited-coverage games)
    momentum_pts: list[MomentumPoint] = []
    pbp_attack_events = sum(
        1
        for c in comments_chron
        if c.type in ("attemptSaved", "attemptMissed", "attemptBlocked", "corner", "freeKickWon", "post", "offside")
    )
    if not match_event.is_upcoming and pbp_attack_events >= 5:
        cur_clock_min, _ = _parse_minute_str(match_event.status_description)
        max_played_min = 90 if match_event.is_finished else max(
            1,
            min(90, cur_clock_min or max((c.time for c in comments_chron), default=45)),
        )
        for m in range(1, max_played_min + 1):
            w_cur = momentum_map.get(m, 0.0)
            w_prev1 = momentum_map.get(m - 1, 0.0)
            w_next1 = momentum_map.get(m + 1, 0.0) if m < max_played_min else 0.0
            if abs(w_cur) > 0.1:
                # Reinforce with same-side pressure from adjacent minutes without cancelling opposite-side spikes
                same_prev = w_prev1 * 0.35 if (w_cur * w_prev1 > 0) else 0.0
                same_next = w_next1 * 0.25 if (w_cur * w_next1 > 0) else 0.0
                combined = w_cur + same_prev + same_next
            else:
                combined = w_prev1 * 0.45 + w_next1 * 0.30
            momentum_pts.append(MomentumPoint(minute=float(m), value=round(max(-98.0, min(98.0, combined)), 1)))

    # 4. Parse Rosters / Lineups & Compute SofaScore-Style Player Ratings
    home_lu = TeamLineup()
    away_lu = TeamLineup()

    # Tactical depth & lateral coordinate maps for accurate formation pitch ordering
    depth_map: dict[str, float] = {
        "G": 0.0,
        "CD": 1.0, "CD-L": 1.0, "CD-R": 1.0, "D": 1.0, "LB": 1.1, "RB": 1.1,
        "SW": 1.4, "LWB": 1.5, "RWB": 1.5, "WB": 1.5,
        "DM": 1.8, "DM-L": 1.8, "DM-R": 1.8,
        "CM": 2.0, "CM-L": 2.0, "CM-R": 2.0, "M": 2.0, "LM": 2.1, "RM": 2.1,
        "AM": 3.0, "AM-L": 3.0, "AM-R": 3.0,
        "LF": 4.0, "RF": 4.0, "CF-L": 4.0, "CF-R": 4.0, "LW": 4.0, "RW": 4.0,
        "CF": 4.4, "ST": 4.5, "F": 4.5,
    }
    lat_map: dict[str, float] = {
        "LB": -2.0, "LWB": -2.0, "LM": -2.0, "AM-L": -2.0, "LF": -2.0, "LW": -2.0,
        "CD-L": -1.0, "DM-L": -1.0, "CM-L": -1.0, "CF-L": -1.0,
        "G": 0.0, "SW": 0.0, "CD": 0.0, "D": 0.0, "DM": 0.0, "CM": 0.0, "M": 0.0, "AM": 0.0, "CF": 0.0, "F": 0.0, "ST": 0.0,
        "CD-R": 1.0, "DM-R": 1.0, "CM-R": 1.0, "CF-R": 1.0,
        "RB": 2.0, "RWB": 2.0, "RM": 2.0, "AM-R": 2.0, "RF": 2.0, "RW": 2.0,
    }
    role_display_map: dict[str, str] = {
        "G": "GK", "CD": "CB", "CD-L": "CB", "CD-R": "CB", "D": "DEF",
        "LB": "LB", "RB": "RB", "LWB": "LWB", "RWB": "RWB", "WB": "WB", "SW": "DM",
        "DM": "DM", "DM-L": "DM", "DM-R": "DM",
        "CM": "CM", "CM-L": "CM", "CM-R": "CM", "M": "MID", "LM": "LM", "RM": "RM",
        "AM": "CAM", "AM-L": "LW", "AM-R": "RW",
        "LF": "LW", "RF": "RW", "LW": "LW", "RW": "RW",
        "CF-L": "CF", "CF-R": "CF", "CF": "CF", "F": "ST", "ST": "ST",
    }

    for r_side in summary.get("rosters") or []:
        side_str = str(r_side.get("homeAway") or "home")
        roster_entries = r_side.get("roster") or []
        formation = str(r_side.get("formation") or ("4-3-3" if roster_entries else ""))
        is_home_side = side_str == "home"
        team_won = (match_event.winner_code == 1) if is_home_side else (match_event.winner_code == 2)
        team_drew = match_event.winner_code == 0 and match_event.is_finished
        conceded = int((match_event.away_score.current if is_home_side else match_event.home_score.current) or 0)

        players_list: list[PlayerLineup] = []
        for idx, entry in enumerate(r_side.get("roster") or []):
            ath = entry.get("athlete") or {}
            pos = entry.get("position") or {}
            raw_abbr = str(pos.get("abbreviation") or "M").strip().upper()
            raw_pos_name = str(pos.get("name") or "").lower()
            if raw_abbr == "G" or "goalkeeper" in raw_pos_name:
                pos_abbr = "G"
            elif raw_abbr in ("D", "CD", "CD-L", "CD-R", "LB", "RB", "LWB", "RWB", "WB") or "defender" in raw_pos_name or "back" in raw_pos_name:
                pos_abbr = "D"
            elif raw_abbr in ("F", "CF", "CF-L", "CF-R", "LF", "RF", "ST", "LW", "RW") or "forward" in raw_pos_name or "striker" in raw_pos_name:
                pos_abbr = "F"
            else:
                pos_abbr = "M"
            tactical_role = role_display_map.get(raw_abbr, pos_abbr)

            starter = bool(entry.get("starter"))
            sub_in = bool(entry.get("subbedIn"))
            sub_out = bool(entry.get("subbedOut"))

            st_raw_list = entry.get("stats") or []
            st_float: dict[str, float] = {}
            for s_it in st_raw_list:
                try:
                    st_float[str(s_it.get("name") or "")] = float(s_it.get("value") or 0.0)
                except (TypeError, ValueError):
                    pass

            if match_event.is_upcoming:
                rating: float | None = None
                mins = 0
            else:
                rating = _compute_player_rating(
                    st_float, pos_abbr, starter, sub_in, team_won, team_drew, conceded
                )
                mins = 90 if (starter and not sub_out) else (68 if (starter and sub_out) else (22 if sub_in else 0))
            goals_i = int(st_float.get("totalGoals", 0.0))
            assists_i = int(st_float.get("goalAssists", 0.0))
            sot_i = int(st_float.get("shotsOnTarget", 0.0))
            shots_i = int(st_float.get("totalShots", 0.0))
            yc_i = int(st_float.get("yellowCards", 0.0))
            rc_i = int(st_float.get("redCards", 0.0))
            saves_i = int(st_float.get("saves", 0.0))
            fc_i = int(st_float.get("foulsCommitted", 0.0))
            fs_i = int(st_float.get("foulsSuffered", 0.0))

            p_xg = round(goals_i * 0.38 + sot_i * 0.16 + max(0, shots_i - sot_i) * 0.05, 2) if mins > 0 else 0.0
            p_xa = round(assists_i * 0.35 + (0.08 if mins > 45 else 0.02), 2) if mins > 0 else 0.0

            rich_stats: dict[str, Any] = {
                **({"rating": rating} if rating is not None else {}),
                "minutesPlayed": mins,
                "goals": goals_i,
                "goalAssist": assists_i,
                "expectedGoals": p_xg,
                "expectedAssists": p_xa,
                "totalScoringAttempt": shots_i,
                "onTargetScoringAttempt": sot_i,
                "touches": int(mins * 0.62 + shots_i * 3 + assists_i * 4) if mins > 0 else 0,
                "accuratePass": int(mins * 0.42) if mins > 0 else 0,
                "totalPass": int(mins * 0.49) if mins > 0 else 0,
                "keyPass": assists_i + (1 if sot_i > 0 else 0),
                "fouls": fc_i,
                "wasFouled": fs_i,
                "saves": saves_i if pos_abbr == "G" else "-",
                "tacticalRole": tactical_role,
                "_rawAbbr": raw_abbr,
                "_depth": depth_map.get(raw_abbr, 2.0),
                "_lat": lat_map.get(raw_abbr, 0.0),
            }

            c_name = str(ath.get("citizenship") or (ath.get("flag") or {}).get("alt") or "")
            c_code = (
                COUNTRY_ALPHA3_MAP.get(c_name.lower(), "")
                or str(ath.get("citizenshipCountry") or (c_name[:3].upper() if c_name else ""))
            )

            players_list.append(
                PlayerLineup(
                    id=int(ath.get("id") or (idx + 1 + (0 if is_home_side else 100))),
                    name=str(ath.get("displayName") or ath.get("fullName") or "Player"),
                    short_name=str(ath.get("shortName") or ath.get("displayName") or "Player"),
                    shirt_number=str(entry.get("jersey") or "-"),
                    position=pos_abbr,
                    substitute=not starter,
                    captain=bool(entry.get("captain")),
                    rating=rating,
                    minutes_played=mins,
                    goals=goals_i,
                    assists=assists_i,
                    yellow_cards=yc_i,
                    red_cards=rc_i,
                    subbed_in=70 if sub_in else None,
                    subbed_out=70 if sub_out else None,
                    country_name=c_name,
                    country_code=c_code,
                    stats=rich_stats,
                )
            )

        # Sort starters by tactical line depth and left-to-right pitch coordinate
        starters_raw = [p for p in players_list if not p.substitute]
        subs_raw = [p for p in players_list if p.substitute]
        if starters_raw:
            starters_raw.sort(key=lambda p: float(p.stats.get("_depth", 2.0)))
            gk_list = starters_raw[:1]
            outfield_list = starters_raw[1:11]
            f_parts = [int(x) for x in formation.split("-") if x.strip().isdigit()]
            if not f_parts or sum(f_parts) != len(outfield_list):
                f_parts = [4, 3, 3] if len(outfield_list) == 10 else [len(outfield_list)]
            ordered_starters: list[PlayerLineup] = list(gk_list)
            s_idx = 0
            for cnt in f_parts:
                row_slice = outfield_list[s_idx : s_idx + cnt]
                s_idx += cnt
                row_slice.sort(key=lambda p: float(p.stats.get("_lat", 0.0)))
                ordered_starters.extend(row_slice)
            if s_idx < len(outfield_list):
                ordered_starters.extend(outfield_list[s_idx:])
            players_list = ordered_starters + subs_raw

        t_lu = TeamLineup(formation=formation, players=players_list)
        if is_home_side:
            home_lu = t_lu
        else:
            away_lu = t_lu

    # Cross-reference substitution incidents with lineup players for exact minutes & injury flags
    all_lu_players = home_lu.players + away_lu.players
    for inc in incidents_chron:
        if inc.incident_type == "substitution" and inc.time > 0:
            pin_l = inc.player_in_name.lower()
            pout_l = inc.player_out_name.lower()
            for p in all_lu_players:
                ps_l = p.short_name.lower()
                pn_l = p.name.lower()
                if pin_l and (ps_l == pin_l or pn_l == pin_l or pin_l in pn_l):
                    p.subbed_in = inc.time
                    p.minutes_played = max(1, 90 - inc.time)
                    p.stats["minutesPlayed"] = p.minutes_played
                if pout_l and (ps_l == pout_l or pn_l == pout_l or pout_l in pn_l):
                    p.subbed_out = inc.time
                    p.minutes_played = min(90, max(1, inc.time))
                    p.stats["minutesPlayed"] = p.minutes_played
                    if inc.is_injury_sub:
                        p.subbed_out_injured = True

    lineups = MatchLineups(confirmed=True, home=home_lu, away=away_lu)

    # 5. Parse Standings
    standings_rows: list[StandingRow] = []
    standings_raw = summary.get("standings") or {}
    standings_name = str(standings_raw.get("header") or match_event.tournament.name)
    for grp in standings_raw.get("groups") or []:
        entries = (grp.get("standings") or {}).get("entries") or []
        for idx, ent in enumerate(entries):
            st_map: dict[str, str] = {}
            for s in ent.get("stats") or []:
                st_map[str(s.get("name") or "")] = str(s.get("displayValue") or s.get("value") or "0")

            def _si(k: str, default: int = 0) -> int:
                try:
                    return int(float(st_map.get(k, str(default))))
                except ValueError:
                    return default

            tid = int(ent.get("id") or 0) if str(ent.get("id") or "").isdigit() else (idx + 1)
            tname = str(ent.get("team") or "")
            note_txt = str((ent.get("note") or {}).get("description") or "")
            standings_rows.append(
                StandingRow(
                    position=_si("rank", idx + 1),
                    team_id=tid,
                    team_name=tname,
                    team_short=tname,
                    matches=_si("gamesPlayed"),
                    wins=_si("wins"),
                    draws=_si("ties"),
                    losses=_si("losses"),
                    scores_for=_si("pointsFor"),
                    scores_against=_si("pointsAgainst"),
                    score_diff=st_map.get("pointDifferential", "0"),
                    points=_si("points"),
                    promotion_text=note_txt,
                )
            )

    # 6. Parse Pre-match Form, Season Series (Past Leg) & H2H
    h2h = H2HInfo()
    for lfg in summary.get("lastFiveGames") or []:
        t_id = int((lfg.get("team") or {}).get("id") or 0)
        results = [str(ev.get("gameResult") or "D") for ev in (lfg.get("events") or [])[:5]]
        if t_id == home_id:
            h2h.home_form = results
        elif t_id == away_id:
            h2h.away_form = results

    for s_ser in summary.get("seasonseries") or []:
        if not isinstance(s_ser, dict):
            continue
        ser_type = str(s_ser.get("type") or "")
        ser_events = s_ser.get("events") or []
        for s_ev in ser_events:
            if not isinstance(s_ev, dict):
                continue
            s_eid = int(s_ev.get("id") or 0) if str(s_ev.get("id") or "").isdigit() else 0
            s_comps = s_ev.get("competitors") or []
            if len(s_comps) < 2:
                continue
            h_sc: int | None = None
            a_sc: int | None = None
            for sc in s_comps:
                sc_tid = int((sc.get("team") or {}).get("id") or 0)
                try:
                    val = int(float(sc.get("score")))
                except (TypeError, ValueError):
                    val = None
                if sc_tid == home_id:
                    h_sc = val
                elif sc_tid == away_id:
                    a_sc = val
            if h_sc is not None and a_sc is not None:
                if ser_type == "head-to-head":
                    if h_sc > a_sc:
                        h2h.home_wins += 1
                    elif a_sc > h_sc:
                        h2h.away_wins += 1
                    else:
                        h2h.draws += 1
                elif s_eid and s_eid != match_event.id and not match_event.prev_leg_score:
                    match_event.prev_leg_score = f"1st Leg: {h_sc} - {a_sc}"

    return FullMatchBundle(
        event=match_event,
        incidents=incidents,
        statistics=period_stats,
        comments=comments,
        lineups=lineups,
        momentum=momentum_pts,
        standings=standings_rows,
        standings_name=standings_name,
        h2h=h2h,
    )
