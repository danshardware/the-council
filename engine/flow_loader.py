"""Flow loader — parses a flow YAML file into a runnable PocketFlow Flow."""

from __future__ import annotations

import sys
import os
from pathlib import Path

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pocketflow import Flow
from engine.block import make_block, BaseBlock


def load_flow(flow_path: str | Path) -> tuple[Flow, dict]:
    """
    Load a flow YAML and return (PocketFlow Flow, raw flow_config dict).

    The YAML must have:
        id:     str
        start:  block_id
        blocks:
            <block_id>:
                type: llm | guardrail | tool_call | checkpoint | human_input
                transitions:
                    <action>: <block_id> | END
                ... (block-type specific fields)

    Transitions mapped to "END" (or absent) cause the flow to terminate naturally.
    """
    path = Path(flow_path)
    with path.open() as fh:
        flow_config: dict = yaml.safe_load(fh)

    blocks_config: dict = flow_config.get("blocks", {})

    # Instantiate all blocks first so we can wire them in a second pass
    block_instances: dict[str, BaseBlock] = {}
    for block_id, block_cfg in blocks_config.items():
        block_instances[block_id] = make_block(block_id, block_cfg)

    # Wire transitions
    for block_id, block_cfg in blocks_config.items():
        node = block_instances[block_id]
        for action, target in block_cfg.get("transitions", {}).items():
            if target and target.upper() != "END":
                if target not in block_instances:
                    raise ValueError(
                        f"Flow '{flow_config.get('id')}': block '{block_id}' "
                        f"transition '{action}' points to unknown block '{target}'"
                    )
                node.next(block_instances[target], action)
            # "END" (or missing) → no successor registered → flow terminates

    start_id = flow_config.get("start")
    if start_id not in block_instances:
        raise ValueError(
            f"Flow '{flow_config.get('id')}': start block '{start_id}' not found"
        )

    flow = Flow(start=block_instances[start_id])
    return flow, flow_config
