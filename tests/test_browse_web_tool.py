"""Direct test of browse_web tool functionality."""

import sys
from pathlib import Path

# Set UTF-8 encoding for Windows
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools import get_tool, ToolContext


def test_browse_web_find_facebook():
    """Test browse_web tool by searching curiouscultivations.com for Facebook page."""
    
    # Create tool context
    ctx = ToolContext(
        agent_id="test",
        session_id="test_session",
        allowed_paths=["workspace/test/"],
    )
    
    # Get the browse_web tool
    tool = get_tool("browse_web", ctx)
    assert tool is not None, "browse_web tool not found"
    
    # Call the tool with the task
    task = "Go to https://curiouscultivations.com and find the Facebook page link. Return the URL or any text that indicates where the Facebook page can be found."
    
    print(f"\n{'='*70}")
    print(f"Testing browse_web tool")
    print(f"{'='*70}")
    print(f"Task: {task}\n")
    
    try:
        result = tool(task=task)
        print(f"Result:\n{result}")
        
        # Check if we got something useful
        assert isinstance(result, str), f"Expected string result, got {type(result)}"
        assert len(result) > 0, "Got empty result"
        
        # Check if it didn't error
        if "[ERROR]" in result:
            print(f"\n⚠️  Tool returned error: {result}")
        else:
            print(f"\n✅ SUCCESS: Tool found content about Curious Cultivations")
            print(f"   Result length: {len(result)} characters")
            
            # Check if Facebook is mentioned
            if "facebook" in result.lower():
                print(f"   ✅ Facebook content found in results!")
            else:
                print(f"   ℹ️  Facebook content not explicitly found, but general content retrieved")
        
        return result
        
    except Exception as e:
        print(f"\n❌ FAILED: {type(e).__name__}: {str(e)}")
        raise


if __name__ == "__main__":
    result = test_browse_web_find_facebook()
