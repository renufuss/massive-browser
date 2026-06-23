"""Background asyncio event loop for async Playwright.

PySide6 owns the main thread's event loop; Playwright's async API needs its own
asyncio loop. Running that loop in a dedicated daemon thread lets us schedule
coroutines from the GUI without ever blocking it. Results flow back to the GUI
exclusively through Qt signals, so the GUI is only ever touched on its own
thread (thread-safe UI updates).

On Windows, ``asyncio.new_event_loop()`` yields a ProactorEventLoop by default,
which is exactly what Playwright requires for subprocess transport.
"""

from __future__ import annotations

import asyncio
import threading
from concurrent.futures import Future
from typing import Any, Coroutine


class AsyncRunner:
    """Owns a private asyncio loop running on a background thread."""

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()

    def start(self) -> None:
        """Spin up the loop thread and block until it is ready to accept work."""
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="AsyncRunner", daemon=True)
        self._thread.start()
        self._ready.wait()

    def _run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._ready.set()
        try:
            self._loop.run_forever()
        finally:
            # Cancel anything still pending, then close cleanly.
            pending = asyncio.all_tasks(self._loop)
            for task in pending:
                task.cancel()
            if pending:
                self._loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
            self._loop.close()

    def submit(self, coro: Coroutine[Any, Any, Any]) -> Future:
        """Schedule a coroutine on the loop thread; returns a concurrent Future."""
        if self._loop is None:
            raise RuntimeError("AsyncRunner has not been started")
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    def stop(self) -> None:
        """Stop the loop and join its thread (best-effort, used on shutdown)."""
        if self._loop is None:
            return
        self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._thread = None
        self._loop = None
