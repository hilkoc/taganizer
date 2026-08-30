"""Anything is an Item. Files, folder, tags, urls, pieces of text."""

from typing import Optional, Iterable, Callable, Generator, Any


class ItemError(Exception):
    """Custom error for Item operations.

    Raised when invalid operations are attempted, e.g. making an item a
    descendant of itself.
    """


class Item(object):
    """Class to represent a taggable item.

    Attributes:
        uid: Unique integer identifier from the storage backend.
        typ: Type string, e.g. 'TAG', 'DIR', 'URL', 'TXT', 'CMD'.
        url: The visible value of the item (tag name, URL, text, ...).
        parents: Optional mapping of parent uid to Item.
        children: Optional mapping of child uid to Item.
    """

    def __init__(self, uid: int, typ: str, url: str) -> None:
        """Initialize an Item.

        Args:
            uid: Numeric id for the item.
            typ: Type/category of the item.
            url: String value representing the item.
        """
        self.uid: int = uid
        self.typ: str = typ
        self.url: str = url
        self.parents: Optional[dict[int, Item]] = None
        self.children: Optional[dict[int, Item]] = None

    def __str__(self) -> str:
        """Return a human-friendly representation: "<type>: <url>"."""
        return self.typ + ": " + self.url

    def __repr__(self) -> str:
        """Return a concise constructor-like representation."""
        return "Item('%(typ)s', '%(url)s')" % ({"typ": self.typ, "url": self.url})

    def __eq__(self, other: object) -> bool:
        """Equality compares items by their url.

        Non-Item objects always compare unequal.
        """
        if not isinstance(other, Item):
            return False
        return self.url == other.url

    def _add_parent(self, parent: Item) -> None:
        """Add a parent Item to this item's parent mapping.

        Args:
            parent: Item instance to add as a parent.
        """
        if self.parents is None:
            self.parents = dict()
        self.parents.setdefault(parent.uid, parent)

    def add_child(self, child: Item) -> None:
        """Create a parent-child relationship with another item.

        Raises:
            ItemError: If the given child is already a descendant of this item.
        """
        # Ensure that a child can never occur as its own ancestor.
        for d, level in self.ancestors():
            if child == d:
                raise ItemError("Given item %s is already a descendent." % child.url)
        if self.children is None:
            self.children = dict()
        self.children.setdefault(child.uid, child)
        child._add_parent(self)

    def parent_items(self) -> Optional[Iterable[Item]]:
        """Return an iterable of parent Items, or None if there are no parents."""
        return self.parents if self.parents is None else self.parents.values()

    def child_items(self) -> Optional[Iterable[Item]]:
        """Return an iterable of child Items, or None if there are no children."""
        return self.children if self.children is None else self.children.values()

    def _traverse(
        self,
        next_items: Callable[[Item], Optional[Iterable[Item]]],
        func: Callable[..., None],
        *func_args: Any,
    ) -> None:
        """Traverse items breadth- or depth-first applying func to each visited item.

        Args:
            next_items: Function that returns the next items for a node (or None).
            func: Callable invoked as func(item, level, *func_args).
            func_args: Additional positional args forwarded to func.
        """
        items: list[tuple[Item, int]] = [(self, 0)]
        while len(items) > 0:
            current, level = items.pop()
            func(current, level, *func_args)
            next_item_list = next_items(current)
            if next_item_list is not None:
                level += 1
                items.extend([(x, level) for x in next_item_list])  # Extend the list.

    def traverse_parents(self, func: Callable[..., None], *func_args: Any) -> None:
        """Traverse parent nodes applying func to each visited item."""
        self._traverse(Item.parent_items, func, *func_args)

    def traverse_children(self, func: Callable[..., None], *func_args: Any) -> None:
        """Traverse child nodes applying func to each visited item."""
        self._traverse(Item.child_items, func, *func_args)

    def _recurse(
        self,
        next_items: Callable[[Item], Optional[Iterable[Item]]],
        func: Callable[..., None],
        *func_args: Any,
    ) -> None:
        """Recursively apply func to this item and its reachable neighbors.

        Args:
            next_items: Function returning neighbors for a node.
            func: Callable invoked as func(item, level, *func_args).
            func_args: Extra args forwarded to func.
        """
        level = 0

        def recurse(item: Item, level: int, func: Callable[..., None], *func_args: Any) -> None:
            func(item, level, *func_args)
            next_item_list = next_items(item)
            if next_item_list is not None:
                level += 1
                for next_item in next_item_list:
                    recurse(next_item, level, func, *func_args)

        recurse(self, level, func, *func_args)

    def recurse_parents(self, func: Callable[..., None], *func_args: Any) -> None:
        """Recursively apply func to this item and its ancestors."""
        self._recurse(Item.parent_items, func, *func_args)

    def recurse_children(self, func: Callable[..., None], *func_args: Any) -> None:
        """Recursively apply func to this item and its descendants."""
        self._recurse(Item.child_items, func, *func_args)

    def descendents(self, width_first: bool = True) -> Generator[tuple[Item, int], None, None]:
        """Yield (item, level) for this item and all its descendants.

        Args:
            width_first: If True yields in breadth-first order, otherwise depth-first.
        """
        popdex = 0 if width_first else -1
        items: list[tuple[Item, int]] = [(self, 0)]
        while len(items) > 0:
            current, level = items.pop(popdex)
            yield (current, level)
            if current.children is not None:
                level += 1
                items.extend([(child, level) for child in current.children.values()])

    def ancestors(self, width_first: bool = True) -> Generator[tuple[Item, int], None, None]:
        """Yield (item, level) for this item and all its ancestors.

        Args:
            width_first: If True yields in breadth-first order, otherwise depth-first.
        """
        popdex = 0 if width_first else -1
        items: list[tuple[Item, int]] = [(self, 0)]
        while len(items) > 0:
            current, level = items.pop(popdex)
            yield (current, level)
            if current.parents is not None:
                level -= 1
                items.extend([(parent, level) for parent in current.parents.values()])


def show_item(item: Item, level: int, indent: str) -> None:
    """Helper to print an item with indentation.

    Args:
        item: Item to display.
        level: Depth level used to compute indentation.
        indent: String used for one level of indentation.
    """
    temp = level * indent
    print(temp, str(item), sep="")


def just_print(item: Item, level: int) -> None:
    """Simple printer that prints the item object."""
    print(item)


def recurse_children(item: Item, func: Callable[..., None], *func_args: Any) -> None:
    """Apply func to item and recursively to all its children.

    Args:
        item: Root Item to start recursion from.
        func: Callable invoked as func(item, level, *func_args).
        func_args: Additional arguments forwarded to func.
    """
    level = 0

    def recurse(item: Item, level: int, func: Callable[..., None], *func_args: Any) -> None:
        func(item, level, *func_args)
        if item.children is not None:
            level += 1
            for child in item.children.values():
                recurse(child, level, func, *func_args)

    recurse(item, level, func, *func_args)


def traverse_down2(item: Item, func: Callable[..., None], *func_args: Any) -> None:
    """Non-recursive, width-first traversal applying func to each visited item."""
    items: list[tuple[Item, int]] = [(item, 0)]
    while len(items) > 0:
        current, level = items.pop()
        func(current, level, *func_args)
        if current.children is not None:
            level += 1
            items[0:0] = [
                (child, level) for child in current.children.values()
            ]  # Extend at the beginning of the list.


def main() -> None:
    """Example usage of the Item class and traversal helpers."""
    me = Item(1, "tag", "me")
    dad = Item(2, "tag", "dad")
    mom = Item(3, "tag", "mom")
    steven = Item(4, "tag", "steven")
    tzr = Item(5, "tag", "tzr")

    dad.add_child(me)
    mom.add_child(me)
    dad.add_child(steven)
    mom.add_child(steven)
    me.add_child(tzr)

    recurse_children(dad, show_item, "  ")
    print()
    for item, level in dad.descendents(False):
        show_item(item, level, ",,,,")


if __name__ == "__main__":
    main()
