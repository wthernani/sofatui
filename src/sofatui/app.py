"""SofaTUI Textual Application — SofaScore in your terminal."""

from __future__ import annotations

import argparse
import datetime
import sys
import time
from typing import Any

from rich.align import Align
from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Footer, Input, Label, OptionList, Static
from textual.widgets.option_list import Option

from sofatui.api import SofaScoreClient
from sofatui.favorites import FavoritesStore
from sofatui.models import FullMatchBundle, MatchEvent, sanitize_hex_color
from sofatui.renderers import (
    render_commentary_tab,
    render_lineups_tab,
    render_overview_tab,
    render_scoreboard_banner,
    render_standings_tab,
    render_statistics_tab,
)


HELP_TEXT = """[bold #00e676]⚽ SofaTUI — Keyboard Shortcuts & Guide[/]

[bold #38bdf8]Navigation & Match List[/]
  [bold #ffd166]↑ / ↓[/]         Move up / down in the match list
  [bold #ffd166]Enter[/]         Open full Match Center for selected match
  [bold #ffd166]h / l[/] or [bold #ffd166]\\[ / ][/] Previous day (-1d) / Next day (+1d)
  [bold #ffd166]t[/]             Jump to Today's matches
  [bold #ffd166]/[/]             Search matches locally (press [bold]Enter[/] in search box for Global SofaScore team/match search)
  [bold #ffd166]Esc[/]           Clear search filter & return focus to match list

[bold #38bdf8]Match Filters & Favorites[/]
  [bold #ffd166]a[/]             Show ALL matches for active date
  [bold #ffd166]v[/]             Show ● LIVE matches only (worldwide live feed)
  [bold #ffd166]f[/]             Show FINISHED matches only
  [bold #ffd166]u[/]             Show UPCOMING matches only
  [bold #ffd166]s[/]             Show ★ STARRED / Pinned matches & teams
  [bold #ffd166]m[/]             Toggle ★ Star/Pin on the currently active match

[bold #38bdf8]Match Center Tabs & Deep Controls[/]
  [bold #ffd166]1[/]             ⚡ Overview, Attack Momentum Graph & Timeline
  [bold #ffd166]2[/]             ▤ Full SofaScore Match Statistics (xG, Shots, Passes, Duels)
  [bold #ffd166]3[/]             ⊞ 2D Tactical Pitch, Lineups & SofaScore Player Ratings
  [bold #ffd166]4[/]             » Live Play-by-Play Text Commentary
  [bold #ffd166]5[/]             🏆 Live League Standings & Head-to-Head (H2H)
  [bold #ffd166]p[/]             Cycle Statistics Period ([bold]ALL[/] / [bold]1ST[/] / [bold]2ND[/] half)
  [bold #ffd166]n / N[/]         Cycle Next / Previous Player in Lineups Inspector for full individual stats
  [bold #ffd166]k[/]             Toggle Key Commentary Highlights vs All Play-by-Play
  [bold #ffd166]r[/]             Refresh live scores and active match details now
  [bold #ffd166]q[/]             Quit SofaTUI
"""


class HelpModal(ModalScreen[None]):
    """Modal screen showing keyboard shortcuts."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
        Binding("question_mark", "dismiss", "Close"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="help-dialog"):
            yield Static(
                Panel(
                    Text.from_markup(HELP_TEXT),
                    border_style="#00e676",
                    padding=(1, 2),
                )
            )
            yield Label("Press Esc or ? to close", id="help-close-hint")


def format_match_option_label(
    ev: MatchEvent,
    now_ts: float,
    is_starred: bool = False,
    show_date: bool = False,
) -> Text:
    """Format a single match row for the left sidebar OptionList."""
    row = Text()
    row.append("★ " if is_starred else "  ", style="bold #ffd166")

    if show_date:
        dt_short = datetime.datetime.fromtimestamp(ev.start_timestamp).strftime("%d/%m ")
        row.append(dt_short, style="dim #64748b")

    clock = ev.live_minute_str(now_ts)
    if ev.is_live:
        row.append(f"● {clock:<6}", style="bold #00e676")
    elif ev.is_finished:
        row.append(f"  {clock:<6}", style="dim #94a3b8")
    else:
        row.append(f"  {clock:<6}", style="#38bdf8")

    h_name = ev.home_team.short_name[:14]
    a_name = ev.away_team.short_name[:14]

    h_style = "bold #ffffff" if ev.winner_code == 1 else ("#cbd5e1" if ev.winner_code == 2 else "#f1f5f9")
    a_style = "bold #ffffff" if ev.winner_code == 2 else ("#cbd5e1" if ev.winner_code == 1 else "#f1f5f9")

    h_c1 = sanitize_hex_color(ev.home_team.color_primary, "#38bdf8")
    a_c1 = sanitize_hex_color(ev.away_team.color_primary, "#38bdf8")

    row.append("▌", style=f"bold {h_c1}")
    row.append(" ")
    if ev.home_team.red_cards > 0:
        h_short = h_name[:12]
        row.append(h_short, style=h_style)
        row.append(" ■", style="bold #ff1744")
        row.append(" " * max(0, 14 - len(h_short) - 2))
    else:
        row.append(f"{h_name:<14}", style=h_style)

    h_sc = ev.home_score.display if ev.home_score.display is not None else ev.home_score.current
    a_sc = ev.away_score.display if ev.away_score.display is not None else ev.away_score.current
    if ev.is_upcoming and h_sc is None:
        row.append("  vs   ", style="dim #64748b")
    else:
        score_str = f" {h_sc if h_sc is not None else 0}-{a_sc if a_sc is not None else 0} "
        sc_style = "bold #00e676" if ev.is_live else "bold #ffd166"
        row.append(f"{score_str:^7}", style=sc_style)

    row.append("▌", style=f"bold {a_c1}")
    row.append(" ")
    if ev.away_team.red_cards > 0:
        a_short = a_name[:12]
        row.append(a_short, style=a_style)
        row.append(" ■", style="bold #ff1744")
        row.append(" " * max(0, 14 - len(a_short) - 2))
    else:
        row.append(f"{a_name:<14}", style=a_style)

    if ev.home_score.aggregated is not None and ev.away_score.aggregated is not None:
        row.append(f" ({ev.home_score.aggregated}-{ev.away_score.aggregated})", style="dim #38bdf8")
    return row


class SofaTuiApp(App[None]):
    """SofaScore-style Terminal User Interface for football scores, stats, lineups, and commentary."""

    TITLE = "SofaTUI — Football Live Scores, Stats & Match Center"

    CSS = """
    Screen {
        background: #0b0e14;
        color: #e2e8f0;
    }

    #top-bar {
        height: 3;
        background: #111722;
        border-bottom: solid #1e293b;
        padding: 0 1;
        align: left middle;
    }

    #brand-label {
        width: auto;
        content-align: left middle;
        padding-right: 2;
    }

    #date-status-label {
        width: 1fr;
        content-align: center middle;
    }

    #search-input {
        width: 38;
        background: #0b0e14;
        border: tall #1e293b;
        color: #f8fafc;
    }

    #search-input:focus {
        border: tall #00e676;
    }

    #main-split {
        height: 1fr;
        width: 100%;
    }

    #left-pane {
        width: 56;
        height: 100%;
        background: #0f141d;
        border-right: solid #1e293b;
    }

    #filter-strip {
        height: 2;
        padding: 0 1;
        background: #131b28;
        border-bottom: solid #1e293b;
        content-align: left middle;
    }

    #matches-list {
        height: 1fr;
        background: #0f141d;
        border: none;
        padding: 0;
    }

    #matches-list:focus {
        border: none;
    }

    #right-pane {
        width: 1fr;
        height: 100%;
        background: #0b0e14;
        padding: 0 1;
    }

    #scoreboard-header {
        height: auto;
        margin-top: 0;
    }

    #tabs-bar {
        height: 2;
        background: #131b28;
        border-bottom: solid #1e293b;
        content-align: center middle;
        margin-bottom: 0;
    }

    #detail-scroll {
        height: 1fr;
        background: #0b0e14;
        border: none;
        padding: 0 1;
    }

    #status-line {
        height: 1;
        background: #111722;
        color: #94a3b8;
        padding: 0 1;
    }

    #help-dialog {
        width: 78;
        height: auto;
        background: #111722;
        border: thick #00e676;
        padding: 1 2;
        align: center middle;
    }

    #help-close-hint {
        width: 100%;
        text-align: center;
        color: #94a3b8;
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("1", "tab_1", "Overview", show=True),
        Binding("2", "tab_2", "Stats", show=True),
        Binding("3", "tab_3", "Lineups/Pitch", show=True),
        Binding("4", "tab_4", "Commentary", show=True),
        Binding("5", "tab_5", "Standings", show=True),
        Binding("v", "filter_live", "Live", show=True),
        Binding("a", "filter_all", "All", show=True),
        Binding("f", "filter_finished", "FT", show=False),
        Binding("u", "filter_upcoming", "Upcoming", show=False),
        Binding("s", "filter_starred", "★Starred", show=True),
        Binding("m", "toggle_star", "Pin Match", show=True),
        Binding("h", "prev_day", "-1d", show=True),
        Binding("l", "next_day", "+1d", show=True),
        Binding("left_square_bracket", "prev_day", "-1d", show=False),
        Binding("right_square_bracket", "next_day", "+1d", show=False),
        Binding("t", "today", "Today", show=False),
        Binding("p", "cycle_period", "Period", show=False),
        Binding("n", "next_player", "Next Player", show=False),
        Binding("N", "prev_player", "Prev Player", show=False),
        Binding("k", "toggle_key_comments", "Key Comm", show=False),
        Binding("slash", "focus_search", "Search", show=True),
        Binding("escape", "clear_search", "Clear", show=False),
        Binding("r", "refresh_now", "Refresh", show=True),
        Binding("question_mark", "show_help", "Help", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    active_date: reactive[datetime.date] = reactive(datetime.date.today)
    active_filter: reactive[str] = reactive("all")  # "all", "live", "finished", "upcoming", "starred", "search"
    active_tab: reactive[int] = reactive(1)         # 1..5
    stat_period: reactive[str] = reactive("ALL")    # "ALL", "1ST", "2ND"
    selected_player_idx: reactive[int] = reactive(0)
    key_comments_only: reactive[bool] = reactive(False)

    def __init__(
        self,
        initial_date: datetime.date | None = None,
        initial_match_id: int | None = None,
    ) -> None:
        super().__init__()
        self.client = SofaScoreClient()
        self.favorites = FavoritesStore()
        self._initial_date = initial_date or datetime.date.today()
        self._initial_match_id = initial_match_id
        self._all_matches: list[MatchEvent] = []
        self._displayed_matches: dict[str, MatchEvent] = {}
        self._current_bundle: FullMatchBundle | None = None
        self._current_match_id: int | None = initial_match_id
        self._local_query: str = ""
        self._previous_scores: dict[int, tuple[int | None, int | None]] = {}
        self._rebuilding_list: bool = False
        self._highlight_timer: Any = None

    def compose(self) -> ComposeResult:
        with Horizontal(id="top-bar"):
            yield Static(
                Text.from_markup("[bold #0b132b on #00e676] ⚽ SOFATUI [/] [bold #38bdf8]LIVE CENTER[/]"),
                id="brand-label",
            )
            yield Static("", id="date-status-label")
            yield Input(placeholder="[/] Filter or Enter for Global Search...", id="search-input")

        with Horizontal(id="main-split"):
            with Vertical(id="left-pane"):
                yield Static("", id="filter-strip")
                yield OptionList(id="matches-list")
            with Vertical(id="right-pane"):
                yield Static("", id="scoreboard-header")
                yield Static("", id="tabs-bar")
                with VerticalScroll(id="detail-scroll"):
                    yield Static(
                        Panel(
                            Align.center(Text("Loading matches from SofaScore...", style="bold #38bdf8")),
                            border_style="#1e293b",
                        ),
                        id="detail-content",
                    )

        yield Static("Initializing SofaScore feed...", id="status-line")
        yield Footer()

    def on_mount(self) -> None:
        self.active_date = self._initial_date
        self.query_one("#matches-list", OptionList).focus()
        self._update_header_bars()
        self.load_matches_worker(force=False)
        self.set_interval(30.0, self._auto_refresh_tick)

    def _auto_refresh_tick(self) -> None:
        if self.active_filter in ("live", "all") and self.active_date == datetime.date.today():
            self.load_matches_worker(force=True, silent=True)
        if self._current_bundle and self._current_bundle.event.is_live and self._current_match_id:
            self.load_match_detail_worker(self._current_match_id, force=True, silent=True)

    def _update_header_bars(self) -> None:
        # Date & count bar
        date_str = self.active_date.strftime("%a %d %b %Y")
        is_today = self.active_date == datetime.date.today()
        date_txt = Text()
        date_txt.append("◀ [h]  ", style="dim #94a3b8")
        date_txt.append(f"◆ {date_str}", style="bold #f8fafc")
        if is_today:
            date_txt.append(" ")
            date_txt.append(" TODAY ", style="bold #0b132b on #00e676")
        date_txt.append("  [l] ▶", style="dim #94a3b8")
        self.query_one("#date-status-label", Static).update(date_txt)

        # Filter pills strip
        live_count = sum(1 for m in self._all_matches if m.is_live)
        ft_count = sum(1 for m in self._all_matches if m.is_finished)
        up_count = sum(1 for m in self._all_matches if m.is_upcoming)
        star_count = sum(
            1
            for m in self._all_matches
            if self.favorites.is_match_starred(m.id, m.home_team.id, m.away_team.id)
        )

        pills = [
            ("all", f"[a] ALL ({len(self._all_matches)})"),
            ("live", f"[v] ● LIVE ({live_count})"),
            ("finished", f"[f] FT ({ft_count})"),
            ("upcoming", f"[u] NEXT ({up_count})"),
            ("starred", f"[s] ★ ({star_count})"),
        ]
        strip = Text()
        for key, label in pills:
            if self.active_filter == key:
                style = "bold #0b132b on #00e676" if key != "live" else "bold #ffffff on #e11d48"
                strip.append(f" {label} ", style=style)
            else:
                strip.append(f" {label} ", style="dim #cbd5e1")
            strip.append(" ")
        self.query_one("#filter-strip", Static).update(strip)

        # Right pane tabs bar
        tab_defs = [
            (1, "1 ⚡ Overview & Momentum"),
            (2, "2 ▤ Statistics"),
            (3, "3 ⊞ Lineups & Pitch"),
            (4, "4 » Commentary"),
            (5, "5 ★ Standings & H2H"),
        ]
        t_bar = Text()
        for idx, t_label in tab_defs:
            if self.active_tab == idx:
                t_bar.append(f"  {t_label}  ", style="bold #0b132b on #38bdf8")
            else:
                t_bar.append(f"  {t_label}  ", style="bold #94a3b8 on #131b28")
            t_bar.append(" ")
        self.query_one("#tabs-bar", Static).update(t_bar)

    def _set_status(self, message: str) -> None:
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        self.query_one("#status-line", Static).update(
            Text.from_markup(f"[bold #00e676]● ONLINE[/] • {message} • [dim]Updated {now_str} • Press '?' for shortcuts[/]")
        )

    @work(exclusive=True, group="load_matches", thread=True)
    def load_matches_worker(self, force: bool = False, silent: bool = False) -> None:
        if not silent:
            self.call_from_thread(self._set_status, f"Fetching matches for {self.active_date.isoformat()}...")
        t0 = time.monotonic()
        if self.active_filter == "live":
            matches = self.client.get_live_matches(force=force)
        else:
            matches = self.client.get_matches_for_date(self.active_date.isoformat(), force=force)
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        self.call_from_thread(self._on_matches_loaded, matches, elapsed_ms, silent)

    def _on_matches_loaded(self, matches: list[MatchEvent], elapsed_ms: float, silent: bool) -> None:
        if not matches and self._all_matches:
            self._set_status("Refresh returned no new events; keeping current match feed.")
            return

        # Check for live goal notifications!
        for m in matches:
            h_sc = m.home_score.display if m.home_score.display is not None else m.home_score.current
            a_sc = m.away_score.display if m.away_score.display is not None else m.away_score.current
            prev = self._previous_scores.get(m.id)
            if prev is not None and m.is_live and (h_sc, a_sc) != prev:
                if (h_sc or 0) > (prev[0] or 0) or (a_sc or 0) > (prev[1] or 0):
                    self.notify(
                        f"⚽ GOAL! {m.home_team.short_name} {h_sc} - {a_sc} {m.away_team.short_name} ({m.tournament.name})",
                        title="Live Goal Alert",
                        severity="information",
                    )
            self._previous_scores[m.id] = (h_sc, a_sc)

        self._all_matches = matches
        self._rebuild_option_list(preserve_selection=True)
        self._update_header_bars()
        self._set_status(
            f"Loaded {len(matches)} matches ({sum(1 for m in matches if m.is_live)} live) via {self.client.active_provider} in {elapsed_ms:.0f}ms"
        )

        # Auto-select initial or first match if none loaded yet
        if self._current_match_id and self._current_bundle is None:
            self.load_match_detail_worker(self._current_match_id, force=False)
        elif self._current_bundle is None and self._displayed_matches:
            first_ev = next(iter(self._displayed_matches.values()))
            self._current_match_id = first_ev.id
            self.load_match_detail_worker(first_ev.id, force=False)

    def _rebuild_option_list(self, preserve_selection: bool = True, show_date: bool = False) -> None:
        opt_list = self.query_one("#matches-list", OptionList)
        prev_opt_id: str | None = None
        if preserve_selection and opt_list.highlighted is not None:
            try:
                prev_opt_id = opt_list.get_option_at_index(opt_list.highlighted).id
            except Exception:
                prev_opt_id = None

        filtered: list[MatchEvent] = []
        q_lower = self._local_query.lower().strip()
        for m in self._all_matches:
            if self.active_filter == "live" and not m.is_live:
                continue
            if self.active_filter == "finished" and not m.is_finished:
                continue
            if self.active_filter == "upcoming" and not m.is_upcoming:
                continue
            if self.active_filter == "starred" and not self.favorites.is_match_starred(
                m.id, m.home_team.id, m.away_team.id
            ):
                continue
            if q_lower:
                haystack = f"{m.home_team.name} {m.away_team.name} {m.tournament.name} {m.tournament.category_name}".lower()
                if q_lower not in haystack:
                    continue
            filtered.append(m)

        # Sort starred matches to top if in 'all' mode, else group by tournament priority
        self._rebuilding_list = True
        try:
            self._displayed_matches.clear()

            if not filtered:
                opt_list.set_options(
                    [
                        Option(
                            Text("No matches match the current filter. Press 'a' for All or 'h'/'l' to change date.", style="dim #94a3b8"),
                            id="empty",
                            disabled=True,
                        )
                    ]
                )
                return

            now_ts = time.time()
            current_league_key: str | None = None
            target_highlight_idx: int | None = None
            opt_idx = 0
            new_options: list[Option] = []

            for m in filtered:
                league_key = f"{m.tournament.category_name} • {m.tournament.name}"
                if league_key != current_league_key:
                    current_league_key = league_key
                    hdr_txt = Text(f"🏆 {league_key}", style="bold #38bdf8 on #162032")
                    new_options.append(Option(hdr_txt, id=f"hdr:{opt_idx}", disabled=True))
                    opt_idx += 1

                opt_id = f"match:{m.id}"
                is_star = self.favorites.is_match_starred(m.id, m.home_team.id, m.away_team.id)
                label = format_match_option_label(m, now_ts, is_starred=is_star, show_date=show_date)
                new_options.append(Option(label, id=opt_id))
                self._displayed_matches[opt_id] = m
                if prev_opt_id == opt_id or m.id == self._current_match_id:
                    target_highlight_idx = opt_idx
                elif target_highlight_idx is None:
                    target_highlight_idx = opt_idx
                opt_idx += 1

            opt_list.set_options(new_options)
            if target_highlight_idx is not None:
                opt_list.highlighted = target_highlight_idx
        finally:
            self._rebuilding_list = False

    @work(exclusive=True, group="load_detail", thread=True)
    def load_match_detail_worker(self, event_id: int, force: bool = False, silent: bool = False) -> None:
        if not silent:
            self.call_from_thread(self._set_status, f"Loading full match center for #{event_id}...")
        t0 = time.monotonic()
        hint_ev: MatchEvent | None = None
        if self._current_bundle and self._current_bundle.event.id == event_id:
            hint_ev = self._current_bundle.event
        else:
            hint_ev = self._displayed_matches.get(f"match:{event_id}")
        bundle = self.client.get_full_match_bundle(event_id, force=force, hint_event=hint_ev)
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        self.call_from_thread(self._on_bundle_loaded, bundle, elapsed_ms, event_id)

    def _on_bundle_loaded(
        self, bundle: FullMatchBundle | None, elapsed_ms: float, requested_id: int = 0
    ) -> None:
        if requested_id and self._current_match_id and requested_id != self._current_match_id:
            # User already scrolled to a different match; skip rendering stale intermediate match
            return
        if bundle is None:
            if self._current_bundle is not None:
                # Keep displaying existing bundle instead of wiping out the screen on transient error
                self._render_active_bundle()
                self._set_status("Refresh kept cached match details.")
                return
            self.query_one("#detail-content", Static).update(
                Panel(
                    Align.center(Text("Could not load details for this match.", style="bold #ef4444")),
                    border_style="#ef4444",
                )
            )
            return

        self._current_bundle = bundle
        self._current_match_id = bundle.event.id
        self._render_active_bundle()
        self._set_status(
            f"Viewing {bundle.event.home_team.short_name} vs {bundle.event.away_team.short_name} via {self.client.active_provider} ({elapsed_ms:.0f}ms)"
        )

    def on_resize(self) -> None:
        if self._current_bundle is not None:
            self._render_active_bundle()

    def _render_active_bundle(self) -> None:
        bundle = self._current_bundle
        if not bundle:
            return
        ev = bundle.event
        is_starred = self.favorites.is_match_starred(ev.id, ev.home_team.id, ev.away_team.id)
        self.query_one("#scoreboard-header", Static).update(
            render_scoreboard_banner(bundle, is_starred=is_starred)
        )
        self._update_header_bars()

        scroll_w = self.query_one("#detail-scroll").size.width
        pane_w = scroll_w if scroll_w > 45 else max(72, (self.size.width or 176) - 60)
        chart_w = max(48, min(168, pane_w - 16))

        if self.active_tab == 1:
            body: RenderableType = render_overview_tab(bundle, width=chart_w)
        elif self.active_tab == 2:
            body = render_statistics_tab(bundle, period=self.stat_period, width=pane_w)
        elif self.active_tab == 3:
            body = render_lineups_tab(bundle, selected_player_idx=self.selected_player_idx)
        elif self.active_tab == 4:
            body = render_commentary_tab(bundle, key_only=self.key_comments_only)
        elif self.active_tab == 5:
            body = render_standings_tab(bundle)
        else:
            body = render_overview_tab(bundle, width=chart_w)

        self.query_one("#detail-content", Static).update(body)

    @on(OptionList.OptionSelected, "#matches-list")
    def _on_match_selected(self, event: OptionList.OptionSelected) -> None:
        if self._highlight_timer is not None:
            self._highlight_timer.stop()
            self._highlight_timer = None
        opt_id = event.option.id or ""
        ev_obj = self._displayed_matches.get(opt_id)
        if ev_obj:
            self._current_match_id = ev_obj.id
            self.selected_player_idx = 0
            self.load_match_detail_worker(ev_obj.id, force=False)

    @on(OptionList.OptionHighlighted, "#matches-list")
    def _on_match_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        if self._rebuilding_list:
            return
        opt_id = event.option.id or ""
        ev_obj = self._displayed_matches.get(opt_id)
        if not ev_obj:
            return
        if self._initial_match_id is not None:
            if ev_obj.id != self._initial_match_id:
                return
            self._initial_match_id = None
        if ev_obj.id != self._current_match_id:
            self._current_match_id = ev_obj.id
            self.selected_player_idx = 0
            if self._highlight_timer is not None:
                self._highlight_timer.stop()
            target_id = ev_obj.id
            self._highlight_timer = self.set_timer(
                0.14,
                lambda: self.load_match_detail_worker(target_id, force=False, silent=True),
            )

    @on(Input.Changed, "#search-input")
    def _on_search_changed(self, event: Input.Changed) -> None:
        self._local_query = event.value
        self._rebuild_option_list(preserve_selection=False)

    @on(Input.Submitted, "#search-input")
    def _on_search_submitted(self, event: Input.Submitted) -> None:
        q = event.value.strip()
        if not q:
            self.query_one("#matches-list", OptionList).focus()
            return
        self.global_search_worker(q)
        self.query_one("#matches-list", OptionList).focus()

    @work(exclusive=True, group="global_search", thread=True)
    def global_search_worker(self, query: str) -> None:
        self.call_from_thread(self._set_status, f"Searching SofaScore globally for '{query}'...")
        entities, matches = self.client.search_matches_and_teams(query)
        self.call_from_thread(self._on_global_search_results, query, entities, matches)

    def _on_global_search_results(
        self, query: str, entities: list[dict[str, Any]], matches: list[MatchEvent]
    ) -> None:
        if matches:
            self._local_query = ""
            self.active_filter = "all"
            self._all_matches = matches
            self._rebuild_option_list(preserve_selection=False, show_date=True)
            self._update_header_bars()
            first = matches[0]
            self._current_match_id = first.id
            self.load_match_detail_worker(first.id, force=False)
            self._set_status(f"Global search '{query}': found {len(matches)} matches ({len(entities)} entities)")
        else:
            self.notify(f"No football matches found on SofaScore for '{query}'.", severity="warning")

    # Actions
    def action_tab_1(self) -> None:
        self.active_tab = 1
        self._render_active_bundle()

    def action_tab_2(self) -> None:
        self.active_tab = 2
        self._render_active_bundle()

    def action_tab_3(self) -> None:
        self.active_tab = 3
        self._render_active_bundle()

    def action_tab_4(self) -> None:
        self.active_tab = 4
        self._render_active_bundle()

    def action_tab_5(self) -> None:
        self.active_tab = 5
        self._render_active_bundle()

    def action_filter_all(self) -> None:
        was_live = self.active_filter == "live"
        self.active_filter = "all"
        self._update_header_bars()
        if was_live:
            self.load_matches_worker(force=False)
        else:
            self._rebuild_option_list()

    def action_filter_live(self) -> None:
        self.active_filter = "live"
        self._update_header_bars()
        self.load_matches_worker(force=True)

    def action_filter_finished(self) -> None:
        self.active_filter = "finished"
        self._update_header_bars()
        self._rebuild_option_list()

    def action_filter_upcoming(self) -> None:
        self.active_filter = "upcoming"
        self._update_header_bars()
        self._rebuild_option_list()

    def action_filter_starred(self) -> None:
        self.active_filter = "starred"
        self._update_header_bars()
        self._rebuild_option_list()

    def action_toggle_star(self) -> None:
        if not self._current_match_id:
            return
        now_starred = self.favorites.toggle_match(self._current_match_id)
        state = "Pinned ★" if now_starred else "Unpinned"
        self.notify(f"{state} match #{self._current_match_id}")
        self._rebuild_option_list(preserve_selection=True)
        self._render_active_bundle()

    def action_prev_day(self) -> None:
        self.active_date = self.active_date - datetime.timedelta(days=1)
        if self.active_filter == "live":
            self.active_filter = "all"
        self._update_header_bars()
        self.load_matches_worker(force=False)

    def action_next_day(self) -> None:
        self.active_date = self.active_date + datetime.timedelta(days=1)
        if self.active_filter == "live":
            self.active_filter = "all"
        self._update_header_bars()
        self.load_matches_worker(force=False)

    def action_today(self) -> None:
        self.active_date = datetime.date.today()
        self._update_header_bars()
        self.load_matches_worker(force=False)

    def action_cycle_period(self) -> None:
        order = ["ALL", "1ST", "2ND"]
        idx = (order.index(self.stat_period) + 1) % len(order) if self.stat_period in order else 0
        self.stat_period = order[idx]
        if self.active_tab != 2:
            self.active_tab = 2
        self._render_active_bundle()

    def action_next_player(self) -> None:
        self.selected_player_idx += 1
        if self.active_tab != 3:
            self.active_tab = 3
        self._render_active_bundle()

    def action_prev_player(self) -> None:
        self.selected_player_idx = max(0, self.selected_player_idx - 1)
        if self.active_tab != 3:
            self.active_tab = 3
        self._render_active_bundle()

    def action_toggle_key_comments(self) -> None:
        self.key_comments_only = not self.key_comments_only
        if self.active_tab != 4:
            self.active_tab = 4
        self._render_active_bundle()

    def action_focus_search(self) -> None:
        self.query_one("#search-input", Input).focus()

    def action_clear_search(self) -> None:
        inp = self.query_one("#search-input", Input)
        inp.value = ""
        self._local_query = ""
        self._rebuild_option_list()
        self.query_one("#matches-list", OptionList).focus()

    def action_refresh_now(self) -> None:
        self.client.clear_cache()
        self.load_matches_worker(force=True)
        if self._current_match_id:
            self.load_match_detail_worker(self._current_match_id, force=True)

    def action_show_help(self) -> None:
        self.push_screen(HelpModal())


def run_cli_snapshot(
    date_str: str | None = None,
    match_id: int | None = None,
    search_query: str | None = None,
) -> int:
    """Render a full Rich terminal snapshot of SofaTUI (live/daily list + all 5 Match Center tabs)."""
    console = Console(width=120)
    client = SofaScoreClient()
    target_date = date_str or datetime.date.today().isoformat()

    if search_query:
        console.print(f"[bold #00e676]⚽ SofaTUI Global Search:[/] '{search_query}'")
        _, matches = client.search_matches_and_teams(search_query)
    else:
        console.print(f"[bold #00e676]⚽ SofaTUI Live & Scheduled Matches[/] ({target_date})")
        matches = client.get_matches_for_date(target_date)
        if not matches:
            matches = client.get_live_matches()

    if matches:
        now_ts = time.time()
        preview_lines: list[RenderableType] = []
        cur_league = None
        for m in matches[:18]:
            lg = f"{m.tournament.category_name} • {m.tournament.name}"
            if lg != cur_league:
                cur_league = lg
                preview_lines.append(Text(f"\n🏆 {lg}", style="bold #38bdf8"))
            preview_lines.append(format_match_option_label(m, now_ts, show_date=bool(search_query)))
        console.print(
            Panel(
                Group(*preview_lines),
                title=f"[bold #00e676]▤ Matches Feed ({len(matches)} total)[/]",
                border_style="#1e293b",
            )
        )

    chosen_id = match_id or (matches[0].id if matches else 16363889)
    bundle = client.get_full_match_bundle(chosen_id)
    if not bundle:
        console.print(f"[bold red]Could not load match #{chosen_id}[/]")
        return 1

    console.print(render_scoreboard_banner(bundle))
    console.print(render_overview_tab(bundle))
    console.print(render_statistics_tab(bundle, period="ALL"))
    console.print(render_lineups_tab(bundle, selected_player_idx=0))
    console.print(render_commentary_tab(bundle, key_only=True))
    console.print(render_standings_tab(bundle))
    return 0


def main(argv: list[str] | None = None) -> int:
    from sofatui import __version__

    parser = argparse.ArgumentParser(
        prog="sofatui",
        description="SofaTUI: SofaScore-style Terminal UI for football scores, stats, commentary, lineups, and standings.",
    )
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--date", help="Initial date in YYYY-MM-DD format (default: today)")
    parser.add_argument("--match-id", type=int, help="Open directly to a specific SofaScore match ID")
    parser.add_argument("--search", help="Search team/tournament/match and open results")
    parser.add_argument(
        "--dump",
        action="store_true",
        help="Render a full non-interactive Rich snapshot of matches + all 5 Match Center tabs to stdout",
    )
    args = parser.parse_args(argv)

    if args.dump:
        return run_cli_snapshot(date_str=args.date, match_id=args.match_id, search_query=args.search)

    init_date = None
    if args.date:
        try:
            init_date = datetime.date.fromisoformat(args.date)
        except ValueError:
            print(f"Invalid --date '{args.date}', expected YYYY-MM-DD", file=sys.stderr)
            return 2

    app = SofaTuiApp(initial_date=init_date, initial_match_id=args.match_id)
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
