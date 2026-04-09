"""Tests for search_web and scrape_url inline guardrails.

Covers:
  - check_blacklists()  — pattern and domain matching, no LLM
  - pre_scrape()        — blacklist wrapper
  - pre_search()        — blacklist fast-path (LLM call skipped when blocked)
  - YAML config structure for search_guardrails / scrape_guardrails
  - search_web / scrape_url return [BLOCKED] / [FILTERED] correctly (mocked guardrails)
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Config structure
# ---------------------------------------------------------------------------

class TestGuardrailConfig:
    """Verify the YAML config has both new sections with required keys."""

    def _load(self) -> dict:
        path = Path(__file__).parent.parent / "config" / "browser_guardrails.yaml"
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_search_guardrails_section_exists(self):
        config = self._load()
        assert "search_guardrails" in config, "Missing search_guardrails section"

    def test_search_guardrails_has_model(self):
        config = self._load()
        assert "model_id" in config["search_guardrails"]

    def test_search_guardrails_has_pre_prompt(self):
        config = self._load()
        prompt = config["search_guardrails"].get("pre_execution_prompt", "")
        assert len(prompt) > 50, "pre_execution_prompt is empty or too short"

    def test_search_guardrails_has_post_prompt(self):
        config = self._load()
        prompt = config["search_guardrails"].get("post_execution_prompt", "")
        assert len(prompt) > 50, "post_execution_prompt is empty or too short"

    def test_scrape_guardrails_section_exists(self):
        config = self._load()
        assert "scrape_guardrails" in config, "Missing scrape_guardrails section"

    def test_scrape_guardrails_has_post_prompt(self):
        config = self._load()
        prompt = config["scrape_guardrails"].get("post_execution_prompt", "")
        assert len(prompt) > 50, "scrape post_execution_prompt is empty or too short"


# ---------------------------------------------------------------------------
# check_blacklists — pure regex/string matching, no LLM
# ---------------------------------------------------------------------------

class TestCheckBlacklists:

    def test_blocked_pattern_exe_download(self):
        from tools.tool_guardrails import check_blacklists
        blocked, reason = check_blacklists("download malware.exe")
        assert blocked is True
        assert "blocked pattern" in reason.lower()

    def test_blocked_pattern_gambling(self):
        from tools.tool_guardrails import check_blacklists
        blocked, reason = check_blacklists("best casino strategy 2025")
        assert blocked is True

    def test_blocked_pattern_weapons(self):
        from tools.tool_guardrails import check_blacklists
        blocked, _ = check_blacklists("where to buy a firearm")
        assert blocked is True

    def test_blocked_domain(self):
        from tools.tool_guardrails import check_blacklists
        blocked, reason = check_blacklists("https://thepiratebay.org/search")
        assert blocked is True
        assert "blocked domain" in reason.lower()

    def test_blocked_domain_onion(self):
        from tools.tool_guardrails import check_blacklists
        blocked, _ = check_blacklists("http://some.onion/page")
        assert blocked is True

    def test_safe_text_passes(self):
        from tools.tool_guardrails import check_blacklists
        blocked, _ = check_blacklists("AWS Lambda pricing and best practices")
        assert blocked is False

    def test_safe_url_passes(self):
        from tools.tool_guardrails import check_blacklists
        blocked, _ = check_blacklists("https://docs.aws.amazon.com/lambda/latest/dg/welcome.html")
        assert blocked is False


# ---------------------------------------------------------------------------
# pre_scrape — wraps check_blacklists, returns (verdict, reason)
# ---------------------------------------------------------------------------

class TestPreScrape:

    def test_blocked_url_returns_rejected(self):
        from tools.tool_guardrails import pre_scrape
        verdict, reason = pre_scrape("https://thepiratebay.org/torrent/12345")
        assert verdict == "rejected"
        assert reason

    def test_safe_url_returns_approved(self):
        from tools.tool_guardrails import pre_scrape
        verdict, _ = pre_scrape("https://en.wikipedia.org/wiki/Python_(programming_language)")
        assert verdict == "approved"

    def test_no_llm_called_for_pre_scrape(self):
        """pre_scrape must never make an LLM call — blacklist only."""
        from tools.tool_guardrails import pre_scrape
        with patch("tools.tool_guardrails.run_guardrail") as mock_llm:
            pre_scrape("https://safe-site.example.com/article")
            mock_llm.assert_not_called()


# ---------------------------------------------------------------------------
# pre_search — blacklist fast-path (LLM skipped when blocked by blacklist)
# ---------------------------------------------------------------------------

class TestPreSearch:

    def test_blacklisted_query_blocked_without_llm(self):
        from tools.tool_guardrails import pre_search
        with patch("tools.tool_guardrails.run_guardrail") as mock_llm:
            verdict, reason = pre_search("best casino betting tips")
            assert verdict == "rejected"
            mock_llm.assert_not_called()

    def test_safe_query_calls_llm(self):
        from tools.tool_guardrails import pre_search
        with patch("tools.tool_guardrails.run_guardrail", return_value=("approved", "looks fine")) as mock_llm:
            verdict, _ = pre_search("Python asyncio tutorial")
            assert verdict == "approved"
            mock_llm.assert_called_once()

    def test_llm_rejection_propagates(self):
        from tools.tool_guardrails import pre_search
        with patch("tools.tool_guardrails.run_guardrail", return_value=("rejected", "inappropriate topic")):
            verdict, reason = pre_search("some borderline query")
            assert verdict == "rejected"
            assert "inappropriate" in reason


# ---------------------------------------------------------------------------
# Tool integration — search_web and scrape_url return correct blocked strings
# ---------------------------------------------------------------------------

class TestSearchWebGuardrails:
    """search_web must return [BLOCKED] / [FILTERED] when guardrails fire."""

    def _make_ctx(self):
        from tools import ToolContext
        return ToolContext(agent_id="test", session_id="test_session")

    def test_blocked_query_returns_blocked_message(self):
        from tools.brightdata_tools import search_web
        ctx = self._make_ctx()
        with patch("tools.tool_guardrails.run_guardrail", return_value=("rejected", "query is unsafe")):
            # Blacklist won't fire for this query, so LLM mock will
            result = search_web(query="some edge-case query", context=ctx)
        assert result.startswith("[BLOCKED]")

    def test_blacklisted_query_blocked(self):
        """Query matching blacklist → [BLOCKED] without any HTTP call."""
        from tools.brightdata_tools import search_web
        ctx = self._make_ctx()
        with patch("tools.brightdata_tools._post_with_retry") as mock_http:
            result = search_web(query="download malware.exe installer", context=ctx)
            assert result.startswith("[BLOCKED]")
            mock_http.assert_not_called()

    def test_post_guardrail_filtered(self):
        """post_search rejection → [FILTERED] even if search succeeded."""
        from tools.brightdata_tools import search_web
        ctx = self._make_ctx()
        mock_results = {
            "organic": [
                {"title": "Result 1", "link": "https://example.com", "description": "Some text"}
            ]
        }
        import json
        with patch("tools.tool_guardrails.run_guardrail") as mock_gr:
            # pre approved, post rejected
            mock_gr.side_effect = [("approved", "ok"), ("rejected", "injection detected")]
            with patch("tools.brightdata_tools._credentials", return_value=("fake-key", "fake-zone")):
                with patch("tools.brightdata_tools._post_with_retry", return_value=(200, json.dumps(mock_results))):
                    result = search_web(query="safe query", context=ctx)
        assert result.startswith("[FILTERED]")


class TestScrapeUrlGuardrails:
    """scrape_url must return [BLOCKED] / [FILTERED] when guardrails fire."""

    def _make_ctx(self):
        from tools import ToolContext
        return ToolContext(agent_id="test", session_id="test_session")

    def test_blacklisted_url_blocked_without_http_call(self):
        from tools.brightdata_tools import scrape_url
        ctx = self._make_ctx()
        with patch("tools.brightdata_tools._post_with_retry") as mock_http:
            result = scrape_url(url="https://thepiratebay.org/page", context=ctx)
            assert result.startswith("[BLOCKED]")
            mock_http.assert_not_called()

    def test_post_guardrail_filtered_on_injection(self):
        from tools.brightdata_tools import scrape_url
        ctx = self._make_ctx()
        with patch("tools.tool_guardrails.run_guardrail", return_value=("rejected", "prompt injection found")):
            with patch("tools.brightdata_tools._credentials", return_value=("fake-key", "fake-zone")):
                with patch("tools.brightdata_tools._post_with_retry", return_value=(200, "Normal looking page content")):
                    result = scrape_url(url="https://safe-looking.example.com/article", context=ctx)
        assert result.startswith("[FILTERED]")

    def test_safe_url_passes_through(self):
        from tools.brightdata_tools import scrape_url
        ctx = self._make_ctx()
        page_content = "# Article Title\n\nSome normal article content."
        with patch("tools.tool_guardrails.run_guardrail", return_value=("approved", "content is safe")):
            with patch("tools.brightdata_tools._post_with_retry", return_value=(200, page_content)):
                with patch("tools.brightdata_tools._credentials", return_value=("fake-key", "fake-zone")):
                    result = scrape_url(url="https://en.wikipedia.org/wiki/Python", context=ctx)
        assert result == page_content


# ---------------------------------------------------------------------------
# URL deduplication (fetched_cache on ToolContext)
# ---------------------------------------------------------------------------

class TestSearchWebDedup:

    def _make_ctx(self):
        from tools import ToolContext
        return ToolContext(agent_id="test", session_id="test_session")

    def test_second_identical_query_returns_cached(self):
        from tools.brightdata_tools import search_web
        ctx = self._make_ctx()
        with patch("tools.tool_guardrails.run_guardrail", return_value=("approved", "ok")):
            with patch("tools.brightdata_tools._credentials", return_value=("k", "z")):
                with patch("tools.brightdata_tools._post_with_retry", return_value=(200, '{"organic": [{"title": "T", "link": "https://x.com"}]}')):
                    first = search_web(query="python asyncio", context=ctx)
                    second = search_web(query="python asyncio", context=ctx)
        assert not first.startswith("[CACHED]")
        assert second.startswith("[CACHED]")

    def test_different_queries_both_execute(self):
        from tools.brightdata_tools import search_web
        ctx = self._make_ctx()
        with patch("tools.tool_guardrails.run_guardrail", return_value=("approved", "ok")):
            with patch("tools.brightdata_tools._credentials", return_value=("k", "z")):
                with patch("tools.brightdata_tools._post_with_retry", return_value=(200, '{"organic": [{"title": "T", "link": "https://x.com"}]}')):
                    r1 = search_web(query="query one", context=ctx)
                    r2 = search_web(query="query two", context=ctx)
        assert not r1.startswith("[CACHED]")
        assert not r2.startswith("[CACHED]")

    def test_cache_is_per_context_instance(self):
        """Different ToolContext instances must not share the cache."""
        from tools.brightdata_tools import search_web
        from tools import ToolContext
        ctx1 = ToolContext(agent_id="a", session_id="s1")
        ctx2 = ToolContext(agent_id="a", session_id="s2")
        with patch("tools.tool_guardrails.run_guardrail", return_value=("approved", "ok")):
            with patch("tools.brightdata_tools._credentials", return_value=("k", "z")):
                with patch("tools.brightdata_tools._post_with_retry", return_value=(200, '{"organic": [{"title": "T", "link": "https://x.com"}]}')):
                    search_web(query="shared query", context=ctx1)
                    r2 = search_web(query="shared query", context=ctx2)
        assert not r2.startswith("[CACHED]")


class TestScrapeUrlDedup:

    def _make_ctx(self):
        from tools import ToolContext
        return ToolContext(agent_id="test", session_id="test_session")

    def test_second_identical_url_returns_cached(self):
        from tools.brightdata_tools import scrape_url
        ctx = self._make_ctx()
        with patch("tools.tool_guardrails.run_guardrail", return_value=("approved", "ok")):
            with patch("tools.brightdata_tools._credentials", return_value=("k", "z")):
                with patch("tools.brightdata_tools._post_with_retry", return_value=(200, "content")):
                    first = scrape_url(url="https://example.com/page", context=ctx)
                    second = scrape_url(url="https://example.com/page", context=ctx)
        assert not first.startswith("[CACHED]")
        assert second.startswith("[CACHED]")

    def test_no_http_call_on_cache_hit(self):
        from tools.brightdata_tools import scrape_url
        ctx = self._make_ctx()
        with patch("tools.tool_guardrails.run_guardrail", return_value=("approved", "ok")):
            with patch("tools.brightdata_tools._credentials", return_value=("k", "z")):
                with patch("tools.brightdata_tools._post_with_retry", return_value=(200, "content")) as mock_http:
                    scrape_url(url="https://example.com/page", context=ctx)
                    scrape_url(url="https://example.com/page", context=ctx)
                    assert mock_http.call_count == 1  # only one real HTTP call

    def test_search_and_scrape_caches_are_independent(self):
        """search:X and scrape:X are different cache keys."""
        from tools.brightdata_tools import search_web, scrape_url
        from tools import ToolContext
        ctx = ToolContext(agent_id="a", session_id="s")
        url = "https://example.com/page"
        with patch("tools.tool_guardrails.run_guardrail", return_value=("approved", "ok")):
            with patch("tools.brightdata_tools._credentials", return_value=("k", "z")):
                with patch("tools.brightdata_tools._post_with_retry", return_value=(200, '{"organic": [{"title": "T", "link": "https://x.com"}]}')):
                    search_web(query=url, context=ctx)  # caches "search:<url>"
                with patch("tools.brightdata_tools._credentials", return_value=("k", "z")):
                    with patch("tools.brightdata_tools._post_with_retry", return_value=(200, "content")) as mock_http:
                        scrape_url(url=url, context=ctx)  # "scrape:<url>" is NOT cached yet
                        assert mock_http.call_count == 1
