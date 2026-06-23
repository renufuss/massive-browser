# Multi Browser Launcher

A production-ready **desktop application** for opening many browsers at once for
website **testing, QA, monitoring and cross-browser/compatibility** work.

Built with **Python 3.12**, **Playwright (async)** and **PySide6**.

Each launched browser gets a *randomly chosen engine* (Chromium / Firefox /
WebKit), a *randomly chosen device profile* (60+ desktop, mobile and tablet
fingerprints) and an *isolated browser context* — its own viewport, screen size,
timezone, locale, language, colour-scheme and user-agent.

---

## Features

- **START** opens *N* browsers, each from a random engine + random device profile.
- Every browser runs in its **own isolated context** and opens your target URL.
- Each instance has a **unique ID, unique name** (`Browser-001`, `QA-Test-001`,
  `Monitor-001`, …) and a **unique window title**.
- **60+ device profiles** (≥ 50 required) with matching viewport, user-agent,
  platform, language and timezone.
- **Realtime log** panel (also written to `logs/session_*.log`).
- **Two dashboard views** (switch via the *View* dropdown):
  - **Table**: `ID | Name | Browser | Device Profile | Status` with colour-coded
    live status.
  - **Grid (thumbnails)**: a wall of small live previews — ideal when you launch
    dozens or 100+ browsers. Tile size is adjustable (Small / Medium / Large),
    and **clicking a tile opens an enlarged preview** with full details, a
    refresh button, and a **Show browser window** button that raises the real
    (headful) browser window. Works in headless mode too (previews come from
    `page.screenshot()`).
- **Window control** (headful): **Minimize All** button minimises every browser
  window; **Show browser window** raises a chosen one. Matched by each window's
  unique title — Windows-only (no-op on other OSes; see `services/window_control.py`).
- **Concurrent launch**: browsers start in parallel (the *Delay* only staggers
  the starts; set it to `0` to fire them all at once).
- Buttons: **START**, **STOP ALL**, **Take Screenshot All**, **Minimize All**,
  **Open Log Folder**, **Export Report**.
- **Screenshots** of every browser saved to `screenshots/browser_001.png`, …
- **CSV report** export: `instance_id, instance_name, browser_engine,
  device_profile, start_time, status`.
- Optional **headless** mode, configurable **delay** between launches and
  optional **auto-close** timer.
- Robust **error handling**: Playwright not installed, launch failure, invalid
  URL, browser crash and network timeout are all caught and surfaced in the log.

---

## Install (end users — no Python needed)

Run either installer, then launch *Multi Browser Launcher* from the Start menu /
desktop. Python, Playwright and all three browser engines are bundled — nothing
else to install:

- **`MultiBrowserLauncher-Setup.exe`** — Inno Setup installer (per-user).
- **`Multi Browser Launcher-1.0.0-win64.msi`** — MSI (per-user), for managed/
  silent deployment: `msiexec /i "Multi Browser Launcher-1.0.0-win64.msi" /qn`.

## Build the installers yourself

From a checkout with the dev setup below (and Playwright browsers installed):

```bash
packaging\build.bat
```

This generates the icon, bundles everything with **PyInstaller** (onedir), then
produces both installers into `dist\`:

- the `.exe` via [Inno Setup](https://jrsoftware.org) (skipped if `iscc` isn't on PATH);
- the `.msi` via **cx_Freeze** (`python setup_msi.py bdist_msi`, no extra tools).

Sanity-check a frozen build with `MultiBrowserLauncher.exe --selftest` (launches a
bundled browser headless and writes `%TEMP%\mbl_selftest.txt`).

## Installation (development)

Requires **Python 3.12+**.

```bash
# 1. (recommended) create a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 2. install Python dependencies
pip install -r requirements.txt

# 3. download the browser binaries used by Playwright (one-time, ~hundreds of MB)
python -m playwright install
#   or just a subset, e.g.:  python -m playwright install chromium firefox webkit
```

## Running

```bash
python main.py
```

1. Enter the **target URL** (a missing scheme is auto-prefixed with `https://`).
2. Set the **number of browsers**.
3. Toggle **Headless** on/off.
4. Set the **delay** between launches (seconds).
5. Optionally set **Auto close** (minutes; `0` = disabled).
6. Click **START**.

Use **Take Screenshot All** while browsers are running, **Export Report** to save
a CSV, and **STOP ALL** (or close the window) to shut everything down cleanly.

---

## Example UI (layout)

```
┌─ Multi Browser Launcher ────────────────────────────────────────────────┐
│ Configuration                                                            │
│   Target URL:            [ https://example.com                        ]  │
│   Number of browsers:    [ 3        ]                                     │
│   Headless:              [x] Run browsers headless (no visible window)   │
│   Delay between launches:[ 1.0 s    ]                                     │
│   Auto close (optional): [ 0 min    ]                                     │
│                                                                          │
│ [ START ] [ STOP ALL ] [ Take Screenshot All ] [ Open Log Folder ] [Export]│
│                                                                          │
│ Dashboard                                                                │
│  ┌────┬────────────┬──────────┬───────────────────────┬──────────┐       │
│  │ ID │ Name       │ Browser  │ Device Profile        │ Status   │       │
│  ├────┼────────────┼──────────┼───────────────────────┼──────────┤       │
│  │ 1  │ Browser-001│ Chromium │ Google Pixel 8        │ Running  │       │
│  │ 2  │ Browser-002│ Firefox  │ Windows 11 - Chrome…  │ Running  │       │
│  │ 3  │ Browser-003│ Webkit   │ iPhone 15 Pro         │ Running  │       │
│  └────┴────────────┴──────────┴───────────────────────┴──────────┘       │
│                                                                          │
│ Realtime Log                                                             │
│  [10:01:01] Browser-001 launched  (chromium - Google Pixel 8)            │
│  [10:01:01] Browser-001 loaded page                                      │
│  [10:01:02] Browser-002 launched  (firefox - Windows 11 - Chrome FHD)    │
│  [10:01:02] Browser-002 loaded page                                      │
└──────────────────────────────────────────────────────────────────────────┘
```

> A live screenshot is produced the first time you click **Take Screenshot All**
> (saved under `screenshots/`).

---

## Project structure

```
project/
├── main.py                      # Entry point: builds QApplication + MainWindow
│
├── ui/
│   ├── main_window.py           # PySide6 window: form, buttons, table, log
│   ├── preview_view.py          # Thumbnail grid + enlarged preview dialog
│   └── styles.py                # Shared status->colour helper
│
├── browser/
│   ├── models.py                # BrowserInstance dataclass
│   ├── device_profiles.py       # 60+ DeviceProfile entries + random pools
│   ├── browser_factory.py       # Builds instances + Playwright context options
│   └── browser_manager.py       # Async orchestrator (launch/screenshot/stop)
│
├── services/
│   ├── logger.py                # Thread-safe file + signal logger
│   ├── async_runner.py          # Background asyncio loop (GUI<->async bridge)
│   ├── window_control.py        # OS window minimise/raise by title (Windows)
│   └── report_exporter.py       # CSV report writer
│
├── config/
│   └── settings.py              # Paths, constants, RunConfig value object
│
├── screenshots/                 # Output: browser_NNN.png
├── logs/                        # Output: session_YYYYmmdd_HHMMSS.log
├── reports/                     # Output: report_*.csv
└── requirements.txt
```

### Architecture in one picture

```
   GUI thread (Qt)                         Worker thread (asyncio)
 ┌──────────────────┐   submit(coro)     ┌────────────────────────┐
 │   MainWindow     │ ─────────────────► │     AsyncRunner loop    │
 │  (widgets only)  │                    │  ┌──────────────────┐   │
 │                  │ ◄───── signals ─── │  │  BrowserManager  │   │
 │  slots update    │  (queued, safe)    │  │  + Playwright    │   │
 │  table / log     │                    │  └──────────────────┘   │
 └──────────────────┘                    └────────────────────────┘
```

The GUI **never** runs async/Playwright code; the worker thread **never** touches
widgets. They communicate only via `AsyncRunner.submit()` (GUI → worker) and Qt
signals (worker → GUI). Qt delivers cross-thread signals through a queued
connection, which is what makes UI updates thread-safe.

---

## Class-by-class explanation

| Class | File | Responsibility |
|-------|------|----------------|
| `RunConfig` | `config/settings.py` | Immutable value object describing one START run (url, count, headless, delay, auto-close, timeout). |
| `DeviceProfile` | `browser/device_profiles.py` | One immutable fingerprint: name, category, user-agent, viewport, screen, scale factor, mobile/touch flags, platform. The module also exposes `PROFILES` (60+) and the `LOCALES` / `TIMEZONES` / `COLOR_SCHEMES` random pools. |
| `BrowserInstance` | `browser/models.py` | Runtime state of one browser: identity (index, id, name), engine, the chosen `DeviceProfile`, the four random picks (locale, accept-language, timezone, colour-scheme), status, start time, error, plus the live Playwright `browser`/`context`/`page` handles. |
| `DeviceProfile` + `PROFILES` | `browser/device_profiles.py` | One immutable device fingerprint (viewport, screen, UA, platform, scale, touch/mobile) and the 60+ catalogue, plus the `LOCALES`/`TIMEZONES`/`COLOR_SCHEMES` random pools. |
| `BrowserFactory` | `browser/browser_factory.py` | Per-run factory. `create_instance()` picks a random engine/profile/locale/timezone/colour-scheme and builds a `BrowserInstance`; `build_context_options()` translates it into **engine-aware** `new_context` kwargs; `build_init_script()` aligns `navigator.platform`/`languages`. |
| `BrowserManager` | `browser/browser_manager.py` | Async orchestrator and the single owner of the Playwright runtime. `launch_all()` opens browsers sequentially (honouring the delay), `screenshot_all()` captures every page, `stop_all()` tears everything down, and an internal timer powers auto-close. Emits Qt signals (`instance_registered`, `instance_status`, `run_started`, `launch_complete`, `all_stopped`) so the GUI can react. Catches every failure mode (missing Playwright, launch failure, timeout, crash). |
| `LogService` | `services/logger.py` | Thread-safe logger. Each `log()` writes a timestamped line to `logs/session_*.log` (lock-guarded) **and** emits `message_logged` for the live panel. |
| `AsyncRunner` | `services/async_runner.py` | Runs a dedicated asyncio event loop on a daemon thread and exposes `submit(coro)` so the GUI can schedule async work without blocking. On Windows this is a ProactorEventLoop, which Playwright requires. |
| `ReportExporter` | `services/report_exporter.py` | Writes the CSV report (`instance_id, instance_name, browser_engine, device_profile, start_time, status`). |
| `MainWindow` | `ui/main_window.py` | The PySide6 window. Builds the form/buttons/dashboard/log, validates input, submits work to the `AsyncRunner`, and updates the table + grid + log from manager signals (always on the GUI thread). Handles clean shutdown in `closeEvent`. |
| `PreviewGrid` / `PreviewCard` / `PreviewDialog` / `FlowLayout` | `ui/preview_view.py` | The thumbnail grid view. `FlowLayout` wraps tiles to the window width; `PreviewCard` is one small clickable tile (thumbnail + name + status); `PreviewGrid` scrolls the whole wall; `PreviewDialog` is the enlarged single-browser view with a refresh button. |

---

## Quality / design notes

- **Clean architecture & SOLID** — UI, orchestration, domain models, factory and
  cross-cutting services are separated into their own packages; each class has a
  single responsibility and depends on abstractions (e.g. the manager depends on
  a `LogService`, not on the GUI).
- **OOP + Type hints** — fully type-annotated dataclasses and classes.
- **Async Playwright** — all browser I/O is `async` and runs on a dedicated loop.
- **Thread-safe UI** — widgets are only ever mutated on the GUI thread; updates
  arrive via queued Qt signals.
- **Modular & extensible** — add a new engine quirk in `BrowserFactory`, a new
  device in `device_profiles.py`, or a new output in `services/` without touching
  anything else (Open/Closed principle).

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Playwright unavailable` in the log | `pip install -r requirements.txt` |
| `Executable doesn't exist` / launch fails | `python -m playwright install` |
| Status shows `Timeout` | Site slow/unreachable — the browser stays open; raise `DEFAULT_TIMEOUT_MS` in `config/settings.py` if needed. |
| Status shows `Crashed` | The page crashed (e.g. heavy site under many concurrent browsers); reduce the count. |

---

© 2026 Renufus — Multi Browser Launcher.
