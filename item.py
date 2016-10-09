""" Anything is an Item. Files, folder, tags, urls, pieces of text. """

class Item(object):
    """ Class to represent a taggable item.
    The type can be for example TAG, DIR, URL, TXT, CMD.
    The name is the name is the value of this itemm
    i.e. the tag name, or the url, or the text.
    """
    # _instance_count = 0
    # def _make_unique_id():
    #     Item._instance_count += 1
    #     return Item._instance_count

    def __init__(self, uid, typ, url):
        self.uid = uid
        self.typ = typ
        self.url = url
        self.parents = None
        self.children = None

    def __str__(self):
        return (str(self.uid) + ': ' + self.url)

    def __repr__(self):
        return "Item('%(typ)s', '%(url)s')" % ({'typ': self.typ, 'url': self.url})


    def _add_parent(self, parent):
        if self.parents is None:
            self.parents = dict()
        self.parents.setdefault(parent.uid, parent)

    def add_child(self, child):
        """ TODO ensure that a child can never occur as its own ancenstor."""
        if self.children is None:
            self.children = dict()
        self.children.setdefault(child.uid, child)
        child._add_parent(self)


    def parent_items(self):
        return self.parents if self.parents is None else self.parents.values()

    def child_items(self):
        return self.children if self.children is None else self.children.values()

    def _traverse(self, next_items, func, *func_args):
        """ Traverse all the children, or all the parents, depending on the next_items() function.
            next_items(item) returns a list of items or None if there are no more."""
        items = [self]
        levels = [0]
        while len(items) > 0:
            current = items.pop()
            level = levels.pop()
            func(current, level, *func_args)
            next_item_list = next_items(current)
            if next_item_list is not None:
                level += 1
                items.extend(next_item_list)  # Extend the list.
                levels.extend([level] * len(next_item_list))
            # Do something on the way up

    def traverse_parents(self, func, *func_args):
        self._traverse(Item.parent_items, func, *func_args)

    def traverse_children(self, func, *func_args):
        self._traverse(Item.child_items, func, *func_args)

    def _recurse(self, next_items, func, *func_args):
        """ applies func to the given item and to each of its children.
            func takes at least two parameters: item and level.
            func_args is a list of additional arguments passed to func. """
        level = 0
        def recurse(item, level, func, *func_args):
            func(item, level, *func_args)
            next_item_list = next_items(item)
            if next_item_list is not None:
                level += 1
                for next_item in next_item_list:
                    recurse(next_item, level, func, *func_args)
            # Do something on the way up
        recurse(self, level, func, *func_args)

    def recurse_parents(self, func, *func_args):
        self._recurse(Item.parent_items, func, *func_args)

    def recurse_children(self, func, *func_args):
        self._recurse(Item.child_items, func, *func_args)


def show_item(item, level, indent):
    temp = level * indent
    print(temp, str(item), sep='')

def just_print(item, level):
    print(item)


def recurse_children(item, func, *func_args):
    """ applies func to the given item and to each of its children.
        func takes at least two parameters: item and level.
        func_args is a list of additional arguments passed to func. """
    level = 0
    def recurse(item, level, func, *func_args):
        func(item, level, *func_args)
        if item.children is not None:
            level += 1
            for child in item.children.values():
                recurse(child, level, func, *func_args)
        # Do something on the way up
    recurse(item, level, func, *func_args)


def traverse_down(item, func, *func_args):
    """ Same as recurse_children, but non-recurseive implementation"""
    # Display itself
    # If no children => Done
    # Else => increment level
    #         repeat with next child
    items = [item]
    levels = [0]
    while len(items) > 0:
        current = items.pop()
        level = levels.pop()
        func(current, level, *func_args)
        if current.children is not None:
            children = current.children.values()
            level += 1
            items.extend(children)  # Extend at the the list.
            levels.extend([level] * len(children))
        # Do something on the way up


def traverse_down2(item, func, *func_args):
    """ Same as recurse_children, but non-recurseive implementation"""
    items = [item]
    levels = [0]
    while len(items) > 0:
        current = items.pop(0)
        level = levels.pop(0)
        func(current, level, *func_args)
        if current.children is not None:
            children = current.children.values()
            level += 1
            items[0:0] = children  # Extend at the beginning of the list.
            levels[0:0] = [level] * len(children)


def main():
    me = Item(1, 'tag','me')
    dad = Item(2, 'tag', 'dad')
    mom = Item(3, 'tag', 'mom')
    steven = Item(4, 'tag', 'steven')
    la = Item(5, 'tag', 'la')

    dad.add_child(me)
    mom.add_child(me)
    dad.add_child(steven)
    mom.add_child(steven)
    me.add_child(la)


    recurse_children(dad, show_item, '  ')
    #print(dad.children)
    #print(me.children)
    traverse_down2(mom, show_item, '..')
    print()
    traverse_down(mom, show_item, '**')
    me.traverse_parents(show_item, '...')
    me.traverse_children(show_item, '...')
    print()
    print('some recursion')
    steven.recurse_parents(show_item, '##')
    mom.recurse_children(show_item, '##')

if __name__ == '__main__':
    main()
