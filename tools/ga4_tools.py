"""Google Analytics 4 Data API tools for website performance metrics.

Requires environment variables:
  GA4_PROPERTY_ID   — Numeric GA4 property ID (e.g. '123456789'), found in GA4 Admin → Property Settings
  GA4_CREDENTIALS_FILE — Path to a service account JSON key file with 'Viewer' access to the property

The service account must be added as a user in GA4 Admin → Property → Property access management.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from tools import ToolContext, tool

logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _client() -> Any:
    """Return an authenticated GA4 BetaAnalyticsDataClient."""
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.oauth2 import service_account
    except ImportError as exc:
        raise ImportError(
            "google-analytics-data and google-auth packages are required. "
            "Run: uv add google-analytics-data"
        ) from exc

    creds_file = os.environ.get("GA4_CREDENTIALS_FILE", "").strip()
    if not creds_file:
        raise EnvironmentError(
            "GA4_CREDENTIALS_FILE must point to a service account JSON key file."
        )
    credentials = service_account.Credentials.from_service_account_file(
        creds_file,
        scopes=["https://www.googleapis.com/auth/analytics.readonly"],
    )
    return BetaAnalyticsDataClient(credentials=credentials)


def _property_id() -> str:
    pid = os.environ.get("GA4_PROPERTY_ID", "").strip()
    if not pid:
        raise EnvironmentError("GA4_PROPERTY_ID must be set.")
    return f"properties/{pid}"


def _run_report(dimensions: list[str], metrics: list[str], date_range_days: int, row_limit: int = 10) -> list[dict]:
    """Run a GA4 report and return rows as list of dicts."""
    from google.analytics.data_v1beta.types import (
        DateRange,
        Dimension,
        Metric,
        RunReportRequest,
    )

    client = _client()
    request = RunReportRequest(
        property=_property_id(),
        dimensions=[Dimension(name=d) for d in dimensions],
        metrics=[Metric(name=m) for m in metrics],
        date_ranges=[DateRange(start_date=f"{date_range_days}daysAgo", end_date="today")],
        limit=row_limit,
    )
    response = client.run_report(request)

    rows: list[dict] = []
    dim_headers = [h.name for h in response.dimension_headers]
    met_headers = [h.name for h in response.metric_headers]
    for row in response.rows:
        entry: dict[str, str] = {}
        for i, dv in enumerate(row.dimension_values):
            entry[dim_headers[i]] = dv.value
        for i, mv in enumerate(row.metric_values):
            entry[met_headers[i]] = mv.value
        rows.append(entry)
    return rows


@tool
def get_traffic_report(days: int, context: ToolContext) -> str:
    """Get a summary of website traffic for the past N days: sessions, users, and bounce rate by channel.

    Args:
        days: Number of days to look back (e.g. 7, 30).
    """
    days = int(days)
    rows = _run_report(
        dimensions=["sessionDefaultChannelGroup"],
        metrics=["sessions", "totalUsers", "bounceRate"],
        date_range_days=days,
        row_limit=10,
    )
    if not rows:
        return "No traffic data available."
    lines = [f"Traffic by channel — last {days} days:"]
    for r in rows:
        channel = r.get("sessionDefaultChannelGroup", "Unknown")
        sessions = r.get("sessions", "0")
        users = r.get("totalUsers", "0")
        bounce = float(r.get("bounceRate", 0)) * 100
        lines.append(f"  {channel}: {sessions} sessions, {users} users, {bounce:.0f}% bounce")
    return "\n".join(lines)


@tool
def get_top_pages(days: int, limit: int, context: ToolContext) -> str:
    """Get the top pages by pageviews for the past N days. Useful for identifying popular content topics.

    Args:
        days:  Number of days to look back.
        limit: Number of top pages to return. Max 20.
    """
    days = int(days)
    limit = min(int(limit), 20)
    rows = _run_report(
        dimensions=["pagePath", "pageTitle"],
        metrics=["screenPageViews", "averageSessionDuration"],
        date_range_days=days,
        row_limit=limit,
    )
    if not rows:
        return "No page data available."
    lines = [f"Top {limit} pages — last {days} days:"]
    for r in rows:
        path = r.get("pagePath", "")
        title = r.get("pageTitle", "")
        views = r.get("screenPageViews", "0")
        avg_time = float(r.get("averageSessionDuration", 0))
        lines.append(f"  [{views} views, {avg_time:.0f}s avg] {title} ({path})")
    return "\n".join(lines)


@tool
def get_top_referrers(days: int, limit: int, context: ToolContext) -> str:
    """Get the top referring sources (domains) sending traffic to the site for the past N days.

    Args:
        days:  Number of days to look back.
        limit: Number of referrers to return. Max 20.
    """
    days = int(days)
    limit = min(int(limit), 20)
    rows = _run_report(
        dimensions=["sessionSource"],
        metrics=["sessions", "totalUsers"],
        date_range_days=days,
        row_limit=limit,
    )
    if not rows:
        return "No referrer data available."
    lines = [f"Top referrers — last {days} days:"]
    for r in rows:
        source = r.get("sessionSource", "(direct)")
        sessions = r.get("sessions", "0")
        users = r.get("totalUsers", "0")
        lines.append(f"  {source}: {sessions} sessions, {users} users")
    return "\n".join(lines)
