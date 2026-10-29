#!/usr/bin/env bash
# Copy this repo's tools into place (idempotent; existing files get a dated backup when they differ).
#   bin/*            → ~/.local/bin/
#   hooks/*.py       → ~/.claude/hooks/
#   skills/<name>/   → ~/.claude/skills/<name>/
#   codex-skills/<name>/ → ~/.codex/skills/<name>/
# Then run `sessions install` (hook line, skills, ghostty-session integration) and, once,
# `ghostty-session install` (systemd timer + login restore). See README.md.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
stamp=$(date +%Y%m%d-%H%M%S)
changed=0

put() {  # put SRC DST [mode]
  local src=$1 dst=$2 mode=${3:-644}
  mkdir -p "$(dirname "$dst")"
  if [[ -f "$dst" ]] && cmp -s "$src" "$dst"; then return; fi
  if [[ -f "$dst" ]]; then cp -p "$dst" "$dst.bak-$stamp"; echo "backup  $dst.bak-$stamp"; fi
  install -m "$mode" "$src" "$dst"; echo "install $dst"; changed=1
}

for f in "$here"/bin/*; do [[ -f "$f" ]] || continue; put "$f" "$HOME/.local/bin/$(basename "$f")" 755; done   # skip __pycache__ etc.
for f in "$here"/hooks/*.py; do put "$f" "$HOME/.claude/hooks/$(basename "$f")" 755; done
for d in "$here"/skills/*/; do
  name=$(basename "$d")
  for f in "$d"*; do put "$f" "$HOME/.claude/skills/$name/$(basename "$f")"; done
done
for d in "$here"/codex-skills/*/; do
  name=$(basename "$d")
  for f in "$d"*; do put "$f" "$HOME/.codex/skills/$name/$(basename "$f")"; done
done

[[ $changed == 1 ]] || echo "everything already in place"

if ! grep -q 'ghostty-split-run pickup' "$HOME/.bashrc" 2>/dev/null; then
  echo "TODO: append shell/bashrc-snippet.sh to ~/.bashrc (new splits cannot pick up commands without it)"
fi
if ! grep -q 'tab-status.py' "$HOME/.claude/settings.json" 2>/dev/null; then
  echo "TODO: wire hooks/tab-status.py into ~/.claude/settings.json (docs/ghostty-tab-status.md)"
fi
if ! systemctl --user is-active -q ghostty-session-save.timer 2>/dev/null; then
  echo "TODO: ghostty-session install   (20 s snapshots + login restore)"
fi
echo "next: sessions install   (idempotent: hook line, skills, ghostty-session integration)"
