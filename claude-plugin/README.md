# tzr-memory

A Claude Code plugin that gives Claude a memory that lasts across sessions and is shared by
all your projects.

Claude writes what it learns as markdown notes and tags them with
[Taganizer](../README.md) (`tzr`). At the start of each session it is shown the notes that
are relevant to the project you are in. It remembers:

- the projects you worked on, on this machine, and how they relate;
- your preferences, both the ones you state and the ones it distils from your choices;
- installed tools, versions and environments, and the extra steps they need;
- anything you ask it to remember.

Claude tells you in one line each time it saves something.

## Prerequisite

The `tzr` command must be on your `PATH`. See [Installation](../README.md#installation) in
the Taganizer README, then check with `tzr --version`.

## Install

The Claude Code CLI and the VS Code extension share `~/.claude/settings.json`, so installing
in one makes the plugin available in the other.

### Claude Code CLI

From your shell:

```bash
claude plugin marketplace add hilkoc/taganizer
claude plugin install tzr-memory@taganizer
```

This installs for you in every project (user scope). The same two steps work inside a
session as `/plugin marketplace add hilkoc/taganizer` and
`/plugin install tzr-memory@taganizer`.

From Claude Code v2.1.292 you can do both in one command:

```bash
claude plugin install tzr-memory --marketplace hilkoc/taganizer
```

### VS Code extension

1. In the Claude Code panel, type `/plugins` in the prompt box. **Manage plugins** opens.
2. On the **Marketplaces** tab, add `hilkoc/taganizer`.
3. On the **Plugins** tab, find `tzr-memory` and click **Install**.
4. Choose **Install for you**.

Or open this link, which does the same:
`vscode://anthropic.claude-code/install-plugin?plugin=tzr-memory&marketplace=hilkoc/taganizer`

### Check that it works

Type `/` in a session: `/tzr-memory:memory` is listed. `claude plugin list` in your shell
shows the plugin too.

The first time, Claude runs the plugin's `scripts/setup.sh`, which creates the notes folder
and the category tags.

## Where your data lives

| What | Where |
| --- | --- |
| Notes | `~/.claude/tzr-memory/*.md` |
| Tags | your default tzr database, `~/.tzr.db` |

The plugin uses the same tzr database as you do. Everything Claude saves carries the tag
`CC_MEMORY`, so `tzr search CC_MEMORY` lists exactly what Claude saved, and your own items
stay recognizable. You can read, edit, retag or delete any note yourself.

The tags and the rules Claude follows are described in
[skills/memory/SKILL.md](skills/memory/SKILL.md).

Claude recalls notes with commands of the form `tzr search … | xargs grep …`. Depending on
your permission mode, Claude Code may ask before running them.

## Update

Third-party marketplaces do not update automatically:

```bash
claude plugin update tzr-memory@taganizer
```

## Uninstall

```bash
claude plugin uninstall tzr-memory@taganizer
```

Your notes and tags are left in place. To remove them as well, delete
`~/.claude/tzr-memory/` and delete the items listed by `tzr search AGENT_MEMORY` with
`tzr delete`.

## Development

Load the plugin from a checkout for one session, without installing it:

```bash
claude --plugin-dir ./claude-plugin
```

The scripts are tested in [tests/test_plugin_scripts.py](../tests/test_plugin_scripts.py).
