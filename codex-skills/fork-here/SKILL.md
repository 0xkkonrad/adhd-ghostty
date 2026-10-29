---
name: fork-here
description: Fork this Codex session into a new Ghostty split (like ctrl+shift+o) running `codex fork <this session>`. Use only when the user types $fork-here or says "fork-here".
---

Run exactly this, with no other steps first:

```bash
codex-fork-split "$CODEX_THREAD_ID" right
```

(Use `down` instead of `right` if the user asked for it.)

Then reply with one line: the split is open, the fork's direction, and that this
session keeps going unchanged. If it fails, show the error. Common causes: the
command ran inside a sandbox without D-Bus access (re-run it with escalated
permissions), no Ghostty window on D-Bus, or the split opened in the wrong window
(set `GHOSTTY_SPLIT_WINDOW=<n>` — list windows with
`gdbus introspect --session -d com.mitchellh.ghostty -o /com/mitchellh/ghostty/window`).
Tooling: `~/.local/bin/ghostty-split-run`, `~/.local/bin/codex-fork-split`,
pickup hook at the end of `~/.bashrc`.

If the command is not found, the tools are not installed: run `./install.sh` from
https://github.com/0xkkonrad/adhd-ghostty and add `shell/bashrc-snippet.sh` to `~/.bashrc`.
