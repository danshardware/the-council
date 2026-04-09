"""Browser automation tools using browser-use library with AWS Bedrock."""

from __future__ import annotations

import asyncio
import logging
import os

from tools import ToolContext, tool

logger = logging.getLogger(__name__)

# Haiku is fast and cheap — sufficient for navigation / extraction tasks.
# Override via BROWSER_MODEL env var if a more capable model is needed.
_DEFAULT_MODEL = 'us.anthropic.claude-haiku-4-5-20251001-v1:0'


@tool
def browse_web(task: str, context: ToolContext) -> str:
    """
    Automate a web browsing task using browser-use. Allows interaction with websites: clicking, filling forms, navigating multi-step flows.

    Args:
        task: Natural language task description (e.g., "Find the pricing page on example.com")
        context: ToolContext with agent/session info

    Returns:
        Extracted text content from the browser session, or an [ERROR] message.
    """
    try:
        from browser_use import Agent
        from browser_use.browser.session import BrowserSession
        from browser_use.llm.aws import ChatAnthropicBedrock
    except ImportError as exc:
        return f"[ERROR] browser-use not installed: {exc}. Run: uv add browser-use"

    try:
        # ChatAnthropicBedrock uses the Anthropic SDK's AsyncAnthropicBedrock client,
        # which picks up credentials from the standard AWS credential chain
        # (env vars, ~/.aws/credentials, IAM role, etc.) when no explicit keys are given.
        # Critically, it passes the FULL Pydantic JSON schema to Anthropic's native
        # tool_use API with tool_choice forced, guaranteeing structured action objects.
        llm = ChatAnthropicBedrock(
            model=os.environ.get('BROWSER_MODEL', _DEFAULT_MODEL),
            aws_region=os.environ.get('AWS_REGION', 'us-west-2'),
            max_tokens=4096,
        )

        # Sandbox downloads/temp files into the agent's session workspace so
        # nothing lands in the project root.  Fall back to '.' if no paths set.
        workspace_path = (
            context.allowed_paths[0].rstrip('/') if context.allowed_paths else '.'
        )

        browser_session = BrowserSession(
            headless=True,
            downloads_path=workspace_path,
        )

        agent = Agent(
            task=(
                task
                + "\n\n## Important instructions\n"
                "- If you encounter a CAPTCHA, bot-detection page, login wall, or any block "
                "that prevents access, do NOT spend time trying to solve or bypass it. "
                "Immediately mark the site as inaccessible and include its URL in your final "
                "result prefixed with 'BLOCKED: ' so the caller can use scrape_url instead.\n"
                "- Do NOT use search engines (Google, Bing, DuckDuckGo) — they will show "
                "CAPTCHAs. The caller will use the search_web tool for search engine queries.\n"
                "- Focus only on interactive tasks: clicking, filling forms, navigating "
                "multi-step flows on the specific site given."
            ),
            llm=llm,
            browser=browser_session,
            flash_mode=True,
        )

        result = asyncio.run(agent.run())

        # AgentHistoryList.final_result() returns the extracted_content string
        # from the last done action, or None if the agent didn't complete.
        content = result.final_result() if hasattr(result, 'final_result') else str(result)
        content = content or "[No content extracted from browser session]"

        # Append token usage so the tool_use log entry carries billing context.
        if hasattr(result, 'usage') and result.usage is not None:
            u = result.usage
            content += (
                f"\n\n[browser_tokens: input={u.total_prompt_tokens}"
                f" output={u.total_completion_tokens}"
                f" total={u.total_tokens}]"
            )

        return content

    except asyncio.TimeoutError:
        return "[ERROR] Browser task timed out"
    except Exception as exc:
        logger.exception("browse_web error for agent %s", context.agent_id)
        return f"[ERROR] Browser task failed: {type(exc).__name__}: {exc}"

