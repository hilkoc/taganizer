#!/usr/bin/python3
""" The main entry point for la. Requires python3"""

import argparse
from item import Item
import item_store


def output(*args, **kwargs):
    print(*args, **kwargs)


def show_item(item, level, indent):
    temp = level * indent
    output(temp, str(item), sep='')


def init(args):
    output('initializing database')
    result = item_store.initialize_db(item_store.db())
    output(result)


def export(args):
    output('exporting database')
    dump_file = args.dump_file
    result = item_store.db().dump_db(dump_file)
    output(result)


def build_tree(item_dict, pairs_list):
    for pair in pairs_list:
        p = item_dict[pair[0]]
        c = item_dict[pair[1]]
        p.add_child(c)

def list_items(args):
    item_dict = item_store.db().select_all()
    if not args.tree:
        for x in item_dict.values():
            output(x)
    else:
        pairs_list = item_store.db().all_associations()
        build_tree(item_dict, pairs_list)
        for root in item_dict.values():
            if root.parents is None:
                root.traverse_children(show_item, '  ')


def create(args):
    item = Item(-1, args.type.upper(), args.name)
    rowid = item_store.db().create_item(item)
    output('created item with id: %i' % rowid)


def rename(args):
    old_name = args.old
    new_name = args.new
    rowcount = item_store.db().rename_item(old_name, new_name)
    output('renamed %i item' % rowcount)


def delete(args):
    rowcount = item_store.db().delete_item(args.name)
    output('delted %i item' % rowcount)


def add_association(args):
    rowcount = item_store.db().associate(args.parent_name, args.child_name)
    output('associated %i item' % rowcount)


def search(args):
    query = args.query
    output(query)
    item_dict, pairs_list = item_store.db().search(query)
    if False:
        for x in item_dict.values():
            output(x)
    else:
        build_tree(item_dict, pairs_list)
        for root in item_dict.values():
            if root.parents is None:
                root.traverse_children(show_item, '  ')

def main(main_args=None):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command_name', title='subcommands', description='valid subcommands', help='sub-command help')
    # the parser for the "init" command
    parser_init = subparsers.add_parser('init', help='Initializes the sqlite database.')
    parser_init.set_defaults(func=init)
    # the parser for the "export" command
    parser_export = subparsers.add_parser('export', help='Export the sqlite database to a file.')
    parser_export.add_argument('dump_file', nargs='?', type=argparse.FileType('w'), default='la_export.sql', help='The file to export to')
    parser_export.set_defaults(func=export)
    # the parser for the "ls" command
    parser_ls = subparsers.add_parser('ls', aliases=['list'], help='List all tags.')
    parser_ls.add_argument('-t', '--tree', help='list in tree structure.', action='store_true')
    parser_ls.set_defaults(func=list_items)
    # the parser for the "create" command
    parser_create = subparsers.add_parser('create', aliases=['cr', 'add'], help='create [type] [name].')
    parser_create.add_argument('type', choices=['tag', 'dir', 'url', 'txt', 'cmd'], help='the type of the item. Must be one of [TAG, DIR, URL, TXT, CMD]')
    parser_create.add_argument('name', help='the name of tag or url of the item')
    parser_create.set_defaults(func=create)
    # the parser for the "rename" command
    parser_rename = subparsers.add_parser('rename', aliases=['mv'], help='rename [old] [new]. The type of items cannot be changed.')
    parser_rename.add_argument('old', help='the current name or url of the item')
    parser_rename.add_argument('new', help='the new name or url of the item')
    # the parser for the "delete" command
    parser_delete = subparsers.add_parser('delete', aliases=['rm', 'del'], help='delete [name].')
    parser_delete.add_argument('name', help='Deltes the item with given name and all its descendents')
    parser_delete.set_defaults(func=delete)
    # the parser for the "rename" command
    parser_rename = subparsers.add_parser('tag', aliases=['label'], help='tag [child] [parent]. Labels child with parent. parent must be a tag.')
    parser_rename.add_argument('child_name', help='the child name or url')
    parser_rename.add_argument('parent_name', help='the parent name or url')
    parser_rename.set_defaults(func=add_association)
    # the parser for the "search" command
    parser_search = subparsers.add_parser('search', aliases=['s', 'show', 'select'], help='Search for items.')
    parser_search.add_argument('query', nargs='+', help='The labels to search for.')
    parser_search.set_defaults(func=search)

    args = parser.parse_args(main_args)

    if args.__contains__('func'):
        # output('running %s' % args.command_name)
        args.func(args)
    else:
        parser.print_help()





if __name__ == '__main__':
    from sys import argv
    main(argv[1:])
