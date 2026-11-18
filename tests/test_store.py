"""Tests for Markdown note storage."""

from __future__ import annotations

from datetime import datetime

import pytest

from markdown_notes.store import NoteError, add_note, list_notes, search_notes


def test_add_writes_markdown_and_lists_in_id_order(tmp_path):
    first = add_note(tmp_path, "  Meeting Notes  ", [" work ", "work", "planning"])
    second = add_note(tmp_path, "Buy milk", ["home"])

    assert first.id == 1
    assert first.title == "Meeting Notes"
    assert first.tags == ("work", "planning")
    assert first.path == tmp_path / "1.md"
    assert second.id == 2
    assert "T" in first.created and first.created.endswith("+00:00")
    datetime.fromisoformat(first.created)

    text = first.path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "title: Meeting Notes\n" in text
    assert "tag: work\n" in text
    assert "tag: planning\n" in text
    assert "# Meeting Notes\n" in text
    assert "Tags: work, planning\n" in text
    assert b"\r" not in first.path.read_bytes()

    listed = list_notes(tmp_path)
    assert [note.id for note in listed] == [1, 2]
    assert [note.title for note in listed] == ["Meeting Notes", "Buy milk"]


def test_round_trip_preserves_markup_newlines_and_backslashes(tmp_path):
    title = "Note [draft]\n---\r\\n :smile: [/]"
    tags = ("a[/]", "work\\n", "plan, later")
    saved = add_note(tmp_path, title, tags)

    loaded = list_notes(tmp_path)
    assert loaded == [saved]
    assert loaded[0].title == title
    assert loaded[0].tags == tags


def test_search_matches_title_and_tags_without_regex(tmp_path):
    add_note(tmp_path, "C++ notes", ["language"])
    add_note(tmp_path, "Shopping", ["groceries"])

    assert [note.title for note in search_notes(tmp_path, "c++")] == ["C++ notes"]
    assert [note.title for note in search_notes(tmp_path, "  GROCERIES ")] == ["Shopping"]
    assert search_notes(tmp_path, "a.+") == []
    assert search_notes(tmp_path, "note.") == []


def test_rejects_blank_title_tag_and_keyword(tmp_path):
    with pytest.raises(NoteError, match="Title cannot be empty"):
        add_note(tmp_path, " \t ")
    with pytest.raises(NoteError, match="Tag cannot be empty"):
        add_note(tmp_path, "Ok", ["work", "  "])
    with pytest.raises(NoteError, match="Search keyword cannot be empty"):
        search_notes(tmp_path, "   ")
    assert list(tmp_path.iterdir()) == []


def test_missing_directory_is_empty_and_nested_files_are_ignored(tmp_path):
    missing = tmp_path / "missing"
    assert list_notes(missing) == []
    assert search_notes(missing, "anything") == []
    assert not missing.exists()

    nested = tmp_path / "notes" / "nested"
    nested.mkdir(parents=True)
    (nested / "1.md").write_text("ignored\n", encoding="utf-8")
    (tmp_path / "notes" / "README.md").write_text("# hello\n", encoding="utf-8")
    assert list_notes(tmp_path / "notes") == []


def test_malformed_notes_are_reported(tmp_path):
    (tmp_path / "1.md").write_text("not a note\n", encoding="utf-8")
    with pytest.raises(NoteError, match="1.md is missing front matter"):
        list_notes(tmp_path)

    (tmp_path / "1.md").write_bytes(b"\xff\xfe")
    with pytest.raises(NoteError, match="1.md is not valid UTF-8"):
        list_notes(tmp_path)

    (tmp_path / "1.md").write_text("---\nid: 1\n", encoding="utf-8")
    with pytest.raises(NoteError, match="unclosed front matter"):
        list_notes(tmp_path)

    (tmp_path / "1.md").write_text(
        "---\nid: 1\nbad line\ntitle: Hi\n---\n",
        encoding="utf-8",
    )
    with pytest.raises(NoteError, match="invalid front matter line"):
        list_notes(tmp_path)

    (tmp_path / "1.md").write_text(
        "---\nid: 1\ntitle: Hi\ntitle: Again\n---\n",
        encoding="utf-8",
    )
    with pytest.raises(NoteError, match="duplicate title"):
        list_notes(tmp_path)

    (tmp_path / "1.md").write_text("---\ntitle: Hi\n---\n", encoding="utf-8")
    with pytest.raises(NoteError, match="missing an id"):
        list_notes(tmp_path)

    (tmp_path / "1.md").write_text("---\nid: no\ntitle: Hi\n---\n", encoding="utf-8")
    with pytest.raises(NoteError, match="invalid id"):
        list_notes(tmp_path)

    (tmp_path / "1.md").write_text("---\nid: 0\ntitle: Hi\n---\n", encoding="utf-8")
    with pytest.raises(NoteError, match="invalid id"):
        list_notes(tmp_path)

    (tmp_path / "1.md").write_text("---\nid: 1\ntitle:    \n---\n", encoding="utf-8")
    with pytest.raises(NoteError, match="empty title"):
        list_notes(tmp_path)

    (tmp_path / "1.md").write_text(
        "---\nid: 1\ntitle: Hi\ntag:\n---\n",
        encoding="utf-8",
    )
    with pytest.raises(NoteError, match="empty tag"):
        list_notes(tmp_path)
    (tmp_path / "1.md").unlink()

    (tmp_path / "4.md").write_text("---\nid: 5\ntitle: Hi\n---\n", encoding="utf-8")
    with pytest.raises(NoteError, match="does not match the filename"):
        list_notes(tmp_path)


def test_duplicate_ids_and_crlf_files(tmp_path):
    note = add_note(tmp_path, "Hello: world", ["keep"])
    padded = tmp_path / "01.md"
    padded.write_bytes(note.path.read_bytes())
    with pytest.raises(NoteError, match="Duplicate note id 1"):
        list_notes(tmp_path)
    padded.unlink()

    crlf = (
        "---\r\n"
        "id: 2\r\n"
        "title: Windows note\r\n"
        "tag: desk\r\n"
        "extra: ignored\r\n"
        "---\r\n"
        "\r\n"
        "# Windows note\r\n"
    )
    (tmp_path / "2.md").write_bytes(crlf.encode("utf-8"))
    loaded = {note.id: note for note in list_notes(tmp_path)}
    assert loaded[2].title == "Windows note"
    assert loaded[2].tags == ("desk",)


def test_notes_path_must_be_a_directory(tmp_path):
    path = tmp_path / "notes-file"
    path.write_text("nope", encoding="utf-8")
    with pytest.raises(NoteError, match="not a directory"):
        list_notes(path)
    with pytest.raises(NoteError, match="not a directory"):
        add_note(path, "Title")


def test_closing_fence_without_trailing_newline_and_unused_ids(tmp_path):
    (tmp_path / "1.md").write_text("---\nid: 1\ntitle: Fence\n---", encoding="utf-8")
    assert list_notes(tmp_path)[0].title == "Fence"

    add_note(tmp_path, "Second")
    (tmp_path / "1.md").unlink()
    third = add_note(tmp_path, "Third")
    assert third.id == 3
    assert [note.id for note in list_notes(tmp_path)] == [2, 3]


def test_title_is_not_used_as_a_path(tmp_path):
    saved = add_note(tmp_path, "../../outside", [])
    assert saved.path == tmp_path / "1.md"
    assert saved.path.is_file()
    assert [path.name for path in tmp_path.iterdir()] == ["1.md"]
