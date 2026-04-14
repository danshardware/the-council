"""Read-only Reddit tools for community monitoring.

Requires two environment variables:
  REDDIT_CLIENT_ID      — from https://www.reddit.com/prefs/apps (script app)
  REDDIT_CLIENT_SECRET  — from the same app

Uses the Reddit OAuth2 client_credentials flow (app-only auth, no user account needed).
Rate limit: 100 requests/minute for authenticated apps.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request
from typing import Any

from tools import ToolContext, tool

logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
_API_BASE = "https://oauth.reddit.com"
_USER_AGENT = "CuriousCultivations/1.0 (community monitoring bot)"
_TIMEOUT = 30

# Simple in-process token cache (expires in 1 hour; fine for a single session)
_token_cache: dict[str, Any] = {}


def _credentials() -> tuple[str, str]:
    client_id = os.environ.get("REDDIT_CLIENT_ID", "").strip()
    secret = os.environ.get("REDDIT_CLIENT_SECRET", "").strip()
    if not client_id or not secret:
        raise EnvironmentError(
            "REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET must be set. "
            "Create a script app at https://www.reddit.com/prefs/apps"
        )
    return client_id, secret


def _get_token() -> str:
    """Return a cached or freshly obtained bearer token."""
    import time

    if _token_cache.get("expires_at", 0) > time.time() + 60:
        return _token_cache["access_token"]

    client_id, secret = _credentials()
    credentials = f"{client_id}:{secret}".encode()
    import base64
    encoded = base64.b64encode(credentials).decode()

    data = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode()
    req = urllib.request.Request(
        _TOKEN_URL,
        data=data,
        headers={
            "Authorization": f"Basic {encoded}",
            "User-Agent": _USER_AGENT,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        payload = json.loads(resp.read())

    import time
    _token_cache["access_token"] = payload["access_token"]
    _token_cache["expires_at"] = time.time() + payload.get("expires_in", 3600)
    return _token_cache["access_token"]


def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    """Authenticated GET to Reddit OAuth API."""
    token = _get_token()
    url = f"{_API_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": _USER_AGENT,
        },
    )
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return json.loads(resp.read())


def _fmt_post(post: dict) -> str:
    """Format a Reddit post dict into a compact readable string."""
    d = post.get("data", {})
    score = d.get("score", 0)
    num_comments = d.get("num_comments", 0)
    title = d.get("title", "")
    url = d.get("url", "")
    selftext = (d.get("selftext") or "")[:300].replace("\n", " ")
    permalink = f"https://reddit.com{d.get('permalink', '')}"
    return (
        f"[{score}↑ {num_comments}💬] {title}\n"
        f"  url: {url}\n"
        f"  reddit: {permalink}\n"
        f"  body: {selftext or '(link post)'}"
    )


@tool
def get_hot_posts(subreddit: str, limit: int, context: ToolContext) -> str:
    """Fetch the current hot posts from a subreddit. Returns titles, scores, comment counts, and URLs.

    Args:
        subreddit: Subreddit name without the r/ prefix (e.g. 'SpaceBuckets').
        limit:     Number of posts to return. Max 25.
    """
    limit = min(int(limit), 25)
    data = _get(f"/r/{subreddit}/hot", {"limit": limit, "raw_json": 1})
    posts = data.get("data", {}).get("children", [])
    if not posts:
        return f"No posts found in r/{subreddit}."
    lines = [f"Hot posts in r/{subreddit}:"]
    for p in posts:
        lines.append(_fmt_post(p))
    return "\n\n".join(lines)


@tool
def search_reddit(subreddit: str, query: str, limit: int, context: ToolContext) -> str:
    """Search a subreddit for posts matching a query. Returns titles, scores, comment counts, and URLs.

    Args:
        subreddit: Subreddit name without the r/ prefix (e.g. 'microgrowery').
        query:     Search query string.
        limit:     Number of results to return. Max 25.
    """
    limit = min(int(limit), 25)
    data = _get(
        f"/r/{subreddit}/search",
        {"q": query, "restrict_sr": "true", "sort": "relevance", "limit": limit, "raw_json": 1},
    )
    posts = data.get("data", {}).get("children", [])
    if not posts:
        return f"No results for '{query}' in r/{subreddit}."
    lines = [f"Search results for '{query}' in r/{subreddit}:"]
    for p in posts:
        lines.append(_fmt_post(p))
    return "\n\n".join(lines)


@tool
def get_post_comments(subreddit: str, post_id: str, limit: int, context: ToolContext) -> str:
    """Fetch the top-level comments from a Reddit post. Useful for identifying unanswered questions.

    Args:
        subreddit: Subreddit name without the r/ prefix.
        post_id:   Reddit post ID (the alphanumeric string, e.g. '1abc23').
        limit:     Number of top-level comments to return. Max 20.
    """
    limit = min(int(limit), 20)
    data = _get(
        f"/r/{subreddit}/comments/{post_id}",
        {"limit": limit, "depth": 1, "raw_json": 1},
    )
    if not isinstance(data, list) or len(data) < 2:
        return "Could not retrieve comments."
    comments = data[1].get("data", {}).get("children", [])
    lines = []
    for c in comments:
        d = c.get("data", {})
        if d.get("body") in (None, "[deleted]", "[removed]"):
            continue
        score = d.get("score", 0)
        body = (d.get("body") or "")[:400].replace("\n", " ")
        lines.append(f"  [{score}↑] {body}")
    if not lines:
        return "No comments found."
    return f"Top comments:\n" + "\n".join(lines)
