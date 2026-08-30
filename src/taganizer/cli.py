#!/usr/bin/python3
"""The main entry point for tzr."""

import argparse
import os
import sys
from importlib.metadata import version, PackageNotFoundError
from .item import Item
from . import item_store

# Default database location: a hidden file in the user's home directory.
DEFAULT_DB = "~/.tzr.db"

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
    item_dict = store.select_all()
    if not args.tree:
        for x in item_dict.values():
            output(x)
    else:
        pairs_list = store.all_associations()
        build_tree(item_dict, pairs_list)
        for root in item_dict.values():
            if root.parents is None:
                root.traverse_children(show_item, "  ")


def create(store, args):
    item = Item(-1, args.type.upper(), args.name)
    rowid = store.create_item(item)
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
    output("%s tagged with %s" % (args.child_name, args.parent_name))


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
    parser_ls.set_defaults(func=list_items)
    # the parser for the "create" command
    parser_create = subparsers.add_parser(
        "create",
        parents=[common],
        aliases=["cr", "add"],
        help="Create a new item of the given type.",
    )
    parser_create.add_argument(
        "type", choices=["tag", "dir", "url", "txt", "cmd"], help="Item type."
    )
    parser_create.add_argument("name", help="Tag name, or URL/value of the item.")
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
    # the parser for the "search" command
    parser_search = subparsers.add_parser(
        "search", parents=[common], aliases=["s", "show", "select"], help="Search items by tag."
    )
    parser_search.add_argument(
        "query",
        nargs="+",
        help="Tags to search for. Example: 'A B + C' means items tagged with (A and B) or C.",
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
