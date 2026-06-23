"""Thread-safe, timestamped logging service.

The service does two things on every ``log()`` call:
  1. append the line to a per-session file under ``logs/`` (guarded by a lock
     because the asyncio worker thread and the GUI thread can both log);
  2. emit a Qt signal so the GUI can show the line in real time. Emitting a
     signal across threads is safe in Qt — it is delivered via a queued
     connection to the receiver's (GUI) thread.
"""

from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from config.settings import LOGS_DIR


class LogService(QObject):
    """Realtime logger: file sink + ``message_logged`` Qt signal."""

    message_logged = Signal(str)  # fully formatted "[HH:MM:SS] message" line

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._lock = threading.Lock()
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._file_path = LOGS_DIR / f"session_{stamp}.log"
        # Line-buffered append handle kept open for the session.
        self._file = open(self._file_path, "a", encoding="utf-8")

    @property
    def file_path(self) -> Path:
        return self._file_path

    def log(self, message: str) -> None:
        """Record one message. Safe to call from any thread."""
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        with self._lock:
            try:
                self._file.write(line + "\n")
                self._file.flush()
            except (ValueError, OSError):
                pass  # never let logging crash the app
        self.message_logged.emit(line)

    def close(self) -> None:
        with self._lock:
            try:
                self._file.close()
            except (ValueError, OSError):
                pass
