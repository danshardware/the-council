"""Bright Data search and scrape tools.

Requires two environment variables:
  BRIGHTDATA_API_KEY         — API key from https://brightdata.com/cp
  BRIGHTDATA_UNLOCKER_ZONE   — Web Unlocker zone name

search_web  — Google SERP via Bright Data's parsed SERP API (no captchas)
scrape_url  — Fetch any URL as Markdown via Bright Data's Web Unlocker (bypasses blocks)
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from tools import ToolContext, tool

logger = logging.getLogger(__name__)

# Load .env so credentials are available when running tests or scripts
# directly without going through run.py
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

_API_URL = "https://api.brightdata.com/request"
_RETRY_STATUSES = {408, 429, 500, 502, 503, 504}
_MAX_RETRIES = 4


def _post(payload: dict[str, Any], api_key: str) -> tuple[int, str]:
    """POST to Bright Data API, return (status_code, body_text)."""
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        _API_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return exc.code, body


def _post_with_retry(payload: dict[str, Any], api_key: str) -> tuple[int, str]:
    """POST with exponential backoff on transient errors."""
    for attempt in range(_MAX_RETRIES):
        status, body = _post(payload, api_key)
        if status not in _RETRY_STATUSES:
            return status, body
        wait = 0.5 * (2 ** attempt)
        logger.warning("Bright Data transient %s, retrying in %.1fs (attempt %d/%d)",
                       status, wait, attempt + 1, _MAX_RETRIES)
        time.sleep(wait)
    return status, body  # type: ignore[possibly-undefined]


def _credentials() -> tuple[str, str]:
    """Return (api_key, zone) or raise a clear error."""
    api_key = os.environ.get("BRIGHTDATA_API_KEY", "").strip()
    zone = os.environ.get("BRIGHTDATA_UNLOCKER_ZONE", "").strip()
    if not api_key:
        raise EnvironmentError(
            "BRIGHTDATA_API_KEY is not set. "
            "Get a key from https://brightdata.com/cp and set it in your environment."
        )
    if not zone:
        raise EnvironmentError(
            "BRIGHTDATA_UNLOCKER_ZONE is not set. "
            "Create a Web Unlocker zone at https://brightdata.com/cp and set its name."
        )
    return api_key, zone


@tool
def search_web(query: str, context: ToolContext) -> str:
    """
    Search Google via Bright Data's SERP API (no CAPTCHA).
    Returns up to 10 organic results with title, URL and description snippet.

    Args:
        query:   Search query string
        context: ToolContext (injected by framework)

    Returns:
        Numbered list of search results, or an [ERROR] message.
    """
    from tools.tool_guardrails import pre_search, post_search

    # Dedup: skip if this exact query was already fetched in this session
    cache_key = f"search:{query}"
    if cache_key in context.fetched_cache:
        logger.info("search_web cache hit, skipping duplicate query=%r", query)
        return f"[CACHED] Already searched this session: {query}"
    context.fetched_cache.add(cache_key)

    verdict, reason = pre_search(query)
    if verdict != "approved":
        logger.warning("search_web pre-guardrail blocked query=%r reason=%s", query, reason)
        return f"[BLOCKED] Search query rejected by safety guardrail: {reason}"

    try:
        api_key, zone = _credentials()
    except EnvironmentError as exc:
        return f"[ERROR] {exc}"

    search_url = (
        "https://www.google.com/search?q="
        + urllib.parse.quote_plus(query)
    )
    payload = {
        "url": search_url,
        "zone": zone,
        "format": "raw",
        "data_format": "parsed_light",
    }

    try:
        status, body = _post_with_retry(payload, api_key)
    except Exception as exc:
        logger.exception("search_web request failed")
        return f"[ERROR] Bright Data request failed: {exc}"

    if status != 200:
        return f"[ERROR] Bright Data search returned HTTP {status}: {body[:500]}"

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return f"[ERROR] Could not parse Bright Data response: {body[:500]}"

    organic: list[dict] = [
        item for item in (data.get("organic") or [])
        if item.get("link") and item.get("title")
    ]

    if not organic:
        return "[No results found]"

    lines = [f"Search results for: {query}\n"]
    for i, item in enumerate(organic, 1):
        lines.append(f"{i}. {item['title']}")
        lines.append(f"   URL: {item['link']}")
        if item.get("description"):
            lines.append(f"   {item['description']}")
        lines.append("")

    result = "\n".join(lines)

    verdict, reason = post_search(query, result)
    if verdict != "approved":
        logger.warning("search_web post-guardrail filtered query=%r reason=%s", query, reason)
        return f"[FILTERED] Search results blocked by safety guardrail: {reason}"

    return result


@tool
def scrape_url(url: str, context: ToolContext) -> str:
    """
    Fetch a web page as Markdown.
    Bypasses CAPTCHAs and bot-detection that block the browser tool.
    Use this when browse_web reports a CAPTCHA or blocked access.

    Args:
        url:     Full URL to fetch (must start with http:// or https://)
        context: ToolContext (injected by framework)

    Returns:
        Page content as Markdown, or an [ERROR] message.
    """
    if not url.startswith(("http://", "https://")):
        return "[ERROR] url must start with http:// or https://"

    # Dedup: skip if this URL was already fetched in this session
    cache_key = f"scrape:{url}"
    if cache_key in context.fetched_cache:
        logger.info("scrape_url cache hit, skipping duplicate url=%r", url)
        return f"[CACHED] Already scraped this session: {url}"
    context.fetched_cache.add(cache_key)

    from tools.tool_guardrails import pre_scrape, post_scrape

    verdict, reason = pre_scrape(url)
    if verdict != "approved":
        logger.warning("scrape_url pre-guardrail blocked url=%r reason=%s", url, reason)
        return f"[BLOCKED] URL rejected by safety guardrail: {reason}"

    try:
        api_key, zone = _credentials()
    except EnvironmentError as exc:
        return f"[ERROR] {exc}"

    payload = {
        "url": url,
        "zone": zone,
        "format": "raw",
        "data_format": "markdown",
    }

    try:
        status, body = _post_with_retry(payload, api_key)
    except Exception as exc:
        logger.exception("scrape_url request failed")
        return f"[ERROR] Bright Data request failed: {exc}"

    if status != 200:
        return f"[ERROR] Bright Data scrape returned HTTP {status}: {body[:500]}"

    content = body or "[No content returned]"

    verdict, reason = post_scrape(url, content)
    if verdict != "approved":
        logger.warning("scrape_url post-guardrail filtered url=%r reason=%s", url, reason)
        return f"[FILTERED] Scraped content blocked by safety guardrail: {reason}"

    return content
