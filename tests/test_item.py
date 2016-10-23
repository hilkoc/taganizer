""" Test case for item_store.
    Must run from directory above. """
import unittest
from item import Item, ItemError


class TestItem(unittest.TestCase):
    """ Test various methods on Item class."""

    def test_hierarchy(self):
        me = Item(1, 'tag','me')
        la = Item(2, 'tag', 'la')
        me2 = Item(3, 'tag','me')
        self.assertTrue(me == me2)
        self.assertEqual(me2, me)
        me.add_child(la)
        self.assertEqual(list(me.child_items()),[la])
        self.assertEqual([x for x in la.parent_items()],[me])

    def test_descendents(self):
        a = Item(1, 'tag', 'a')
        b = Item(2, 'tag', 'b')
        c = Item(3, 'tag', 'c')
        d = Item(4, 'tag', 'd')
        a.add_child(b)
        a.add_child(c)
        c.add_child(d)
        width_first_items = [a,b,c,d]
        depth_first_items = [(a,0),(c,1),(d,2),(b,1)]
        actual_width_first_items = [x[0] for x in a.descendents()]
        actual_depth_first_items = list(a.descendents(width_first=False))
        self.assertEqual(actual_width_first_items, width_first_items)
        self.assertEqual(actual_depth_first_items, depth_first_items)
        # test that c and d are descendents of a. and can break on that.
        searched_descendents = list()
        for item,level in a.descendents():
            if item == b:
                break
            searched_descendents.append(item)
        self.assertTrue(len(searched_descendents) < 4)
        # test that c is a descendents of a. and can break on that.
        searched_descendents = list()
        for item,level in a.descendents():
            if item == c:
                break
            searched_descendents.append(item)
        self.assertTrue(len(searched_descendents) < 4)

    def test_no_cycles(self):
        """ Assert that an item can not be added as its own descendent. """
        a = Item(1, 'tag', 'a')
        b = Item(2, 'tag', 'b')
        c = Item(3, 'tag', 'c')
        d = Item(4, 'tag', 'd')
        a.add_child(b)
        a.add_child(c)
        c.add_child(d)
        self.assertRaises(ItemError, lambda: a.add_child(a))
        self.assertRaises(ItemError, b.add_child, a)
        self.assertRaises(ItemError, d.add_child, a)

if __name__ == '__main__':
    unittest.main()
