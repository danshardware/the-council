"""Post-session memory consolidation — summarization + fact extraction + conflict-aware reconciliation."""

from __future__ import annotations

import json
import re
import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.llm import call_llm
from memory.store import MemoryStore

_console = Console()

# Cosine distance: 0 = identical, 2 = opposite. Below this = check for conflict.
_CONFLICT_DISTANCE = 0.40

_MODEL_SUMMARISE = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
_MODEL_FACTS     = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
_MODEL_RECONCILE = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

_SUMMARISE_SYSTEM = """\
You are processing a completed agent session to create an institutional memory record.

Read the transcript and produce a comprehensive summary that captures:
- Key decisions made and the reasoning behind them
- Important facts, figures, or context shared
- Actions taken or committed to during the session
- Next steps agreed upon
- Significant new information about people, products, or strategy

Write a dense, information-rich narrative (3-5 paragraphs). The summary will be
stored permanently and retrieved in future sessions, so include all detail that
would be useful to an agent who wasn't present.

Respond ONLY with valid YAML:
```yaml
reasoning: "brief characterization of the session"
action: store
action_input:
  summary: |
    Full multi-paragraph summary text here...
  topic: "compact_snake_case_topic_tag"
```"""

_EXTRACT_FACTS_SYSTEM = """\
Extract all discrete atomic facts from this conversation transcript.

A GOOD fact is:
- Specific and verifiable ("TechLight Remote costs $30 to manufacture")
- About the business, people, products, financials, strategy, or decisions
- Stated as a single complete true sentence
- Cannot be derived from simple math, common sense, or general world knowledge (e.g. "the sky is blue")

EXCLUDE:
- Questions without answers
- Speculation or hypotheticals
- Greetings or procedural comments
- Items that are clearly temporal ("we will do X next week")
- Opinions or subjective statements ("the marketing team is great", "X looks really good")
- Math calculations

Extract as many distinct facts as are clearly supported by the conversation.

Respond ONLY with valid YAML:
```yaml
reasoning: "how many facts found and why"
action: facts_ready
action_input:
  facts:
    - "Fact one stated as a complete sentence."
    - "Fact two."
```"""

_RECONCILE_SYSTEM = """\
You are reconciling a new fact against existing memory entries to prevent
duplication and flag contradictions.

Given a NEW FACT and a list of SIMILAR EXISTING ENTRIES, choose ONE action:

- "skip"      — the new fact is essentially IDENTICAL in substance to an existing
                entry; it adds no new information and would only create a duplicate.
                Use this when the new and existing fact say the same thing, even if
                worded slightly differently.

- "supersede" — the new fact is a more accurate, more specific, or more recent version
                of EXACTLY the same claim as an existing entry. The existing entry
                should be replaced because it is now outdated or less precise.
                Example: existing="a few hundred email subscribers",
                         new="132 email subscribers" → supersede (more precise value)
                Example: existing="product is in validation phase",
                         new="product is entering DFM phase" → supersede (status update)

- "insert"    — the new fact contains genuinely new information not covered by any
                existing entry. Use this when the new fact and existing entries address
                DIFFERENT aspects of the same topic — both facts can be true at the
                same time.
                Example: new="first run is 50 units", existing="company has <$10k capital"
                → insert (unrelated claims about the same company)

- "flag"      — the new fact DIRECTLY CONTRADICTS an existing entry and BOTH CANNOT
                be simultaneously true. Reserve this for clear, unambiguous conflicts
                (e.g. two different people named as CEO, contradictory founding dates).

Rules of thumb:
1. When a precise number/value replaces a vague estimate of the SAME metric → supersede.
2. When the new and existing facts are about DIFFERENT attributes of the same entity → insert.
3. Only flag when the values are mutually exclusive and the conflict is unambiguous.
4. When unsure between flag and supersede → supersede.
5. When unsure between supersede and insert → insert.
6. When unsure between insert and skip → skip (avoid duplicates).

Respond ONLY with valid YAML:
```yaml
reasoning: "brief explanation"
action: insert  # insert | supersede | skip | flag
action_input:
  supersede_id: ""   # first 8 chars of entry ID to replace, only if action=supersede
  flag_reason: ""    # description of the contradiction, only if action=flag
```"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_yaml_block(text: str) -> str:
    fenced = re.search(r"```(?:yaml)?\s*\n(.*?)```", text, re.DOTALL)
    return fenced.group(1).strip() if fenced else text.strip()


def _parse_transcript(events: list[dict]) -> str:
    """Build a human-readable transcript from parsed log events."""
    if not events:
        return ""
    agent_id = events[0].get("agent_id", "AGENT").upper()
    start_prompt = events[0].get("prompt", "")
    turns: list[str] = []

    if start_prompt:
        turns.append(f"[USER] {start_prompt}")

    for ev in events:
        event = ev.get("event", "")

        if event == "llm_call":
            action = ev.get("action", "")
            raw = ev.get("raw_response", "")
            if not raw:
                continue
            try:
                parsed = yaml.safe_load(_extract_yaml_block(raw))
                if isinstance(parsed, dict):
                    ai = parsed.get("action_input") or {}
                    if action == "ask_human":
                        msg = ai.get("message", "") if isinstance(ai, dict) else str(ai)
                        if msg:
                            turns.append(f"[{agent_id}] {str(msg).strip()[:1200]}")
                    elif action == "done":
                        summary = (ai.get("summary", "") if isinstance(ai, dict) else "") \
                                  or parsed.get("reasoning", "")
                        if summary:
                            turns.append(f"[{agent_id}:CLOSING] {str(summary).strip()[:600]}")
            except Exception:
                pass

        elif event == "human_reply":
            text = ev.get("text", "")
            if text:
                turns.append(f"[USER] {text}")

        elif event == "tool_use":
            tool = ev.get("tool", "")
            inp = str(ev.get("input", ""))[:150]
            result = str(ev.get("result", ""))[:200]
            turns.append(f"[TOOL:{tool}] in={inp} → {result}")

    return "\n\n".join(turns)


def _load_events(log_path: Path) -> list[dict]:
    events: list[dict] = []
    with log_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def _make_file_logger(log_path: Path, agent_id: str, session_id: str) -> Callable:
    """Return a _log(event, **kwargs) function that appends directly to a JSONL file."""
    fh = open(log_path, "a", buffering=1, encoding="utf-8")

    def _log(event: str, **kwargs: Any) -> None:
        record: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "agent_id": agent_id,
            "session_id": session_id,
            "event": event,
            **kwargs,
        }
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        fh.flush()

    def _close() -> None:
        fh.close()

    _log.close = _close  # type: ignore[attr-defined]
    return _log


# ---------------------------------------------------------------------------
# Core runner
# ---------------------------------------------------------------------------

class PostSessionRunner:
    """
    Runs after an agent session completes to:
      1. Summarise the conversation and store in `institutional` memory.
      2. Extract atomic facts and reconcile them into `agent_facts` memory,
         detecting conflicts with existing entries.
    """

    def __init__(
        self,
        model_summarise: str = _MODEL_SUMMARISE,
        model_facts: str = _MODEL_FACTS,
        model_reconcile: str = _MODEL_RECONCILE,
    ) -> None:
        self._model_summarise = model_summarise
        self._model_facts = model_facts
        self._model_reconcile = model_reconcile
        self._store = MemoryStore()

    # ------------------------------------------------------------------
    # Public entry-points
    # ------------------------------------------------------------------

    def run_on_log(self, log_path: str | Path) -> None:
        """Run post-session processing on an existing JSONL log file."""
        log_path = Path(log_path)
        if not log_path.exists():
            raise FileNotFoundError(f"Log not found: {log_path}")

        events = _load_events(log_path)
        if not events:
            raise ValueError("Empty log file.")

        agent_id = events[0]["agent_id"]
        session_id = events[0]["session_id"]
        transcript = _parse_transcript(events)

        _log = _make_file_logger(log_path, agent_id, session_id)
        try:
            self._process(agent_id, session_id, transcript, _log)
        finally:
            _log.close()  # type: ignore[attr-defined]

    def run_after_session(self, shared: dict) -> None:
        """Called directly after the main session flow finishes (logger still open)."""
        agent_id = shared["agent_id"]
        session_id = shared["session_id"]

        # Build a readable transcript from the persisted messages list
        msgs = shared.get("messages", [])
        turns: list[str] = []
        for m in msgs:
            prefix = "[USER]" if m["role"] == "user" else "[AGENT]"
            turns.append(f"{prefix} {str(m['content'])[:1000]}")
        transcript = "\n\n".join(turns)

        logger = shared["logger"]

        def _log(event: str, **kwargs: Any) -> None:
            logger.log_event(shared, event, **kwargs)

        self._process(agent_id, session_id, transcript, _log)

    # ------------------------------------------------------------------
    # Core pipeline
    # ------------------------------------------------------------------

    def _process(
        self,
        agent_id: str,
        session_id: str,
        transcript: str,
        _log: Callable,
    ) -> None:
        _console.print(
            Rule(f"[bold blue]Post-Session Processing — {agent_id} : {session_id}[/bold blue]")
        )
        _log("post_session_start", transcript_chars=len(transcript))

        # ── Step 1: Summarise ────────────────────────────────────────────────
        _console.print()
        _console.print("[bold]Step 1/3:[/bold] Summarising session…")
        summary_text, summary_topic = self._summarise(session_id, transcript, _log)

        # ── Step 2: Extract facts ────────────────────────────────────────────
        _console.print()
        _console.print("[bold]Step 2/3:[/bold] Extracting facts…")
        facts = self._extract_facts(transcript, _log)
        _console.print(f"  [cyan]→ {len(facts)} facts extracted[/cyan]")

        # ── Step 3: Reconcile each fact ──────────────────────────────────────
        _console.print()
        _console.print(f"[bold]Step 3/3:[/bold] Reconciling {len(facts)} facts…")
        results: list[tuple[str, str, str]] = []
        for i, fact in enumerate(facts, 1):
            action_taken, detail = self._reconcile_fact(fact, agent_id, session_id)
            _log("post_session_fact", fact=fact[:300], action=action_taken, detail=detail)
            results.append((fact, action_taken, detail))
            color = {"inserted": "green", "superseded": "yellow", "flagged": "red", "skipped": "dim"}.get(
                action_taken, "dim"
            )
            _console.print(
                f"  [{color}]{i}/{len(facts)} {action_taken:<12}[/{color}]"
                f"  {fact[:80]}"
            )

        # Summary table
        _console.print()
        t = Table(title="Fact Reconciliation", show_header=True, header_style="bold")
        t.add_column("Fact", max_width=65)
        t.add_column("Action", style="bold", width=12)
        t.add_column("Detail", max_width=25)
        for fact, act, detail in results:
            color = {"inserted": "green", "superseded": "yellow", "flagged": "red", "skipped": "dim"}.get(act, "white")
            t.add_row(fact[:65], f"[{color}]{act}[/{color}]", detail[:25])
        _console.print(t)

        counts = {
            "inserted": sum(1 for _, a, _ in results if a == "inserted"),
            "superseded": sum(1 for _, a, _ in results if a == "superseded"),
            "flagged": sum(1 for _, a, _ in results if a == "flagged"),
            "skipped": sum(1 for _, a, _ in results if a == "skipped"),
        }
        _log(
            "post_session_complete",
            summary_stored=bool(summary_text),
            summary_topic=summary_topic,
            facts_total=len(facts),
            **counts,
        )
        _console.print(
            Panel(
                f"Summary stored ✓\n"
                f"Facts: [green]{counts['inserted']} inserted[/green]  "
                f"[yellow]{counts['superseded']} superseded[/yellow]  "
                f"[red]{counts['flagged']} flagged[/red]  "
                f"[dim]{counts['skipped']} skipped[/dim]",
                title="✅  Post-Session Complete",
                border_style="green",
            )
        )
        _console.print(Rule("[dim]Post-session complete[/dim]"))

    # ------------------------------------------------------------------
    # Steps
    # ------------------------------------------------------------------

    def _summarise(
        self, session_id: str, transcript: str, _log: Callable
    ) -> tuple[str, str]:
        user_msg = f"SESSION TRANSCRIPT (session_id={session_id}):\n\n{transcript}"
        with _console.status("[dim]⏳ calling LLM…[/dim]", spinner="dots"):
            parsed, in_tok, out_tok = call_llm(
                model_id=self._model_summarise,
                system_prompt=_SUMMARISE_SYSTEM,
                messages=[{"role": "user", "content": user_msg}],
            )

        ai = parsed.get("action_input") or {}
        summary_text: str = ai.get("summary", parsed.get("raw_response", "")) if isinstance(ai, dict) else ""
        topic: str = (ai.get("topic", "session_summary") if isinstance(ai, dict) else "session_summary") or "session_summary"

        if summary_text:
            full_content = f"Session summary [{session_id}] — agent={session_id[:8]}\n\n{summary_text}"
            # Include session_id in topic so summaries are distinguishable
            store_topic = f"{topic}_{session_id[:8]}"
            doc_id = self._store.store(
                content=full_content,
                topic=store_topic,
                realm="institutional",
                agent_id="post_session",
                session_id=session_id,
            )
            _log(
                "post_session_summary_stored",
                doc_id=doc_id,
                topic=store_topic,
                input_tokens=in_tok,
                output_tokens=out_tok,
            )
            _console.print(
                Panel(
                    f"[dim]topic:[/dim] [yellow]{store_topic}[/yellow]  "
                    f"[dim]id:[/dim] {doc_id[:8]}…\n\n"
                    f"[dim]{summary_text[:400]}…[/dim]",
                    title="📝  Summary Stored → institutional",
                    border_style="blue",
                )
            )
        else:
            _console.print("[yellow]⚠  Summarisation produced no output.[/yellow]")

        return summary_text, topic

    def _extract_facts(self, transcript: str, _log: Callable) -> list[str]:
        with _console.status("[dim]⏳ calling LLM…[/dim]", spinner="dots"):
            parsed, in_tok, out_tok = call_llm(
                model_id=self._model_facts,
                system_prompt=_EXTRACT_FACTS_SYSTEM,
                messages=[{"role": "user", "content": f"TRANSCRIPT:\n\n{transcript}"}],
            )

        ai = parsed.get("action_input") or {}
        facts: list[str] = ai.get("facts", []) if isinstance(ai, dict) else []
        if not isinstance(facts, list):
            facts = []
        # Normalise: each fact must be a non-empty string
        facts = [str(f).strip() for f in facts if str(f).strip()]

        _log(
            "post_session_facts_extracted",
            count=len(facts),
            input_tokens=in_tok,
            output_tokens=out_tok,
        )
        return facts

    def _reconcile_fact(
        self, fact: str, agent_id: str, session_id: str
    ) -> tuple[str, str]:
        """
        Search agent_facts for similar entries.
        - No close hits → insert directly.
        - Close hits exist → ask LLM: insert | supersede | flag.
        Returns (action_taken, detail_string).
        """
        hits = self._store.search(query=fact, realm="agent_facts", n_results=3)
        close_hits = [h for h in hits if h["distance"] < _CONFLICT_DISTANCE]

        if not close_hits:
            doc_id = self._store.store(
                content=fact,
                topic="fact",
                realm="agent_facts",
                agent_id=agent_id,
                session_id=session_id,
            )
            return "inserted", doc_id[:8]

        # Present similar entries to the LLM for a reconciliation decision
        existing_block = "\n\n".join(
            f"ID={h['id'][:8]} (similarity_dist={h['distance']:.3f}):\n{h['content']}"
            for h in close_hits
        )
        user_msg = f"NEW FACT:\n{fact}\n\nSIMILAR EXISTING ENTRIES:\n{existing_block}"

        with _console.status("[dim]⏳ reconciling…[/dim]", spinner="dots"):
            parsed, _, _ = call_llm(
                model_id=self._model_reconcile,
                system_prompt=_RECONCILE_SYSTEM,
                messages=[{"role": "user", "content": user_msg}],
            )

        action = parsed.get("action", "insert")
        ai = parsed.get("action_input") or {}

        if action == "skip":
            return "skipped", f"dup of {close_hits[0]['id'][:8]}"

        elif action == "supersede":
            target_short = str(ai.get("supersede_id", "")).strip()[:8]
            # Resolve short ID prefix to full ID
            full_id = next(
                (h["id"] for h in close_hits if h["id"][:8] == target_short),
                close_hits[0]["id"],
            )
            updated = self._store.update(doc_id=full_id, content=fact, realm="agent_facts")
            if updated:
                return "superseded", full_id[:8]
            # Fallback: insert if update failed (e.g. ID mismatch)
            doc_id = self._store.store(
                content=fact, topic="fact", realm="agent_facts",
                agent_id=agent_id, session_id=session_id,
            )
            return "inserted", f"{doc_id[:8]} (supersede fallback)"

        elif action == "flag":
            flag_reason = str(ai.get("flag_reason", "conflict detected"))[:200]
            flagged = (
                f"⚠️ CONFLICT — needs human review\n"
                f"Reason: {flag_reason}\n\n"
                f"NEW CLAIM: {fact}\n\n"
                f"EXISTING: {close_hits[0]['content']}"
            )
            doc_id = self._store.store(
                content=flagged,
                topic="fact_conflict",
                realm="agent_facts",
                agent_id=agent_id,
                session_id=session_id,
            )
            return "flagged", f"id={doc_id[:8]}"

        else:  # insert
            doc_id = self._store.store(
                content=fact, topic="fact", realm="agent_facts",
                agent_id=agent_id, session_id=session_id,
            )
            return "inserted", doc_id[:8]
