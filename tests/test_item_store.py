''' Test case for item_store.
    Must run from directory above. '''
import unittest
from item import Item
import item_store


class TestStringMethods(unittest.TestCase):

  def test_upper(self):
      self.assertEqual('foo'.upper(), 'FOO')

  def test_isupper(self):
      self.assertTrue('FOO'.isupper())
      self.assertFalse('Foo'.isupper())

  def test_split(self):
      s = 'hello world'
      self.assertEqual(s.split(), ['hello', 'world'])
      # check that s.split fails when the separator is not a string
      with self.assertRaises(TypeError):
          s.split(2)


class TestItemStore(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
      item_store.db_name = ':memory:'
      item_store.initialize_db()

  def test_insert(self):
      me = Item(9, 'tag','me')
      la = Item(17, 'tag', 'la')
      rowid = item_store.db().create_item(me)
      self.assertEqual(rowid, 1)
      rowid = item_store.db().create_item(la)
      self.assertEqual(rowid, 2)

  def test_select_all(self):
      item_list = item_store.db().select_all()
      self.assertEqual( len(item_list), 2)
      self.assertEqual( type(item_list[0]), Item)
      self.assertEqual( item_list[1].uid, 2)
      self.assertEqual( item_list[0].url, 'me')
      self.assertEqual( item_list[1].typ, 'tag')

if __name__ == '__main__':
    unittest.main()
