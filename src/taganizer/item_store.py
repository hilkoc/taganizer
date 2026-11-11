#!/usr/bin/python
from typing import Optional, TextIO
import logging
from .item import Item
import sqlite3 as sqlite

# Set up logging for the item store
logger = logging.getLogger(__name__)


class ItemStore(object):
    """A thin SQLite-backed store for Item objects and their associations.

    The class manages a sqlite3.Connection on self.con and provides CRUD
    operations for items and their parent/child associations.
    """

    def __init__(self, db_name: str) -> None:
        """Create an ItemStore and open its database connection.

        The store owns a single connection for its lifetime; use it as a
        context manager (``with ItemStore(path) as store: ...``) for
        deterministic cleanup.

        Args:
            db_name: Path to the SQLite database file (e.g. ':memory:').
        """
        self.con: Optional[sqlite.Connection] = None
        self.connect_db(db_name)

    def __enter__(self) -> "ItemStore":
        """Enter the runtime context and return the store itself."""
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Exit the runtime context, closing the connection.

        Returns None so any in-flight exception propagates normally.
        """
        self.close()

    def close(self) -> None:
        """Close the database connection if it is open.

        It is safe to call multiple times.
        """
        if self.con is not None:
            try:
                self.con.close()
                logger.debug("Database connection closed")
            except sqlite.Error as e:
                logger.error("Error closing database connection: %s", e)
            finally:
                self.con = None

    def connect_db(self, db_name: str) -> None:
        """Connect to the SQLite database and enable foreign keys.

        Args:
            db_name: Path to the SQLite database file.

        Raises:
            sqlite.Error: If the connection or PRAGMA fails.
            ValueError: If db_name is empty or None.
        """
        if not db_name or not isinstance(db_name, str):
            raise ValueError("db_name must be a non-empty string")

        # Ensure at most one open connection per instance: drop any existing one first.
        self.close()
        self.con = sqlite.connect(db_name)
        # Foreign keys are disabled by default, so we need to turn them on every time.
        self.con.cursor().execute("PRAGMA foreign_keys=ON")
        logger.info("Connected to database: %s", db_name)

    def initialize(self) -> str:
        """Create the schema (items, associations) and the cycle-prevention trigger.

        Uses ``IF NOT EXISTS`` throughout, so it is idempotent and safe to call
        on an already-initialized database.

        Returns:
            Status string indicating initialization result.

        Raises:
            sqlite.Error: If the schema creation fails.
        """
        assert self.con is not None, "Database not connected."
        self.con.execute(
            "CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " url VARCHAR UNIQUE, type VARCHAR) ;"
        )
        self.con.execute(
            "CREATE TABLE IF NOT EXISTS associations ( "
            "parent INTEGER REFERENCES items (id) ON DELETE CASCADE , "
            "child INTEGER REFERENCES items (id) ON DELETE CASCADE, "
            "PRIMARY KEY (parent, child) ) WITHOUT ROWID ; "
        )
        cr_trig_no_cycles = (
            "CREATE TRIGGER IF NOT EXISTS nocycles BEFORE INSERT ON associations"
            " BEGIN"
            " WITH RECURSIVE anc(x) AS ("
            "   SELECT NEW.parent"
            "   UNION ALL"
            "   SELECT parent FROM associations, anc WHERE child = x"
            " )"
            ' SELECT RAISE(ABORT, "Item is already a descendent")'
            " FROM anc WHERE EXISTS ("
            " 	SELECT 1 FROM anc WHERE x = NEW.child"
            " );"
            " END;"
        )
        self.con.execute(cr_trig_no_cycles)
        return "database initialized"

    def dump_db(self, dump_file: TextIO) -> str:
        """Write the SQL dump of the connected database to a file-like object.

        Args:
            dump_file: Text IO object to receive the SQL dump.

        Returns:
            A short status string.

        Raises:
            sqlite.Error: If the dump operation fails.
        """
        for line in self.con.iterdump():
            print(line)
            dump_file.write("%s\n" % line)
        return "Database exported"

    # The methods below assume the database is connected
    def create_item(self, item: Item) -> int:
        """Insert a new item and return its row id.

        Args:
            item: Item instance to insert. Uses item.url and item.typ.

        Returns:
            The newly inserted row id (lastrowid).

        Raises:
            sqlite.Error: If the insert operation fails.
        """
        cur = self.con.cursor()
        cur.execute("INSERT INTO items (url, type) VALUES (?, ?)", (item.url, item.typ))
        self.con.commit()
        return cur.lastrowid

    def rename_item(self, old_name: str, new_name: str) -> int:
        """Rename an item url and return the number of rows updated.

        Args:
            old_name: Current item url.
            new_name: New item url.

        Returns:
            Number of rows updated.

        Raises:
            sqlite.Error: If the update operation fails.
        """
        cur = self.con.cursor()
        cur.execute(
            "UPDATE items set url = :new_url WHERE items.url = :old_url ;",
            {"new_url": new_name, "old_url": old_name},
        )
        self.con.commit()
        return cur.rowcount

    def delete_item(self, name: str) -> int:
        """Delete an item by url and return the number of rows deleted.

        Args:
            name: Item url to delete.

        Returns:
            Number of rows deleted.

        Raises:
            sqlite.Error: If the delete operation fails.
        """
        cur = self.con.cursor()
        cur.execute("DELETE from items where url = :name ;", {"name": name})
        self.con.commit()
        return cur.rowcount

    # query = "with p as (select id from items where url = :purl), "
    #     "c as (select id from items where url = :curl ) select p.id, c.id from p, c ;"
    def associate(self, parent_name: str, child_name: str) -> bool:
        """Create an association between two items identified by url.

        The parent is the tag: it must be an existing item of type ``TAG``.
        This guards against accidentally reversed arguments (which would tag an
        item under a non-tag and break searches).

        Args:
            parent_name: URL of the parent item (must be a TAG).
            child_name: URL of the child item.

        Returns:
            True on success.

        Raises:
            ValueError: If parent_name is missing or is not a TAG, or if
                child_name does not exist.
            sqlite.Error: If the association creation fails.
        """
        parent = self.get_item(parent_name)
        if parent is None or parent.typ.upper() != "TAG":
            found = "no such item" if parent is None else parent.typ
            raise ValueError("parent %r must be a TAG, but is %s" % (parent_name, found))
        if self.get_item(child_name) is None:
            # Without this check the INSERT ... SELECT below would insert zero rows
            # and the call would report success for an item that does not exist.
            raise ValueError("no such item %r" % child_name)
        insert_select = (
            "with p as (select id from items where url = :purl), "
            "c as (select id from items where url = :curl ) "
            "INSERT INTO associations (parent, child) select p.id, c.id from p, c ;"
        )
        cur = self.con.cursor()
        cur.execute(insert_select, {"purl": parent_name, "curl": child_name})
        self.con.commit()
        return True

    def dissociate(self, parent_name: str, child_name: str) -> int:
        """Remove the association between two items identified by url.

        Args:
            parent_name: URL of the parent item (the tag).
            child_name: URL of the child item.

        Returns:
            Number of associations removed (0 if the items were not associated).

        Raises:
            sqlite.Error: If the delete operation fails.
        """
        cur = self.con.cursor()
        cur.execute(
            "DELETE FROM associations "
            "WHERE parent = (select id from items where url = :purl) "
            "AND child = (select id from items where url = :curl) ;",
            {"purl": parent_name, "curl": child_name},
        )
        self.con.commit()
        return cur.rowcount

    def parents(self, name: str) -> list[Item]:
        """Return the items directly associated as parents (tags) of an item.

        Only direct parents are returned, not further ancestors.

        Args:
            name: URL of the item whose tags are wanted.

        Returns:
            List of parent Items ordered by url (empty if there are none, or
            if no item has that url).

        Raises:
            sqlite.Error: If the query fails.
        """
        cur = self.con.cursor()
        cur.execute(
            "SELECT p.id, p.url, p.type FROM items AS p "
            "JOIN associations ON associations.parent = p.id "
            "JOIN items AS c ON associations.child = c.id "
            "WHERE c.url = ? ORDER BY p.url ;",
            (name,),
        )
        return [Item(item_id, item_type, url) for item_id, url, item_type in cur.fetchall()]

    def all_associations(self) -> list[tuple[int, int]]:
        """Return all parent/child associations as a list of (parent, child) tuples.

        Returns:
            A list of (parent_id, child_id) tuples representing stored associations.

        Raises:
            sqlite.Error: If the query fails.
        """
        cur = self.con.cursor()
        cur.execute("SELECT parent, child FROM associations ;")
        result = cur.fetchall()
        return result

    def select_all(self) -> dict[int, Item]:
        """Return a mapping of item id to Item objects for all items in the DB.

        Returns:
            Dict mapping item id (int) to Item instance.

        Raises:
            sqlite.Error: If the query fails.
        """
        cur = self.con.cursor()
        cur.execute("SELECT id, url, type FROM items ;")
        rows = cur.fetchall()
        result: dict[int, Item] = dict()
        for item_id, url, item_type in rows:
            result[item_id] = Item(item_id, item_type, url)
        return result

    def get_item(self, url: str) -> Optional[Item]:
        """Return the Item with the given url, or None if it does not exist.

        Args:
            url: The item url to look up.

        Returns:
            The matching Item, or None if no item has that url.

        Raises:
            sqlite.Error: If the query fails.
        """
        cur = self.con.cursor()
        cur.execute("SELECT id, url, type FROM items WHERE url = ? ;", (url,))
        row = cur.fetchone()
        if row is None:
            return None
        item_id, item_url, item_type = row
        return Item(item_id, item_type, item_url)

    @staticmethod
    def _normalize_groups(query: "list[str] | list[list[str]]") -> list[list[str]]:
        """Normalize a search query into a list of tag groups.

        Accepts either a flat list of tag urls (a single intersection group,
        preserved for backward compatibility) or a list of groups. Empty
        groups are dropped.

        Args:
            query: Either ``['A', 'B']`` (one group) or ``[['A', 'B'], ['C']]``.

        Returns:
            A list of non-empty groups, e.g. ``[['A', 'B'], ['C']]``.
        """
        if query and isinstance(query[0], str):
            query = [query]  # backward compat: flat list is a single group
        return [group for group in query if group]

    def _search_intersection(self, tags: list[str]) -> dict[int, Item]:
        """Return items that are descendents of ALL given tags (intersection).

        Args:
            tags: List of item url strings; the result is the intersection of
                the descendents of each tag.

        Returns:
            Dict mapping item id to Item for the matches.

        Raises:
            sqlite.Error: If the query fails.
        """
        cur = self.con.cursor()
        # Collect every descendent of each tag, labelled with the originating tag url.
        query_descendents = (
            "WITH RECURSIVE descendents(p, c, anc_url) AS ( "
            "  select parent, child, url from ASSOCIATIONS join items ON items.id = parent "
            "  where items.url IN (" + ", ".join(["?"] * len(tags)) + " ) "
            " UNION ALL "
            "  SELECT parent, child, anc_url "
            "  FROM ASSOCIATIONS join descendents ON parent = c ) "
        )

        query_intersect = " SELECT c as child from descendents as d" " WHERE d.anc_url = ? "
        query_matches = " INTERSECT ".join([query_intersect] * len(tags))
        query_items = (
            query_descendents
            + " , matched_ids as ("
            + query_matches
            + ") SELECT items.id, items.url, items.type FROM items JOIN matched_ids ON id = child; "
        )

        item_dict: dict[int, Item] = dict()
        cur.execute(query_items, tags * 2)
        rows = cur.fetchall()
        for item_id, url, item_type in rows:
            item_dict[item_id] = Item(item_id, item_type, url)
        return item_dict

    def search(
        self, query: "list[str] | list[list[str]]"
    ) -> tuple[dict[int, Item], list[tuple[int, int]]]:
        """Search items by url and return matching items and association pairs.

        Each group of tags is resolved to the items that are descendents of
        ALL tags in the group (the intersection). The final result is the
        UNION of every group's intersection, i.e. a union of intersections.

        A flat list of tags is treated as a single group, preserving the
        original intersection-only behaviour.

        Args:
            query: Either a flat list of tag urls (one group) or a list of
                groups, e.g. ``[['A', 'B'], ['C']]`` for ``(A ∩ B) ∪ (C)``.

        Returns:
            A tuple containing:
            - dict mapping item id to Item for matches
            - list of association pairs (currently empty, preserved for API compatibility)

        Raises:
            sqlite.Error: If the query fails.
        """
        groups = self._normalize_groups(query)
        pairs_list: list[tuple[int, int]] = []
        item_dict: dict[int, Item] = dict()
        # Union across groups: dict is keyed by item id, so merging deduplicates.
        for group in groups:
            item_dict.update(self._search_intersection(group))
        return item_dict, pairs_list


class SqlItemStore(ItemStore):
    """ItemStore whose search computes the union of intersections in a single
    SQL statement, rather than unioning per-group results in Python.

    The recursive ``descendents`` CTE is evaluated once and shared by every
    group; each group becomes its own CTE (an INTERSECT of its tags) and the
    groups are combined with UNION.

    SQLite gives all compound set operators (UNION/INTERSECT/EXCEPT) equal,
    left-to-right precedence, so ``A INTERSECT B UNION C INTERSECT D`` would be
    read as ``(((A ∩ B) ∪ C) ∩ D)``. Isolating each group's INTERSECT in its
    own CTE forces the intended ``(A ∩ B) ∪ (C ∩ D)`` grouping.
    """

    def search(
        self, query: "list[str] | list[list[str]]"
    ) -> tuple[dict[int, Item], list[tuple[int, int]]]:
        """Resolve a union of intersections in a single SQL query.

        Args:
            query: Either a flat list of tag urls (one group) or a list of
                groups, e.g. ``[['A', 'B'], ['C']]`` for ``(A ∩ B) ∪ (C)``.

        Returns:
            A tuple of (dict mapping item id to Item, empty pairs list).

        Raises:
            sqlite.Error: If the query fails.
        """
        groups = self._normalize_groups(query)
        pairs_list: list[tuple[int, int]] = []
        if not groups:
            return dict(), pairs_list

        # The tags appear once in the seed IN(...) list and once across the
        # per-group WHERE anc_url = ? clauses, in the same flattened order.
        flat = [tag for group in groups for tag in group]

        query_descendents = (
            "WITH RECURSIVE descendents(p, c, anc_url) AS ( "
            "  select parent, child, url from ASSOCIATIONS join items ON items.id = parent "
            "  where items.url IN (" + ", ".join(["?"] * len(flat)) + " ) "
            " UNION ALL "
            "  SELECT parent, child, anc_url "
            "  FROM ASSOCIATIONS join descendents ON parent = c ) "
        )

        # One CTE per group: the INTERSECT of that group's tags.
        group_ctes = []
        for i, group in enumerate(groups):
            intersect = " INTERSECT ".join(
                ["SELECT c AS child FROM descendents WHERE anc_url = ?"] * len(group)
            )
            group_ctes.append("g%d AS ( %s )" % (i, intersect))

        # Union across the groups.
        union = " UNION ".join("SELECT child FROM g%d" % i for i in range(len(groups)))
        query_items = (
            query_descendents
            + " , "
            + " , ".join(group_ctes)
            + " , matched_ids AS ( "
            + union
            + " ) "
            + "SELECT items.id, items.url, items.type FROM items JOIN matched_ids ON id = child ; "
        )

        item_dict: dict[int, Item] = dict()
        cur = self.con.cursor()
        cur.execute(query_items, flat * 2)
        for item_id, url, item_type in cur.fetchall():
            item_dict[item_id] = Item(item_id, item_type, url)
        return item_dict, pairs_list
