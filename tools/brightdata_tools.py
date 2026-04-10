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
import re
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
    except urllib.error.URLError as exc:
        return 0, str(exc)

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


# ---------------------------------------------------------------------------
# Helpers for research_web
# ---------------------------------------------------------------------------

_SKIP_DOMAINS: frozenset[str] = frozenset({
    "facebook.com", "twitter.com", "x.com", "instagram.com",
    "tiktok.com", "pinterest.com", "youtube.com",
})

# Sites that require interactive browser navigation (login walls, product search, checkout).
# research_web will flag these rather than skip or attempt a static scrape.
_INTERACTIVE_DOMAINS: frozenset[str] = frozenset({
    "amazon.com", "amazon.co.uk", "amazon.ca", "amazon.de", "amazon.fr",
    "amazon.co.jp", "amazon.com.au",
    "ebay.com", "ebay.co.uk",
    "walmart.com",
    "etsy.com",
    "alibaba.com", "aliexpress.com",
    "target.com",
    "bestbuy.com",
    "homedepot.com",
    "wayfair.com",
    "costco.com",
})

# Short phrases that indicate a page is a login/registration gate.
_LOGIN_KEYWORDS: frozenset[str] = frozenset({
    "sign in to continue", "log in to continue", "please sign in",
    "please log in", "login required", "you must be logged in",
    "sign up to access", "register to access", "members only",
    "create an account to",
})


def _is_login_wall(body: str) -> bool:
    """Return True if the scraped content is a thin login/registration gate."""
    if len(body) > 6000:
        return False
    lower = body.lower()
    return any(kw in lower for kw in _LOGIN_KEYWORDS)


def _clean_page(content: str, focus_words: set[str], max_chars: int = 4000) -> str:
    """Strip navigation noise from markdown and return the most relevant portion."""
    lines = content.split("\n")
    kept: list[str] = []
    for line in lines:
        s = line.strip()
        if not s:
            if kept and kept[-1]:
                kept.append("")
            continue
        # Skip lines that are pure markdown links (nav items like `[Home](/)`)
        if re.fullmatch(r"\[.{0,80}\]\([^)]{0,200}\)", s):
            continue
        # Skip horizontal rules
        if re.fullmatch(r"[-*_=]{3,}", s):
            continue
        kept.append(s)

    cleaned = "\n".join(kept).strip()

    if not focus_words or len(cleaned) <= max_chars:
        return cleaned[:max_chars]

    # Score paragraphs by focus keyword density and prefer high-scoring ones
    paragraphs = [p for p in cleaned.split("\n\n") if p.strip()]

    def _score_para(para: str) -> int:
        lower = para.lower()
        return sum(1 for w in focus_words if w in lower)

    # Always keep the intro (first two paragraphs), then fill with highest-scoring
    intro = paragraphs[:2]
    rest = paragraphs[2:]
    scored = sorted(rest, key=_score_para, reverse=True)

    selected = list(intro)
    total = sum(len(p) for p in selected)
    for para in scored:
        cost = len(para) + 2  # +2 for "\n\n"
        if total + cost > max_chars:
            break
        selected.append(para)
        total += cost

    return "\n\n".join(selected)[:max_chars]


# ---------------------------------------------------------------------------
# research_web tool
# ---------------------------------------------------------------------------

@tool
def research_web(
    queries: list,
    focus: str = "",
    max_pages: int = 6,
    context: ToolContext | None = None,
) -> str:
    """
    Research a topic end-to-end: runs multiple searches, deduplicates URLs, scrapes
    the top pages, and saves cleaned excerpts to research_results.md in the workspace.

    The entire pipeline is Python — no extra LLM turns are needed.

    Args:
        queries:   List of search query strings (up to 8).
        focus:     Short phrase describing what to look for (e.g. "reliability issues").
        max_pages: Maximum number of pages to scrape (default 6).

    Returns:
        A brief summary of what was found and the path to the saved results file.
    """
    from tools.tool_guardrails import pre_search, post_search, pre_scrape, post_scrape

    if context is None:
        context = ToolContext(agent_id="", session_id="")

    try:
        api_key, zone = _credentials()
    except EnvironmentError as exc:
        return f"[ERROR] {exc}"

    # Normalise queries — models sometimes pass a JSON string or comma-separated string
    if isinstance(queries, str):
        import json as _json
        try:
            queries = _json.loads(queries)
        except Exception:
            queries = [q.strip() for q in queries.split(",") if q.strip()]
    queries = [str(q) for q in queries[:8]]
    if not queries:
        return "[ERROR] No queries provided."

    focus_words: set[str] = set(re.sub(r"[^\w\s]", "", focus).lower().split()) if focus else set()

    # ── Phase 1: multi-query SERP ──────────────────────────────────────────────
    seen_urls: set[str] = set()
    candidates: list[dict] = []

    for query in queries:
        verdict, _ = pre_search(query)
        if verdict != "approved":
            continue
        cache_key = f"search:{query}"
        if cache_key in context.fetched_cache:
            continue
        context.fetched_cache.add(cache_key)

        search_url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)
        status, body = _post_with_retry(
            {"url": search_url, "zone": zone, "format": "raw", "data_format": "parsed_light"},
            api_key,
        )
        if status != 200:
            logger.warning("research_web SERP failed for %r: HTTP %s", query, status)
            continue
        try:
            import json as _json
            data = _json.loads(body)
        except Exception:
            continue

        organic = [
            item for item in (data.get("organic") or [])
            if item.get("link") and item.get("title")
        ]
        post_verdict, _ = post_search(query, "\n".join(r.get("link", "") for r in organic))
        if post_verdict != "approved":
            continue

        for rank, item in enumerate(organic):
            url = item["link"]
            if url in seen_urls:
                continue
            seen_urls.add(url)
            domain = urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")
            if any(skip in domain for skip in _SKIP_DOMAINS):
                continue
            candidates.append({
                "url": url,
                "title": item["title"],
                "snippet": item.get("description", ""),
                "rank": rank,
            })

    if not candidates:
        return "[No search results found for any of the provided queries]"

    # ── Phase 2: score & select top URLs ──────────────────────────────────────
    def _score_url(entry: dict) -> float:
        text = (entry["title"] + " " + entry["snippet"]).lower()
        keyword_bonus = sum(1.0 for w in focus_words if w in text)
        return keyword_bonus - entry["rank"] * 0.1  # rank 0–9 acts as gentle tie-break

    top_entries = sorted(candidates, key=_score_url, reverse=True)[:max_pages]

    # ── Phase 3: scrape & clean ────────────────────────────────────────────────
    output_sections: list[str] = []
    scraped_titles: list[tuple[str, str, str]] = []
    interactive_sources: list[tuple[str, str, str]] = []  # (title, url, reason)

    for entry in top_entries:
        url = entry["url"]
        title = entry["title"]
        snippet = entry["snippet"]
        header = f"### {title}\nURL: {url}\nSnippet: {snippet}"

        try:
            domain = urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")
        except Exception:
            domain = ""
        is_interactive_domain = any(d in domain for d in _INTERACTIVE_DOMAINS)

        pre_verdict, _ = pre_scrape(url)
        if pre_verdict != "approved":
            output_sections.append(header + "\n[Page blocked by guardrail — snippet only]")
            scraped_titles.append((f"{title} (blocked)", url, ""))
            continue

        cache_key = f"scrape:{url}"
        if cache_key in context.fetched_cache:
            output_sections.append(header + "\n[Already scraped this session]")
            scraped_titles.append((f"{title} (cached)", url, ""))
            continue
        context.fetched_cache.add(cache_key)

        status, body = _post_with_retry(
            {"url": url, "zone": zone, "format": "raw", "data_format": "markdown"},
            api_key,
        )
        if status != 200:
            output_sections.append(header + f"\n[Scrape failed: HTTP {status}]")
            scraped_titles.append((f"{title} (failed)", url, ""))
            continue

        post_verdict, _ = post_scrape(url, body)
        if post_verdict != "approved":
            output_sections.append(header + "\n[Content blocked by post-guardrail]")
            scraped_titles.append((f"{title} (filtered)", url, ""))
            continue

        excerpt = _clean_page(body, focus_words, max_chars=4000)
        output_sections.append(f"{header}\n\n{excerpt}")

        # Tag for browser follow-up if it's a known marketplace or if content is a login wall
        if is_interactive_domain or _is_login_wall(body):
            reason = "marketplace / product-listing site" if is_interactive_domain else "login-gated page"
            interactive_sources.append((title, url, reason))
        scraped_titles.append((title, url, excerpt[:300]))

    # ── Phase 4: write to workspace file ──────────────────────────────────────
    full_content = "\n\n---\n\n".join(output_sections)

    if context.allowed_paths:
        from pathlib import Path as _Path
        save_path = _Path(context.allowed_paths[0]) / "research_results.md"
        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_text(full_content, encoding="utf-8")
        except Exception as exc:
            logger.warning("research_web failed to write results file: %s", exc)

    # ── Phase 5: return key excerpts (agent does not need to read the file) ───
    lines = [f"Research complete. Found {len(scraped_titles)} sources:\n"]
    for i, (title, url, snippet) in enumerate(scraped_titles, 1):
        lines.append(f"[{i}] {title}\n    {url}\n    {snippet}\n")

    if interactive_sources:
        lines.append(
            "\nINTERACTIVE REQUIRED — these pages need browser navigation (browse_web):"
        )
        for i, (title, url, reason) in enumerate(interactive_sources, 1):
            lines.append(f"[{i}] {title}\n    {url}\n    Reason: {reason}\n")

    return "\n".join(lines)
