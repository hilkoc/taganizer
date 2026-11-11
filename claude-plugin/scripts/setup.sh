#!/bin/sh
# One-time setup for the tzr-memory plugin: creates the notes folder, initializes the tzr
# database and creates the category tags the memory skill relies on.
# Safe to run again: existing tags and links are left as they are.
#
# TZR_MEMORY_DB and TZR_MEMORY_DIR override the database and the notes folder. They exist for
# the test suite; the skill itself always uses the tzr default database.
set -eu

t() {
    if [ -n "${TZR_MEMORY_DB:-}" ]; then
        tzr --db "$TZR_MEMORY_DB" "$@"
    else
        tzr "$@"
    fi
}

if ! command -v tzr >/dev/null 2>&1; then
    echo "tzr-memory: tzr is not on PATH. Install taganizer first." >&2
    exit 1
fi
if ! tzr tags --help >/dev/null 2>&1; then
    echo "tzr-memory: the installed tzr is too old (no 'tags' command). Upgrade taganizer." >&2
    exit 1
fi

notes_dir=${TZR_MEMORY_DIR:-$HOME/.claude/tzr-memory}
mkdir -p "$notes_dir"
t init >/dev/null

# ensure NAME [PARENT]: create the tag if it is missing, then link it under PARENT.
ensure() {
    if ! t ls --type tag | grep -qxF "TAG: $1"; then
        t create tag "$1" >/dev/null
        echo "created tag $1"
    fi
    if [ -n "${2:-}" ] && ! t tags "$1" | grep -qxF "TAG: $2"; then
        t tag "$1" "$2" >/dev/null
        echo "linked $1 under $2"
    fi
}

ensure AGENT_MEMORY
ensure CC_MEMORY AGENT_MEMORY
for tag in PINNED PROJECT PROJECT_CARD RELATION TOOL ENV QUIRK PREFERENCE USER REFERENCE \
    USER_REQUEST INFERRED HOST; do
    ensure "$tag"
done
ensure "host:$(uname -n)" HOST

echo "tzr-memory is set up. Notes folder: $notes_dir"
