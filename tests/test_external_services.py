"""Live integration tests for the three new external services.

Each test makes a real API call. Tests skip automatically if the required
environment variables are not set (i.e. placeholders still in .env).

Run individually:
    uv run pytest tests/test_external_services.py -v -s

Or a single service:
    uv run pytest tests/test_external_services.py -v -s -k reddit
    uv run pytest tests/test_external_services.py -v -s -k wordpress
    uv run pytest tests/test_external_services.py -v -s -k ga4
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env before importing tools so credentials are available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from tools import _load_all_tools, _REGISTRY, ToolContext

_load_all_tools()

# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

def _ctx() -> ToolContext:
    return ToolContext(
        agent_id="test",
        session_id="test_session",
        allowed_paths=["workspace/"],
    )


def _skip_if_placeholder(*env_vars: str) -> None:
    """Raise pytest.skip if any env var is missing or still the placeholder value."""
    placeholders = {"your_client_id", "your_client_secret", "your_property_id", ""}
    for var in env_vars:
        val = os.environ.get(var, "").strip()
        if not val or val in placeholders:
            pytest.skip(f"{var} is not configured — set it in .env to run this test")


# ===========================================================================
# Reddit
# ===========================================================================

class TestReddit:

    def test_get_hot_posts_space_buckets(self):
        """Fetch hot posts from r/SpaceBuckets and confirm we get real data back."""
        _skip_if_placeholder("REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET")

        func = _REGISTRY["get_hot_posts"]
        result = func(subreddit="SpaceBuckets", limit=5, context=_ctx())

        print(f"\n--- Reddit get_hot_posts(r/SpaceBuckets) ---\n{result}")
        assert "SpaceBuckets" in result
        assert "↑" in result, "Expected score indicator in output"

    def test_search_reddit_led_lighting(self):
        """Search r/microgrowery for LED-related posts."""
        _skip_if_placeholder("REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET")

        func = _REGISTRY["search_reddit"]
        result = func(subreddit="microgrowery", query="LED lighting controller", limit=5, context=_ctx())

        print(f"\n--- Reddit search(r/microgrowery, 'LED lighting controller') ---\n{result}")
        assert isinstance(result, str)
        assert len(result) > 20

    def test_get_post_comments(self):
        """Fetch comments from a known stable Reddit post (r/SpaceBuckets wiki/stickied post).
        
        We fetch hot posts first to get a live post ID, then retrieve its comments.
        This avoids hardcoding a post ID that might age out.
        """
        _skip_if_placeholder("REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET")

        import json
        import urllib.request
        from tools.reddit_tools import _get, _get_token

        # Get a real post ID from hot posts
        _get_token()  # ensure auth
        data = _get("/r/SpaceBuckets/hot", {"limit": 3, "raw_json": 1})
        posts = data.get("data", {}).get("children", [])
        assert posts, "No posts returned from r/SpaceBuckets"

        post_id = posts[0]["data"]["id"]
        func = _REGISTRY["get_post_comments"]
        result = func(subreddit="SpaceBuckets", post_id=post_id, limit=5, context=_ctx())

        print(f"\n--- Reddit get_post_comments(SpaceBuckets, {post_id}) ---\n{result}")
        assert isinstance(result, str)


# ===========================================================================
# WordPress
# ===========================================================================

class TestWordPress:

    def test_list_drafts(self):
        """List existing WordPress drafts — confirms auth and REST API connectivity."""
        _skip_if_placeholder("WP_SITE_URL", "WP_USERNAME", "WP_APP_PASSWORD")

        func = _REGISTRY["list_wordpress_drafts"]
        result = func(limit=5, context=_ctx())

        print(f"\n--- WordPress list_drafts ---\n{result}")
        assert isinstance(result, str)
        # Either "No draft posts found." or a list of drafts
        assert len(result) > 0

    def test_create_and_retrieve_draft(self):
        """Create a test draft post and immediately retrieve it to confirm round-trip."""
        _skip_if_placeholder("WP_SITE_URL", "WP_USERNAME", "WP_APP_PASSWORD")

        create_func = _REGISTRY["create_wordpress_draft"]
        get_func = _REGISTRY["get_wordpress_post"]

        result = create_func(
            title="[TEST] Council Integration Check — safe to delete",
            content="<p>This is an automated test post created by the Council marketing agent. It is safe to delete.</p>",
            excerpt="Automated integration test. Delete me.",
            tags="test,council,automated",
            context=_ctx(),
        )

        print(f"\n--- WordPress create_draft ---\n{result}")
        assert "Draft created" in result
        assert "id=" in result

        # Extract the post ID from the result string
        post_id_str = [part for part in result.split() if part.startswith("id=")][0]
        post_id = int(post_id_str.replace("id=", ""))

        # Retrieve it back
        get_result = get_func(post_id=post_id, context=_ctx())
        print(f"\n--- WordPress get_post({post_id}) ---\n{get_result}")
        assert "Council Integration Check" in get_result
        assert "draft" in get_result


# ===========================================================================
# GA4
# ===========================================================================

class TestGA4:

    def test_get_traffic_report(self):
        """Pull 7-day traffic by channel — confirms service account auth and property access."""
        _skip_if_placeholder("GA4_PROPERTY_ID", "GA4_CREDENTIALS_FILE")

        func = _REGISTRY["get_traffic_report"]
        result = func(days=7, context=_ctx())

        print(f"\n--- GA4 get_traffic_report(7 days) ---\n{result}")
        assert isinstance(result, str)
        assert "last 7 days" in result

    def test_get_top_pages(self):
        """Fetch top 5 pages by views over the last 30 days."""
        _skip_if_placeholder("GA4_PROPERTY_ID", "GA4_CREDENTIALS_FILE")

        func = _REGISTRY["get_top_pages"]
        result = func(days=30, limit=5, context=_ctx())

        print(f"\n--- GA4 get_top_pages(30 days, top 5) ---\n{result}")
        assert isinstance(result, str)
        assert "views" in result

    def test_get_top_referrers(self):
        """Fetch top referral sources over the last 30 days."""
        _skip_if_placeholder("GA4_PROPERTY_ID", "GA4_CREDENTIALS_FILE")

        func = _REGISTRY["get_top_referrers"]
        result = func(days=30, limit=5, context=_ctx())

        print(f"\n--- GA4 get_top_referrers(30 days) ---\n{result}")
        assert isinstance(result, str)
