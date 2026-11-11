# Markdown Notes

## 简介

`mnotes` 是一个在终端里记录 Markdown 笔记的命令行工具。每条笔记保存为一个 `.md` 文件，可以添加多个标签，并按标题或标签搜索（不区分大小写）。笔记默认放在 `~/.markdown-notes`，也可以用 `--notes-dir` 或环境变量 `MNOTES_DIR` 指定目录。以下为英文说明。

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/Master-626/markdown-notes/actions/workflows/ci.yml/badge.svg)](https://github.com/Master-626/markdown-notes/actions/workflows/ci.yml)

A small command-line tool for keeping Markdown notes. Each note is one `.md` file with a title and any number of tags. You can list what you have saved and search titles and tags without leaving the terminal.

## Installation

Python 3.8 or newer is required.

```bash
git clone https://github.com/Master-626/markdown-notes.git
cd markdown-notes
python -m pip install .
```

This installs the `mnotes` command. To work on the project and run tests, install the development extra instead:

```bash
python -m pip install -e ".[dev]"
```

## Usage

```bash
# Save a note. Repeat --tag (or -t) for each tag.
mnotes add "Meeting Notes" --tag work --tag planning

# A note does not need tags.
mnotes add "Buy milk" -t home

# Show every saved note.
mnotes list

# Search titles and tags. Matching is case-insensitive.
mnotes search meeting
mnotes search home
```

`add` prints a confirmation. `list` and `search` print a table with the note id, title, and tags. Search also prints the keyword it used. An empty list or a search with no hits says so, instead of showing a placeholder note.

Titles and tags are stripped of surrounding whitespace. Blank titles, tags, and search keywords are rejected. Text is stored and printed literally, so a title such as `Note [draft]` or `status :smile:` is not treated as terminal markup.

### Choose a directory

Notes are written to `~/.markdown-notes` unless you pick another folder. The flag overrides the environment variable when both are set.

```bash
mnotes --notes-dir ./notes add "Project idea" -t project
mnotes --notes-dir ./notes list

# Same folder for every command in this shell.
export MNOTES_DIR=./notes
mnotes search project
```

Put `--notes-dir` before the command name. Only files named `<id>.md` in that folder (not in subfolders) are notes. Other files, such as `README.md`, are left alone.

### Note file

`mnotes add "Meeting Notes" -t work -t planning` creates `1.md`:

```markdown
---
id: 1
title: Meeting Notes
created: 2026-11-11T17:20:00+00:00
tag: work
tag: planning
---

# Meeting Notes

Tags: work, planning
```

The front matter is what `list` and `search` read. Ids start at 1 and are not reused. A later note is `2.md`, even if an older file was removed.

## Options

| Option | Where | Description |
| --- | --- | --- |
| `--notes-dir DIR` | Before the command | Store notes in `DIR` instead of `~/.markdown-notes`. |
| `MNOTES_DIR` | Environment | Same as `--notes-dir` when the flag is omitted. |
| `-t`, `--tag TEXT` | `add` | Tag to save with the note. Repeat the option for another tag. Duplicate tags are stored once. |
| `--version` | Top level | Print the program version. |
| `--help` | Top level or a command | Print usage for the program or that command. |

Commands:

| Command | Arguments | Description |
| --- | --- | --- |
| `add` | `TITLE` | Save a Markdown note. |
| `list` | | List saved notes. |
| `search` | `KEYWORD` | List notes whose title or tags contain `KEYWORD`. |

## Running tests

From a checkout, with the development extra installed:

```bash
ruff check .
pytest
```

`ruff check .` lints the package and the tests. `pytest` runs the suite in `tests/`. Continuous integration runs both on Python 3.8, 3.9, 3.10, 3.11, 3.12, and 3.13.

## License

MIT License. Copyright (c) 2026 Xu Jiaqi.
