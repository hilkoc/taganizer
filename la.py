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
    result = item_store.initialize_db()
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
        output('displaya as tree')
        pairs_list = item_store.db().all_associations()
        # build a tree
        build_tree(item_dict, pairs_list)
        root = None  # take the fist
        for x in item_dict.values():
            root = x
            root.traverse_children(show_item, '...')


def create(args):
    item = Item(-1, args.type.upper(), args.name)
    rowid = item_store.db().create_item(item)
    output('created item with id: %i' % rowid)


def rename(args):
    old_name = args.old
    new_name = args.new
    rowcount = item_store.db().rename_item(old_name, new_name)
    output('renamed %i item' % rowcount)

def add_association(args):
    rowcount = item_store.db().associate(args.parent_name, args.child_name)
    output('associated %i item' % rowcount)


def main(main_args=None):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command_name', title='subcommands', description='valid subcommands', help='sub-command help')
    # the parser for the "init" command
    parser_init = subparsers.add_parser('init', help='Initializes the sqlite database.')
    parser_init.set_defaults(func=init)
    # the parser for the "ls" command
    parser_ls = subparsers.add_parser('ls', aliases=['list'], help='List all tags.')
    parser_ls.add_argument('-t', '--tree', help='list in tree structure.', action='store_true')
    parser_ls.set_defaults(func=list_items)
    # the parser for the "create" command
    parser_create = subparsers.add_parser('create', aliases=['cr', 'add'], help='create [type] [name].')
    parser_create.add_argument('type', choices=['tag', 'url', 'txt', 'cmd'], help='the type of the item. Must be one of [TAG, URL, TXT, CMD]')
    parser_create.add_argument('name', help='the name of tag or url of the item')
    parser_create.set_defaults(func=create)
    # the parser for the "rename" command
    parser_rename = subparsers.add_parser('rename', aliases=['mv'], help='rename [old] [new]. The type of items cannot be changed.')
    parser_rename.add_argument('old', help='the current name or url of the item')
    parser_rename.add_argument('new', help='the new name or url of the item')
    parser_rename.set_defaults(func=rename)
    # the parser for the "rename" command
    parser_rename = subparsers.add_parser('tag', aliases=['label'], help='tag [child] [parent]. Labels child with parent. parent must be a tag.')
    parser_rename.add_argument('child_name', help='the child name or url')
    parser_rename.add_argument('parent_name', help='the parent name or url')
    parser_rename.set_defaults(func=add_association)

    args = parser.parse_args(main_args)

    if args.__contains__('func'):
        # output('running %s' % args.command_name)
        args.func(args)
    else:
        parser.print_help()





if __name__ == '__main__':
    from sys import argv
    main(argv[1:])
