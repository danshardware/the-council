"""Test tool discovery tools — list_tools and search_tools."""

import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools import ToolContext, _REGISTRY
from tools.registry_tools import list_tools, search_tools


def make_test_context():
    """Create a minimal ToolContext for testing."""
    return ToolContext(
        agent_id="test",
        session_id="test_session",
        allowed_paths=["workspace/test/"],
    )


def test_list_tools_returns_all_registered():
    """Test that list_tools returns all registered tools."""
    # Ensure all tool modules are imported (they should be on initial import)
    result = list_tools(make_test_context())
    
    # Should have all tools in registry
    assert len(result.splitlines()) == len(_REGISTRY), \
        f"Expected {len(_REGISTRY)} tools, got {len(result.splitlines())}"


def test_list_tools_format():
    """Test that list_tools returns correct format: 'name: description'."""
    result = list_tools(make_test_context())
    
    for line in result.splitlines():
        assert ": " in line, f"Bad format (missing ': '): {line!r}"
    
    # Verify it can be parsed correctly
    for line in result.splitlines():
        name, desc = line.split(": ", 1)
        assert name in _REGISTRY, f"Tool name {name!r} not in registry"


def test_search_tools_file_query():
    """Test search_tools returns file-related tools for 'file' query."""
    result = search_tools("file reading and writing", make_test_context())
    
    assert "read_file" in result, "read_file should be in results"
    assert "write_file" in result, "write_file should be in results"


def test_search_tools_memory_query():
    """Test search_tools returns memory-related tools for memory query."""
    result = search_tools("memory storage", make_test_context())
    
    assert "store_memory" in result or "search_memory" in result, \
        "memory tools should be in results"


def test_search_tools_schedule_query():
    """Test search_tools returns schedule tools for schedules query."""
    result = search_tools("schedules", make_test_context())
    
    assert any(tool in result for tool in ["schedule_agent", "list_schedules", "cancel_schedule"]), \
        "scheduling tools should be in results"


def test_search_tools_networking_query():
    """Test search_tools returns run_command for networking query."""
    result = search_tools("networking", make_test_context())
    
    assert "run_command" in result, "run_command should be in networking results"


def test_search_tools_no_match():
    """Test search_tools returns empty message when no tools match."""
    result = search_tools("quantum entanglement xyz123", make_test_context())
    
    # Should have empty or no-matching-message result
    assert result.lower() == "(no matching tools)" or result == "", \
        f"Expected no matching tools message, got: {result!r}"


def test_search_tools_returns_correct_format():
    """Test that search_tools returns correct format: 'name: description'."""
    result = search_tools("file", make_test_context())
    
    for line in result.splitlines():
        assert ": " in line, f"Bad format (missing ': '): {line!r}"


def test_registered_tools_exist():
    """Verify both list_tools and search_tools are registered."""
    assert "list_tools" in _REGISTRY, "list_tools should be in registry"
    assert "search_tools" in _REGISTRY, "search_tools should be in registry"


if __name__ == "__main__":
    # Run all tests
    test_functions = [
        test_list_tools_returns_all_registered,
        test_list_tools_format,
        test_search_tools_file_query,
        test_search_tools_memory_query,
        test_search_tools_schedule_query,
        test_search_tools_networking_query,
        test_search_tools_no_match,
        test_search_tools_returns_correct_format,
        test_registered_tools_exist,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        try:
            test_func()
            print(f"✅ {test_func.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"❌ {test_func.__name__}: {e}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    
    if failed > 0:
        sys.exit(1)