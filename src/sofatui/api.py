"""Dual-Engine SofaScore + ESPN API client with fast direct IPv4 DNS resolution, persistent disk fallback cache, and automatic WAF failover."""

from __future__ import annotations

import datetime
import json
import os
import socket
import struct
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

try:
    from curl_cffi import CurlOpt, requests as cffi_requests
    HAS_CURL_CFFI = True
except ImportError:
    CurlOpt = None  # type: ignore[assignment]
    cffi_requests = None  # type: ignore[assignment]
    HAS_CURL_CFFI = False

import httpx

from sofatui.espn import parse_espn_scoreboard_event, parse_espn_summary_bundle
from sofatui.models import (
    CommentItem,
    FullMatchBundle,
    H2HInfo,
    IncidentItem,
    MatchEvent,
    MatchLineups,
    MissingPlayer,
    MomentumPoint,
    PeriodStats,
    PlayerLineup,
    StandingRow,
    StatGroup,
    StatItem,
    TeamLineup,
)

SOFASCORE_BASE = "https://www.sofascore.com/api/v1"
ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer/all"
FALLBACK_SOFASCORE_IPS = ["151.101.195.52", "199.232.35.52", "151.101.67.52", "151.101.3.52"]
FALLBACK_ESPN_IPS = ["3.162.112.92", "18.165.83.50"]


def _resolve_cache_path() -> Path:
    xdg_cache = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg_cache) if xdg_cache and not xdg_cache.startswith("/tmp") else (Path.home() / ".cache")
    return base / "sofatui" / "http_cache.json"


PERSISTENT_CACHE_PATH = _resolve_cache_path()
LEGACY_CACHE_PATH = Path(__file__).resolve().parents[2] / "data" / "http_cache.json"

# Priority football categories for SofaScore
PRIORITY_CATEGORIES = [
    1465,  # Europe (UEFA Champions League, Europa League, Conference League)
    1,     # England (Premier League, FA Cup, EFL Cup, Championship)
    32,    # Spain (LaLiga, Copa del Rey)
    31,    # Italy (Serie A, Coppa Italia)
    30,    # Germany (Bundesliga, DFB-Pokal)
    7,     # France (Ligue 1, Coupe de France)
    44,    # Portugal (Liga Portugal Betclic, Taça de Portugal)
    13,    # Brazil (Brasileirão Série A)
]


def resolve_a_fast(hostname: str = "www.sofascore.com") -> str:
    """Resolve an IPv4 A record via direct UDP query to 1.1.1.1 / 8.8.8.8 in ~10ms."""
    tid = b"\x42\x42\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
    qname = b"".join(bytes([len(p)]) + p.encode("ascii") for p in hostname.split(".")) + b"\x00\x00\x01\x00\x01"
    pkt = tid + qname

    for dns_server in ("1.1.1.1", "8.8.8.8", "9.9.9.9"):
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(0.8)
            sock.sendto(pkt, (dns_server, 53))
            resp, _ = sock.recvfrom(512)
            ancount = struct.unpack("!H", resp[6:8])[0]
            idx = len(pkt)
            for _ in range(ancount):
                if resp[idx] & 0xC0 == 0xC0:
                    idx += 2
                else:
                    end = resp.index(0, idx)
                    idx = end + 1
                rtype, _, _, rdlen = struct.unpack("!HHIH", resp[idx : idx + 10])
                idx += 10
                if rtype == 1 and rdlen == 4:
                    return socket.inet_ntoa(resp[idx : idx + 4])
                idx += rdlen
        except Exception:
            continue
        finally:
            if sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass
    if "espn" in hostname:
        return FALLBACK_ESPN_IPS[0]
    return FALLBACK_SOFASCORE_IPS[0]


def _team_tokens(name: str) -> set[str]:
    stop = {"fc", "cf", "sc", "ac", "afc", "club", "de", "real", "sporting", "united", "city", "utd"}
    words = {w for w in re.sub(r"[^a-z0-9 ]", " ", name.lower()).split() if len(w) >= 3}
    core = words - stop
    return core if core else words


import re


class SofaScoreClient:
    """High-speed Dual-Engine (SofaScore + ESPN) football client with non-destructive caching."""

    def __init__(self) -> None:
        self._sofascore_ip = resolve_a_fast("www.sofascore.com")
        self._espn_ip = resolve_a_fast("site.api.espn.com")
        self._local = threading.local()
        self._cache: dict[str, tuple[float, Any]] = {}
        self._stale_cache: dict[str, Any] = {}
        self._bundle_cache: dict[int, tuple[float, FullMatchBundle]] = {}
        self._known_events: dict[int, MatchEvent] = {}
        self._cache_lock = threading.Lock()
        self._cache_dirty: bool = False
        self._last_disk_save: float = 0.0
        self._sofascore_cooldown_until: float = 0.0
        self._pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="sofatui-net")
        self._load_disk_cache()

    @property
    def active_provider(self) -> str:
        return "ESPN+SofaScore" if time.monotonic() < self._sofascore_cooldown_until else "SofaScore"

    def _load_disk_cache(self) -> None:
        target = PERSISTENT_CACHE_PATH
        if not target.exists() and LEGACY_CACHE_PATH.exists():
            target = LEGACY_CACHE_PATH
        if not target.exists():
            return
        try:
            raw = json.loads(target.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                with self._cache_lock:
                    for k, v in raw.items():
                        self._stale_cache[k] = v
        except Exception:
            pass

    def _save_disk_cache(self) -> None:
        now = time.monotonic()
        with self._cache_lock:
            if not self._cache_dirty or (now - self._last_disk_save) < 25.0:
                return
            self._cache_dirty = False
            self._last_disk_save = now
            # Keep at most 35 recent entries on disk so serialization is sub-millisecond
            keys = [k for k in self._stale_cache.keys() if not k.startswith("__")][-35:]
            snapshot = {k: self._stale_cache[k] for k in keys}
        try:
            PERSISTENT_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            PERSISTENT_CACHE_PATH.write_text(json.dumps(snapshot), encoding="utf-8")
        except Exception:
            pass

    def _get_session(self) -> Any:
        sess = getattr(self._local, "session", None)
        if sess is None:
            headers = {
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.sofascore.com/",
            }
            if HAS_CURL_CFFI and cffi_requests is not None and CurlOpt is not None:
                sess = cffi_requests.Session(
                    impersonate="chrome",
                    headers=headers,
                    curl_options={
                        CurlOpt.IPRESOLVE: 1,
                        CurlOpt.RESOLVE: [
                            f"www.sofascore.com:443:{self._sofascore_ip}",
                            f"site.api.espn.com:443:{self._espn_ip}",
                        ],
                    },
                )
            else:
                sess = httpx.Client(
                    headers={
                        **headers,
                        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0",
                    },
                    follow_redirects=True,
                )
            self._local.session = sess
        return sess

    def get_json(
        self,
        path: str,
        ttl: float = 15.0,
        timeout: float = 6.0,
        allow_stale: bool = True,
    ) -> dict[str, Any] | None:
        now = time.monotonic()
        with self._cache_lock:
            cached = self._cache.get(path)
            if cached and ttl > 0 and (now - cached[0]) < ttl:
                return cached[1]

        is_sofascore = path.startswith("/") or "sofascore.com" in path
        if is_sofascore and now < self._sofascore_cooldown_until:
            with self._cache_lock:
                return self._stale_cache.get(path) if allow_stale else None

        url = f"{SOFASCORE_BASE}{path}" if path.startswith("/") else path
        for attempt in range(2):
            try:
                sess = self._get_session()
                resp = sess.get(url, timeout=timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    with self._cache_lock:
                        self._cache[path] = (time.monotonic(), data)
                        self._stale_cache[path] = data
                        self._cache_dirty = True
                    return data
                if resp.status_code == 403 and is_sofascore:
                    # SofaScore Varnish challenge/rate-limit triggered; activate ESPN failover cooldown
                    self._sofascore_cooldown_until = time.monotonic() + 240.0
                    break
                if resp.status_code == 404:
                    return None
            except Exception:
                if attempt == 0:
                    self._local.session = None
        if allow_stale:
            with self._cache_lock:
                return self._stale_cache.get(path)
        return None

    def clear_cache(self) -> None:
        """Expire TTLs so next fetch hits the network, while preserving _stale_cache for safe fallback."""
        with self._cache_lock:
            self._cache.clear()
            self._bundle_cache.clear()

    def _register_events(self, events: list[MatchEvent]) -> None:
        with self._cache_lock:
            for ev in events:
                self._known_events[ev.id] = ev

    def get_espn_matches_for_date(self, date_str: str, force: bool = False) -> list[MatchEvent]:
        """Fetch all global matches for YYYY-MM-DD from ESPN in a single HTTP request."""
        espn_date = date_str.replace("-", "")
        ttl = 0.0 if force else 20.0
        url = f"{ESPN_BASE}/scoreboard?dates={espn_date}&limit=200"
        data = self.get_json(url, ttl=ttl, timeout=7.0)
        if not data or not isinstance(data.get("events"), list):
            return []

        matches: list[MatchEvent] = []
        for raw_ev in data["events"]:
            parsed = parse_espn_scoreboard_event(raw_ev)
            if parsed and parsed.id:
                matches.append(parsed)

        matches.sort(
            key=lambda m: (
                -m.tournament.priority,
                m.tournament.category_name,
                m.tournament.name,
                m.start_timestamp,
                m.id,
            )
        )
        self._register_events(matches)
        return matches

    def get_live_matches(self, force: bool = False) -> list[MatchEvent]:
        ttl = 0.0 if force else 12.0
        if time.monotonic() >= self._sofascore_cooldown_until:
            data = self.get_json("/sport/football/events/live", ttl=ttl, allow_stale=False)
            if data and isinstance(data.get("events"), list):
                events = [MatchEvent.from_dict(ev) for ev in data["events"] if ev.get("id")]
                events.sort(
                    key=lambda m: (
                        -m.tournament.priority,
                        m.tournament.category_name,
                        m.tournament.name,
                        m.start_timestamp,
                    )
                )
                self._register_events(events)
                return events

        # ESPN fallback for live matches
        today_str = datetime.date.today().isoformat()
        all_today = self.get_espn_matches_for_date(today_str, force=force)
        live = [m for m in all_today if m.is_live]
        return live

    def get_matches_for_date(self, date_str: str, force: bool = False) -> list[MatchEvent]:
        """Fetch scheduled & live matches for YYYY-MM-DD with automatic ESPN failover."""
        ttl = 0.0 if force else 30.0
        cache_key = f"__date_matches__:{date_str}"
        if not force:
            with self._cache_lock:
                cached = self._cache.get(cache_key)
                if cached and (time.monotonic() - cached[0]) < ttl:
                    return list(cached[1])

        try:
            target_date = datetime.date.fromisoformat(date_str)
        except ValueError:
            target_date = datetime.date.today()

        # Try SofaScore if not in 403 challenge cooldown
        if time.monotonic() >= self._sofascore_cooldown_until:
            today_str = datetime.date.today().isoformat()
            futures = {}
            for cid in PRIORITY_CATEGORIES[:6]:
                futures[self._pool.submit(self.get_json, f"/category/{cid}/scheduled-events/{date_str}", ttl, 5.0, False)] = f"cat:{cid}"
            if date_str == today_str:
                futures[self._pool.submit(self.get_json, "/sport/football/events/live", 10.0, 5.0, False)] = "live"

            by_id: dict[int, MatchEvent] = {}
            live_ids: set[int] = set()

            for fut in as_completed(futures):
                tag = futures[fut]
                res = fut.result()
                if not res:
                    continue
                for raw_ev in res.get("events") or []:
                    eid = int(raw_ev.get("id") or 0)
                    if not eid:
                        continue
                    ev_obj = MatchEvent.from_dict(raw_ev)
                    ev_local_date = datetime.datetime.fromtimestamp(ev_obj.start_timestamp).date()
                    if tag == "live":
                        live_ids.add(eid)
                        if ev_local_date == target_date or ev_obj.is_live:
                            by_id[eid] = ev_obj
                    else:
                        if ev_local_date == target_date and eid not in live_ids:
                            by_id[eid] = ev_obj

            if by_id:
                matches = list(by_id.values())
                matches.sort(
                    key=lambda m: (
                        -m.tournament.priority,
                        m.tournament.category_name,
                        m.tournament.name,
                        m.start_timestamp,
                        m.id,
                    )
                )
                self._register_events(matches)
                with self._cache_lock:
                    self._cache[cache_key] = (time.monotonic(), matches)
                    self._stale_cache[cache_key] = matches
                return matches

        # Automatic ESPN failover (1 single HTTP request!)
        espn_matches = self.get_espn_matches_for_date(date_str, force=force)
        if espn_matches:
            with self._cache_lock:
                self._cache[cache_key] = (time.monotonic(), espn_matches)
                self._stale_cache[cache_key] = espn_matches
            return espn_matches

        # Last-resort stale cache so pressing 'r' never blanks out the screen
        with self._cache_lock:
            stale = self._stale_cache.get(cache_key)
            if stale:
                return list(stale)
        return []

    def _resolve_espn_event_id(self, event_id: int, hint_event: MatchEvent | None = None) -> int | None:
        """Map a SofaScore 8-digit match ID to its corresponding ESPN 9-digit event ID by team names & date."""
        if event_id >= 400_000_000:
            return event_id

        ev = hint_event
        if ev is None:
            with self._cache_lock:
                ev = self._known_events.get(event_id)
        if ev is None:
            # Check stale cache for /event/{event_id}
            with self._cache_lock:
                raw_ev = (self._stale_cache.get(f"/event/{event_id}") or {}).get("event")
            if raw_ev:
                ev = MatchEvent.from_dict(raw_ev)

        if ev is None:
            return None

        ev_date = datetime.datetime.fromtimestamp(ev.start_timestamp).date().isoformat()
        espn_matches = self.get_espn_matches_for_date(ev_date, force=False)
        h_tokens = _team_tokens(ev.home_team.name) | _team_tokens(ev.home_team.short_name)
        a_tokens = _team_tokens(ev.away_team.name) | _team_tokens(ev.away_team.short_name)

        best_id: int | None = None
        best_score = 0
        for cand in espn_matches:
            ch_tokens = _team_tokens(cand.home_team.name) | _team_tokens(cand.home_team.short_name)
            ca_tokens = _team_tokens(cand.away_team.name) | _team_tokens(cand.away_team.short_name)
            score = len(h_tokens & ch_tokens) * 2 + len(a_tokens & ca_tokens) * 2
            if cand.home_team.name.lower() in ev.home_team.name.lower() or ev.home_team.short_name.lower() in cand.home_team.name.lower():
                score += 3
            if cand.away_team.name.lower() in ev.away_team.name.lower() or ev.away_team.short_name.lower() in cand.away_team.name.lower():
                score += 3
            if score > best_score:
                best_score = score
                best_id = cand.id

        return best_id if best_score >= 2 else None

    def get_espn_match_bundle(self, espn_event_id: int, force: bool = False) -> FullMatchBundle | None:
        ttl = 0.0 if force else 15.0
        url = f"{ESPN_BASE}/summary?event={espn_event_id}"
        data = self.get_json(url, ttl=ttl, timeout=7.0)
        if not data:
            return None
        bundle = parse_espn_summary_bundle(data)
        if bundle:
            self._save_disk_cache()
        return bundle

    def get_full_match_bundle(
        self,
        event_id: int,
        force: bool = False,
        hint_event: MatchEvent | None = None,
    ) -> FullMatchBundle | None:
        """Fetch full match center from SofaScore or ESPN (with automatic cross-provider failover)."""
        now = time.monotonic()
        if not force:
            with self._cache_lock:
                b_cached = self._bundle_cache.get(event_id)
                if b_cached and (now - b_cached[0]) < 25.0:
                    return b_cached[1]

        # 1. If event_id is an ESPN ID (>= 400,000,000), fetch directly from ESPN in 1 request
        if event_id >= 400_000_000:
            bundle = self.get_espn_match_bundle(event_id, force=force)
            if bundle:
                with self._cache_lock:
                    self._bundle_cache[event_id] = (time.monotonic(), bundle)
                return bundle

        # 2. Try SofaScore if not in 403 challenge cooldown (or if cached in _stale_cache)
        ttl = 0.0 if force else 15.0
        if time.monotonic() >= self._sofascore_cooldown_until:
            bundle = self._fetch_sofascore_bundle(event_id, ttl=ttl, allow_stale=False)
            if bundle:
                with self._cache_lock:
                    self._bundle_cache[event_id] = (time.monotonic(), bundle)
                self._save_disk_cache()
                return bundle

        # 3. Cross-provider failover: resolve SofaScore match on ESPN by team names & date!
        espn_id = self._resolve_espn_event_id(event_id, hint_event=hint_event)
        if espn_id:
            espn_bundle = self.get_espn_match_bundle(espn_id, force=force)
            if espn_bundle:
                with self._cache_lock:
                    self._bundle_cache[event_id] = (time.monotonic(), espn_bundle)
                return espn_bundle

        # 4. Fallback to cached SofaScore data if available in memory/disk
        stale_bundle = self._fetch_sofascore_bundle(event_id, ttl=999999.0, allow_stale=True)
        if stale_bundle:
            with self._cache_lock:
                self._bundle_cache[event_id] = (time.monotonic(), stale_bundle)
            return stale_bundle

        return None

    def _fetch_sofascore_bundle(
        self,
        event_id: int,
        ttl: float = 15.0,
        allow_stale: bool = True,
    ) -> FullMatchBundle | None:
        endpoints = {
            "event": f"/event/{event_id}",
            "incidents": f"/event/{event_id}/incidents",
            "statistics": f"/event/{event_id}/statistics",
            "comments": f"/event/{event_id}/comments",
            "lineups": f"/event/{event_id}/lineups",
            "graph": f"/event/{event_id}/graph",
            "h2h": f"/event/{event_id}/h2h",
            "pregame": f"/event/{event_id}/pregame-form",
            "managers": f"/event/{event_id}/managers",
        }
        futures = {
            key: self._pool.submit(self.get_json, path, ttl, 5.0, allow_stale)
            for key, path in endpoints.items()
        }
        results = {key: fut.result() for key, fut in futures.items()}

        ev_payload = results.get("event")
        if not ev_payload or not ev_payload.get("event"):
            return None

        match_event = MatchEvent.from_dict(ev_payload["event"])
        mgr_payload = results.get("managers") or {}
        if not match_event.home_manager and isinstance(mgr_payload.get("homeManager"), dict):
            match_event.home_manager = str(mgr_payload["homeManager"].get("name") or "")
        if not match_event.away_manager and isinstance(mgr_payload.get("awayManager"), dict):
            match_event.away_manager = str(mgr_payload["awayManager"].get("name") or "")
        self._register_events([match_event])

        incidents: list[IncidentItem] = []
        inc_payload = results.get("incidents")
        if inc_payload and isinstance(inc_payload.get("incidents"), list):
            incidents = [IncidentItem.from_dict(x) for x in inc_payload["incidents"]]

        period_stats: list[PeriodStats] = []
        stat_payload = results.get("statistics")
        if stat_payload and isinstance(stat_payload.get("statistics"), list):
            for p_raw in stat_payload["statistics"]:
                period_name = str(p_raw.get("period") or "ALL")
                groups: list[StatGroup] = []
                for g_raw in p_raw.get("groups") or []:
                    g_name = str(g_raw.get("groupName") or "Stats")
                    items = [StatItem.from_dict(it) for it in (g_raw.get("statisticsItems") or [])]
                    groups.append(StatGroup(group_name=g_name, items=items))
                period_stats.append(PeriodStats(period=period_name, groups=groups))

        comments: list[CommentItem] = []
        comm_payload = results.get("comments")
        if comm_payload and isinstance(comm_payload.get("comments"), list):
            comments = [CommentItem.from_dict(c) for c in comm_payload["comments"]]

        lineups = self._parse_lineups(results.get("lineups"), incidents)

        momentum: list[MomentumPoint] = []
        graph_payload = results.get("graph")
        if graph_payload and isinstance(graph_payload.get("graphPoints"), list):
            for pt in graph_payload["graphPoints"]:
                try:
                    momentum.append(
                        MomentumPoint(
                            minute=float(pt.get("minute") or 0.0),
                            value=float(pt.get("value") or 0.0),
                        )
                    )
                except (TypeError, ValueError):
                    pass

        h2h = H2HInfo()
        h2h_payload = results.get("h2h")
        if h2h_payload and isinstance(h2h_payload.get("teamDuel"), dict):
            td = h2h_payload["teamDuel"]
            h2h.home_wins = int(td.get("homeWins") or 0)
            h2h.draws = int(td.get("draws") or 0)
            h2h.away_wins = int(td.get("awayWins") or 0)

        pre_payload = results.get("pregame")
        if pre_payload:
            ht = pre_payload.get("homeTeam") or {}
            at = pre_payload.get("awayTeam") or {}
            h2h.home_form = [str(x) for x in (ht.get("form") or [])]
            h2h.away_form = [str(x) for x in (at.get("form") or [])]
            h2h.home_avg_rating = str(ht.get("avgRating") or "")
            h2h.away_avg_rating = str(at.get("avgRating") or "")
            h2h.home_position = ht.get("position")
            h2h.away_position = at.get("position")
            h2h.home_points = str(ht.get("value") or "")
            h2h.away_points = str(at.get("value") or "")

        standings_rows: list[StandingRow] = []
        standings_name = ""
        ut_id = match_event.tournament.unique_id
        s_id = match_event.tournament.season_id
        if ut_id and s_id:
            st_payload = self.get_json(
                f"/unique-tournament/{ut_id}/season/{s_id}/standings/total",
                ttl=120.0,
                allow_stale=allow_stale,
            )
            if st_payload and isinstance(st_payload.get("standings"), list) and st_payload["standings"]:
                chosen_group = st_payload["standings"][0]
                for grp in st_payload["standings"]:
                    row_team_ids = {int((r.get("team") or {}).get("id") or 0) for r in (grp.get("rows") or [])}
                    if match_event.home_team.id in row_team_ids or match_event.away_team.id in row_team_ids:
                        chosen_group = grp
                        break
                standings_name = str(chosen_group.get("name") or match_event.tournament.name)
                for r in chosen_group.get("rows") or []:
                    t_info = r.get("team") or {}
                    promo = r.get("promotion") or {}
                    standings_rows.append(
                        StandingRow(
                            position=int(r.get("position") or 0),
                            team_id=int(t_info.get("id") or 0),
                            team_name=str(t_info.get("name") or ""),
                            team_short=str(t_info.get("shortName") or t_info.get("name") or ""),
                            matches=int(r.get("matches") or 0),
                            wins=int(r.get("wins") or 0),
                            draws=int(r.get("draws") or 0),
                            losses=int(r.get("losses") or 0),
                            scores_for=int(r.get("scoresFor") or 0),
                            scores_against=int(r.get("scoresAgainst") or 0),
                            score_diff=str(r.get("scoreDiffFormatted") or "0"),
                            points=int(r.get("points") or 0),
                            promotion_text=str(promo.get("text") or ""),
                        )
                    )

        return FullMatchBundle(
            event=match_event,
            incidents=incidents,
            statistics=period_stats,
            comments=comments,
            lineups=lineups,
            momentum=momentum,
            standings=standings_rows,
            standings_name=standings_name,
            h2h=h2h,
        )

    def _parse_lineups(
        self, payload: dict[str, Any] | None, incidents: list[IncidentItem]
    ) -> MatchLineups | None:
        if not payload or ("home" not in payload and "away" not in payload):
            return None

        def build_team(side_raw: dict[str, Any] | None) -> TeamLineup:
            if not side_raw:
                return TeamLineup()
            players = [PlayerLineup.from_dict(p) for p in (side_raw.get("players") or [])]
            missing: list[MissingPlayer] = []
            for m in side_raw.get("missingPlayers") or []:
                mp = m.get("player") or {}
                missing.append(
                    MissingPlayer(
                        name=str(mp.get("name") or ""),
                        short_name=str(mp.get("shortName") or mp.get("name") or ""),
                        reason=str(m.get("description") or m.get("reason") or "Injured/Out"),
                        status_type=str(m.get("type") or "missing"),
                    )
                )
            return TeamLineup(
                formation=str(side_raw.get("formation") or ""),
                players=players,
                missing_players=missing,
            )

        home_lu = build_team(payload.get("home"))
        away_lu = build_team(payload.get("away"))

        all_players = home_lu.players + away_lu.players
        for inc in incidents:
            if inc.incident_type == "card":
                for p in all_players:
                    if inc.player_name and (p.name == inc.player_name or p.short_name == inc.player_short):
                        if "red" in inc.incident_class.lower():
                            p.red_cards += 1
                        else:
                            p.yellow_cards += 1
            elif inc.incident_type == "substitution":
                for p in all_players:
                    if inc.player_in_name and (p.short_name == inc.player_in_name or p.name == inc.player_in_name):
                        p.subbed_in = inc.time
                    if inc.player_out_name and (p.short_name == inc.player_out_name or p.name == inc.player_out_name):
                        p.subbed_out = inc.time
                        if inc.is_injury_sub:
                            p.subbed_out_injured = True

        return MatchLineups(
            confirmed=bool(payload.get("confirmed")),
            home=home_lu,
            away=away_lu,
        )

    def search_matches_and_teams(self, query: str) -> tuple[list[dict[str, Any]], list[MatchEvent]]:
        """Search SofaScore or recent ESPN days for teams/tournaments/matches."""
        q = query.strip()
        if not q:
            return [], []

        if time.monotonic() >= self._sofascore_cooldown_until:
            encoded = urllib.parse.quote(q)
            data = self.get_json(f"/search/all?q={encoded}", ttl=60.0, allow_stale=False)
            if data and isinstance(data.get("results"), list):
                entities: list[dict[str, Any]] = []
                direct_events: list[MatchEvent] = []
                top_team_id: int | None = None

                for item in data["results"]:
                    rtype = str(item.get("type") or "")
                    ent = item.get("entity") or {}
                    sport = (ent.get("sport") or (ent.get("category") or {}).get("sport") or {}).get("slug")
                    if sport and sport != "football":
                        continue
                    if rtype == "event" and ent.get("id"):
                        direct_events.append(MatchEvent.from_dict(ent))
                    elif rtype in ("team", "uniqueTournament", "player"):
                        entities.append({"type": rtype, "entity": ent})
                        if rtype == "team" and top_team_id is None:
                            top_team_id = int(ent.get("id") or 0)

                team_matches: list[MatchEvent] = list(direct_events)
                if top_team_id:
                    last_data = self.get_json(f"/team/{top_team_id}/events/last/0", ttl=60.0)
                    next_data = self.get_json(f"/team/{top_team_id}/events/next/0", ttl=60.0)
                    last_evs = [MatchEvent.from_dict(e) for e in ((last_data or {}).get("events") or [])[-8:]]
                    next_evs = [MatchEvent.from_dict(e) for e in ((next_data or {}).get("events") or [])[:5]]
                    seen = {m.id for m in team_matches}
                    for m in reversed(last_evs + next_evs):
                        if m.id not in seen:
                            seen.add(m.id)
                            team_matches.append(m)
                if team_matches:
                    self._register_events(team_matches)
                    return entities[:12], team_matches[:20]

        # ESPN fallback search across recent & upcoming 7-day window
        ql = q.lower()
        found_matches: list[MatchEvent] = []
        base_day = datetime.date.today()
        for delta in (0, -1, -2, -3, 1, 2):
            dt_s = (base_day + datetime.timedelta(days=delta)).isoformat()
            for m in self.get_espn_matches_for_date(dt_s):
                hay = f"{m.home_team.name} {m.away_team.name} {m.tournament.name} {m.tournament.category_name}".lower()
                if ql in hay:
                    found_matches.append(m)
        return [], found_matches[:25]
