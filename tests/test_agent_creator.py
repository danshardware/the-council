"""Tests for the Agent Creator agent and concierge agent definitions.

Structural tests: validate YAML files load correctly and contain all required fields.
These do not make LLM calls.

Run all:
    uv run pytest tests/test_agent_creator.py -v
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


# ---------------------------------------------------------------------------
# Agent Creator — agent YAML
# ---------------------------------------------------------------------------

class TestAgentCreatorYaml:
    @pytest.fixture(autouse=True)
    def load(self):
        path = _AGENTS_DIR / "agent_creator.yaml"
        assert path.exists(), f"agents/agent_creator.yaml not found"
        self.data = _load_yaml(path)

    def test_id_matches_filename(self):
        assert self.data["id"] == "agent_creator"

    def test_required_top_level_fields(self):
        for field in ("id", "name", "description", "flows", "model_defaults", "permissions"):
            assert field in self.data, f"Missing field: {field}"

    def test_main_flow_declared(self):
        assert "main" in self.data["flows"]

    def test_uses_opus_model(self):
        model = self.data["model_defaults"]["model_id"]
        assert "opus" in model, f"Expected opus model for large-context agent, got {model!r}"

    def test_write_paths_inside_data(self):
        write_paths = self.data.get("permissions", {}).get("write_paths", [])
        for p in write_paths:
            assert p.startswith("data/"), f"write_path outside data/: {p!r}"

    def test_read_paths_include_docs_and_agents(self):
        read_paths = self.data.get("permissions", {}).get("read_paths", [])
        assert any("docs" in p for p in read_paths), "read_paths should include docs/"
        assert any("agents" in p for p in read_paths), "read_paths should include agents/"

    def test_context_files_declared(self):
        context_files = self.data.get("context_files", [])
        assert len(context_files) >= 1, "agent_creator should inject creation guide via context_files"
        globs = [cf.get("glob", "") for cf in context_files]
        assert any("how-to-create-agents" in g for g in globs), (
            "context_files should include how-to-create-agents.md"
        )

    def test_no_dangerous_allowed_commands(self):
        dangerous = {"curl", "wget", "python", "bash", "sh", "rm", "dd"}
        allowed = set(self.data.get("permissions", {}).get("allowed_commands", []))
        overlap = allowed & dangerous
        assert not overlap, f"Dangerous commands in allowed_commands: {overlap}"


# ---------------------------------------------------------------------------
# Agent Creator — flow YAML
# ---------------------------------------------------------------------------

class TestAgentCreatorFlowYaml:
    @pytest.fixture(autouse=True)
    def load(self, tmp_path):
        # The flow name comes from agents/agent_creator.yaml
        agent = _load_yaml(_AGENTS_DIR / "agent_creator.yaml")
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
        assert llm_blocks, "Flow should have at least one llm block"

    def test_has_guardrail_before_write(self):
        blocks = self.data["blocks"]
        guardrail_blocks = [b for b, d in blocks.items() if d.get("type") == "guardrail"]
        assert guardrail_blocks, "Flow should have at least one guardrail block (agent_definition_safety)"

    def test_guardrail_uses_agent_definition_safety(self):
        blocks = self.data["blocks"]
        guardrail_prompts = [
            d.get("system_prompt", "")
            for d in blocks.values()
            if d.get("type") == "guardrail"
        ]
        assert any("agent_definition_safety" in p for p in guardrail_prompts), (
            "No guardrail references config.guardrails.agent_definition_safety"
        )

    def test_testing_tools_available_in_some_block(self):
        blocks = self.data["blocks"]
        all_tools = []
        for block_def in blocks.values():
            all_tools.extend(block_def.get("tools", []))
        testing_tools = {"agent_test", "agent_test_modify", "read_session_log", "list_agent_sessions"}
        found = testing_tools & set(all_tools)
        assert found, f"None of the testing tools found in any block. Expected one of: {testing_tools}"

    def test_ask_human_block_exists(self):
        blocks = self.data["blocks"]
        human_blocks = [b for b, d in blocks.items() if d.get("type") == "human_input"]
        assert human_blocks, "Flow should have at least one human_input block for gather/review gates"

    def test_has_end_reachable(self):
        """At least one transition points to END."""
        blocks = self.data["blocks"]
        all_targets = []
        for block_def in blocks.values():
            all_targets.extend(block_def.get("transitions", {}).values())
        assert "END" in all_targets, "No block transitions to END — flow can never complete"
