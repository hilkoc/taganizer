"""Tests for the shell scripts of the tzr-memory Claude Code plugin (claude-plugin/scripts).

The scripts call the `tzr` command, so these tests run them as subprocesses with the
directory of the current interpreter first on PATH (where the entry point is installed).
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "claude-plugin", "scripts")
BIN_DIR = os.path.dirname(os.path.abspath(sys.executable))


@unittest.skipUnless(os.name == "posix", "the plugin scripts are POSIX shell")
@unittest.skipUnless(shutil.which("tzr", path=BIN_DIR), "tzr entry point is not installed")
class TestPluginScripts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "tzr.db")
        self.notes = os.path.join(self.tmp, "notes")
        self.env = dict(
            os.environ,
            PATH=BIN_DIR + os.pathsep + os.environ["PATH"],
            TZR_MEMORY_DB=self.db,
            TZR_MEMORY_DIR=self.notes,
        )
        self.env.pop("CLAUDE_PLUGIN_ROOT", None)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _script(self, name, project=None, env=None):
        env = dict(env or self.env)
        if project is not None:
            env["CLAUDE_PROJECT_DIR"] = project
        return subprocess.run(
            ["sh", os.path.join(SCRIPTS, name)], env=env, capture_output=True, text=True
        )

    def _tzr(self, *args):
        result = subprocess.run(
            ["tzr", "--db", self.db] + list(args), env=self.env, capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def _note(self, name, summary, *tags):
        path = os.path.join(self.notes, name)
        with open(path, "w") as f:
            f.write("# %s\n\nbody\n" % summary)
        tag_args = [arg for tag in ("CC_MEMORY",) + tags for arg in ("--tag", tag)]
        self._tzr("create", "file", path, *tag_args)

    def _project(self, name, *topics):
        self._tzr("create", "tag", "project:" + name, "--tag", "PROJECT")
        tag_args = [
            arg for tag in ("CC_MEMORY", "project:" + name) + topics for arg in ("--tag", tag)
        ]
        self._tzr("create", "dir", "/work/" + name, *tag_args)

    def test_hook_without_tzr_reports_inactive(self):
        result = self._script("session-start.sh", "/work/a", dict(self.env, PATH="/usr/bin:/bin"))
        self.assertEqual(result.returncode, 0)
        self.assertIn("inactive", result.stdout)

    def test_hook_before_setup_does_not_create_database(self):
        result = self._script("session-start.sh", "/work/a")
        self.assertEqual(result.returncode, 0)
        self.assertIn("setup.sh", result.stdout)
        self.assertFalse(os.path.exists(self.db))

    def test_setup_is_idempotent(self):
        first = self._script("setup.sh")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn("created tag CC_MEMORY", first.stdout)
        self.assertEqual(self._tzr("tags", "CC_MEMORY"), "TAG: AGENT_MEMORY\n")
        tags_before = self._tzr("ls", "--tree", "--type", "tag")
        second = self._script("setup.sh")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertNotIn("created", second.stdout)
        self.assertEqual(self._tzr("ls", "--tree", "--type", "tag"), tags_before)

    def test_hook_reports_unregistered_project(self):
        self._script("setup.sh")
        result = self._script("session-start.sh", "/work/new")
        self.assertIn("new is not registered", result.stdout)

    def test_hook_carries_knowledge_between_projects(self):
        """A preference saved for one Python project shows up in another Python project."""
        self._script("setup.sh")
        for tag in ("python", "go"):
            self._tzr("create", "tag", tag)
        self._tzr("create", "tag", "tool:aws", "--tag", "TOOL")
        self._project("a", "python")
        self._project("b", "python")
        self._note("project-a.md", "a: demo project", "project:a", "PROJECT_CARD")
        self._note("pref-layout.md", "(inferred) Prefers src/ layout", "PREFERENCE", "python")
        self._note("pref-terse.md", "Answer tersely", "PREFERENCE", "PINNED")
        self._note("pref-go.md", "Go formatting", "PREFERENCE", "go")
        self._note("tool aws.md", "aws: run awslogin first", "tool:aws", "QUIRK")

        out = self._script("session-start.sh", "/work/b").stdout
        self.assertIn("Project: b (registered)", out)
        self.assertIn("Tools with notes (read the note before using the tool): aws", out)
        self.assertIn("pref-layout.md: (inferred) Prefers src/ layout", out)  # shared topic
        self.assertIn("pref-terse.md: Answer tersely", out)  # pinned
        self.assertNotIn("pref-go.md", out)  # other topic
        self.assertNotIn("project-a.md", out)  # other project

        self.assertIn(
            "project-a.md: a: demo project", self._script("session-start.sh", "/work/a").stdout
        )

    def test_hook_caps_the_number_of_notes(self):
        self._script("setup.sh")
        for i in range(45):
            self._note("pin-%02d.md" % i, "pinned %d" % i, "PINNED")
        out = self._script("session-start.sh", "/work/a").stdout
        self.assertEqual(sum(1 for line in out.splitlines() if line.startswith("pin-")), 40)
        self.assertIn("5 more", out)


if __name__ == "__main__":
    unittest.main()
