#!/usr/bin/env bash
# Install verify-glm skill to ~/.claude/skills/
set -euo pipefail

DEST="${HOME}/.claude/skills/verify-glm"
SRC="$(cd "$(dirname "$0")" && pwd)/skills/verify-glm"

if [[ ! -d "$SRC" ]]; then
  echo "ERROR: source dir not found: $SRC" >&2
  exit 1
fi

mkdir -p "$(dirname "$DEST")"
if [[ -e "$DEST" ]]; then
  echo "Updating existing skill at $DEST"
  rm -rf "$DEST"
fi
cp -r "$SRC" "$DEST"

echo "✅ Installed: $DEST"
echo
echo "Test it:"
echo "  python $DEST/verify_glm.py"
