# ⚽ SofaTUI — SofaScore in Your Terminal

[![Built with Gemini 4 Argon High](https://img.shields.io/badge/AI-Gemini%204%20Argon%20High-4285F4?style=flat-square&logo=googlegemini&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Textual TUI](https://img.shields.io/badge/TUI-Textual%20%2B%20Rich-00e676?style=flat-square)](https://textual.textualize.io/)
[![Arch Linux PKGBUILD](https://img.shields.io/badge/Arch%20Linux-PKGBUILD-1793D1?style=flat-square&logo=archlinux&logoColor=white)](PKGBUILD)
[![License: MIT](https://img.shields.io/badge/License-MIT-ffd166?style=flat-square)](LICENSE)

A full-featured, fast, SofaScore-style Terminal User Interface (TUI) for live football scores, match statistics, Attack Momentum graphs, 2D tactical pitch formations, SofaScore player ratings, play-by-play commentary, and live league standings.

![SofaTUI Animated Demo](assets/demo.gif)

## 📸 Screenshots

| 1. Overview, Attack Momentum & Timeline | 3. 2D Tactical Pitch, Lineups & Ratings |
| :---: | :---: |
| ![Overview & Momentum](assets/01_overview.png) | ![2D Tactical Pitch & Lineups](assets/03_lineups_pitch.png) |

| 2. Full Match Statistics | 4. Play-by-Play Commentary & Highlights | 5. Live Standings & H2H |
| :---: | :---: | :---: |
| ![Match Statistics](assets/02_statistics.png) | ![Commentary & Highlights](assets/04_commentary.png) | ![Live Standings](assets/05_standings.png) |

## ✨ Features

- **Dual-Engine Real-Time Football Data (SofaScore + ESPN)**:
  - Live matches worldwide & daily scheduled fixtures across 100+ leagues (UEFA Champions League, Europa League, Conference League, Copa Libertadores, Copa Sudamericana, Premier League, LaLiga, Serie A, Bundesliga, Ligue 1, Liga Portugal, Brasileirão, etc.).
  - Low-latency HTTP pipeline with automatic cross-provider failover, in-memory bundle caching, and XDG persistent disk caching (`~/.cache/sofatui/`).
- **Rich Scoreboard & Match Header**:
  - Low-res Unicode half-block **club crests** (`6×5` sub-pixel rendering) and **club country codes** (`FRA • France`, `ESP • Spain`, `POR • Portugal`).
  - **Competition stage, leg & aggregate scores** for two-legged knockout ties (`Semifinals • 2nd Leg • AGG: 2 - 3 (1st Leg: 1 - 0)`).
  - **Match referee & nationality** (`⚖ Ref: Michael Oliver (ENG)`), venue, attendance, halftime/stoppage time (`1H +3' / 2H +3'`), and expected goals (`xG`).
- **5-Tab SofaScore Match Center**:
  1. **`[1]` ⚡ Overview & Attack Momentum**:
     - **SofaScore Attack Momentum Graph**: Full-width minute-by-minute (`1'`–`90+'`) bi-directional pressure chart colored in each club's **actual jersey colors** (with automatic contrast resolution) and goal (`⚽`) / card (`🟥`) markers.
     - **Chronological Match Timeline**: 1st Half / 2nd Half / Extra Time incidents including Goals, Assists, Yellow/Red Cards, **Injury-Forced (`✚ INJ` / `✚▼`) vs Tactical (`▲` / `▼`) Substitutions**, VAR decisions, and **Announced Stoppage / Additional Time (`+3'`)**.
     - **Team Form & H2H**: Recent 5-match `W`/`D`/`L` badges and historical Head-to-Head record.
  2. **`[2]` 📊 Full Match Statistics**:
     - Switch between **`ALL`**, **`1ST`**, and **`2ND`** half (`p` key).
     - Proportional dual-bar visual comparisons for *Match Overview*, *Shots*, *Attack*, *Passes*, *Duels*, *Defending*, and *Goalkeeping* (Ball Possession, Expected Goals `xG`, Big Chances, Shots on Target, Touches in Box, Accurate Passes, Tackles, Saves, etc.).
  3. **`[3]` 🏟 2D Tactical Pitch, Lineups & Player Ratings**:
     - **2D Tactical Pitch**: Starting XIs arranged in their actual formations (`4-3-3`, `4-2-3-1`, etc.) with shirt numbers, incident icons (`⚽👟🟨🟥`), and **color-coded SofaScore Rating Badges** (`9.0+` blue, `8.0+` emerald, `7.0+` green, `6.5+` yellow, `<6.0` red) + `★` Player of the Match (`MOTM`).
     - **Interactive Player Stats Inspector**: Cycle through players with `n` / `N` to inspect individual match stats (Minutes, Goals, Assists, xG, xA, Shots, Touches, Accurate Passes, Key Passes, Crosses, Duels Won, Dribbles, Tackles, Interceptions, Clearances, Saves).
     - **Full Bench & Injured/Missing Players** lists.
  4. **`[4]` 🎙 Live Play-by-Play Commentary**:
     - Minute-by-minute text commentary with color-coded event badges (`⚽ GOAL`, `🟨 YELLOW`, `🟥 RED`, `🧤 SAVED`, `🔄 SUB`, `📺 VAR`). Press `k` to filter between *Key Highlights* and *All Play-by-Play*.
  5. **`[5]` 🏆 Live Standings & Head-to-Head**:
     - Full tournament league table with Champions League / Europa / Relegation zones, automatically highlighting the **Home** (`◀ HOME`) and **Away** (`◀ AWAY`) clubs.

## 📦 Installation (Arch Linux Native Package)

Build and install natively via `pacman` / `makepkg`:

```bash
git clone https://github.com/wthernani/sofatui.git
cd sofatui
makepkg -si
```

Once installed, run `sofatui` (or `scores-tui`) from anywhere in your terminal:

```bash
sofatui
```

## 🚀 Usage

Run the interactive TUI directly from a checkout:

```bash
./sofatui
```

Or via a local virtualenv:

```bash
./.venv/bin/sofatui
```

### CLI Options

```bash
# Launch interactive TUI for today
./sofatui

# Launch interactive TUI for a specific date
./sofatui --date 2026-10-18

# Open directly to a specific SofaScore match ID
./sofatui --match-id 16363889

# Render a non-interactive Rich snapshot of matches + all 5 Match Center tabs
./sofatui --dump --date 2026-10-18
./sofatui --dump --search "Arsenal"
```

## ⌨️ Keyboard Shortcuts

| Key | Action |
| --- | --- |
| `↑` / `↓` | Navigate match list or scroll Match Center |
| `Enter` | Load selected match into Match Center |
| `1` – `5` | Switch tabs: `1` Overview/Momentum, `2` Stats, `3` Lineups/Pitch, `4` Commentary, `5` Standings |
| `h` / `l` or `[` / `]` | Previous day (`-1d`) / Next day (`+1d`) |
| `t` | Jump to Today's matches |
| `a` / `v` / `f` / `u` / `s` | Filter: `All` / `● Live` / `Finished` / `Upcoming` / `★ Starred` |
| `m` | Pin / Star (`★`) current match to persistent favorites |
| `p` | Cycle Statistics period (`ALL` / `1ST` / `2ND` half) |
| `n` / `N` | Cycle Next / Previous Player in Lineups Inspector |
| `k` | Toggle Key Commentary Highlights vs All Commentary |
| `/` | Filter current list or press `Enter` for **Global SofaScore Search** (teams, leagues, matches) |
| `r` | Refresh live scores & current match details |
| `?` | Open keyboard shortcuts help modal |
| `q` | Quit SofaTUI |

## 🤖 Credits & Stack

- **AI Pair Programmer & Architecture**: **Gemini 4 Argon High** (Google DeepMind Antigravity)
- **Language & Runtime**: Python 3.11+ (`Textual`, `Rich`, `curl_cffi`, `httpx`)
- **Packaging**: Arch Linux native `PKGBUILD` (`pacman` / `makepkg`)
- **License**: [MIT](LICENSE)
