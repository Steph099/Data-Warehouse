"""Read access to the Spark analytics outputs (totals, regression_results)."""
from __future__ import annotations

from datetime import date

from cassandra.cluster import Session

from acme_dwh.dal.session import get_session
from acme_dwh.dal.timeseries_repository import _to_pydate


class AnalyticsRepository:
    def __init__(self, session: Session | None = None) -> None:
        self.session = session or get_session()
        self._totals = self.session.prepare(
            "SELECT business_date_year, cnt, min_close, max_close, avg_close "
            "FROM totals WHERE asset_id = ? AND data_source_id = ?"
        )
        self._predictions = self.session.prepare(
            "SELECT seconds, business_date, open, prediction "
            "FROM regression_results WHERE asset_id = ? AND data_source_id = ? LIMIT ?"
        )

    def totals(self, asset_id: str, data_source_id: str) -> list[dict]:
        rows = self.session.execute(self._totals, (asset_id, data_source_id))
        out = [
            {
                "year": r.business_date_year,
                "count": r.cnt,
                "minClose": r.min_close,
                "maxClose": r.max_close,
                "avgClose": r.avg_close,
            }
            for r in rows
        ]
        return sorted(out, key=lambda x: x["year"])

    def predictions(self, asset_id: str, data_source_id: str, limit: int = 200) -> list[dict]:
        rows = self.session.execute(self._predictions, (asset_id, data_source_id, limit))
        out = [
            {
                "businessDate": _iso(_to_pydate(r.business_date)),
                "open": r.open,
                "prediction": r.prediction,
            }
            for r in rows
        ]
        return sorted(out, key=lambda x: x["businessDate"])


def _iso(d: date) -> str:
    return d.isoformat() if hasattr(d, "isoformat") else str(d)
