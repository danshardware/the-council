#!/usr/bin/env python
"""
memory.py — Council memory management CLI

Commands:
    list    List stored documents (with optional filters)
    add     Add a single document interactively
    search  Semantic search across memory
    edit    Update document content by ID
    delete  Delete a document by ID
    import  Import files via the PocketFlow pipeline

Usage examples:
    uv run memory.py list --realm knowledge_base
    uv run memory.py add --topic "product roadmap" --realm institutional
    uv run memory.py search "quarterly revenue targets"
    uv run memory.py edit <doc_id> --realm knowledge_base
    uv run memory.py delete <doc_id> --realm knowledge_base
    uv run memory.py import docs/ --topic "api reference" --realm knowledge_base
    uv run memory.py import README.md --topic "project overview" --realm institutional
"""

from __future__ import annotations

import argparse
import glob
import sys
import textwrap
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from memory.store import MemoryStore, _REALMS

console = Console()

_DB_PATH = "memory_db"
_SUPPORTED_EXTENSIONS = {".md", ".txt", ".rst", ".yaml", ".yml", ".json", ".py", ".ts", ".js"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_store() -> MemoryStore:
    return MemoryStore(db_path=_DB_PATH)


def _realm_choices() -> list[str]:
    return list(_REALMS)


def _truncate(text: str, max_len: int = 80) -> str:
    return text[:max_len] + "…" if len(text) > max_len else text


def _confirm(prompt: str) -> bool:
    try:
        answer = input(f"{prompt} [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return answer in ("y", "yes")


def _resolve_doc_id(store: MemoryStore, doc_id: str, realm: str) -> str | None:
    """
    Resolve a full document ID from an exact ID or a unique prefix.

    Returns the full ID if exactly one match is found, or None otherwise.
    Prints an error message when multiple prefixes match.
    """
    col = store._collections[realm]
    if col.count() == 0:
        return None
    # Try exact match first (fast path)
    exact = col.get(ids=[doc_id], include=[])
    if exact["ids"]:
        return doc_id
    # Prefix scan
    all_ids: list[str] = col.get(include=[])["ids"]
    matches = [i for i in all_ids if i.startswith(doc_id)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        console.print(f"[red]Prefix '{doc_id}' is ambiguous — {len(matches)} documents match. Use a longer prefix.[/red]")
    return None


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


def cmd_list(args: argparse.Namespace) -> None:
    """List documents stored in memory."""
    store = _get_store()

    realms = [args.realm] if args.realm else list(_REALMS)
    total = 0

    for realm in realms:
        col = store._collections[realm]
        count = col.count()
        if count == 0:
            if args.realm:
                console.print(f"[dim]No documents in realm '{realm}'.[/dim]")
            continue

        where = None
        if args.topic:
            where = {"topic": {"$eq": args.topic}}

        try:
            results = col.get(
                where=where,  # type: ignore[arg-type]
                limit=args.limit,
                include=["documents", "metadatas"],
            )
        except Exception as exc:
            console.print(f"[red]Error querying realm '{realm}': {exc}[/red]")
            continue

        if not results["ids"]:
            continue

        table = Table(
            title=f"Realm: {realm}  ({count} total)",
            show_lines=False,
            header_style="bold cyan",
        )
        table.add_column("ID", style="dim", width=10)
        table.add_column("Topic", style="yellow", width=20)
        table.add_column("Agent", width=12)
        table.add_column("Timestamp", width=20)
        table.add_column("Content Preview", no_wrap=False)

        for doc_id, doc, meta in zip(
            results["ids"],
            results["documents"] or [],
            results["metadatas"] or [],
        ):
            table.add_row(
                doc_id[:8],
                str(meta.get("topic", "")),
                str(meta.get("agent_id", "")),
                str(meta.get("timestamp", ""))[:19],
                _truncate(doc.replace("\n", " "), 60),
            )
        console.print(table)
        total += len(results["ids"])

    console.print(f"\n[bold]Total shown:[/bold] {total}")


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------


def cmd_add(args: argparse.Namespace) -> None:
    """Interactively add a single document to memory."""
    store = _get_store()

    topic = args.topic or console.input("[bold]Topic:[/bold] ").strip()
    realm = args.realm or console.input(f"[bold]Realm[/bold] ({'/'.join(_REALMS)}): ").strip()
    if realm not in _REALMS:
        console.print(f"[red]Invalid realm '{realm}'. Must be one of: {list(_REALMS)}[/red]")
        sys.exit(1)

    if args.content:
        content = args.content
    else:
        console.print("[dim]Enter content (end with a blank line, then Ctrl-D / Ctrl-Z):[/dim]")
        lines: list[str] = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            pass
        content = "\n".join(lines).strip()

    if not content:
        console.print("[red]No content provided — aborting.[/red]")
        sys.exit(1)

    keywords = [k.strip() for k in args.keywords.split(",")] if args.keywords else []
    doc_id = store.store(
        content=content,
        topic=topic,
        realm=realm,
        agent_id="memory_cli",
        session_id="manual",
        keywords=keywords,
    )
    console.print(Panel(f"[green]Stored[/green]  ID: [bold]{doc_id}[/bold]", expand=False))


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


def cmd_search(args: argparse.Namespace) -> None:
    """Semantic search across memory."""
    store = _get_store()

    results = store.search(
        query=args.query,
        realm=args.realm or None,
        topic=args.topic or None,
        n_results=args.top_k,
    )

    if not results:
        console.print("[dim]No results found.[/dim]")
        return

    table = Table(
        title=f"Search: '{args.query}'",
        show_lines=True,
        header_style="bold cyan",
    )
    table.add_column("#", width=3)
    table.add_column("ID", style="dim", width=10)
    table.add_column("Realm", width=14)
    table.add_column("Topic", style="yellow", width=20)
    table.add_column("Score", width=7)
    table.add_column("Content")

    for i, r in enumerate(results, 1):
        score = f"{1 - r['distance']:.3f}"
        table.add_row(
            str(i),
            r["id"][:8],
            r["metadata"].get("realm", ""),
            r["metadata"].get("topic", ""),
            score,
            _truncate(r["content"].replace("\n", " "), 80),
        )
    console.print(table)

    if args.show_full:
        for i, r in enumerate(results, 1):
            console.print(Panel(r["content"], title=f"#{i} {r['id'][:8]}  score={1 - r['distance']:.3f}"))


# ---------------------------------------------------------------------------
# edit
# ---------------------------------------------------------------------------


def cmd_edit(args: argparse.Namespace) -> None:
    """Update the content of a document by ID."""
    store = _get_store()

    realm = args.realm
    if realm not in _REALMS:
        console.print(f"[red]Invalid realm '{realm}'. Must be one of: {list(_REALMS)}[/red]")
        sys.exit(1)

    if args.content:
        new_content = args.content
    else:
        console.print("[dim]Enter new content (Ctrl-D / Ctrl-Z to finish):[/dim]")
        lines: list[str] = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            pass
        new_content = "\n".join(lines).strip()

    if not new_content:
        console.print("[red]No content provided — aborting.[/red]")
        sys.exit(1)

    full_id = _resolve_doc_id(store, args.doc_id, realm)
    if not full_id:
        console.print(f"[red]Document '{args.doc_id}' not found in realm '{realm}'.[/red]")
        sys.exit(1)

    store.update(doc_id=full_id, content=new_content, realm=realm)
    console.print(f"[green]Updated[/green] {full_id}")


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


def cmd_delete(args: argparse.Namespace) -> None:
    """Delete a document by ID."""
    store = _get_store()

    realm = args.realm
    if realm not in _REALMS:
        console.print(f"[red]Invalid realm '{realm}'. Must be one of: {list(_REALMS)}[/red]")
        sys.exit(1)

    full_id = _resolve_doc_id(store, args.doc_id, realm)
    if not full_id:
        console.print(f"[red]Document '{args.doc_id}' not found in realm '{realm}'.[/red]")
        sys.exit(1)

    if not args.yes and not _confirm(f"Delete document '{full_id}' from realm '{realm}'?"):
        console.print("[dim]Cancelled.[/dim]")
        return

    store.delete(doc_id=full_id, realm=realm)
    console.print(f"[green]Deleted[/green] {full_id[:8]}")


# ---------------------------------------------------------------------------
# import
# ---------------------------------------------------------------------------


def _resolve_paths(path_arg: str) -> list[Path]:
    """Expand a path argument — directory, glob, or single file."""
    p = Path(path_arg)
    if p.is_dir():
        found: list[Path] = []
        for ext in _SUPPORTED_EXTENSIONS:
            found.extend(p.rglob(f"*{ext}"))
        return sorted(found)
    # Try as glob
    matches = [Path(m) for m in glob.glob(path_arg, recursive=True)]
    if matches:
        return sorted(m for m in matches if m.is_file())
    # Single file
    if p.is_file():
        return [p]
    console.print(f"[red]No files found at '{path_arg}'[/red]")
    sys.exit(1)


def cmd_import(args: argparse.Namespace) -> None:
    """Import files into memory using the PocketFlow pipeline."""
    from memory.pipeline import import_file  # imported here to avoid slow startup for other commands

    realm = args.realm
    if realm not in _REALMS:
        console.print(f"[red]Invalid realm '{realm}'. Must be one of: {list(_REALMS)}[/red]")
        sys.exit(1)

    files = _resolve_paths(args.path)
    if not files:
        console.print("[red]No supported files found.[/red]")
        sys.exit(1)

    store = _get_store()
    total_chunks = 0
    total_files = 0
    errors: list[str] = []

    console.print(f"\n[bold]Importing {len(files)} file(s)[/bold]  →  realm=[yellow]{realm}[/yellow]  topic=[yellow]{args.topic}[/yellow]\n")

    for file_path in files:
        try:
            ids = import_file(
                path=file_path,
                topic=args.topic,
                realm=realm,
                store=store,
                chunk_size=args.chunk_size,
                source_tag=args.source_tag or None,
                agent_id="memory_cli",
                session_id="import",
            )
            total_chunks += len(ids)
            total_files += 1
            label = str(file_path)
            console.print(f"  [green]✓[/green] {label}  [dim]({len(ids)} chunk{'s' if len(ids) != 1 else ''})[/dim]")
        except Exception as exc:
            errors.append(f"{file_path}: {exc}")
            console.print(f"  [red]✗[/red] {file_path}  [red]{exc}[/red]")

    console.print(
        f"\n[bold green]Done.[/bold green]  "
        f"{total_files} file(s) imported, {total_chunks} chunks stored."
        + (f"  [red]{len(errors)} error(s).[/red]" if errors else "")
    )


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="memory",
        description="Council memory management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """\
            Examples:
              uv run memory.py list
              uv run memory.py list --realm knowledge_base --topic "api docs" --limit 50
              uv run memory.py search "quarterly revenue"
              uv run memory.py search "onboarding process" --realm institutional --top-k 5 --show-full
              uv run memory.py add --topic "meeting notes" --realm institutional
              uv run memory.py edit <doc_id> --realm knowledge_base
              uv run memory.py delete <doc_id> --realm knowledge_base
              uv run memory.py import README.md --topic "project" --realm knowledge_base
              uv run memory.py import docs/ --topic "api reference" --realm knowledge_base --chunk-size 2000
            """
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- list ---
    p_list = sub.add_parser("list", help="List stored documents")
    p_list.add_argument("--realm", choices=_realm_choices(), help="Filter by realm")
    p_list.add_argument("--topic", help="Filter by topic (exact match)")
    p_list.add_argument("--limit", type=int, default=50, help="Max documents to show (default: 50)")

    # --- add ---
    p_add = sub.add_parser("add", help="Add a document manually")
    p_add.add_argument("--topic", help="Topic label")
    p_add.add_argument("--realm", choices=_realm_choices(), help="Target realm")
    p_add.add_argument("--content", help="Content string (skip interactive prompt)")
    p_add.add_argument("--keywords", help="Comma-separated keywords")

    # --- search ---
    p_search = sub.add_parser("search", help="Semantic search")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--realm", choices=_realm_choices(), help="Restrict to realm")
    p_search.add_argument("--topic", help="Restrict to topic")
    p_search.add_argument("--top-k", type=int, default=10, dest="top_k", help="Number of results (default: 10)")
    p_search.add_argument("--show-full", action="store_true", dest="show_full", help="Print full content of each result")

    # --- edit ---
    p_edit = sub.add_parser("edit", help="Update a document by ID")
    p_edit.add_argument("doc_id", help="Document ID (or prefix)")
    p_edit.add_argument("--realm", choices=_realm_choices(), required=True, help="Realm the document lives in")
    p_edit.add_argument("--content", help="New content string (skip interactive prompt)")

    # --- delete ---
    p_delete = sub.add_parser("delete", help="Delete a document by ID")
    p_delete.add_argument("doc_id", help="Document ID")
    p_delete.add_argument("--realm", choices=_realm_choices(), required=True, help="Realm the document lives in")
    p_delete.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")

    # --- import ---
    p_import = sub.add_parser("import", help="Import file(s) via the PocketFlow pipeline")
    p_import.add_argument("path", help="File, directory, or glob pattern to import")
    p_import.add_argument("--topic", required=True, help="Topic label for imported documents")
    p_import.add_argument("--realm", choices=_realm_choices(), required=True, help="Target realm")
    p_import.add_argument("--chunk-size", type=int, default=4000, dest="chunk_size", help="Max characters per chunk (default: 4000)")
    p_import.add_argument("--source-tag", dest="source_tag", help="Optional source label stored in keywords (e.g. URL)")

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "list": cmd_list,
        "add": cmd_add,
        "search": cmd_search,
        "edit": cmd_edit,
        "delete": cmd_delete,
        "import": cmd_import,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
