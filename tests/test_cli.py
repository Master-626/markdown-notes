"""Tests for the mnotes command."""

from __future__ import annotations

from importlib.metadata import version

from click.testing import CliRunner

from markdown_notes import __version__, cli
from markdown_notes.cli import main


def run(notes_dir, *args):
    return CliRunner().invoke(main, ["--notes-dir", str(notes_dir), *args])


def test_version_matches_package_metadata():
    assert version("markdown-notes") == __version__
    result = CliRunner().invoke(main, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_plain_add_list_and_search(tmp_path):
    added = run(tmp_path, "add", "Meeting Notes")
    assert added.exit_code == 0
    assert "Added note: Meeting Notes" in added.output

    listed = run(tmp_path, "list")
    assert listed.exit_code == 0
    assert "Meeting Notes" in listed.output
    assert "No notes yet." not in listed.output

    found = run(tmp_path, "search", "meeting")
    assert found.exit_code == 0
    assert "Searching for: meeting" in found.output
    assert "Meeting Notes" in found.output

    missed = run(tmp_path, "search", "absent")
    assert missed.exit_code == 0
    assert "Searching for: absent" in missed.output
    assert "No matching notes." in missed.output
    assert "Meeting Notes" not in missed.output


def test_list_does_not_invent_a_note(tmp_path):
    notes = tmp_path / "notes"
    listed = run(notes, "list")
    assert listed.exit_code == 0
    assert "No notes yet." in listed.output
    assert "Meeting Notes" not in listed.output
    assert not notes.exists()


def test_rich_markup_and_emoji_codes_stay_literal(tmp_path):
    title = "Note [draft] :smile: [/]"
    added = run(tmp_path, "add", title, "-t", "a[/]")
    assert added.exit_code == 0
    assert title in added.output
    assert "😄" not in added.output

    listed = run(tmp_path, "list")
    assert listed.exit_code == 0
    assert title in listed.output
    assert "a[/]" in listed.output

    found = run(tmp_path, "search", "[/]")
    assert found.exit_code == 0
    assert "Searching for: [/]" in found.output
    assert title in found.output
    assert (tmp_path / "1.md").read_text(encoding="utf-8").count(title) >= 1


def test_blank_title_and_tag_are_rejected(tmp_path):
    blank_title = run(tmp_path, "add", "   ")
    assert blank_title.exit_code == 1
    assert "Title cannot be empty" in blank_title.output

    blank_tag = run(tmp_path, "add", "Ok", "-t", " \t ")
    assert blank_tag.exit_code == 1
    assert "Tag cannot be empty" in blank_tag.output
    assert list(tmp_path.iterdir()) == []

    blank_keyword = run(tmp_path, "search", "  ")
    assert blank_keyword.exit_code == 1
    assert "Search keyword cannot be empty" in blank_keyword.output


def test_tags_are_stored_listed_and_searchable(tmp_path):
    added = run(
        tmp_path,
        "add",
        "买牛奶",
        "-t",
        "生活",
        "-t",
        "生活",
        "-t",
        "home",
    )
    assert added.exit_code == 0
    assert "Added note: 买牛奶" in added.output

    listed = run(tmp_path, "list")
    assert listed.exit_code == 0
    assert "买牛奶" in listed.output
    assert "生活, home" in listed.output
    assert "生活, 生活" not in listed.output

    by_tag = run(tmp_path, "search", "HOME")
    assert by_tag.exit_code == 0
    assert "买牛奶" in by_tag.output

    by_title = run(tmp_path, "search", "牛奶")
    assert "买牛奶" in by_title.output

    text = (tmp_path / "1.md").read_text(encoding="utf-8")
    assert "tag: 生活\n" in text
    assert "tag: home\n" in text
    assert text.count("tag: 生活\n") == 1


def test_notes_dir_option_and_environment_variable(tmp_path, monkeypatch):
    via_option = tmp_path / "option"
    result = run(via_option, "add", "From option")
    assert result.exit_code == 0
    assert (via_option / "1.md").is_file()

    via_env = tmp_path / "env"
    env_result = CliRunner().invoke(
        main,
        ["add", "From env"],
        env={"MNOTES_DIR": str(via_env)},
    )
    assert env_result.exit_code == 0
    assert "Added note: From env" in env_result.output
    assert (via_env / "1.md").is_file()

    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(cli.store, "default_notes_dir", lambda: home / ".markdown-notes")
    default_result = CliRunner().invoke(main, ["add", "From home"])
    assert default_result.exit_code == 0
    assert (home / ".markdown-notes" / "1.md").is_file()


def test_commands_remain_available():
    help_result = CliRunner().invoke(main, ["--help"])
    assert help_result.exit_code == 0
    assert "add" in help_result.output
    assert "list" in help_result.output
    assert "search" in help_result.output
    assert "--notes-dir" in help_result.output

    add_help = CliRunner().invoke(main, ["add", "--help"])
    assert add_help.exit_code == 0
    assert "--tag" in add_help.output
