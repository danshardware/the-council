"""WordPress REST API tools for creating and listing content drafts.

Requires environment variables:
  WP_SITE_URL    — Base URL of the site, e.g. https://curiouscultivations.com
  WP_USERNAME    — WordPress username
  WP_APP_PASSWORD — Application password (generated at Users → Profile → Application Passwords)

All posts are created in 'draft' status — nothing is published without Dan's manual review.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
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

_TIMEOUT = 30


def _credentials() -> tuple[str, str, str]:
    site = os.environ.get("WP_SITE_URL", "").rstrip("/")
    username = os.environ.get("WP_USERNAME", "").strip()
    app_password = os.environ.get("WP_APP_PASSWORD", "").strip()
    if not site or not username or not app_password:
        raise EnvironmentError(
            "WP_SITE_URL, WP_USERNAME, and WP_APP_PASSWORD must be set. "
            "Create an Application Password at Users → Profile in wp-admin."
        )
    return site, username, app_password


def _auth_header(username: str, app_password: str) -> str:
    import base64
    token = base64.b64encode(f"{username}:{app_password}".encode()).decode()
    return f"Basic {token}"


def _request(method: str, path: str, body: dict | None = None) -> Any:
    site, username, app_password = _credentials()
    url = f"{site}/wp-json/wp/v2{path}"
    data = json.dumps(body).encode() if body else None
    headers: dict[str, str] = {
        "Authorization": _auth_header(username, app_password),
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise RuntimeError(f"WordPress API error {exc.code}: {body_text}") from exc


@tool
def create_wordpress_draft(
    title: str,
    content: str,
    excerpt: str,
    tags: str,
    context: ToolContext,
) -> str:
    """Create a WordPress post draft for Dan to review and publish. Never publishes automatically.

    Args:
        title:   Post title.
        content: Full post body in HTML or plain text (WordPress accepts both).
        excerpt: Short summary shown in post listings and SEO meta.
        tags:    Comma-separated list of tag names (e.g. 'LED lighting,ESP32,grow tent').
    """
    # Resolve tag IDs (create tags that don't exist yet)
    tag_ids: list[int] = []
    for tag_name in [t.strip() for t in tags.split(",") if t.strip()]:
        try:
            result = _request("POST", "/tags", {"name": tag_name})
            tag_ids.append(result["id"])
        except RuntimeError as exc:
            # Tag may already exist; search for it
            try:
                search = _request("GET", f"/tags?search={urllib.parse.quote(tag_name)}&per_page=1")
                if search:
                    tag_ids.append(search[0]["id"])
            except Exception:
                logger.warning("Could not resolve tag '%s': %s", tag_name, exc)

    payload: dict[str, Any] = {
        "title": title,
        "content": content,
        "excerpt": excerpt,
        "status": "draft",
    }
    if tag_ids:
        payload["tags"] = tag_ids

    result = _request("POST", "/posts", payload)
    post_id = result.get("id")
    edit_url = result.get("_links", {}).get("wp:post_type", [{}])[0]
    site, _, _ = _credentials()
    admin_link = f"{site}/wp-admin/post.php?post={post_id}&action=edit"
    return (
        f"Draft created: id={post_id}\n"
        f"Title: {title}\n"
        f"Edit URL: {admin_link}"
    )


@tool
def list_wordpress_drafts(limit: int, context: ToolContext) -> str:
    """List existing WordPress draft posts (not yet published). Useful for avoiding duplicate content.

    Args:
        limit: Maximum number of drafts to return. Max 20.
    """
    limit = min(int(limit), 20)
    posts = _request("GET", f"/posts?status=draft&per_page={limit}&orderby=modified&order=desc")
    if not posts:
        return "No draft posts found."
    site, _, _ = _credentials()
    lines = ["WordPress drafts (unpublished):"]
    for p in posts:
        pid = p.get("id")
        title = (p.get("title") or {}).get("rendered", "(no title)")
        modified = p.get("modified", "")[:10]
        admin_link = f"{site}/wp-admin/post.php?post={pid}&action=edit"
        lines.append(f"  [{modified}] {title} — {admin_link}")
    return "\n".join(lines)


@tool
def get_wordpress_post(post_id: int, context: ToolContext) -> str:
    """Retrieve the title and content of a WordPress post by ID. Works for drafts and published posts.

    Args:
        post_id: The numeric WordPress post ID.
    """
    post = _request("GET", f"/posts/{post_id}")
    title = (post.get("title") or {}).get("rendered", "")
    content = (post.get("content") or {}).get("rendered", "")[:1000]
    status = post.get("status", "")
    return f"Post {post_id} ({status})\nTitle: {title}\n\nContent (first 1000 chars):\n{content}"
