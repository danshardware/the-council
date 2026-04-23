"""Tests for the Concierge agent YAML definitions.

Structural tests: validate YAML files load correctly and contain all required fields.
These do not make LLM calls.

Run all:
    uv run pytest tests/test_concierge_routing.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

_AGENTS_DIR = Path(__file__).parent.parent / "agents"
_FLOWS_DIR = Path(__file__).parent.parent / "flows"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _all_block_defs(data: dict) -> dict[str, dict]:
    return data.get("blocks", {})


def _all_system_prompts(data: dict) -> list[str]:
    return [
        b.get("system_prompt", "")
        for b in _all_block_defs(data).values()
        if b.get("system_prompt")
    ]


def _all_tools_lists(data: dict) -> list[list[str]]:
    return [
        b.get("tools", [])
        for b in _all_block_defs(data).values()
        if b.get("tools")
    ]


def _all_tools_flat(data: dict) -> list[str]:
    result = []
    for lst in _all_tools_lists(data):
        result.extend(lst)
    return result


# ---------------------------------------------------------------------------
# Concierge — agent YAML
# ---------------------------------------------------------------------------

class TestConciergeYaml:
    @pytest.fixture(autouse=True)
    def load(self):
        path = _AGENTS_DIR / "concierge.yaml"
        assert path.exists(), "agents/concierge.yaml not found"
        self.data = _load_yaml(path)

    def test_id_matches_filename(self):
        assert self.data["id"] == "concierge"

    def test_required_top_level_fields(self):
        for field in ("id", "name", "description", "flows", "model_defaults", "permissions"):
            assert field in self.data, f"Missing field: {field}"

    def test_main_and_onboarding_flows_declared(self):
        flows = self.data["flows"]
        assert "main" in flows, "concierge must declare a 'main' flow"
        assert "onboarding" in flows, "concierge must declare an 'onboarding' flow"

    def test_uses_opus_model(self):
        model = self.data["model_defaults"]["model_id"]
        assert "opus" in model, f"Expected opus model for concierge, got {model!r}"

    def test_write_paths_inside_data(self):
        write_paths = self.data.get("permissions", {}).get("write_paths", [])
        for p in write_paths:
            assert p.startswith("data/"), f"write_path outside data/: {p!r}"

    def test_write_paths_limited_to_shared_knowledge(self):
        write_paths = self.data.get("permissions", {}).get("write_paths", [])
        # Concierge is read-only except for onboarding: only shared_knowledge/
        for p in write_paths:
            assert "shared_knowledge" in p, (
                f"Concierge write_path should be shared_knowledge only, got {p!r}"
            )

    def test_read_paths_include_key_dirs(self):
        read_paths = self.data.get("permissions", {}).get("read_paths", [])
        for required in ("agents", "flows", "config", "docs"):
            assert any(required in p for p in read_paths), (
                f"read_paths should include '{required}/'"
            )

    def test_no_dangerous_allowed_commands(self):
        dangerous = {"curl", "wget", "python", "bash", "sh", "rm", "dd"}
        allowed = set(self.data.get("permissions", {}).get("allowed_commands", []))
        overlap = allowed & dangerous
        assert not overlap, f"Dangerous commands in allowed_commands: {overlap}"


# ---------------------------------------------------------------------------
# Concierge — main loop flow
# ---------------------------------------------------------------------------

class TestConciergeLoopYaml:
    @pytest.fixture(autouse=True)
    def load(self):
        agent = _load_yaml(_AGENTS_DIR / "concierge.yaml")
        flow_name = agent["flows"]["main"]
        path = _FLOWS_DIR / f"{flow_name}.yaml"
        assert path.exists(), f"flows/{flow_name}.yaml not found"
        self.data = _load_yaml(path)

    def test_required_top_level_fields(self):
        for field in ("id", "start", "blocks"):
            assert field in self.data, f"Missing field: {field}"

    def test_start_block_exists(self):
        start = self.data["start"]
        assert start in self.data["blocks"], (
            f"start block '{start}' not found in blocks"
        )

    def test_all_transitions_point_to_existing_blocks_or_end(self):
        blocks = self.data["blocks"]
        for block_id, block_def in blocks.items():
            transitions = block_def.get("transitions", {})
            for action, target in transitions.items():
                assert target == "END" or target in blocks, (
                    f"Block '{block_id}' transition '{action}' → '{target}' not found"
                )

    def test_has_llm_blocks(self):
        blocks = self.data["blocks"]
        llm_blocks = [b for b, d in blocks.items() if d.get("type") == "llm"]
        assert llm_blocks, "concierge_loop should have at least one llm block"

    def test_has_guardrail_for_external_messages(self):
        blocks = self.data["blocks"]
        guardrail_blocks = [b for b, d in blocks.items() if d.get("type") == "guardrail"]
        assert guardrail_blocks, "concierge_loop should have an external_message_safety guardrail"

    def test_guardrail_uses_external_message_safety(self):
        blocks = self.data["blocks"]
        guardrail_prompts = [
            d.get("system_prompt", "")
            for d in blocks.values()
            if d.get("type") == "guardrail"
        ]
        assert any("external_message_safety" in p for p in guardrail_prompts), (
            "A guardrail block should reference config.guardrails.external_message_safety"
        )

    def test_has_human_input_block(self):
        blocks = self.data["blocks"]
        human_blocks = [b for b, d in blocks.items() if d.get("type") == "human_input"]
        assert human_blocks, "concierge_loop should have at least one human_input block"

    def test_agent_creator_routing_mentioned(self):
        """Routing rules must explicitly mention spawn_agent for agent_creator."""
        prompts = _all_system_prompts(self.data)
        combined = "\n".join(prompts)
        assert "agent_creator" in combined, (
            "concierge_loop system prompts must mention routing to agent_creator"
        )

    def test_ops_routing_mentioned(self):
        prompts = _all_system_prompts(self.data)
        combined = "\n".join(prompts)
        assert "ops" in combined, (
            "concierge_loop system prompts must mention routing to ops agent"
        )

    def test_end_reachable(self):
        blocks = self.data["blocks"]
        end_blocks = [
            b for b, d in blocks.items()
            if "END" in d.get("transitions", {}).values()
        ]
        assert end_blocks, "At least one block should transition to END"


# ---------------------------------------------------------------------------
# Concierge — onboarding flow
# ---------------------------------------------------------------------------

class TestConciergeOnboardingYaml:
    @pytest.fixture(autouse=True)
    def load(self):
        agent = _load_yaml(_AGENTS_DIR / "concierge.yaml")
        flow_name = agent["flows"]["onboarding"]
        path = _FLOWS_DIR / f"{flow_name}.yaml"
        assert path.exists(), f"flows/{flow_name}.yaml not found"
        self.data = _load_yaml(path)

    def test_required_top_level_fields(self):
        for field in ("id", "start", "blocks"):
            assert field in self.data, f"Missing field: {field}"

    def test_start_block_exists(self):
        start = self.data["start"]
        assert start in self.data["blocks"], (
            f"start block '{start}' not found in blocks"
        )

    def test_all_transitions_point_to_existing_blocks_or_end(self):
        blocks = self.data["blocks"]
        for block_id, block_def in blocks.items():
            transitions = block_def.get("transitions", {})
            for action, target in transitions.items():
                assert target == "END" or target in blocks, (
                    f"Block '{block_id}' transition '{action}' → '{target}' not found"
                )

    def test_checks_for_mission_file(self):
        """Onboarding must check if mission.md already exists before writing."""
        prompts = _all_system_prompts(self.data)
        combined = "\n".join(prompts)
        assert "mission.md" in combined, (
            "Onboarding flow must reference mission.md to check if onboarding was already done"
        )

    def test_writes_to_shared_knowledge(self):
        """Onboarding must use write_file to persist mission info."""
        prompts = _all_system_prompts(self.data)
        combined = "\n".join(prompts)
        assert "shared_knowledge" in combined, (
            "Onboarding flow must write to data/shared_knowledge/company/"
        )

    def test_has_human_input_block(self):
        blocks = self.data["blocks"]
        human_blocks = [b for b, d in blocks.items() if d.get("type") == "human_input"]
        assert human_blocks, "Onboarding flow should gate steps with human_input blocks"

    def test_end_reachable(self):
        blocks = self.data["blocks"]
        end_blocks = [
            b for b, d in blocks.items()
            if "END" in d.get("transitions", {}).values()
        ]
        assert end_blocks, "Onboarding flow must be able to reach END"

    def test_has_llm_blocks(self):
        blocks = self.data["blocks"]
        llm_blocks = [b for b, d in blocks.items() if d.get("type") == "llm"]
        assert llm_blocks, "Onboarding flow should have at least one llm block"
