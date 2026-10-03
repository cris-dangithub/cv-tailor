#!/usr/bin/env sh
# Install cv-tailor for Codex and/or Claude Code (user level) from a clone of this repo,
# by linking skills/cv-tailor into the agents' skill folders, then create its environment.
#
#   ./install.sh            # codex + claude
#   ./install.sh codex      # only Codex   (~/.codex/skills/cv-tailor)
#   ./install.sh claude     # only Claude  (~/.claude/skills/cv-tailor)
#
# Claude Code users can also install it as a plugin instead (see README).
set -eu
SRC="$(cd "$(dirname "$0")" && pwd)/skills/cv-tailor"
TARGETS="${*:-codex claude}"
PY="$(command -v python3 || command -v python)"

for t in $TARGETS; do
  case "$t" in
    codex)  DEST="${CODEX_HOME:-$HOME/.codex}/skills/cv-tailor" ;;
    claude) DEST="$HOME/.claude/skills/cv-tailor" ;;
    *) echo "unknown target: $t (use codex or claude)"; exit 2 ;;
  esac
  mkdir -p "$(dirname "$DEST")"
  if [ -e "$DEST" ] && [ ! -L "$DEST" ]; then
    echo "skip $t: $DEST exists and is not a link (remove it first)"; continue
  fi
  ln -sfn "$SRC" "$DEST"
  echo "linked $DEST -> $SRC"
done

"$PY" "$SRC/cvt.py" setup-env
"$PY" "$SRC/cvt.py" doctor || true
echo
echo "Done. Open your agent in an empty folder (your workspace) and paste a job offer."
