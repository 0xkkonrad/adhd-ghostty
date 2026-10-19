---
name: fork-here
description: Fork this Claude Code session into a new Ghostty split (like ctrl+shift+o) running `claude -r <this session> --fork-session`. Use only when the user types /fork-here or says "fork-here".
argument-hint: "[down]"
disable-model-invocation: true
---

Run exactly this, with no other steps first:

```bash
claude-fork-split "$CLAUDE_CODE_SESSION_ID" right
```

(Use `down` instead of `right` if the user asked for it.)

Then reply with one line: the split is open, which Ghostty window it went to
(the command prints the window number and title), the fork's direction, and
that this session keeps going unchanged. If it fails, show the error verbatim.

How the target window is found (`ghostty-window-of`): the window whose title
is this session's tab title, else the window with keyboard focus. It refuses
rather than guessing when neither is found, e.g. when this tab is not the
visible one or focus is in another app: tell the user to switch to this tab
and run /fork-here again. `GHOSTTY_SPLIT_WINDOW=<n>` forces a window; list
them with `ghostty-window-of --list`.
Tooling: `~/.local/bin/ghostty-window-of`, `~/.local/bin/ghostty-split-run`,
`~/.local/bin/claude-fork-split`, pickup hook at the end of `~/.bashrc`.
