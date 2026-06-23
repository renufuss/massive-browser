"""CSV report exporter."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Iterable

from browser.models import BrowserInstance
from config.settings import REPORTS_DIR


class ReportExporter:
    """Writes a CSV report describing every launched browser instance."""

    FIELDS: tuple[str, ...] = (
        "instance_id",
        "instance_name",
        "browser_engine",
        "device_profile",
        "start_time",
        "status",
    )

    def export(self, instances: Iterable[BrowserInstance], path: Path | None = None) -> Path:
        """Export ``instances`` to ``path`` (auto-named under reports/ if None)."""
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        if path is None:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = REPORTS_DIR / f"report_{stamp}.csv"

        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=self.FIELDS)
            writer.writeheader()
            for inst in instances:
                writer.writerow(
                    {
                        "instance_id": inst.instance_id,
                        "instance_name": inst.name,
                        "browser_engine": inst.engine.name,
                        "device_profile": inst.profile.name,
                        "start_time": inst.start_time,
                        "status": inst.status,
                    }
                )
        return path
