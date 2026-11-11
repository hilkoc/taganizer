"""Test case for item_store.
Must run from directory above."""

import unittest
from taganizer import Item
import taganizer.item_store as item_store


class TestItemStore(unittest.TestCase):
    """Test the database interaction. The order of these tests matters."""

    @classmethod
    def setUpClass(cls):
        cls.test_instance = item_store.ItemStore(":memory:")
        cls.test_instance.initialize()

    def test_create(self):
        me = Item(9, "tag", "me")
        la = Item(17, "tag", "tzr")
        rowid = TestItemStore.test_instance.create_item(me)
        self.assertEqual(rowid, 1)
        rowid = TestItemStore.test_instance.create_item(la)
        self.assertEqual(rowid, 2)

    def test_rename(self):
        new_name = "LabelAnything"
        rowcount = TestItemStore.test_instance.rename_item("tzr", new_name)
        self.assertEqual(rowcount, 1)
        item_dict = TestItemStore.test_instance.select_all()
        self.assertEqual(len(item_dict), 2)
        self.assertEqual(item_dict[2].uid, 2)
        self.assertEqual(item_dict[2].url, new_name)
        self.assertEqual(item_dict[2].typ, "tag")
        rowcount = TestItemStore.test_instance.rename_item("tzr", new_name)
        self.assertEqual(rowcount, 0)

    def test_select_all(self):
        item_dict = TestItemStore.test_instance.select_all()
        self.assertEqual(len(item_dict), 2)
        self.assertEqual(item_dict[1].url, "me")
        self.assertEqual(item_dict[2].url, "LabelAnything")
        self.assertEqual(item_dict[2].uid, 2)
        self.assertEqual(item_dict[2].typ, "tag")

    def test_get_item(self):
        item = TestItemStore.test_instance.get_item("me")
        self.assertIsNotNone(item)
        self.assertEqual(item.url, "me")
        self.assertEqual(item.typ, "tag")
        self.assertIsNone(TestItemStore.test_instance.get_item("does-not-exist"))

    @staticmethod
    def helper_create_tags(*tag_list):
        for name in tag_list:
            t = Item(0, "tag", name)
            TestItemStore.test_instance.create_item(t)

    def test_zadd_parent_tag(self):
        """Test that an item can have multiple parents and multiple children."""
        TestItemStore.helper_create_tags("A", "B", "C", "ab", "cc", "abc", "aab")
        TestItemStore.test_instance.associate("ab", "A")
        TestItemStore.test_instance.associate("ab", "B")
        TestItemStore.test_instance.associate("cc", "C")
        TestItemStore.test_instance.associate("abc", "A")
        TestItemStore.test_instance.associate("abc", "B")
        TestItemStore.test_instance.associate("abc", "C")

        # Verify the associations were created
        all_assocs = TestItemStore.test_instance.all_associations()
        self.assertEqual(len(all_assocs), 6)

        all_items = TestItemStore.test_instance.select_all()
        # Verify that 'ab' has two children: 'A' and 'B'
        ab = next((item for item in all_items.values() if item.url == "ab"), None)
        # Verify that 'abc' has three children: 'A', 'B', and 'C'
        abc = next((item for item in all_items.values() if item.url == "abc"), None)
        # # Verify that 'cc' has only 'C' as a child
        cc = next((item for item in all_items.values() if item.url == "cc"), None)
        ab_children = {
            all_items[child_id].url for parent_id, child_id in all_assocs if parent_id == ab.uid
        }
        abc_children = {
            all_items[child_id].url for parent_id, child_id in all_assocs if parent_id == abc.uid
        }
        cc_children = {
            all_items[child_id].url for parent_id, child_id in all_assocs if parent_id == cc.uid
        }
        self.assertEqual(ab_children, {"A", "B"})
        self.assertEqual(abc_children, {"A", "B", "C"})
        self.assertEqual(cc_children, {"C"})

    # Fixture created above: ab -> {A, B}, abc -> {A, B, C}, cc -> {C}.
    # Search terms are ancestors; results are their (matching) descendents.
    def _search_urls(self, query):
        item_dict, _ = TestItemStore.test_instance.search(query)
        return {item.url for item in item_dict.values()}

    def test_zsearch_intersection(self):
        """A single group returns the intersection of its tags' descendents."""
        self.assertEqual(self._search_urls([["abc"]]), {"A", "B", "C"})
        # Intersecting with ab drops C, which is not a descendent of ab.
        self.assertEqual(self._search_urls([["ab", "abc"]]), {"A", "B"})

    def test_zsearch_union_of_intersections(self):
        """Multiple groups return the union of each group's intersection."""
        # (ab) ∪ (cc) = {A, B} ∪ {C}
        self.assertEqual(self._search_urls([["ab"], ["cc"]]), {"A", "B", "C"})
        # (ab ∩ abc) ∪ (cc) = {A, B} ∪ {C}
        self.assertEqual(self._search_urls([["ab", "abc"], ["cc"]]), {"A", "B", "C"})
        # (ab ∩ cc) ∪ (abc) = {} ∪ {A, B, C}
        self.assertEqual(self._search_urls([["ab", "cc"], ["abc"]]), {"A", "B", "C"})

    def test_zsearch_flat_list_compat(self):
        """A flat list of tags is treated as a single intersection group."""
        self.assertEqual(self._search_urls(["ab", "abc"]), {"A", "B"})

    def test_zz_associate_requires_tag_parent(self):
        """associate refuses a parent that is missing or not a TAG."""
        TestItemStore.test_instance.create_item(Item(0, "url", "https://ex.com"))
        with self.assertRaises(ValueError):  # parent is a URL, not a TAG
            TestItemStore.test_instance.associate("https://ex.com", "A")
        with self.assertRaises(ValueError):  # parent does not exist
            TestItemStore.test_instance.associate("no-such-tag", "A")

    def test_zz_associate_requires_existing_child(self):
        """associate refuses a child that does not exist instead of reporting success."""
        before = len(TestItemStore.test_instance.all_associations())
        with self.assertRaises(ValueError):
            TestItemStore.test_instance.associate("ab", "no-such-item")
        self.assertEqual(len(TestItemStore.test_instance.all_associations()), before)

    def test_zz_parents(self):
        """parents returns the direct parents of an item, ordered by url."""
        urls = [item.url for item in TestItemStore.test_instance.parents("A")]
        self.assertEqual(urls, ["ab", "abc"])
        self.assertEqual(TestItemStore.test_instance.parents("ab"), [])
        self.assertEqual(TestItemStore.test_instance.parents("no-such-item"), [])

    def test_zzz_dissociate(self):
        """dissociate removes one link and reports how many rows it removed."""
        self.assertEqual(TestItemStore.test_instance.dissociate("cc", "C"), 1)
        self.assertEqual(self._search_urls([["cc"]]), set())
        self.assertEqual(TestItemStore.test_instance.dissociate("cc", "C"), 0)
        self.assertEqual(TestItemStore.test_instance.dissociate("no-such-tag", "C"), 0)


class TestSqlItemStoreSearch(unittest.TestCase):
    """Verify SqlItemStore's single-query search matches the Python union."""

    @classmethod
    def setUpClass(cls):
        cls.store = item_store.SqlItemStore(":memory:")
        cls.store.initialize()
        # Same fixture as TestItemStore: ab -> {A, B}, abc -> {A, B, C}, cc -> {C}.
        for name in ("A", "B", "C", "ab", "cc", "abc"):
            cls.store.create_item(Item(0, "tag", name))
        cls.store.associate("ab", "A")
        cls.store.associate("ab", "B")
        cls.store.associate("cc", "C")
        cls.store.associate("abc", "A")
        cls.store.associate("abc", "B")
        cls.store.associate("abc", "C")

    def _search_urls(self, query):
        item_dict, _ = TestSqlItemStoreSearch.store.search(query)
        return {item.url for item in item_dict.values()}

    def test_intersection(self):
        self.assertEqual(self._search_urls([["abc"]]), {"A", "B", "C"})
        self.assertEqual(self._search_urls([["ab", "abc"]]), {"A", "B"})

    def test_union_of_intersections(self):
        self.assertEqual(self._search_urls([["ab"], ["cc"]]), {"A", "B", "C"})
        self.assertEqual(self._search_urls([["ab", "abc"], ["cc"]]), {"A", "B", "C"})
        self.assertEqual(self._search_urls([["ab", "cc"], ["abc"]]), {"A", "B", "C"})

    def test_flat_list_compat(self):
        self.assertEqual(self._search_urls(["ab", "abc"]), {"A", "B"})

    def test_empty_query(self):
        self.assertEqual(self._search_urls([]), set())


class TestItemStoreLifecycle(unittest.TestCase):
    """Test connection lifecycle: context manager and single-connection invariant."""

    def test_context_manager_closes_connection(self):
        with item_store.ItemStore(":memory:") as store:
            store.initialize()
            self.assertIsNotNone(store.con)
        # Leaving the with-block closes and clears the connection.
        self.assertIsNone(store.con)

    def test_close_is_idempotent(self):
        store = item_store.ItemStore(":memory:")
        store.close()
        store.close()  # second call must not raise
        self.assertIsNone(store.con)

    def test_reconnect_closes_previous_connection(self):
        store = item_store.ItemStore(":memory:")
        first = store.con
        store.connect_db(":memory:")
        # A fresh connection replaces the old one; only one is open at a time.
        self.assertIsNotNone(store.con)
        self.assertIsNot(store.con, first)


if __name__ == "__main__":
    unittest.main()
