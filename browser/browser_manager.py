"""Async orchestrator that launches, tracks, screenshots and stops browsers.

``BrowserManager`` is a ``QObject`` so it can emit Qt signals, but all of its
``async`` methods are designed to run on the :class:`AsyncRunner` worker loop —
never on the GUI thread. It owns the Playwright runtime and the live instances;
the GUI only ever observes state changes through signals.

Robust error handling is built in for every failure mode the spec lists:
Playwright missing, launch failure, invalid/timing-out URL and page crashes.
"""

from __future__ import annotations

import asyncio
import random
from datetime import datetime
from typing import Optional

from PySide6.QtCore import QObject, Signal

from browser.browser_factory import BrowserFactory
from browser.models import BrowserInstance
from config.settings import NAME_PREFIXES, SCREENSHOTS_DIR, RunConfig
from services.logger import LogService

# --------------------------------------------------------------------------- #
# Import Playwright defensively so the GUI still starts if it is not installed.
# --------------------------------------------------------------------------- #
try:
    from playwright.async_api import (
        Error as PlaywrightError,
        TimeoutError as PlaywrightTimeoutError,
        async_playwright,
    )

    PLAYWRIGHT_AVAILABLE = True
    PLAYWRIGHT_IMPORT_ERROR = ""
except Exception as exc:  # noqa: BLE001 - any import problem must be tolerated
    async_playwright = None  # type: ignore[assignment]
    PlaywrightError = Exception  # type: ignore[assignment,misc]
    PlaywrightTimeoutError = Exception  # type: ignore[assignment,misc]
    PLAYWRIGHT_AVAILABLE = False
    PLAYWRIGHT_IMPORT_ERROR = str(exc)


class BrowserManager(QObject):
    """Owns the Playwright lifecycle for one or many browser instances."""

    # --- Signals (always emitted from the worker thread, received on GUI) --- #
    instance_registered = Signal(object)        # BrowserInstance (row added)
    instance_status = Signal(str, str)          # (instance_id, status)
    run_started = Signal(int)                    # total count requested
    launch_complete = Signal(int, int)          # (launched, total)
    all_stopped = Signal()                       # cleanup finished
    preview_captured = Signal(str, object)       # (instance_id, PNG bytes)

    def __init__(self, logger: LogService, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._logger = logger
        self._pw = None
        self._instances: dict[str, BrowserInstance] = {}
        self._running = False
        self._stopping = False
        self._auto_close_handle: Optional[asyncio.Future] = None
        self._launch_tasks: list[asyncio.Future] = []

    # ------------------------------------------------------------------ #
    # Public read helpers (safe to call from the GUI thread)
    # ------------------------------------------------------------------ #
    def is_running(self) -> bool:
        return self._running

    def snapshot(self) -> list[BrowserInstance]:
        """Return the current instances for reporting."""
        return list(self._instances.values())

    def _log(self, message: str) -> None:
        self._logger.log(message)

    # ------------------------------------------------------------------ #
    # Launch
    # ------------------------------------------------------------------ #
    async def launch_all(self, config: RunConfig) -> None:
        """Launch ``config.count`` randomised browsers concurrently.

        Each browser runs as its own asyncio task, so they spin up and navigate
        in parallel instead of waiting for the previous one to finish loading.
        ``delay_seconds`` is kept as a *stagger* between starts (set it to 0 to
        fire them all at once).
        """
        if self._running:
            self._log("A run is already in progress - ignoring START.")
            return
        if not PLAYWRIGHT_AVAILABLE:
            self._log(f"ERROR: Playwright is not installed - {PLAYWRIGHT_IMPORT_ERROR}")
            self._log("Fix: pip install -r requirements.txt  &&  python -m playwright install")
            self.all_stopped.emit()
            return

        self._running = True
        self._stopping = False
        self._instances.clear()

        prefix = random.choice(NAME_PREFIXES)
        factory = BrowserFactory(prefix)
        self.run_started.emit(config.count)
        self._log(
            f"START - {config.count} browser(s) | name series '{prefix}-NNN' | "
            f"headless={config.headless} | delay={config.delay_seconds}s | url={config.url}"
        )

        try:
            self._pw = await async_playwright().start()
        except Exception as exc:  # noqa: BLE001
            self._log(f"ERROR: could not start Playwright runtime: {exc}")
            self._running = False
            self.all_stopped.emit()
            return

        # Spawn each browser as an independent task, staggered by the delay but
        # never blocking on the previous browser's page load.
        tasks: list[asyncio.Future] = []
        self._launch_tasks = tasks
        for index in range(1, config.count + 1):
            if self._stopping:
                self._log("Stop requested - halting further launches.")
                break

            instance = factory.create_instance(index)
            self._instances[instance.instance_id] = instance
            self.instance_registered.emit(instance)

            tasks.append(asyncio.ensure_future(self._launch_one(instance, factory, config)))

            # Stagger only the *starts* (skip after the last one).
            if config.delay_seconds > 0 and index < config.count and not self._stopping:
                await asyncio.sleep(config.delay_seconds)

        # Wait for every concurrent launch task to settle.
        results = await asyncio.gather(*tasks, return_exceptions=True)
        launched = sum(1 for result in results if result is True)
        if self._launch_tasks is tasks:
            self._launch_tasks = []

        self._log(f"Launch sequence complete - {launched}/{config.count} browser(s) active.")
        self.launch_complete.emit(launched, config.count)

        if launched == 0 and not self._stopping:
            self._log("No browsers are active - cleaning up runtime.")
            await self.stop_all()
            return

        if config.auto_close_minutes and config.auto_close_minutes > 0 and not self._stopping:
            self._log(f"Auto-close armed: all browsers close in {config.auto_close_minutes} min.")
            self._auto_close_handle = asyncio.ensure_future(
                self._auto_close(config.auto_close_minutes)
            )

    async def _launch_one(
        self, instance: BrowserInstance, factory: BrowserFactory, config: RunConfig
    ) -> bool:
        """Launch a single browser+context+page. Returns True if it stays open."""
        if self._stopping:
            return False
        # 1) Launch the engine process.
        try:
            engine = getattr(self._pw, instance.engine)
            browser = await engine.launch(headless=config.headless)
            instance.browser = browser
        except Exception as exc:  # noqa: BLE001
            self._fail(instance, "Launch Failed", f"failed to launch {instance.engine}: {exc}")
            if "Executable doesn't exist" in str(exc) or "playwright install" in str(exc).lower():
                self._log("Hint: run `python -m playwright install` to download browser binaries.")
            return False

        # 2) Create the isolated context + page.
        try:
            context = await browser.new_context(**factory.build_context_options(instance))
            instance.context = context
            await context.add_init_script(factory.build_init_script(instance))
            page = await context.new_page()
            instance.page = page
            page.on("crash", lambda: self._on_page_crash(instance))

            instance.start_time = datetime.now().isoformat(timespec="seconds")
            self._update(instance, "Launched")
            self._log(f"{instance.name} launched  ({instance.engine} - {instance.profile_name})")
        except Exception as exc:  # noqa: BLE001
            self._fail(instance, "Context Error", f"failed to create context: {exc}")
            return False

        # 3) Navigate to the target URL.
        try:
            await page.goto(config.url, timeout=config.timeout_ms, wait_until="load")
            await self._apply_window_title(page, instance.name)
            self._update(instance, "Running")
            self._log(f"{instance.name} loaded page")
        except PlaywrightTimeoutError:
            instance.error = "Navigation timeout"
            self._update(instance, "Timeout")
            self._log(f"{instance.name} network timeout after {config.timeout_ms} ms")
        except PlaywrightError as exc:
            instance.error = str(exc)
            self._update(instance, "Load Error")
            self._log(f"{instance.name} failed to load page: {exc}")
        except Exception as exc:  # noqa: BLE001
            instance.error = str(exc)
            self._update(instance, "Load Error")
            self._log(f"{instance.name} unexpected navigation error: {exc}")

        return True  # the browser window is open even if navigation failed

    # ------------------------------------------------------------------ #
    # Screenshots
    # ------------------------------------------------------------------ #
    async def screenshot_all(self) -> int:
        """Capture every open page into ``screenshots/browser_NNN.png``."""
        targets = [inst for inst in self._instances.values() if inst.page is not None]
        if not targets:
            self._log("No active pages to screenshot.")
            return 0

        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        self._log(f"Capturing screenshots for {len(targets)} browser(s)...")
        saved = 0
        for inst in targets:
            path = SCREENSHOTS_DIR / f"browser_{inst.index:03d}.png"
            try:
                await inst.page.screenshot(path=str(path))
                saved += 1
                self._log(f"{inst.name} screenshot saved -> {path.name}")
            except Exception as exc:  # noqa: BLE001
                self._log(f"{inst.name} screenshot failed: {exc}")
        self._log(f"Screenshot batch complete - {saved}/{len(targets)} saved.")
        return saved

    # ------------------------------------------------------------------ #
    # Live previews (in-memory PNG bytes for the thumbnail grid)
    # ------------------------------------------------------------------ #
    async def capture_previews(self) -> int:
        """Capture an in-memory preview of every open page (for thumbnails)."""
        targets = [inst for inst in self._instances.values() if inst.page is not None]
        for inst in targets:
            await self._capture_preview(inst)
        return len(targets)

    async def capture_single_preview(self, instance_id: str) -> None:
        """Capture a fresh preview for one instance (used by the detail view)."""
        inst = self._instances.get(instance_id)
        if inst is not None and inst.page is not None:
            await self._capture_preview(inst)

    async def _capture_preview(self, instance: BrowserInstance) -> None:
        try:
            data = await instance.page.screenshot()
            self.preview_captured.emit(instance.instance_id, data)
        except Exception as exc:  # noqa: BLE001
            self._log(f"{instance.name} preview capture failed: {exc}")

    # ------------------------------------------------------------------ #
    # Stop / cleanup
    # ------------------------------------------------------------------ #
    async def stop_all(self) -> None:
        """Close every browser and shut the Playwright runtime down."""
        if not self._running and self._pw is None:
            self.all_stopped.emit()
            return

        self._stopping = True
        if self._auto_close_handle and not self._auto_close_handle.done():
            self._auto_close_handle.cancel()
        self._auto_close_handle = None

        # Cancel any launch tasks still in flight so they stop touching browsers.
        for task in self._launch_tasks:
            if not task.done():
                task.cancel()
        self._launch_tasks = []

        self._log("Stopping all browsers...")
        for inst in list(self._instances.values()):
            await self._close_instance(inst)

        if self._pw is not None:
            try:
                await self._pw.stop()
            except Exception as exc:  # noqa: BLE001
                self._log(f"Warning during Playwright shutdown: {exc}")
            self._pw = None

        self._running = False
        self._stopping = False
        self._log("All browsers stopped.")
        self.all_stopped.emit()

    async def _close_instance(self, instance: BrowserInstance) -> None:
        for closeable in (instance.context, instance.browser):
            try:
                if closeable is not None:
                    await closeable.close()
            except Exception:  # noqa: BLE001 - already closed / crashed
                pass
        instance.browser = instance.context = instance.page = None
        if instance.status not in ("Launch Failed", "Context Error"):
            self._update(instance, "Stopped")

    async def _auto_close(self, minutes: float) -> None:
        try:
            await asyncio.sleep(minutes * 60)
        except asyncio.CancelledError:
            return
        self._log(f"Auto-close timer ({minutes} min) elapsed - stopping all browsers.")
        await self.stop_all()

    # ------------------------------------------------------------------ #
    # Small internal helpers
    # ------------------------------------------------------------------ #
    async def _apply_window_title(self, page, title: str) -> None:
        """Give each page a unique document/window title (best effort)."""
        try:
            await page.evaluate("(t) => { try { document.title = t; } catch (e) {} }", title)
        except Exception:  # noqa: BLE001
            pass

    def _on_page_crash(self, instance: BrowserInstance) -> None:
        instance.error = "Page crashed"
        self._update(instance, "Crashed")
        self._log(f"{instance.name} crashed")

    def _update(self, instance: BrowserInstance, status: str) -> None:
        instance.status = status
        self.instance_status.emit(instance.instance_id, status)

    def _fail(self, instance: BrowserInstance, status: str, message: str) -> None:
        instance.error = message
        self._update(instance, status)
        self._log(f"{instance.name} {message}")
