#!/usr/bin/python3
""" The main entry point for la. Requires python3"""

import argparse
from item import Item
import item_store

def output(s):
    print(s)


def init(args):
    output('initializing database')
    result = item_store.initialize_db()
    output(result)


def list(args):
    item_list = item_store.db().select_all()
    for x in item_list:
        output(x)


def create(args):
    item = Item(-1, args.type, args.name)
    rowid = item_store.db().create_item(item)
    output('created item with id: %i' % rowid)


def rename(args):
    old_name = args.old
    new_name = args.new
    rowcount = item_store.db().rename_item(old_name, new_name)
    output('renamed %i item' % rowcount)


def main(main_args=None):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command_name', title='subcommands', description='valid subcommands', help='sub-command help')
    # the parser for the "init" command
    parser_init = subparsers.add_parser('init', help='Initializes the sqlite database')
    parser_init.set_defaults(func=init)
    # the parser for the "ls" command
    parser_ls = subparsers.add_parser('ls', aliases=['list'], help='list all tags')
    parser_ls.set_defaults(func=list)
    # the parser for the "create" command
    parser_create = subparsers.add_parser('create', aliases=['cr', 'add'], help='create [type] [name]')
    parser_create.add_argument('type', help='the type of the item')
    parser_create.add_argument('name', help='the name of tag or url of the item')
    parser_create.set_defaults(func=create)

    # the parser for the "rename" command
    parser_rename = subparsers.add_parser('rename', aliases=['mv'], help='rename [old] [new]. The type of items cannot be changed.')
    parser_rename.add_argument('old', help='the current name or url of the item')
    parser_rename.add_argument('new', help='the new name or url of the item')
    parser_rename.set_defaults(func=rename)

    args = parser.parse_args(main_args)

    if args.__contains__('func'):
        # output('running %s' % args.command_name)
        args.func(args)
    else:
        parser.print_help()





if __name__ == '__main__':
    from sys import argv
    main(argv[1:])
