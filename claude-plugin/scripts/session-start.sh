#!/bin/sh
# SessionStart hook for the tzr-memory plugin. Prints a short overview of the memory that is
# relevant to the current project; Claude Code adds this output to the conversation context.
# This script only reads. It never creates or changes the database or the notes.
#
# TZR_MEMORY_DB and TZR_MEMORY_DIR override the database and the notes folder. They exist for
# the test suite; the skill itself always uses the tzr default database.

MAX_LINES=40

t() {
    if [ -n "${TZR_MEMORY_DB:-}" ]; then
        tzr --db "$TZR_MEMORY_DB" "$@"
    else
        tzr "$@"
    fi
}

plugin_root=${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}
db=${TZR_MEMORY_DB:-$HOME/.tzr.db}
notes_dir=${TZR_MEMORY_DIR:-$HOME/.claude/tzr-memory}

if ! command -v tzr >/dev/null 2>&1; then
    echo "tzr-memory: inactive, tzr is not on PATH. See $plugin_root/README.md."
    exit 0
fi
if ! tzr tags --help >/dev/null 2>&1; then
    echo "tzr-memory: inactive, the installed tzr is too old (no 'tags' command). Upgrade taganizer."
    exit 0
fi

# Opening a missing database would create it, so check for the file first.
tags=""
if [ -f "$db" ]; then
    tags=$(t ls --type tag 2>/dev/null)
fi
if ! printf '%s\n' "$tags" | grep -qxF "TAG: CC_MEMORY"; then
    echo "tzr-memory: not set up yet. Before the first save, run: sh \"$plugin_root/scripts/setup.sh\""
    exit 0
fi

project_dir=${CLAUDE_PROJECT_DIR:-$PWD}
project=$(basename "$project_dir")

echo "tzr-memory: cross-project memory is active. Use the skill tzr-memory:memory to save and recall."
if printf '%s\n' "$tags" | grep -qxF "TAG: project:$project"; then
    echo "Project: $project (registered)"
else
    echo "Project: $project is not registered. Register it at the first substantive task."
fi

tools=$(t search TOOL --type tag 2>/dev/null | sed -n 's/^ *TAG: tool://p' | sort | tr '\n' ' ')
if [ -n "$tools" ]; then
    echo "Tools with notes (read the note before using the tool): $tools"
fi

# Pinned notes, this project's notes, and the preferences and quirks recorded for each topic
# tag on the project directory (for example 'python'), whichever project they came from.
set -- CC_MEMORY PINNED + CC_MEMORY "project:$project"
topics=$(t tags "$project_dir" 2>/dev/null | sed -n 's/^TAG: //p' | grep -v ':' | grep '[a-z]')
while IFS= read -r topic; do
    if [ -n "$topic" ]; then
        set -- "$@" + CC_MEMORY PREFERENCE "$topic" + CC_MEMORY QUIRK "$topic"
    fi
done <<TOPICS
$topics
TOPICS

notes=$(t search "$@" -p0 2>/dev/null | xargs -0 -r grep -s -H -m1 '^# ' | sed "s|^$notes_dir/||; s|:# |: |")
if [ -n "$notes" ]; then
    echo "Notes in $notes_dir (Read a file for the detail):"
    printf '%s\n' "$notes" | head -n "$MAX_LINES"
    total=$(printf '%s\n' "$notes" | wc -l)
    if [ "$total" -gt "$MAX_LINES" ]; then
        echo "... and $((total - MAX_LINES)) more. Search by tag to see them."
    fi
fi
exit 0
