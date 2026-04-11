"""Parameterised optimisation tests for the post-session fact-reconcile prompt.

Each case exercises the reconcile prompt directly with a known (new_fact,
existing_entries) pair and asserts the expected action.  Add new cases to
CASES to expand coverage when refining the prompt.

These tests make live Bedrock LLM calls, so they are slow/integration tests.

Run all:
    uv run pytest tests/test_post_session_reconcile.py -v

Run a single bucket:
    uv run pytest tests/test_post_session_reconcile.py -v -k skip
    uv run pytest tests/test_post_session_reconcile.py -v -k supersede
    uv run pytest tests/test_post_session_reconcile.py -v -k insert
    uv run pytest tests/test_post_session_reconcile.py -v -k flag
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.post_session_runner import _RECONCILE_SYSTEM, _MODEL_RECONCILE
from engine.llm import call_llm

# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------
# Format: (case_id, new_fact, existing_entries, expected_action)
# existing_entries: list[{"id": str, "content": str, "distance": float}]
# distance: cosine distance — 0 = identical, 2 = opposite; realistic range 0.05-0.40

CASES = [
    # ── SKIP: near-identical content re-stated from memory ───────────────────
    (
        "skip_identical_50_units",
        "The first production run is planned for 50 units.",
        [{"id": "ec62ac3c00", "content": "Curious Cultivations plans an initial production run of 50 units.", "distance": 0.05}],
        "skip",
    ),
    (
        "skip_identical_capital",
        "Curious Cultivations operates with under $10k capital.",
        [{"id": "fb2bed5400", "content": "Curious Cultivations has less than $10,000 in available capital.", "distance": 0.07}],
        "skip",
    ),
    (
        "skip_identical_phase",
        "The strategic plan includes four phases: Pre-Launch, Presale Campaign, Fulfillment & Feedback, and Scale & Expand.",
        [{"id": "deadbeef00", "content": "The strategic plan has four phases: Pre-Launch (Months 1-3), Presale Campaign (Month 3-4), Fulfillment & Feedback (Months 4-6), and Scale & Expand (Months 6-12).", "distance": 0.08}],
        "skip",
    ),

    # ── SUPERSEDE: more precise or more recent version of same claim ─────────
    (
        "supersede_email_precision",
        "Curious Cultivations has 132 email subscribers.",
        [{"id": "5152cffb00", "content": "Curious Cultivations has a few hundred email list members.", "distance": 0.26}],
        "supersede",
    ),
    (
        "supersede_status_dfm",
        "TechLight Remote is now in the DFM (Design for Manufacturing) phase.",
        [{"id": "aabbccdd00", "content": "TechLight Remote is in the validation phase.", "distance": 0.22}],
        "supersede",
    ),
    (
        "supersede_prototype_phase",
        "TechLight Remote is entering the physical prototype development phase.",
        [{"id": "2d2ac45a00", "content": "TechLight Remote has not yet reached physical prototype development.", "distance": 0.28}],
        "supersede",
    ),
    (
        "supersede_subscriber_count_update",
        "The YouTube channel has 2,400 subscribers.",
        [{"id": "ccddee0000", "content": "The YouTube channel has a few thousand subscribers.", "distance": 0.24}],
        "supersede",
    ),

    # ── INSERT: semantically related but genuinely distinct claims ────────────
    (
        "insert_different_topics_units_capital",
        "The first production run is planned for 50 units.",
        [{"id": "fb2bed5400", "content": "Curious Cultivations operates with under $10k capital.", "distance": 0.38}],
        "insert",
    ),
    (
        "insert_different_topics_capital_units",
        "Curious Cultivations operates with under $10k capital.",
        [{"id": "ec62ac3c00", "content": "The first production run is planned for 50 units.", "distance": 0.37}],
        "insert",
    ),
    (
        "insert_different_attributes_same_entity",
        "TechLight Remote uses PWM and 0-10V control protocols.",
        [{"id": "aabb112200", "content": "TechLight Remote is the lead product for Curious Cultivations.", "distance": 0.35}],
        "insert",
    ),
    (
        "insert_new_product_fact",
        "TechLight Mini uses the ESP32-S3 module.",
        [{"id": "aabb334400", "content": "TechLight Remote is entering the DFM phase.", "distance": 0.39}],
        "insert",
    ),

    # ── FLAG: direct, mutually exclusive contradictions ──────────────────────
    (
        "flag_founder_name",
        "Curious Cultivations was founded by Alice.",
        [{"id": "aabbccff00", "content": "Curious Cultivations was founded by Bob.", "distance": 0.12}],
        "flag",
    ),
    (
        "flag_revenue_contradiction",
        "Curious Cultivations is generating $50k/month in revenue.",
        [{"id": "aabb110000", "content": "Curious Cultivations generates minimal revenue (under $500/month).", "distance": 0.18}],
        "flag",
    ),
    (
        "flag_founding_year",
        "Curious Cultivations was founded in 2022.",
        [{"id": "aabb220000", "content": "Curious Cultivations was founded in 2019.", "distance": 0.10}],
        "flag",
    ),
]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _run_reconcile(new_fact: str, existing: list[dict]) -> str:
    """Call the reconcile prompt and return the action string."""
    existing_block = "\n\n".join(
        f"ID={h['id'][:8]} (similarity_dist={h['distance']:.3f}):\n{h['content']}"
        for h in existing
    )
    user_msg = f"NEW FACT:\n{new_fact}\n\nSIMILAR EXISTING ENTRIES:\n{existing_block}"
    parsed, _, _ = call_llm(
        model_id=_MODEL_RECONCILE,
        system_prompt=_RECONCILE_SYSTEM,
        messages=[{"role": "user", "content": user_msg}],
    )
    return parsed.get("action", "insert")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "case_id,new_fact,existing,expected",
    CASES,
    ids=[c[0] for c in CASES],
)
def test_reconcile_action(case_id: str, new_fact: str, existing: list[dict], expected: str) -> None:
    action = _run_reconcile(new_fact, existing)
    assert action == expected, (
        f"\nCase '{case_id}'\n"
        f"  new_fact : {new_fact!r}\n"
        f"  existing : {existing[0]['content']!r}\n"
        f"  expected : {expected!r}\n"
        f"  got      : {action!r}"
    )
