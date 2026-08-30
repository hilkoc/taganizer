# Taganizer

Taganizer is a tag-based item organizer. It stores items in SQLite, arranges them
into a parent/child tag hierarchy, and lets you search by combining tags.

It can be used as tool for agent memory.

## Overview

- Items are anything worth tracking: files, directories, URLs, snippets of text or other tags
- Items are linked into a parent/child **tag hierarchy** (a directed acyclic graph); a
  database trigger prevents cycles.
- **Search** finds the intersection of tags, and supports the *union of intersections*:
  `A B + C` means *(A and B) or C*.
- Pure standard library, no dependencies. Requires Python 3.8+.

## Installation

The package defines a `tzr` entry point, so installing it puts a `tzr` command on your
`PATH` — you can run `tzr <subcommand>` directly, with no `python -m taganizer.cli` prefix.
Install from a checkout of the repository (use `.`), or once published, from PyPI (use
`taganizer`). Verify with `tzr --version`.

### Pipx

Installs `tzr` into an isolated, globally available environment:

```bash
pipx install taganizer
```

### Pip

Installs into the currently active Python environment:

```bash
pip install taganizer
```


## Usage

By default the database lives at `~/.tzr.db`. Point at a different file with the global
`--db PATH` flag (usable before or after the subcommand). See `tzr --version` and
`tzr --help` for details.

```bash
# Create the database schema
tzr init

# Create some items
tzr create tag python
tzr create url https://example.com

# Tag one item with another (child, parent)
tzr tag https://example.com python   # -> "https://example.com tagged with python"

# List items (optionally as a tree)
tzr ls
tzr ls --tree

# Search: intersection of tags, or a union of intersections
tzr search python
tzr search python web + news        # (python and web) or news

# Rename or delete items
tzr rename python py
tzr delete py

# Export the database to a SQL dump (default: tzr_export.sql)
tzr export
tzr export my_dump.sql
```

### Commands

| Command | Description |
| --- | --- |
| `tzr init` | Initialize the database schema. |
| `tzr export [FILE]` | Export the database to an SQL dump file. |
| `tzr ls` / `tzr list` | List all items (`--tree` shows the association tree). |
| `tzr create <type> <name>` | Create a new item of the given type. |
| `tzr rename <old> <new>` | Rename an item (its type is unchanged). |
| `tzr delete <name>` | Delete an item (its tag links are removed; other items are unaffected). |
| `tzr tag <child> <parent>` | Associate an item with a parent tag. |
| `tzr search <query>...` | Search items by tag; `+` unions groups. |


## Library usage

Taganizer can also be used directly as a library. `ItemStore` owns a single database
connection and works as a context manager:

```python
from taganizer import ItemStore, Item

with ItemStore("my.db") as store:
    store.initialize()                       # create schema (idempotent)
    store.create_item(Item(-1, "TAG", "python"))
    store.create_item(Item(-1, "URL", "https://example.com"))
    store.associate("python", "https://example.com")

    # search returns a tuple (map id ->Item, list of associations)
    matches, _ = store.search([["python"]])
    for item in matches.values():
        print(item)
# the connection is closed on exit
```

`SqlItemStore` is a drop-in subclass whose search resolves the union of intersections in
a single SQL statement.

## Development

Set up an isolated virtual environment and install the project in editable mode so code
changes take effect without reinstalling. Run `tzr <subcommand>` afterwards to exercise
your changes.

### Virtual environment

Create and activate a virtual environment in the repository root:

```bash
python3 -m venv .venv          # create the environment
source .venv/bin/activate      # activate it (Linux/macOS)
# .venv\Scripts\activate       # activate it (Windows PowerShell/cmd)
python -m pip install --upgrade pip
```

Then install the project. Include the `dev` extra to get the test and lint tools
(`pytest`, `black`, `flake8`, `build`, `twine`):

```bash
pip install -e ".[dev]"        # editable install with dev tooling
# pip install -e .             # or just the package, without dev tooling
```

Deactivate the environment when you're done with `deactivate`.

### Pipx

Alternatively, install `tzr` into an isolated, globally available environment:

```bash
pipx install --editable .
```

Run the test suite from the repository root (with the virtual environment activated):

```bash
pytest tests
```

## License

Released under the MIT License.
