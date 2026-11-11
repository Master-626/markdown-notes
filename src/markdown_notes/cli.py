"""CLI interface."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.text import Text

from markdown_notes import __version__, store

console = Console()


def _notes_directory(path: Path | None) -> Path:
    if path is not None:
        return path
    return store.default_notes_dir()


def _fail(error: store.NoteError) -> None:
    raise click.ClickException(str(error)) from error


@click.group()
@click.version_option(version=__version__)
@click.option(
    "--notes-dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    envvar="MNOTES_DIR",
    default=None,
    help="Directory for Markdown notes. Defaults to ~/.markdown-notes.",
)
@click.pass_context
def main(ctx: click.Context, notes_dir: Path | None) -> None:
    """Markdown Notes - Simple Markdown note-taking from the terminal."""
    ctx.ensure_object(dict)
    ctx.obj["notes_dir"] = _notes_directory(notes_dir)


def _directory(ctx: click.Context) -> Path:
    return ctx.obj["notes_dir"]


@main.command()
@click.argument("title")
@click.option(
    "-t",
    "--tag",
    "tags",
    multiple=True,
    help="Tag to attach. Repeat for more than one tag.",
)
@click.pass_context
def add(ctx: click.Context, title: str, tags: tuple[str, ...]) -> None:
    """Add a new note."""
    try:
        note = store.add_note(_directory(ctx), title, tags)
    except store.NoteError as exc:
        _fail(exc)
    # Keep user text literal. Rich would otherwise treat [brackets] as markup
    # and :shortcodes: as emoji, which drops characters or raises MarkupError.
    console.print(Text.assemble("✅ Added note: ", (note.title, "bold green")))


@main.command(name="list")
@click.pass_context
def list_notes(ctx: click.Context) -> None:
    """List all notes."""
    try:
        notes = store.list_notes(_directory(ctx))
    except store.NoteError as exc:
        _fail(exc)
    _print_notes(notes, "No notes yet.")


@main.command()
@click.argument("keyword")
@click.pass_context
def search(ctx: click.Context, keyword: str) -> None:
    """Search notes."""
    try:
        notes = store.search_notes(_directory(ctx), keyword)
    except store.NoteError as exc:
        _fail(exc)
    console.print(Text.assemble("🔍 Searching for: ", keyword.strip()))
    _print_notes(notes, "No matching notes.")


def _print_notes(notes: list[store.Note], empty_message: str) -> None:
    table = Table(title="Notes")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="green")
    table.add_column("Tags")
    for note in notes:
        table.add_row(str(note.id), Text(note.title), Text(", ".join(note.tags)))
    console.print(table)
    if not notes:
        console.print(empty_message)


if __name__ == "__main__":
    main()
