"""
Render and print the composed system prompt for an agent's LLM block,
exactly as LLMBlock.exec() would build it — without making any Bedrock calls.

Usage:
    uv run tests/check_system_prompts.py
    uv run tests/check_system_prompts.py --agent ceo --block think
    uv run tests/check_system_prompts.py --agent researcher --block think
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Project root on path
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from engine.flow_loader import load_flow
from tools import ToolContext, get_tool

console = Console()


PREVIEW_SESSION_ID = "preview"


def build_system_prompt(
    block_id: str,
    block_config: dict,
    agent_config: dict,
    context_injection: str = "",
    session_id: str = PREVIEW_SESSION_ID,
) -> str:
    """Replicate the system-prompt assembly in LLMBlock.exec without calling Bedrock."""
    system_prompt: str = block_config["system_prompt"]

    # 1. Prepend context_injection (shared_knowledge files)
    if context_injection:
        system_prompt = context_injection.rstrip() + "\n\n" + system_prompt

    # 2. Inject workspace paths — mirrors runner.py (session-scoped) + block.py formatting
    base_paths: list[str] = agent_config.get("permissions", {}).get("workspace_paths", [])
    # runner.py appends session_id to each base path
    allowed_paths = [str(Path(p.rstrip("/")) / session_id) + "/" for p in base_paths]
    if allowed_paths:
        paths_str = ", ".join(f"`{p}`" for p in allowed_paths)
        session_path = paths_str  # already session-scoped; matches block.py behaviour
        system_prompt = (
            system_prompt.rstrip()
            + f"\n\nYou can access files in: {paths_str}"
            + f"\nYour session working directory is: {session_path}\n"
        )

    # 3. Append ## Available Tools
    tool_names: list[str] = block_config.get("tools", [])
    if tool_names:
        ctx = ToolContext(
            agent_id=agent_config["id"],
            session_id=session_id,
            allowed_paths=allowed_paths,
            allowed_commands=agent_config.get("permissions", {}).get("allowed_commands", []),
        )
        lines = ["\n## Available Tools"]
        for name in tool_names:
            bt = get_tool(name, ctx)
            if bt is None:
                lines.append(f"- **{name}** (NOT FOUND IN REGISTRY)")
                continue
            spec = bt.tool_spec
            props = spec.get("inputSchema", {}).get("json", {}).get("properties", {})
            params = ", ".join(
                f"{k}: {v.get('type', 'string')}" for k, v in props.items()
            )
            lines.append(f"- **{spec['name']}**({params}) — {spec.get('description', '')}")
        system_prompt = system_prompt.rstrip() + "\n" + "\n".join(lines) + "\n"

    return system_prompt


def check_agent(agent_id: str, block_id: str | None) -> None:
    agents_dir = Path("agents")
    flows_dir = Path("flows")

    agent_path = agents_dir / f"{agent_id}.yaml"
    if not agent_path.exists():
        console.print(f"[red]Agent file not found: {agent_path}[/red]")
        sys.exit(1)

    with agent_path.open(encoding="utf-8") as f:
        agent_config: dict = yaml.safe_load(f)

    flow_alias = agent_config["flows"].get("main")
    flow_path = flows_dir / f"{flow_alias}.yaml"
    _, flow_config, _ = load_flow(flow_path)

    blocks: dict = flow_config.get("blocks", {})
    targets = [block_id] if block_id else list(blocks.keys())

    for bid in targets:
        if bid not in blocks:
            console.print(f"[yellow]Block '{bid}' not found in flow '{flow_alias}'[/yellow]")
            continue
        cfg = blocks[bid]
        if cfg.get("type") != "llm":
            console.print(f"[dim]Skipping block '{bid}' (type={cfg.get('type')})[/dim]")
            continue

        prompt = build_system_prompt(
            block_id=bid,
            block_config=cfg,
            agent_config=agent_config,
            context_injection="",  # context_files would be loaded at runtime; omit here
        )

        console.print(Rule(f"[bold cyan]{agent_id}[/bold cyan] › [yellow]{bid}[/yellow]"))
        console.print(Panel(prompt, expand=True, border_style="dim"))
        char_count = len(prompt)
        tool_section_start = prompt.find("## Available Tools")
        manual_above = prompt[:tool_section_start].count("\n") if tool_section_start != -1 else "N/A"
        console.print(
            f"  [dim]Total chars: {char_count} | "
            f"Auto-injected tools: {len(cfg.get('tools', []))} | "
            f"Tool section at char {tool_section_start}[/dim]\n"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview composed LLM system prompts")
    parser.add_argument("--agent", default=None, help="Agent ID (default: all agents)")
    parser.add_argument("--block", default=None, help="Block ID to inspect (default: all llm blocks)")
    args = parser.parse_args()

    agents_dir = Path("agents")
    if args.agent:
        agent_ids = [args.agent]
    else:
        agent_ids = [p.stem for p in sorted(agents_dir.glob("*.yaml"))]

    for agent_id in agent_ids:
        check_agent(agent_id, args.block)


if __name__ == "__main__":
    main()
