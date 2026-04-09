"""Tests for browser automation guardrails using Nova Lite guardrail LLM."""

import sys
import os
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import yaml


class TestBrowserToolImport:
    """Test that browser_tools.py is properly registered."""

    def test_browse_web_tool_registered(self):
        """Verify that browse_web tool is in the registry."""
        from tools import list_tools
        tools = list_tools()
        assert "browse_web" in tools, f"browse_web tool not registered. Available: {tools}"

    def test_get_browse_web_tool(self):
        """Verify that browse_web tool can be retrieved and called."""
        from tools import get_tool, ToolContext
        
        ctx = ToolContext(agent_id="test", session_id="test_session")
        tool = get_tool("browse_web", ctx)
        
        assert tool is not None, "browse_web tool not found"
        assert tool.tool_spec["name"] == "browse_web"
        assert "task" in tool.tool_spec["inputSchema"]["json"]["properties"]


class TestGuardrailConfiguration:
    """Test guardrail config exists and is valid."""
    
    def test_browser_guardrails_yaml_exists(self):
        """Verify guardrail configuration file exists."""
        config_path = Path(__file__).parent.parent / "config" / "browser_guardrails.yaml"
        assert config_path.exists(), f"Guardrail config not found at {config_path}"
    
    def test_browser_guardrails_yaml_loads(self):
        """Verify guardrail YAML is valid."""
        config_path = Path(__file__).parent.parent / "config" / "browser_guardrails.yaml"
        with open(config_path, encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        assert config is not None, "Failed to load guardrail config"
        assert "browser_guardrails" in config, "Missing browser_guardrails key"
        guardrails = config["browser_guardrails"]
        
        # Check structure
        assert "pre_execution_prompt" in guardrails, "Missing pre_execution_prompt"
        assert "post_execution_prompt" in guardrails, "Missing post_execution_prompt"
        assert "blocked_patterns" in guardrails, "Missing blocked_patterns"
        assert "blocked_domains" in guardrails, "Missing blocked_domains"
    
    def test_blocklist_patterns_contain_known_keywords(self):
        """Verify blocklist has patterns for dangerous content."""
        config_path = Path(__file__).parent.parent / "config" / "browser_guardrails.yaml"
        with open(config_path, encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        patterns = config["browser_guardrails"]["blocked_patterns"]
        
        # Check for key categories in blocklist
        pattern_str = " ".join(patterns).lower()
        
        # Should have patterns for weapons
        assert any("gun" in p.lower() or "firearm" in p.lower() for p in patterns), \
            "Blocklist missing weapons-related patterns"
        
        # Should have patterns for gambling
        assert any("casino" in p.lower() or "gambling" in p.lower() for p in patterns), \
            "Blocklist missing gambling-related patterns"
        
        # Should have patterns for adult content
        assert any("porn" in p.lower() or "adult" in p.lower() for p in patterns), \
            "Blocklist missing adult-content patterns"
        
        # Should have patterns for drug-related content
        assert any("drug" in p.lower() or "cocaine" in p.lower() for p in patterns), \
            "Blocklist missing drug-related patterns"
        
        print(f"✅ Blocklist contains {len(patterns)} safety patterns")


class TestFlowIntegration:
    """Test that researcher flow was updated correctly."""
    
    def test_researcher_flow_has_browser_blocks(self):
        """Verify researcher flow has browser guardrail blocks."""
        flow_path = Path(__file__).parent.parent / "flows" / "researcher_loop.yaml"
        with open(flow_path) as f:
            flow = yaml.safe_load(f)
        
        blocks = flow.get("blocks", {})
        
        # Check for guardrail blocks
        assert "check_browse_intent" in blocks, \
            "Missing check_browse_intent block in researcher flow"
        assert "execute_browse" in blocks, \
            "Missing execute_browse block in researcher flow"
        assert "check_browse_result" in blocks, \
            "Missing check_browse_result block in researcher flow"
        
        # Verify block types
        assert blocks["check_browse_intent"]["type"] == "guardrail", \
            "check_browse_intent should be guardrail type"
        assert blocks["execute_browse"]["type"] == "tool_call", \
            "execute_browse should be tool_call type"
        assert blocks["check_browse_result"]["type"] == "guardrail", \
            "check_browse_result should be guardrail type"
        
        # Verify tool call references browse_web
        assert blocks["execute_browse"]["tool"] == "browse_web", \
            "execute_browse should call browse_web tool"
        
        print("✅ Researcher flow properly configured with browser automation blocks")
    
    def test_research_block_can_call_browse_web(self):
        """Verify research LLM block can invoke browse_web action."""
        flow_path = Path(__file__).parent.parent / "flows" / "researcher_loop.yaml"
        with open(flow_path) as f:
            flow = yaml.safe_load(f)
        
        research_block = flow["blocks"]["research"]
        transitions = research_block.get("transitions", {})
        
        # Should have browse_web transition
        assert "browse_web" in transitions, \
            "research block should have browse_web transition"
        assert transitions["browse_web"] == "check_browse_intent", \
            "browse_web transition should lead to check_browse_intent guardrail"
        
        print("✅ Research block properly configured to call browse_web")


class TestGuardrailPrompts:
    """Verify guardrail prompts are well-formed."""
    
    def test_pre_execution_guardrail_prompt_coverage(self):
        """Verify pre-exec guardrail prompt covers key safety categories."""
        config_path = Path(__file__).parent.parent / "config" / "browser_guardrails.yaml"
        with open(config_path, encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        prompt = config["browser_guardrails"]["pre_execution_prompt"].lower()
        
        # Should mention safety categories
        safety_keywords = [
            "malware", "phishing",
            "illegal", "weapons", "trafficking",
            "adult", "sexual",
            "gambling",
            "unauthorized", "authentication",
            "exfiltration", "data",
            "prompt injection"
        ]
        
        for keyword in safety_keywords:
            assert keyword in prompt, \
                f"Pre-execution prompt missing key safety concept: {keyword}"
        
        print(f"✅ Pre-execution guardrail prompt covers {len(safety_keywords)} key safety categories")
    
    def test_post_execution_guardrail_prompt_coverage(self):
        """Verify post-exec guardrail prompt checks for result validity."""
        config_path = Path(__file__).parent.parent / "config" / "browser_guardrails.yaml"
        with open(config_path, encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        prompt = config["browser_guardrails"]["post_execution_prompt"].lower()
        
        # Should check for common issues
        check_keywords = [
            "legitimate",
            "safe", "malware", "injection",
            "coherent", "gibberish",
            "unmanipulated"
        ]
        
        for keyword in check_keywords:
            assert keyword in prompt, \
                f"Post-execution prompt missing validation check: {keyword}"
        
        print(f"✅ Post-execution guardrail prompt validates result quality")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
