---
name: memory
description: >
  Persistent memory shared by all sessions and all projects on this machine: markdown notes
  indexed with tzr tags. Use it when the user asks to remember, recall or forget something;
  after the user answers a question, states a preference or corrects you; when the session
  start output says the project is not registered; before using a tool listed under "Tools
  with notes"; when a command fails for an environmental reason or such a failure is solved;
  and when asked about other projects, installed tools or environments on this machine.
---

# tzr-memory

Memory that outlives the session and is shared across projects. Notes are markdown files;
`tzr` holds the tags that organize them. The tags live only in the tzr database, not in the
files.

- Notes: `~/.claude/tzr-memory/<slug>.md`. One subject per file. The first line is
  `# <one-line summary>`, because that line is all the session start hook shows. No
  frontmatter.
- Index: the default tzr database (`~/.tzr.db`), which the user also uses for their own
  items. Every note is a tzr `file` item named by its absolute path.
- File name prefixes: `project-<name>.md`, `tool-<name>.md`, `env-<name>.md`,
  `pref-<slug>.md`. Anything else gets a descriptive slug.

If the session start output says memory is not set up, run the `setup.sh` command it prints
before the first save. If it says tzr is missing or too old, tell the user; do not work
around it.

## Tags

Uppercase tags are categories. `prefix:<name>` tags are instances that sit under a category.
Lowercase tags are free topics (`python`, `packaging`, `sqlite`) that are shared with the
user's own tags and can be nested (`packaging` under `python`), so a search for the broad
topic also finds the narrow one.

| Tag | Put it on | Meaning |
| --- | --- | --- |
| `CC_MEMORY` | every item you save | Saved by Claude Code. It sits under `AGENT_MEMORY`, which covers all agents. Never put it on a tag: everything under that tag would then count as yours. |
| `PINNED` | notes | The summary line is shown at every session start, in every project. |
| `project:<name>` (under `PROJECT`) | notes, the project's `dir` item | Belongs to that project. Shown at session start in that project. `<name>` is the base name of the project directory. |
| `PROJECT_CARD` | one note per project | The overview note of a project. |
| `uses:<name>` (under `RELATION`) | a project's `dir` item | That project depends on project `<name>`. |
| `tool:<name>` (under `TOOL`) | notes | About an installed CLI, script or library. |
| `ENV` | notes | An environment: Python venv, interpreter, shell, `PATH` setup. |
| `QUIRK` | notes | A prerequisite or workaround that is needed before something works. |
| `PREFERENCE` | notes | How the user wants things done, including corrections. |
| `USER` | notes | A fact about the user: role, expertise. |
| `REFERENCE` | notes, `url` items | A pointer to an external resource. |
| `USER_REQUEST` | notes | The user explicitly asked to remember this. |
| `INFERRED` | notes | Your own generalization, not yet confirmed. |
| `host:<hostname>` (under `HOST`) | project `dir` items, tool and env notes | True for this machine only. The hostname is the output of `uname -n`. |

Look at the existing vocabulary before inventing a tag: `tzr ls --tree --type tag`. A new
tag must be created before it is used: `tzr create tag <name>`, with `--tag <CATEGORY>` for
an instance tag such as `tool:aws` (category `TOOL`).

## What to remember, and when

**Projects.** When the session start output says the project is not registered, register it
at the first substantive task, once you know what the project is:

```bash
tzr create tag project:fotomgr --tag PROJECT
tzr create dir /home/me/dev/fotomgr \
    --tag CC_MEMORY --tag project:fotomgr --tag host:mypc --tag python
```

Then write the card `~/.claude/tzr-memory/project-fotomgr.md` (what the project is, its
stack, its state, related projects) and index it with `--tag CC_MEMORY --tag project:fotomgr
--tag PROJECT_CARD`. The topic tags on the `dir` item matter: at session start, preferences
and quirks recorded for those topics are shown, whichever project they came from. Keep the
card current when something important about the project changes.

**Relations between projects.** Record one when you see a project import, call or copy
conventions from another, or when the user says so. A dependency is a `uses:<name>` tag on
the `dir` item of the dependent project. A shared stack or domain is a shared topic tag on
both `dir` items. A sub-project is `project:<child>` tagged with `project:<parent>`. Also
add one line about the relation to both project cards.

**Stated preferences.** When the user states how they want something done, or corrects you,
save a `pref-<slug>.md` note tagged `PREFERENCE` plus topic tags. Add `PINNED` when it
affects everyday behaviour in any project.

**Distilled preferences.** After the user answers a question or chooses between options,
ask yourself whether a rule lies behind the choice that would apply in other situations. If
the choice only fits this one task, save nothing. If there is a rule:

1. List the existing preferences (recipe below) and look for the same rule or its opposite.
2. Same rule found: add an evidence line to that note. If the note is `INFERRED` and this is
   a second, independent confirmation, remove the tag (`tzr untag <note> INFERRED`) and drop
   `(inferred)` from the summary.
3. Opposite found: narrow the scope of the rule with a topic or project tag, or ask the user
   once which one holds.
4. Nothing found: write a new note. Start the summary with `(inferred)`, tag it `PREFERENCE`
   and `INFERRED`, and record the evidence in the body: date, project, the question, the
   option chosen, the options rejected.

The user confirming an inferred preference in words also removes `INFERRED`.

**Tools, versions and libraries.** Save a `tool-<name>.md` note when a tool mattered and was
not obvious: you checked its version or location, it was installed, or a command failed for
an environmental reason. Record the path, how it was installed, and the version with the
date you checked it. Tag it `tool:<name>` and `host:<hostname>`. Do not scan the machine for
an inventory.

**Environments.** Save an `env-<name>.md` note when a venv, interpreter or `PATH` setup is
created, discovered or needed: where it is, the interpreter version, how to activate it,
what is installed in it. Tag it `ENV`, `host:<hostname>`, and `project:<name>` or
`tool:<name>`.

**Peculiarities.** When something only worked after an extra step (change `PATH`, run a
login script first, activate a venv), or the user explains such a step, put it in the tool
or env note, tag the note `QUIRK`, and state the step in the summary line.

**Explicit requests.** When the user asks you to remember something, always save it here,
tagged `USER_REQUEST` plus whatever else fits. Do not also save it to the built-in project
memory.

Facts that matter only inside one project and fit none of the above stay in the built-in
project memory.

## Rules

- Search before saving. Update the existing note instead of writing a second one about the
  same subject. `tzr create` refuses a name that already exists; treat that as the signal to
  update.
- Tell the user what you saved, in one line, each time: `Remembered: …` or
  `Remembered (inferred): …`. A wrong generalization then gets corrected at once.
- Versions are snapshots. Check again before relying on one, and update the note when it
  has changed.
- Before using a tool listed under "Tools with notes" in the session start output, read its
  note. When a command fails for an environmental reason, search memory before debugging
  from scratch.
- Never store secrets: no passwords, tokens or keys. Name the login script, not the
  credentials.
- Anything the user did not say themselves is your interpretation. Mark it `INFERRED`.

## Recipes

Save a note: write the file, then index it in one command. Pass the path unquoted so the
shell expands `~` to the absolute path.

```bash
tzr create file ~/.claude/tzr-memory/tool-aws.md \
    --tag CC_MEMORY --tag tool:aws --tag QUIRK --tag host:mypc
```

A pointer that needs no explanation can be a `url` item without a file:

```bash
tzr create url https://docs.pypi.org/trusted-publishers/ --tag CC_MEMORY --tag REFERENCE
```

Recall in two steps: select notes by tag, filter them by content, then Read what is left.
In a search, tags separated by spaces must all match, and `+` starts an alternative.

```bash
# notes about python packaging that mention "trusted"
tzr search CC_MEMORY python packaging -p0 | xargs -0r grep -li 'trusted'
# one summary line per note, without reading the files
tzr search CC_MEMORY PREFERENCE -p0 | xargs -0r grep -H -m1 '^# '
# everything known about one tool
tzr search CC_MEMORY tool:aws -p0 | xargs -0r cat
```

Leave out `CC_MEMORY` to include the files the user tagged themselves.

Projects and relations:

```bash
tzr search PROJECT_CARD -p0 | xargs -0r grep -h -m1 '^# '   # all projects, one line each
tzr search PROJECT --type dir                               # their paths
tzr search uses:taganizer --type dir                        # projects that depend on taganizer
tzr tags /home/me/dev/fotomgr                               # stack and relations of one project
```

Maintain:

```bash
tzr tags <note>               # the tags on a note
tzr tag <note> PINNED         # add a tag
tzr untag <note> INFERRED     # remove a tag
tzr delete <note>             # forget: removes the index entry, the file stays on disk
```

To change the content of a note, edit the file; the index does not need to change. Forget a
note only when the user asks, or when it has been replaced by a better note.
