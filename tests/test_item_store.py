""" Test case for item_store.
    Must run from directory above. """
import unittest
from item import Item
import item_store


class TestStringMethods(unittest.TestCase):

    def skip_test_split(self):
        s = 'hello world'
        self.assertEqual(s.split(), ['hello', 'world'])
        # check that s.split fails when the separator is not a string
        with self.assertRaises(TypeError):
          s.split(2)


class TestItemStore(unittest.TestCase):
    """ Test the database interaction. The order of these tests matters."""

    @classmethod
    def setUpClass(cls):
      db_name = ':memory:'
      item_store.db_name = db_name
      cls.test_instance = item_store.ItemStore()
      cls.test_instance.connect_db(db_name)
      item_store.initialize_db(cls.test_instance)

    def test_create(self):
      me = Item(9, 'tag','me')
      la = Item(17, 'tag', 'la')
      rowid = TestItemStore.test_instance.create_item(me)
      self.assertEqual(rowid, 1)
      rowid = TestItemStore.test_instance.create_item(la)
      self.assertEqual(rowid, 2)

    def skiptest_rename(self):
      new_name = 'LabelAnything'
      rowcount = TestItemStore.test_instance.rename_item('la', new_name)
      self.assertEqual(rowcount, 1)
      item_list = TestItemStore.test_instance.select_all()
      self.assertEqual(len(item_list), 2)
      self.assertEqual(item_list[1].uid, 2)
      self.assertEqual(item_list[1].url, new_name)
      self.assertEqual(item_list[1].typ, 'tag')
      rowcount = TestItemStore.test_instance.rename_item('la', new_name)
      self.assertEqual(rowcount, 0)

    def skiptest_select_all(self):
      item_list = TestItemStore.test_instance.select_all()
      self.assertEqual(len(item_list), 2)
    #   print(str(type(item_list[0])))
    #   self.assertEqual(type(item_list[0]), Item)
      self.assertEqual(item_list[0].url, 'me')
      self.assertEqual(item_list[1].url, 'LabelAnything')
      self.assertEqual(item_list[1].uid, 2)
      self.assertEqual(item_list[1].typ, 'tag')

    def helper_create_tags(*tag_list):
      for name in tag_list:
          t = Item(0, 'tag', name)
          TestItemStore.test_instance.create_item(t)

    def skiptest_zadd_parent_tag(self):
        """ Test that an item can have multiple parents and multiple children. """
        # helper_create_tags('A', 'B', 'C', 'ab', 'cc', 'abc', 'aab')
        TestItemStore.helper_create_tags('A', 'B', 'ab')
        TestItemStore.test_instance.associate('ab', 'A')
        TestItemStore.test_instance.associate('ab', 'B')


if __name__ == '__main__':
    unittest.main()
