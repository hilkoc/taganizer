#!/usr/bin/python3
"""The main entry point for tzr."""

import argparse
import os
import sqlite3
import sys
from importlib.metadata import version, PackageNotFoundError
from .item import Item
from . import item_store

# Default database location: a hidden file in the user's home directory.
DEFAULT_DB = "~/.tzr.db"

# Item types accepted by `create` and by the `--type` filter.
ITEM_TYPES = ["tag", "file", "dir", "url", "txt", "cmd"]

try:
    __version__ = version("taganizer")
except PackageNotFoundError:  # not installed (e.g. run from a source checkout)
    __version__ = "0.0.0"


def db(db_path):
    """Open and return an ItemStore for the given database path.

    The returned store owns a single connection; use it as a context manager.
    """
    return item_store.ItemStore(os.path.expanduser(db_path))


def output(*args, **kwargs):
    print(*args, **kwargs)


def error(message):
    """Print an error message to stderr and return the failure exit status."""
    print("tzr: %s" % message, file=sys.stderr)
    return 1


def filter_type(item_dict, typ):
    """Keep only the items of the given type (case-insensitive); None keeps all."""
    if typ is None:
        return item_dict
    return {uid: item for uid, item in item_dict.items() if item.typ.upper() == typ.upper()}


def resolve_path(name, db_path):
    """Return the absolute path for an item name.

    '~' is expanded. A relative name is resolved against the directory that holds the
    database file, so a database and the files it indexes can be moved together.
    """
    path = os.path.expanduser(name)
    if not os.path.isabs(path):
        if db_path == ":memory:":
            base = os.getcwd()
        else:
            base = os.path.dirname(os.path.abspath(os.path.expanduser(db_path)))
        path = os.path.join(base, path)
    return os.path.normpath(path)


def show_item(item, level, indent):
    temp = level * indent
    output(temp, str(item), sep="")


def init(store, args):
    output("initializing database")
    result = store.initialize()
    output(result)


def export(store, args):
    output("Exporting database to %s" % args.dump_file)
    with open(args.dump_file, "w") as f:
        result = store.dump_db(f)
    output(result)


def build_tree(item_dict, pairs_list):
    for pair in pairs_list:
        p = item_dict[pair[0]]
        c = item_dict[pair[1]]
        p.add_child(c)


def list_items(store, args):
    item_dict = filter_type(store.select_all(), args.type)
    if not args.tree:
        for x in item_dict.values():
            output(x)
    else:
        # Drop links to items removed by the type filter.
        pairs_list = [
            pair
            for pair in store.all_associations()
            if pair[0] in item_dict and pair[1] in item_dict
        ]
        build_tree(item_dict, pairs_list)
        for root in item_dict.values():
            if root.parents is None:
                root.traverse_children(show_item, "  ")


def create(store, args):
    if store.get_item(args.name) is not None:
        return error("cannot create: item %r already exists" % args.name)
    # Validate every tag before creating anything, so a typo leaves nothing behind.
    tags = args.tags or []
    bad = []
    for tag in tags:
        parent = store.get_item(tag)
        if parent is None or parent.typ.upper() != "TAG":
            bad.append(tag)
    if bad:
        return error(
            "cannot create: no such tag: %s. Create it first with: tzr create tag <name>"
            % ", ".join(bad)
        )
    item = Item(-1, args.type.upper(), args.name)
    rowid = store.create_item(item)
    for tag in tags:
        store.associate(tag, args.name)
    output("created item with id: %i" % rowid)


def rename(store, args):
    rowcount = store.rename_item(args.old, args.new)
    output("renamed %i item" % rowcount)


def delete(store, args):
    rowcount = store.delete_item(args.name)
    output("deleted %i item" % rowcount)


def add_association(store, args):
    try:
        store.associate(args.parent_name, args.child_name)
    except ValueError as e:
        output(
            "tzr: cannot tag: %s. "
            "Usage: tzr tag <child> <parent> — did you swap the arguments?" % e,
            file=sys.stderr,
        )
        return 1
    except sqlite3.IntegrityError as e:
        # Raised for a duplicate link, or by the trigger that prevents cycles.
        if "UNIQUE" in str(e):
            return error("%s is already tagged with %s" % (args.child_name, args.parent_name))
        return error("cannot tag: %s" % e)
    output("%s tagged with %s" % (args.child_name, args.parent_name))


def remove_association(store, args):
    rowcount = store.dissociate(args.parent_name, args.child_name)
    if rowcount == 0:
        return error("%s is not tagged with %s" % (args.child_name, args.parent_name))
    output("%s no longer tagged with %s" % (args.child_name, args.parent_name))


def list_tags(store, args):
    if store.get_item(args.name) is None:
        return error("no such item %r" % args.name)
    for parent in store.parents(args.name):
        output(parent)


def split_groups(tokens):
    """Split search tokens into groups on the '+' separator.

    E.g. ['A', 'B', '+', 'C'] -> [['A', 'B'], ['C']], meaning (A ∩ B) ∪ (C).
    """
    groups, current = [], []
    for tok in tokens:
        if tok == "+":
            if current:
                groups.append(current)
                current = []
        else:
            current.append(tok)
    if current:
        groups.append(current)
    return groups


def search(store, args):
    groups = split_groups(args.query)
    item_dict, pairs_list = store.search(groups)
    paths = args.paths or args.print0
    # Path output is meant for piping into other tools, so it defaults to files only.
    item_dict = filter_type(item_dict, args.type or ("file" if paths else None))
    if paths:
        end = "\0" if args.print0 else "\n"
        for path in sorted(resolve_path(item.url, args.db) for item in item_dict.values()):
            output(path, end=end)
        return 0
    build_tree(item_dict, pairs_list)
    for root in item_dict.values():
        if root.parents is None:
            root.traverse_children(show_item, "  ")


def main(main_args=None):
    parser = argparse.ArgumentParser(
        prog="tzr", description="Taganizer - a tag-based item organizer."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    # --db is accepted both before the subcommand (top-level, with the default) and after
    # it (via the shared parent parser). SUPPRESS on the parent means it only overrides
    # args.db when actually given, so it never clobbers a value passed before the subcommand.
    parser.add_argument(
        "--db",
        default=DEFAULT_DB,
        help=f"Path to the SQLite database file (default: {DEFAULT_DB}).",
    )
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--db",
        default=argparse.SUPPRESS,
        help=f"Path to the SQLite database file (default: {DEFAULT_DB}).",
    )

    subparsers = parser.add_subparsers(
        dest="command_name",
        title="subcommands",
        description="valid subcommands",
        help="sub-command help",
    )
    # the parser for the "init" command
    parser_init = subparsers.add_parser(
        "init", parents=[common], help="Initialize the database schema."
    )
    parser_init.set_defaults(func=init)
    # the parser for the "export" command
    parser_export = subparsers.add_parser(
        "export", parents=[common], help="Export the database to an SQL dump file."
    )
    parser_export.add_argument(
        "dump_file",
        nargs="?",
        default="tzr_export.sql",
        help="File to write the SQL dump to (default: tzr_export.sql).",
    )
    parser_export.set_defaults(func=export)
    # the parser for the "ls" command
    parser_ls = subparsers.add_parser(
        "ls", parents=[common], aliases=["list"], help="List all items."
    )
    parser_ls.add_argument(
        "-t", "--tree", action="store_true", help="Show items as a tree of associations."
    )
    parser_ls.add_argument("--type", choices=ITEM_TYPES, help="Only list items of this type.")
    parser_ls.set_defaults(func=list_items)
    # the parser for the "create" command
    parser_create = subparsers.add_parser(
        "create",
        parents=[common],
        aliases=["cr", "add"],
        help="Create a new item of the given type.",
    )
    parser_create.add_argument("type", choices=ITEM_TYPES, help="Item type.")
    parser_create.add_argument("name", help="Tag name, or path/URL/value of the item.")
    parser_create.add_argument(
        "--tag",
        dest="tags",
        action="append",
        metavar="TAG",
        help="Tag the new item with this existing tag. Repeat for several tags.",
    )
    parser_create.set_defaults(func=create)
    # the parser for the "rename" command
    parser_rename = subparsers.add_parser(
        "rename", parents=[common], aliases=["mv"], help="Rename an item (its type is unchanged)."
    )
    parser_rename.add_argument("old", help="Current name or URL of the item.")
    parser_rename.add_argument("new", help="New name or URL of the item.")
    parser_rename.set_defaults(func=rename)
    # the parser for the "delete" command
    parser_delete = subparsers.add_parser(
        "delete", parents=[common], aliases=["rm", "del"], help="Delete an item."
    )
    parser_delete.add_argument(
        "name",
        help="Delete the item with the given name and all its associations.",
    )
    parser_delete.set_defaults(func=delete)
    # the parser for the "tag" command
    parser_tag = subparsers.add_parser(
        "tag", parents=[common], aliases=["label"], help="Associate an item with a parent tag."
    )
    parser_tag.add_argument("child_name", help="Item to be tagged (child).")
    parser_tag.add_argument("parent_name", help="Parent tag to apply.")
    parser_tag.set_defaults(func=add_association)
    # the parser for the "untag" command
    parser_untag = subparsers.add_parser(
        "untag", parents=[common], aliases=["unlabel"], help="Remove a parent tag from an item."
    )
    parser_untag.add_argument("child_name", help="Item to remove the tag from (child).")
    parser_untag.add_argument("parent_name", help="Parent tag to remove.")
    parser_untag.set_defaults(func=remove_association)
    # the parser for the "tags" command
    parser_tags = subparsers.add_parser(
        "tags", parents=[common], help="List the tags directly applied to an item."
    )
    parser_tags.add_argument("name", help="Name or path/URL of the item.")
    parser_tags.set_defaults(func=list_tags)
    # the parser for the "search" command
    parser_search = subparsers.add_parser(
        "search", parents=[common], aliases=["s", "show", "select"], help="Search items by tag."
    )
    parser_search.add_argument(
        "query",
        nargs="+",
        help="Tags to search for. Example: 'A B + C' means items tagged with (A and B) or C.",
    )
    parser_search.add_argument(
        "--type",
        choices=ITEM_TYPES,
        help="Only show items of this type (default with --paths: file).",
    )
    parser_search.add_argument(
        "-p",
        "--paths",
        action="store_true",
        help="Print only absolute paths, one per line, for piping, e.g. into 'xargs grep'. "
        "Relative item names are resolved against the directory of the database file.",
    )
    parser_search.add_argument(
        "-0",
        "--print0",
        action="store_true",
        help="Like --paths, but separate paths with NUL instead of newline (for 'xargs -0').",
    )
    parser_search.set_defaults(func=search)

    args = parser.parse_args(main_args)

    if hasattr(args, "func"):
        with db(args.db) as store:
            return args.func(store, args) or 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
