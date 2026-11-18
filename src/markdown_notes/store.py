"""Read and write Markdown note files.

Each note is ``<id>.md`` in the notes directory. Front matter is the source of
truth; the Markdown body mirrors the title and tags for reading in an editor.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


class NoteError(Exception):
    """A note could not be read, written, or validated."""


@dataclass(frozen=True)
class Note:
    """One saved note."""

    id: int
    title: str
    tags: tuple[str, ...]
    created: str
    path: Path

    def matches(self, keyword: str) -> bool:
        """Return whether a search keyword occurs in the title or tags."""
        needle = keyword.casefold()
        return any(needle in field.casefold() for field in (self.title, *self.tags))


def default_notes_dir() -> Path:
    """Return the default notes directory, ``~/.markdown-notes``."""
    return Path.home() / ".markdown-notes"


def add_note(directory: Path, title: str, tags: Sequence[str] = ()) -> Note:
    """Validate and save a note. The directory is created when the note is valid."""
    cleaned_title = _required_text(title, "Title")
    cleaned_tags = tuple(_required_text(tag, "Tag") for tag in tags)
    unique_tags = _dedupe(cleaned_tags)
    _ensure_directory(directory, create=True)
    note_id = _next_id(directory)
    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    path = directory / f"{note_id}.md"
    if path.exists():
        raise NoteError(f"Refusing to overwrite {path.name}.")
    note = Note(
        id=note_id,
        title=cleaned_title,
        tags=unique_tags,
        created=created,
        path=path,
    )
    _write_atomic(path, _render(note))
    return note


def list_notes(directory: Path) -> list[Note]:
    """Return saved notes in id order. A missing directory means there are none."""
    if not directory.exists():
        return []
    _ensure_directory(directory, create=False)
    return _load_all(directory)


def search_notes(directory: Path, keyword: str) -> list[Note]:
    """Return notes whose title or tags contain ``keyword``, case-insensitively."""
    cleaned = keyword.strip()
    if not cleaned:
        raise NoteError("Search keyword cannot be empty or whitespace.")
    return [note for note in list_notes(directory) if note.matches(cleaned)]


def _required_text(value: str, label: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise NoteError(f"{label} cannot be empty or whitespace.")
    return cleaned


def _dedupe(tags: tuple[str, ...]) -> tuple[str, ...]:
    unique: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            unique.append(tag)
    return tuple(unique)


def _ensure_directory(directory: Path, *, create: bool) -> None:
    if directory.exists():
        if not directory.is_dir():
            raise NoteError(f"Notes path is not a directory: {directory}")
        return
    if create:
        directory.mkdir(parents=True, exist_ok=True)


def _next_id(directory: Path) -> int:
    return max((note.id for note in _load_all(directory)), default=0) + 1


def _load_all(directory: Path) -> list[Note]:
    notes: list[Note] = []
    seen: dict[int, Path] = {}
    for path in _note_paths(directory):
        note = _parse(path)
        previous = seen.get(note.id)
        if previous is not None:
            raise NoteError(
                f"Duplicate note id {note.id} in {previous.name} and {path.name}."
            )
        seen[note.id] = path
        notes.append(note)
    return notes


def _note_paths(directory: Path) -> list[Path]:
    numbered: list[tuple[int, str, Path]] = []
    for path in directory.glob("*.md"):
        stem = path.stem
        # Unicode digits such as ² are not safe note ids.
        if stem.isascii() and stem.isdigit():
            numbered.append((int(stem), path.name, path))
    numbered.sort()
    return [path for _, _, path in numbered]


def _parse(path: Path) -> Note:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeError as exc:
        raise NoteError(f"{path.name} is not valid UTF-8.") from exc
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    header = _front_matter(path, text)
    fields: dict[str, str] = {}
    tags: list[str] = []
    for line in header.splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            raise NoteError(f"{path.name} has an invalid front matter line: {line!r}.")
        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = _unescape(raw_value[1:] if raw_value.startswith(" ") else raw_value)
        if key == "tag":
            tag = value.strip()
            if not tag:
                raise NoteError(f"{path.name} has an empty tag.")
            tags.append(tag)
            continue
        if key in fields:
            raise NoteError(f"{path.name} has a duplicate {key} field.")
        fields[key] = value
    note_id = _parse_id(path, fields.get("id"))
    file_id = int(path.stem)
    if note_id != file_id:
        raise NoteError(
            f"{path.name} declares id {note_id}, which does not match the filename."
        )
    if "title" not in fields:
        raise NoteError(f"{path.name} is missing a title.")
    title = fields["title"].strip()
    if not title:
        raise NoteError(f"{path.name} has an empty title.")
    return Note(
        id=note_id,
        title=title,
        tags=tuple(tags),
        created=fields.get("created", "").strip(),
        path=path,
    )


def _front_matter(path: Path, text: str) -> str:
    if not text.startswith("---\n"):
        raise NoteError(f"{path.name} is missing front matter.")
    end = text.find("\n---\n", 3)
    if end != -1:
        return text[4:end]
    # A closing fence at end of file may not have a trailing newline.
    if text.endswith("\n---"):
        return text[4:-4]
    raise NoteError(f"{path.name} has unclosed front matter.")


def _parse_id(path: Path, raw_id: str | None) -> int:
    if raw_id is None:
        raise NoteError(f"{path.name} is missing an id.")
    try:
        note_id = int(raw_id.strip())
    except ValueError as exc:
        raise NoteError(f"{path.name} has an invalid id: {raw_id!r}.") from exc
    if note_id < 1:
        raise NoteError(f"{path.name} has an invalid id: {raw_id!r}.")
    return note_id


def _render(note: Note) -> str:
    lines = [
        "---",
        f"id: {note.id}",
        f"title: {_escape(note.title)}",
        f"created: {note.created}",
    ]
    lines.extend(f"tag: {_escape(tag)}" for tag in note.tags)
    lines.extend(["---", "", f"# {note.title}", ""])
    if note.tags:
        lines.extend([f"Tags: {', '.join(note.tags)}", ""])
    return "\n".join(lines)


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\r", "\\r").replace("\n", "\\n")


def _unescape(value: str) -> str:
    characters: list[str] = []
    index = 0
    while index < len(value):
        if value[index] == "\\" and index + 1 < len(value):
            code = value[index + 1]
            if code == "n":
                characters.append("\n")
            elif code == "r":
                characters.append("\r")
            elif code == "\\":
                characters.append("\\")
            else:
                characters.append("\\")
                characters.append(code)
            index += 2
            continue
        characters.append(value[index])
        index += 1
    return "".join(characters)


def _write_atomic(path: Path, text: str) -> None:
    temporary = path.with_name(path.name + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        temporary.replace(path)
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise
