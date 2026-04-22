# Council new work

## Required Features

Each one of them should be discussed for an implementation plan before writing

- Sessions should show a wrap up with (even if keyboard interrupted):
    - Session ID
    - total tokens used
- New council walkthrough
    - introspection agent
- Python block
- Test guardrail rejection
    - Make a test that lists a bunch of thing unrelated to our business that absolutely should never be allowed (firearms, gambling, porn, etc.) and make sure they get flagged
    - make a guardrail called hater that just outright rejects everything to test flows
    - ensure human override works
- Allow writes to agent's long-term file repo as well as its workspace directory
- Per turn prompt injection and ensure it doesn't get re-inserted if it does not change. Compaction should clear this cache.

## Blocks

- iterate over a list
- logic
- math

## Nice to have

- Web page with status information and file editing.
- Allow defining flows in other files that can be referenced. These would differ from an agent in that they only define logic, but inherit everything else. An example would be something like the Ralph WIggum loop (Make a list and read through the list taking 1 task at a time)
- Local model execution in flows
- Parallel execution of tools and sub agents
- Archive historic data

## Additional tools

- Python: Execute python for doing math and analysys. Should run sandboxed, be limited in total size of code to run, and have a guardrail to prevent it from doing things that aren't appropriate to the task ( mostly concerned that they use this  to get around various other guardrails)
- Other integrations:
    - Hacker News — fully open API, technically savvy audience
    - Mastodon — open API, no approval
    - Bluesky — open AT Protocol, no gating
    - LinkedIn (with their API) — better for B2B brand monitoring
    - Google Alerts — free, no API needed, captures Reddit mentions too

## Utilites

- Utility to improve agents
    - User provides prompt and an evaluation criteria
    - Utility runs the agent while varying any of the following: Model, System Prompt, tools, and agent parameter.
    - Evaluation criteria can contain either yes/no questions, questions about how complete a list is, asked to evaluate the generated results based on subjective criteria. The cumulative results will assign points
    - Evaluation criteria will have negative criteria as well. Such as "Hit guardrail", "crashed", or "started talking about politics" which are more deeply penalized.
    - The agent running the tests can vary parameters to try and improve things except removing guardrails
    - All results are logged for human review with recommended results
    - Basically an LLM-guided task 
    - once a certain number of generation of tests have been run, a human a can evaluate the results and provide steering (change criteria in X way, adjust more like this)
    - should use a cheap model for most tasks except thinking between generation on how to improve
    - Keep context window in comparison of evaluation small by subbing out to another agent to perform the model evaluation. That model should be set with low entropy

The short answer: it was written this way to avoid needing a full running agent context (Bedrock credentials, a real session, shared state, etc.) just to preview a prompt. The test reimplements the assembly logic so it can run anywhere with no side effects.

The maintenance cost you're describing is the classic tradeoff of this approach — the two copies will drift whenever block.py changes, as you've just seen.

The clean fix (when you're ready) would be to extract the prompt-assembly logic out of LLMBlock.exec() into a standalone function in block.py:


def assemble_system_prompt(    base_prompt: str,    context_injection: str,    allowed_paths: list[str],    session_id: str,    tools: list,) -> str:    ...
Then LLMBlock.exec() calls it, and check_system_prompts.py calls it too — passing allowed_paths derived from the YAML + "preview" as the session_id. One source of truth, no drift.

## Compaction

=============================================================
FEATURE SPEC: Conversation.compact_messages
Branch: FEATURE/ConversationCompaction (next after current)
=============================================================

PURPOSE
-------
When a long session accumulates many turns, compact the conversation
history in-place to reduce token usage while preserving enough context
for the agent to continue effectively.

CALL SIGNATURE
--------------
conv.compact(
    focus: str | None = None,
    keep_last: int = 4,
    model_id: str | None = None,   # defaults to conv.model_id
)

PARAMETERS
----------
focus       - Optional instruction to the summarisation LLM about what
              to emphasise. E.g. "focus on open decisions and blockers".
              If None, uses a standard summarisation prompt.

keep_last   - Number of most-recent turns to leave untouched. These are
              retained verbatim at the end of the conversation so the
              agent has immediate context. Default 4.

model_id    - Model to use for the summarisation call. Defaults to the
              Conversation's own model_id. Caller can pass a cheaper/
              faster model (e.g. Haiku) since this is a summarisation
              task, not a reasoning task.

BEHAVIOUR
---------
1. Splits conv.conversation into:
     history  = conv.conversation[:-keep_last]   (to be compacted)
     tail     = conv.conversation[-keep_last:]    (kept verbatim)

2. Renders history turns into a plain text transcript (role + text
   content only; tool use/result pairs rendered as
   "[tool: <name>] input=... → result=...").

3. Calls the summarisation model with:
     system  = standard compact system prompt (or focus-augmented)
     user    = the rendered transcript

   Compact system prompt asks for:
   - What has been done and the outcome
   - Key facts or data gathered that are still needed
   - Decisions made and the reasoning
   - Current plan / next steps
   - Any open questions or blockers
   Instructs: "Be dense. Omit greetings, meta-commentary, iteration
   noise. Preserve all specific numbers, names, and artefact paths."

4. Wraps the summary as a single user-turn Message:
     role: "user"
     content: [{"text": "[SYSTEM] Summary of prior work:\n\n<summary>"}]

5. Replaces conv.conversation in-place:
     conv.conversation = [summary_message] + list(tail)

6. Returns a CompactResult(
       turns_before: int,
       turns_after: int,
       input_tokens: int,
       output_tokens: int,
   )

INTEGRATION POINTS
------------------
- The LLMBlock YAML config gains an optional compact_at parameter:
    compact_at: 20          # compact when len(conv.conversation) > 20
    compact_keep_last: 4    # optional override
    compact_focus: "..."    # optional override
    compact_model: "..."    # optional override

- LLMBlock.exec() checks len before calling call_model():
    if compact_at and len(conv.conversation) > compact_at:
        conv.compact(focus=..., keep_last=..., model_id=...)

- compact() is also callable manually from tools or flow blocks.

CHECKPOINT COMPATIBILITY
-------------------------
Because compact changes conv.conversation in-place, and the checkpoint
saves conv.conversation as serialized dicts, a compacted session resumes
with the compacted history — the summary turn is just another user turn.
No special handling needed.

TOOL CALL PAIR SAFETY
----------------------
Same boundary-alignment rule as context_window slicing: keep_last walks
back to the nearest clean turn boundary (no orphaned toolResult at start
of tail).

FUTURE EXTENSION
----------------
- Auto-compact triggered by token count rather than turn count.
- Tiered compaction: older segments get progressively more compressed.
- Cache checkpoint placed immediately after compact (KV cache reuse).
=============================================================

## Research

- [Natural-Language Agent Harnesses](https://arxiv.org/html/2603.25723v1)
- [How claude remembers your project](https://code.claude.com/docs/en/memory)
- [AgentSpec](https://github.com/haoyuwang99/AgentSpec/tree/master/src/rules/apollo) Agentic Guardrails
- [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
