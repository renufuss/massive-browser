"""PySide6 main window: input form, control buttons, dashboard table, live log.

This module is the *only* place that touches Qt widgets, and every widget mutation
happens on the GUI thread. Work that must run asynchronously is handed to the
:class:`AsyncRunner`; results come back exclusively via :class:`BrowserManager`
signals connected to the slots below, which keeps UI updates thread-safe.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor, QFont, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from browser.browser_manager import (
    PLAYWRIGHT_AVAILABLE,
    PLAYWRIGHT_IMPORT_ERROR,
    BrowserManager,
)
from browser.models import BrowserInstance
from config.settings import (
    LOGS_DIR,
    MAX_AUTOCLOSE_MINUTES,
    MAX_BROWSERS,
    MAX_DELAY_SECONDS,
    REPORTS_DIR,
    SCREENSHOTS_DIR,
    RunConfig,
    ensure_directories,
)
from services.async_runner import AsyncRunner
from services.logger import LogService
from services.report_exporter import ReportExporter
from ui.preview_view import PreviewDialog, PreviewGrid
from ui.styles import status_color


class MainWindow(QMainWindow):
    """Top-level application window."""

    COLUMNS: tuple[str, ...] = ("ID", "Name", "Browser", "Device Profile", "Status")

    # Thumbnail tile sizes for the grid view (label -> width x height).
    _TILE_SIZES: dict[str, tuple[int, int]] = {
        "Small": (160, 100),
        "Medium": (220, 140),
        "Large": (300, 190),
    }

    def __init__(self) -> None:
        super().__init__()
        ensure_directories()
        self.setWindowTitle("Multi Browser Launcher")
        self.resize(1040, 760)

        # Services / orchestration --------------------------------------- #
        self._logger = LogService(self)
        self._runner = AsyncRunner()
        self._runner.start()
        self._manager = BrowserManager(self._logger)
        self._exporter = ReportExporter()
        self._row_for_id: dict[str, int] = {}
        self._preview_cache: dict[str, QPixmap] = {}
        self._preview_dialog: PreviewDialog | None = None

        # Build & wire up ------------------------------------------------- #
        self._build_ui()
        self._connect_signals()

        self._logger.log("Application started. Ready.")
        if not PLAYWRIGHT_AVAILABLE:
            self._logger.log(f"WARNING: Playwright unavailable - {PLAYWRIGHT_IMPORT_ERROR}")
            self._logger.log(
                "Install with: pip install -r requirements.txt  &&  python -m playwright install"
            )

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #
    def _build_ui(self) -> None:
        central = QWidget(self)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        root.addWidget(self._build_input_group())
        root.addLayout(self._build_button_bar())
        root.addWidget(self._build_dashboard_group(), stretch=3)
        root.addWidget(self._build_log_group(), stretch=2)

        self.setCentralWidget(central)
        self.statusBar().showMessage("Idle")

    def _build_input_group(self) -> QGroupBox:
        box = QGroupBox("Configuration")
        form = QFormLayout(box)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText("https://example.com")
        self._url_edit.setText("https://example.com")

        self._count_spin = QSpinBox()
        self._count_spin.setRange(1, MAX_BROWSERS)
        self._count_spin.setValue(3)

        self._headless_check = QCheckBox("Run browsers headless (no visible window)")

        self._delay_spin = QDoubleSpinBox()
        self._delay_spin.setRange(0.0, MAX_DELAY_SECONDS)
        self._delay_spin.setSingleStep(0.5)
        self._delay_spin.setValue(1.0)
        self._delay_spin.setSuffix(" s")

        self._autoclose_spin = QDoubleSpinBox()
        self._autoclose_spin.setRange(0.0, MAX_AUTOCLOSE_MINUTES)
        self._autoclose_spin.setSingleStep(1.0)
        self._autoclose_spin.setValue(0.0)
        self._autoclose_spin.setSuffix(" min")
        self._autoclose_spin.setToolTip("0 = disabled (browsers stay open until you stop them)")

        form.addRow("Target URL:", self._url_edit)
        form.addRow("Number of browsers:", self._count_spin)
        form.addRow("Headless:", self._headless_check)
        form.addRow("Delay between launches:", self._delay_spin)
        form.addRow("Auto close (optional):", self._autoclose_spin)
        return box

    def _build_button_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        self._start_btn = QPushButton("START")
        self._stop_btn = QPushButton("STOP ALL")
        self._screenshot_btn = QPushButton("Take Screenshot All")
        self._minimize_btn = QPushButton("Minimize All")
        self._log_folder_btn = QPushButton("Open Log Folder")
        self._export_btn = QPushButton("Export Report")

        self._start_btn.setMinimumHeight(34)
        self._stop_btn.setMinimumHeight(34)
        self._start_btn.setStyleSheet("font-weight:bold;")

        self._stop_btn.setEnabled(False)
        self._screenshot_btn.setEnabled(False)
        self._minimize_btn.setEnabled(False)

        for btn in (
            self._start_btn,
            self._stop_btn,
            self._screenshot_btn,
            self._minimize_btn,
            self._log_folder_btn,
            self._export_btn,
        ):
            bar.addWidget(btn)
        bar.addStretch(1)

        self._start_btn.clicked.connect(self._on_start)
        self._stop_btn.clicked.connect(self._on_stop)
        self._screenshot_btn.clicked.connect(self._on_screenshot)
        self._minimize_btn.clicked.connect(self._on_minimize_all)
        self._log_folder_btn.clicked.connect(lambda: self._open_folder(LOGS_DIR))
        self._export_btn.clicked.connect(self._on_export)
        return bar

    def _build_dashboard_group(self) -> QGroupBox:
        box = QGroupBox("Dashboard")
        layout = QVBoxLayout(box)

        # --- Display settings toolbar ----------------------------------- #
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("View:"))
        self._view_combo = QComboBox()
        self._view_combo.addItems(["Table", "Grid (thumbnails)"])
        toolbar.addWidget(self._view_combo)
        toolbar.addSpacing(12)
        self._size_label = QLabel("Thumbnail size:")
        toolbar.addWidget(self._size_label)
        self._size_combo = QComboBox()
        self._size_combo.addItems(list(self._TILE_SIZES.keys()))
        toolbar.addWidget(self._size_combo)
        toolbar.addSpacing(12)
        self._refresh_previews_btn = QPushButton("Refresh Previews")
        toolbar.addWidget(self._refresh_previews_btn)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        # --- Table view (index 0) --------------------------------------- #
        self._table = QTableWidget(0, len(self.COLUMNS))
        self._table.setHorizontalHeaderLabels(list(self.COLUMNS))
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        # --- Grid view (index 1) ---------------------------------------- #
        self._grid = PreviewGrid()

        self._view_stack = QStackedWidget()
        self._view_stack.addWidget(self._table)
        self._view_stack.addWidget(self._grid)
        layout.addWidget(self._view_stack)

        # Wiring
        self._view_combo.currentIndexChanged.connect(self._on_view_changed)
        self._size_combo.currentTextChanged.connect(self._on_size_changed)
        self._refresh_previews_btn.clicked.connect(self._refresh_previews)
        self._grid.card_clicked.connect(self._on_card_clicked)

        self._on_size_changed(self._size_combo.currentText())
        self._update_preview_controls()
        return box

    def _build_log_group(self) -> QGroupBox:
        box = QGroupBox("Realtime Log")
        layout = QVBoxLayout(box)
        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setMaximumBlockCount(5000)
        self._log_view.setFont(QFont("Consolas", 9))
        layout.addWidget(self._log_view)
        return box

    # ------------------------------------------------------------------ #
    # Signal wiring
    # ------------------------------------------------------------------ #
    def _connect_signals(self) -> None:
        self._logger.message_logged.connect(self._append_log)
        self._manager.instance_registered.connect(self._on_instance_registered)
        self._manager.instance_status.connect(self._on_instance_status)
        self._manager.run_started.connect(self._on_run_started)
        self._manager.launch_complete.connect(self._on_launch_complete)
        self._manager.all_stopped.connect(self._on_all_stopped)
        self._manager.preview_captured.connect(self._on_preview_captured)

    # ------------------------------------------------------------------ #
    # Button handlers
    # ------------------------------------------------------------------ #
    def _on_start(self) -> None:
        url = self._validate_url()
        if url is None:
            return
        if not PLAYWRIGHT_AVAILABLE:
            QMessageBox.critical(
                self,
                "Playwright missing",
                "Playwright is not installed.\n\n"
                "pip install -r requirements.txt\n"
                "python -m playwright install",
            )
            return

        config = RunConfig(
            url=url,
            count=self._count_spin.value(),
            headless=self._headless_check.isChecked(),
            delay_seconds=self._delay_spin.value(),
            auto_close_minutes=self._autoclose_spin.value(),
        )
        self._reset_table()
        self._set_running_state(True)
        self._runner.submit(self._manager.launch_all(config))

    def _on_stop(self) -> None:
        self._logger.log("STOP ALL requested.")
        self._stop_btn.setEnabled(False)
        self._runner.submit(self._manager.stop_all())

    def _on_screenshot(self) -> None:
        self._runner.submit(self._manager.screenshot_all())

    def _on_minimize_all(self) -> None:
        self._runner.submit(self._manager.minimize_all())

    def _on_export(self) -> None:
        instances = self._manager.snapshot()
        if not instances:
            QMessageBox.information(self, "Export Report", "There is no data to export yet.")
            return
        default_path = str(REPORTS_DIR / "report.csv")
        chosen, _ = QFileDialog.getSaveFileName(
            self, "Export Report", default_path, "CSV Files (*.csv)"
        )
        if not chosen:
            return
        try:
            out = self._exporter.export(instances, Path(chosen))
        except OSError as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        self._logger.log(f"Report exported -> {out}")
        QMessageBox.information(self, "Export complete", f"Report saved to:\n{out}")

    # ------------------------------------------------------------------ #
    # Manager signal slots (run on the GUI thread)
    # ------------------------------------------------------------------ #
    @Slot(str)
    def _append_log(self, line: str) -> None:
        self._log_view.appendPlainText(line)

    @Slot(int)
    def _on_run_started(self, count: int) -> None:
        self.statusBar().showMessage(f"Launching {count} browser(s)...")

    @Slot(object)
    def _on_instance_registered(self, instance: BrowserInstance) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._row_for_id[instance.instance_id] = row
        self._set_cell(row, 0, str(instance.index))
        self._set_cell(row, 1, instance.name)
        self._set_cell(row, 2, instance.engine.capitalize())
        self._set_cell(row, 3, instance.profile.name)
        self._set_status_cell(row, instance.status)
        self._grid.add_card(instance)

    @Slot(str, str)
    def _on_instance_status(self, instance_id: str, status: str) -> None:
        self._grid.set_status(instance_id, status)
        row = self._row_for_id.get(instance_id)
        if row is None:
            return
        self._set_status_cell(row, status)
        self._refresh_summary()

    @Slot(int, int)
    def _on_launch_complete(self, launched: int, total: int) -> None:
        self.statusBar().showMessage(f"{launched}/{total} browser(s) active.")
        self._screenshot_btn.setEnabled(launched > 0)
        if launched > 0 and self._view_stack.currentIndex() == 1:
            self._refresh_previews()

    @Slot()
    def _on_all_stopped(self) -> None:
        self._set_running_state(False)
        self.statusBar().showMessage("All browsers stopped. Idle.")

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _validate_url(self) -> str | None:
        url = self._url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "Invalid URL", "Please enter a target URL.")
            return None
        if not urlparse(url).scheme:
            url = "https://" + url
            self._url_edit.setText(url)
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            QMessageBox.warning(self, "Invalid URL", f"'{url}' is not a valid http(s) URL.")
            return None
        return url

    def _set_running_state(self, running: bool) -> None:
        self._start_btn.setEnabled(not running)
        self._stop_btn.setEnabled(running)
        self._screenshot_btn.setEnabled(running)
        self._minimize_btn.setEnabled(running)
        for widget in (
            self._url_edit,
            self._count_spin,
            self._headless_check,
            self._delay_spin,
            self._autoclose_spin,
        ):
            widget.setEnabled(not running)

    def _reset_table(self) -> None:
        self._table.setRowCount(0)
        self._row_for_id.clear()
        self._grid.clear()
        self._preview_cache.clear()
        if self._preview_dialog is not None:
            self._preview_dialog.close()
            self._preview_dialog = None

    def _set_cell(self, row: int, col: int, text: str) -> None:
        item = QTableWidgetItem(text)
        if col == 0:
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, col, item)

    def _set_status_cell(self, row: int, status: str) -> None:
        item = QTableWidgetItem(status)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        color = status_color(status)
        if color:
            item.setForeground(QColor(color))
            font = item.font()
            font.setBold(True)
            item.setFont(font)
        self._table.setItem(row, 4, item)

    def _refresh_summary(self) -> None:
        running = 0
        for row in range(self._table.rowCount()):
            cell = self._table.item(row, 4)
            if cell and cell.text() == "Running":
                running += 1
        self.statusBar().showMessage(
            f"{running} running / {self._table.rowCount()} total"
        )

    def _open_folder(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", str(path)], check=False)
            else:
                subprocess.run(["xdg-open", str(path)], check=False)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Open folder", f"Could not open folder:\n{exc}")

    # ------------------------------------------------------------------ #
    # Preview / display-mode handlers
    # ------------------------------------------------------------------ #
    @Slot(int)
    def _on_view_changed(self, index: int) -> None:
        self._view_stack.setCurrentIndex(index)
        self._update_preview_controls()
        if index == 1 and self._manager.is_running():
            self._refresh_previews()

    @Slot(str)
    def _on_size_changed(self, label: str) -> None:
        width, height = self._TILE_SIZES.get(label, self._TILE_SIZES["Small"])
        self._grid.set_tile_size(width, height)

    def _refresh_previews(self) -> None:
        self._runner.submit(self._manager.capture_previews())

    def _update_preview_controls(self) -> None:
        grid_active = self._view_stack.currentIndex() == 1
        self._size_label.setEnabled(grid_active)
        self._size_combo.setEnabled(grid_active)
        self._refresh_previews_btn.setEnabled(grid_active)

    @Slot(str, object)
    def _on_preview_captured(self, instance_id: str, data: object) -> None:
        pixmap = QPixmap()
        pixmap.loadFromData(bytes(data))  # type: ignore[arg-type]
        if pixmap.isNull():
            return
        self._preview_cache[instance_id] = pixmap
        self._grid.set_thumbnail(instance_id, pixmap)
        if self._preview_dialog is not None and self._preview_dialog.instance_id == instance_id:
            self._preview_dialog.set_image(pixmap)

    @Slot(str)
    def _on_card_clicked(self, instance_id: str) -> None:
        instance = next(
            (inst for inst in self._manager.snapshot() if inst.instance_id == instance_id),
            None,
        )
        if instance is None:
            return
        if self._preview_dialog is not None:
            self._preview_dialog.close()
        dialog = PreviewDialog(instance, self)
        self._preview_dialog = dialog
        dialog.refresh_requested.connect(
            lambda iid: self._runner.submit(self._manager.capture_single_preview(iid))
        )
        dialog.show_window_requested.connect(
            lambda iid: self._runner.submit(self._manager.show_window(iid))
        )
        dialog.finished.connect(self._on_dialog_finished)
        cached = self._preview_cache.get(instance_id)
        if cached is not None:
            dialog.set_image(cached)
        self._runner.submit(self._manager.capture_single_preview(instance_id))
        dialog.show()

    def _on_dialog_finished(self, *_args) -> None:
        self._preview_dialog = None

    # ------------------------------------------------------------------ #
    # Shutdown
    # ------------------------------------------------------------------ #
    def closeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        """Make sure browsers and the worker loop are torn down on exit."""
        try:
            future = self._runner.submit(self._manager.stop_all())
            future.result(timeout=10)
        except Exception:  # noqa: BLE001
            pass
        self._runner.stop()
        self._logger.close()
        super().closeEvent(event)
