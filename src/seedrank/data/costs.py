"""API cost tracking — log and query API usage costs."""

from __future__ import annotations

import sqlite3

# Estimated costs per API call (USD)
# DataForSEO: https://dataforseo.com/pricing
COST_ESTIMATES: dict[str, dict[str, float]] = {
    "dataforseo": {
        "keywords_data/google_ads/search_volume/live": 0.05,
        "dataforseo_labs/google/keyword_suggestions/live": 0.10,
        "serp/google/organic/live/advanced": 0.10,
        "dataforseo_labs/google/ranked_keywords/live": 0.10,
    },
    "openai": {
        "gpt-4o": 0.01,
        "gpt-4o-mini": 0.002,
    },
    "anthropic": {
        "claude-sonnet-4-6": 0.01,
        "claude-haiku-4-5-20251001": 0.002,
    },
    "perplexity": {
        "default": 0.005,
    },
    "gemini": {
        "default": 0.005,
    },
}


def estimate_cost(provider: str, endpoint_or_model: str) -> float:
    """Look up estimated cost for a provider + endpoint/model combination."""
    provider_costs = COST_ESTIMATES.get(provider, {})
    return provider_costs.get(endpoint_or_model, provider_costs.get("default", 0.0))


def log_api_cost(
    conn: sqlite3.Connection,
    *,
    provider: str,
    endpoint: str,
    cost_usd: float | None = None,
    context: str | None = None,
) -> None:
    """Log an API call cost to the database.

    If cost_usd is not provided, the estimated cost is looked up from COST_ESTIMATES.
    """
    if cost_usd is None:
        cost_usd = estimate_cost(provider, endpoint)

    conn.execute(
        """INSERT INTO api_costs (provider, endpoint, cost_usd, context, called_at)
           VALUES (?, ?, ?, ?, datetime('now'))""",
        (provider, endpoint, cost_usd, context),
    )


def get_cost_summary(
    conn: sqlite3.Connection,
    days: int = 30,
) -> list[dict]:
    """Get cost summary grouped by provider for the last N days."""
    rows = conn.execute(
        """SELECT provider,
                  COUNT(*) as calls,
                  SUM(cost_usd) as total_cost,
                  AVG(cost_usd) as avg_cost
           FROM api_costs
           WHERE called_at >= datetime('now', ?)
           GROUP BY provider
           ORDER BY total_cost DESC""",
        (f"-{days} days",),
    ).fetchall()
    return [dict(r) for r in rows]


def get_total_cost(conn: sqlite3.Connection, days: int = 30) -> float:
    """Get total API cost for the last N days."""
    row = conn.execute(
        """SELECT COALESCE(SUM(cost_usd), 0.0) as total
           FROM api_costs
           WHERE called_at >= datetime('now', ?)""",
        (f"-{days} days",),
    ).fetchone()
    return row["total"]
