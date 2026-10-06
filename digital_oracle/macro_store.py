"""Separate append-only namespace in the existing encrypted SQLite archive."""
from .asset_store import AssetStore


class MacroStore(AssetStore):
    # Never add macro datasets to the legacy model's 'datasets' table.
    TABLES = ("macro_payloads", "macro_evidence", "macro_events", "macro_snapshots",
              "macro_reactions", "macro_ai", "upstream_observations", "upstream_reviews")

    def as_of(self, table, instant, limit=10000):
        from datetime import datetime
        cutoff = datetime.fromisoformat(instant.replace("Z", "+00:00"))
        return [row for row in self.list(table, limit)
                if row.get("available_at", row.get("checked_at")) and
                datetime.fromisoformat(row.get("available_at", row.get("checked_at")).replace("Z", "+00:00")) <= cutoff]
