"""Tests for per-agent guardrail override functionality (A5)."""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from engine.runner import AgentRunner, _resolve_guardrail_prompt


class MockFlow:
    """Mock flow that records if _run was called."""
    
    def __init__(self):
        self._run_called = False
        self._run_shared = None
    
    def _run(self, shared: dict):
        self._run_called = True
        self._run_shared = shared


class TestResolveGuardrailPrompt:
    """Unit tests for the _resolve_guardrail_prompt function."""
    
    def test_resolve_guardrail_prompt_priority(self):
        """Unit test the resolution function - agent override takes priority."""
        agent_cfg = {"guardrails": {"input": "my custom prompt"}}
        defaults = {"input_safety": "system default"}
        result = _resolve_guardrail_prompt(agent_cfg, "input", defaults)
        assert result == "my custom prompt"
    
    def test_resolve_guardrail_prompt_fallback(self):
        """Unit test the resolution function - falls back to system default."""
        agent_cfg = {}
        defaults = {"input_safety": "system default"}
        result = _resolve_guardrail_prompt(agent_cfg, "input", defaults)
        assert result == "system default"
    
    def test_resolve_output_guardrail_prompt_priority(self):
        """Output guardrail: agent override takes priority."""
        agent_cfg = {"guardrails": {"output": "my custom output guardrail"}}
        defaults = {"output_safety": "system output default"}
        result = _resolve_guardrail_prompt(agent_cfg, "output", defaults)
        assert result == "my custom output guardrail"
    
    def test_resolve_output_guardrail_prompt_fallback(self):
        """Output guardrail: falls back to system default when not set."""
        agent_cfg = {}
        defaults = {"output_safety": "system output default"}
        result = _resolve_guardrail_prompt(agent_cfg, "output", defaults)
        assert result == "system output default"
    
    def test_empty_agent_override_falls_back_to_default(self):
        """Empty string in agent config falls back to system default."""
        agent_cfg = {"guardrails": {"input": ""}}
        defaults = {"input_safety": "system default"}
        result = _resolve_guardrail_prompt(agent_cfg, "input", defaults)
        assert result == "system default"
    
    def test_none_agent_override_falls_back_to_default(self):
        """None value in agent config falls back to system default."""
        agent_cfg = {"guardrails": {"input": None}}
        defaults = {"input_safety": "system default"}
        result = _resolve_guardrail_prompt(agent_cfg, "input", defaults)
        assert result == "system default"
    
    def test_no_agent_guardrails_key_falls_back_to_default(self):
        """Missing guardrails key in agent config falls back to system default."""
        agent_cfg = {}
        defaults = {"input_safety": "system default"}
        result = _resolve_guardrail_prompt(agent_cfg, "input", defaults)
        assert result == "system default"
    
    def test_empty_system_defaults_returns_empty(self):
        """Empty system defaults and no agent override returns empty string."""
        agent_cfg = {}
        defaults = {}
        result = _resolve_guardrail_prompt(agent_cfg, "input", defaults)
        assert result == ""
    
    def test_whitespace_stripping(self):
        """Whitespace-only agent override should be treated as empty and fall back."""
        agent_cfg = {"guardrails": {"input": "   "}}
        defaults = {"input_safety": "system default"}
        result = _resolve_guardrail_prompt(agent_cfg, "input", defaults)
        assert result == "system default"


class TestAgentGuardrailOverrideIntegration:
    """Integration tests for per-agent guardrail override in AgentRunner."""
    
    def test_agent_override_replaces_default_input_prompt(self):
        """If agent YAML has guardrails.input, that prompt is used, not system default."""
        mock_flow = MockFlow()
        custom_input_guardrail = "You are a custom input guardrail for agent X"

        with patch('engine.runner.load_flow') as mock_load:
            mock_load.return_value = (mock_flow, {}, {})
            
            with patch('engine.llm.call_llm') as mock_call:
                # Mock the input guardrail to approve
                mock_call.return_value = ({"verdict": "approved"}, 100, 50)
                
                runner = AgentRunner(agent_id="test_agent")
                
                from engine import template
                original_load_config_dir = template._load_config_dir
                
                try:
                    # System default is different from agent override
                    template._load_config_dir = MagicMock(return_value={
                        "guardrails": {
                            "input_safety": "You are the system default input guardrail...",
                            "output_safety": "You are the system default output guardrail..."
                        }
                    })
                    
                    # Agent config has custom input guardrail
                    with patch.object(runner, '_load_agent', return_value={
                        "flows": {"main": "main"},
                        "max_iterations": 50,
                        "guardrails": {
                            "input": custom_input_guardrail,
                            "output": "You are a custom output guardrail..."
                        }
                    }):
                        shared = runner.run(prompt="Hello")
                        
                        # Verify the input guardrail prompt was resolved correctly
                        assert shared.get("_input_guardrail_prompt") == custom_input_guardrail
                        assert shared.get("_input_guardrail_prompt") != "You are the system default input guardrail..."
                        
                        # Verify the call_llm was invoked with correct system prompt
                        call_args = mock_call.call_args_list[0]
                        system_prompt_used = call_args[1].get('system_prompt') or call_args[0][1]
                        assert system_prompt_used == custom_input_guardrail
                        
                finally:
                    template._load_config_dir = original_load_config_dir
    
    def test_agent_override_replaces_default_output_prompt(self):
        """If agent YAML has guardrails.output, that prompt is used, not system default."""
        mock_flow = MockFlow()
        custom_output_guardrail = "You are a custom output guardrail for agent Y"

        with patch('engine.runner.load_flow') as mock_load:
            mock_load.return_value = (mock_flow, {}, {})
            
            runner = AgentRunner(agent_id="test_agent")
            
            from engine import template
            original_load_config_dir = template._load_config_dir
            
            try:
                # System default is different from agent override
                template._load_config_dir = MagicMock(return_value={
                    "guardrails": {
                        "input_safety": "You are the system default input guardrail...",
                        "output_safety": "You are the system default output guardrail..."
                    }
                })
                
                # Agent config has custom output guardrail
                with patch.object(runner, '_load_agent', return_value={
                    "flows": {"main": "main"},
                    "max_iterations": 50,
                    "guardrails": {
                        "input": "You are a custom input guardrail...",
                        "output": custom_output_guardrail
                    }
                }):
                    shared = runner.run(prompt="Hello")
                    
                    # Verify the output guardrail prompt was resolved correctly
                    assert shared.get("_output_guardrail_prompt") == custom_output_guardrail
                    assert shared.get("_output_guardrail_prompt") != "You are the system default output guardrail..."
                    
            finally:
                template._load_config_dir = original_load_config_dir
    
    def test_empty_override_falls_back_to_default_input(self):
        """If guardrails.input is empty/absent, system default is used."""
        mock_flow = MockFlow()
        system_input_default = "You are the system input safety guardrail..."

        with patch('engine.runner.load_flow') as mock_load:
            mock_load.return_value = (mock_flow, {}, {})
            
            with patch('engine.llm.call_llm') as mock_call:
                mock_call.return_value = ({"verdict": "approved"}, 100, 50)
                
                runner = AgentRunner(agent_id="test_agent")
                
                from engine import template
                original_load_config_dir = template._load_config_dir
                
                try:
                    template._load_config_dir = MagicMock(return_value={
                        "guardrails": {
                            "input_safety": system_input_default,
                            "output_safety": "You are the system default output guardrail..."
                        }
                    })
                    
                    # Agent config with empty input guardrail
                    with patch.object(runner, '_load_agent', return_value={
                        "flows": {"main": "main"},
                        "max_iterations": 50,
                        "guardrails": {
                            "input": "",  # Empty string - should fall back
                            "output": "Custom output guardrail"
                        }
                    }):
                        shared = runner.run(prompt="Hello")
                        
                        # Verify it falls back to system default
                        assert shared.get("_input_guardrail_prompt") == system_input_default
                        
                finally:
                    template._load_config_dir = original_load_config_dir
    
    def test_no_agent_guardrails_uses_system_defaults(self):
        """When agent has no guardrails config, system defaults are used."""
        mock_flow = MockFlow()
        system_input_default = "You are the system input guardrail"
        system_output_default = "You are the system output guardrail"

        with patch('engine.runner.load_flow') as mock_load:
            mock_load.return_value = (mock_flow, {}, {})
            
            runner = AgentRunner(agent_id="test_agent")
            
            from engine import template
            original_load_config_dir = template._load_config_dir
            
            try:
                template._load_config_dir = MagicMock(return_value={
                    "guardrails": {
                        "input_safety": system_input_default,
                        "output_safety": system_output_default
                    }
                })
                
                # Agent config with NO guardrails key at all
                with patch.object(runner, '_load_agent', return_value={
                    "flows": {"main": "main"},
                    "max_iterations": 50,
                    # No "guardrails" key
                }):
                    shared = runner.run(prompt="Hello")
                    
                    # Both prompts should use system defaults
                    assert shared.get("_input_guardrail_prompt") == system_input_default
                    assert shared.get("_output_guardrail_prompt") == system_output_default
                    
            finally:
                template._load_config_dir = original_load_config_dir
    
    def test_partial_guardrail_config_uses_defaults_for_missing(self):
        """When agent has only input guardrail, output should default to system."""
        mock_flow = MockFlow()
        system_output_default = "You are the system output guardrail"
        custom_input = "You are a custom input guardrail"

        with patch('engine.runner.load_flow') as mock_load:
            mock_load.return_value = (mock_flow, {}, {})
            
            with patch('engine.llm.call_llm') as mock_call:
                mock_call.return_value = ({"verdict": "approved"}, 100, 50)
                
                runner = AgentRunner(agent_id="test_agent")
                
                from engine import template
                original_load_config_dir = template._load_config_dir
                
                try:
                    template._load_config_dir = MagicMock(return_value={
                        "guardrails": {
                            "input_safety": "System input default",
                            "output_safety": system_output_default
                        }
                    })
                    
                    # Agent config has only input guardrail
                    with patch.object(runner, '_load_agent', return_value={
                        "flows": {"main": "main"},
                        "max_iterations": 50,
                        "guardrails": {
                            "input": custom_input,
                            # No "output" key
                        }
                    }):
                        shared = runner.run(prompt="Hello")
                        
                        # Input should use agent custom, output should use system default
                        assert shared.get("_input_guardrail_prompt") == custom_input
                        assert shared.get("_output_guardrail_prompt") == system_output_default
                        
                finally:
                    template._load_config_dir = original_load_config_dir