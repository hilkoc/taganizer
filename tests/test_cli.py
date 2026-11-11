"""Test case for the tzr command-line interface."""

import contextlib
import io
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

    def _run(self, *argv):
        """Run tzr against the temporary database; return (status, stdout, stderr)."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            status = cli.main(["--db", self.db_path] + list(argv))
        return status, out.getvalue(), err.getvalue()

    def _tags_of(self, name):
        with item_store.ItemStore(self.db_path) as store:
            return [item.url for item in store.parents(name)]

    def test_create_file_type(self):
        status, _, _ = self._run("create", "file", "/tmp/note.md")
        self.assertEqual(status, 0)
        with item_store.ItemStore(self.db_path) as store:
            self.assertEqual(store.get_item("/tmp/note.md").typ, "FILE")

    def test_create_with_tags(self):
        self._run("create", "tag", "A")
        self._run("create", "tag", "B")
        status, _, _ = self._run("create", "file", "/tmp/note.md", "--tag", "A", "--tag", "B")
        self.assertEqual(status, 0)
        self.assertEqual(self._tags_of("/tmp/note.md"), ["A", "B"])

    def test_create_tag_with_tags(self):
        """--tag works for every item type, including a new tag (builds the hierarchy)."""
        self._run("create", "tag", "parent")
        self.assertEqual(self._run("create", "tag", "child", "--tag", "parent")[0], 0)
        self.assertEqual(self._tags_of("child"), ["parent"])

    def test_create_with_missing_tag_creates_nothing(self):
        self._run("create", "tag", "A")
        status, _, err = self._run("create", "file", "/tmp/note.md", "--tag", "A", "--tag", "nope")
        self.assertEqual(status, 1)
        self.assertIn("nope", err)
        self.assertEqual(self._urls(), {"A"})

    def test_create_with_non_tag_parent_is_refused(self):
        self._run("create", "url", "https://ex.com")
        status, _, _ = self._run("create", "file", "/tmp/note.md", "--tag", "https://ex.com")
        self.assertEqual(status, 1)
        self.assertEqual(self._urls(), {"https://ex.com"})

    def test_create_duplicate_fails_cleanly(self):
        self._run("create", "tag", "A")
        status, _, err = self._run("create", "tag", "A")
        self.assertEqual(status, 1)
        self.assertIn("already exists", err)

    def test_tag_missing_child_fails(self):
        self._run("create", "tag", "A")
        status, out, err = self._run("tag", "no-such-item", "A")
        self.assertEqual(status, 1)
        self.assertEqual(out, "")
        self.assertIn("no-such-item", err)

    def test_tag_twice_fails_cleanly(self):
        self._run("create", "tag", "A")
        self._run("create", "file", "/tmp/note.md", "--tag", "A")
        status, _, err = self._run("tag", "/tmp/note.md", "A")
        self.assertEqual(status, 1)
        self.assertIn("already tagged", err)

    def test_untag(self):
        self._run("create", "tag", "A")
        self._run("create", "file", "/tmp/note.md", "--tag", "A")
        self.assertEqual(self._run("untag", "/tmp/note.md", "A")[0], 0)
        self.assertEqual(self._tags_of("/tmp/note.md"), [])
        # Removing a tag that is not applied is reported, not silently accepted.
        self.assertEqual(self._run("untag", "/tmp/note.md", "A")[0], 1)

    def test_tags_lists_direct_parents_only(self):
        self._run("create", "tag", "top")
        self._run("create", "tag", "mid", "--tag", "top")
        self._run("create", "file", "/tmp/note.md", "--tag", "mid")
        status, out, _ = self._run("tags", "/tmp/note.md")
        self.assertEqual(status, 0)
        self.assertEqual(out, "TAG: mid\n")
        self.assertEqual(self._run("tags", "no-such-item")[0], 1)

    def _search_fixture(self):
        """topic -> sub (tag), /abs/b.md, rel/a.md (files), https://ex.com (url)."""
        self._run("create", "tag", "topic")
        self._run("create", "tag", "sub", "--tag", "topic")
        self._run("create", "file", "/abs/b.md", "--tag", "topic")
        self._run("create", "file", "rel/a.md", "--tag", "sub")
        self._run("create", "url", "https://ex.com", "--tag", "topic")
        self._run("create", "dir", "/abs/dir", "--tag", "topic")

    def test_search_paths(self):
        self._search_fixture()
        status, out, _ = self._run("search", "topic", "--paths")
        self.assertEqual(status, 0)
        # Only files, absolute, sorted; the relative name resolves against the db directory.
        rel = os.path.join(os.path.dirname(os.path.abspath(self.db_path)), "rel", "a.md")
        self.assertEqual(out.splitlines(), sorted(["/abs/b.md", rel]))

    def test_search_paths_print0(self):
        self._search_fixture()
        _, out, _ = self._run("search", "sub", "-p0")
        self.assertTrue(out.endswith("rel/a.md\0"))
        self.assertNotIn("\n", out)
        # -0 on its own implies --paths.
        self.assertEqual(self._run("search", "sub", "-0")[1], out)

    def test_search_paths_empty_result_prints_nothing(self):
        self._search_fixture()
        self.assertEqual(self._run("search", "no-such-tag", "-p"), (0, "", ""))

    def test_search_paths_with_type(self):
        self._search_fixture()
        _, out, _ = self._run("search", "topic", "-p", "--type", "dir")
        self.assertEqual(out, "/abs/dir\n")

    def test_search_type_filter(self):
        self._search_fixture()
        _, out, _ = self._run("search", "topic", "--type", "tag")
        self.assertEqual(out, "TAG: sub\n")

    def test_search_default_output_unchanged(self):
        self._search_fixture()
        _, out, _ = self._run("search", "sub")
        self.assertEqual(out, "FILE: rel/a.md\n")

    def test_ls_type_filter(self):
        self._search_fixture()
        _, out, _ = self._run("ls", "--type", "tag")
        self.assertEqual(out.splitlines(), ["TAG: topic", "TAG: sub"])

    def test_ls_tree_type_filter(self):
        """The tree keeps the hierarchy between the remaining items only."""
        self._search_fixture()
        _, out, _ = self._run("ls", "--tree", "--type", "tag")
        self.assertEqual(out.splitlines(), ["TAG: topic", "  TAG: sub"])


class TestResolvePath(unittest.TestCase):
    """Test how item names are turned into absolute paths for --paths."""

    def test_absolute_is_kept(self):
        self.assertEqual(cli.resolve_path("/a/b.md", "/data/tzr.db"), "/a/b.md")

    def test_relative_resolves_against_db_directory(self):
        self.assertEqual(cli.resolve_path("notes/b.md", "/data/tzr.db"), "/data/notes/b.md")

    def test_home_is_expanded(self):
        self.assertEqual(cli.resolve_path("~/b.md", "/data/tzr.db"), os.path.expanduser("~/b.md"))


if __name__ == "__main__":
    unittest.main()
