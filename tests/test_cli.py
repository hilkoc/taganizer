"""Test case for the tzr command-line interface."""

import os
import tempfile
import unittest

from taganizer import cli, item_store


class TestSplitGroups(unittest.TestCase):
    """Test the '+' group splitting used by the search command."""

    def test_single_group(self):
        self.assertEqual(cli.split_groups(["A", "B"]), [["A", "B"]])

    def test_two_groups(self):
        self.assertEqual(cli.split_groups(["A", "B", "+", "C"]), [["A", "B"], ["C"]])

    def test_ignores_empty_groups(self):
        # Leading, trailing and doubled '+' must not create empty groups.
        self.assertEqual(cli.split_groups(["+", "A", "+", "+", "B", "+"]), [["A"], ["B"]])

    def test_empty(self):
        self.assertEqual(cli.split_groups([]), [])


class TestCliDispatch(unittest.TestCase):
    """End-to-end dispatch tests against a temporary database file."""

    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.unlink(self.db_path)  # start from a fresh, non-existent path
        cli.main(["--db", self.db_path, "init"])

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def _urls(self):
        with item_store.ItemStore(self.db_path) as store:
            return {item.url for item in store.select_all().values()}

    def test_rename_dispatches(self):
        """Regression: the rename subcommand must actually run (had no func default)."""
        cli.main(["--db", self.db_path, "create", "tag", "A"])
        cli.main(["--db", self.db_path, "rename", "A", "B"])
        self.assertEqual(self._urls(), {"B"})

    def test_db_flag_after_subcommand(self):
        """--db must work both before and after the subcommand."""
        cli.main(["create", "tag", "X", "--db", self.db_path])
        self.assertEqual(self._urls(), {"X"})


if __name__ == "__main__":
    unittest.main()
