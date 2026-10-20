# ghostty-session — window/tab/split state manager for Ghostty (built 14 Oct 2026)

Konrad's ask after the 7th hard reset: "create split + window state manager for ghostty so that it
always reopens what was last open". Tool: `~/.local/bin/ghostty-session` (python3, no root).

## What it does
- Every 20 s (`ghostty-session-save.timer`) it snapshots what is open: windows → tabs → splits, and
  what runs in each split (claude session id, codex thread id, tmux session, or shell cwd).
  Snapshot: `~/.local/state/ghostty-session/current.json`; history every 10 min in `history/`.
- At login (`ghostty-session-restore.service`, 12 s after graphical-session.target) it reopens the last
  snapshot in a new Ghostty window — after a crash *or* a normal shutdown. Sessions already running
  are skipped. Snapshots older than 14 days are not auto-restored.
- `ghostty-session show` prints the current snapshot; `ghostty-session restore [FILE] [--window N|--new-window] [--dry-run]`
  rebuilds one by hand (e.g. a file from `history/`).
- **Closed windows (added 14 Oct, Konrad: "always reopen last window state if I close a whole window")**
  - A window whose surfaces all vanish between two ticks is appended, with its last layout, to
    `~/.local/state/ghostty-session/closed.json` (newest last, 30 kept). `ghostty-session closed` lists them.
  - `ghostty-session reopen [N] [--batch] [--window W|--new-window]` reopens the N-th last closed window
    (default the last one) in a new window; `--batch` = every window closed at the same moment (a quit).
    GNOME shortcut **Super+Shift+T** = `reopen --new-window` (set by `install`, like a browser's reopen-closed-tab).
  - Closing the *last* window never empties `current.json`. When Ghostty is started again with a single
    surface, the hook at the end of `~/.bashrc` runs `ghostty-session cold-start`: the first surface of the
    last closed window runs in that very shell and the rest is rebuilt in the background (log
    `~/.local/state/ghostty-session/reopen-*.log`). So quit → relaunch = everything back, no click needed.
  - After a reboot the login service restores `current.json` as before (cold-start only acts on windows
    closed during the current boot).

## How (and the limits)
- Programs: `/proc` — each surface is a `/bin/sh -c /bin/bash` child of the ghostty process;
  claude's session id comes from `~/.claude/sessions/<pid>.json` (those files are pruned by the next
  `claude` start after a crash, which is why the snapshot must be taken *while* things run).
- Tabs/splits: GTK accessibility tree (AT-SPI). Needs `gsettings org.gnome.desktop.interface
  toolkit-accessibility true` (set by `install`; GTK4 registers at runtime, Chrome turns its a11y on too).
  AT-SPI shows all tab titles (in order), which frame is focused (ACTIVE state) and the split geometry
  of the *visible* tab only. Every tick the registry is **reconciled** with that: one registry window per
  frame, one tab slot per tab title, each slot anchored by the surface whose title matches (claude →
  tab-status title, shell → bash's "⚪ \w" / "🚧 cmd", codex → its thread name; tmux has no usable title). A surface's
  tab-mates (splits) follow it. The visible tab is then verified against its terminal rectangles: members
  whose pty size matches no rectangle are moved out, rectangles without a member pull in a surface of that
  size when unambiguous. Pty sizes of hidden tabs are stale (GTK does not resize hidden pages), so splits
  in hidden tabs are a best guess until that tab is shown; custom tab titles ("Sail") cannot be matched.
  A brand-new surface goes to the focused window's new (empty) tab slot, else becomes a split of its active
  tab; a new surface whose window is not yet in the a11y tree is left for the next tick.
- Restore: GTK actions over D-Bus. `org.freedesktop.Application.Activate` opens a window at once;
  `new-tab` / `split-right` / `split-down` on `/com/mitchellh/ghostty/window/N`.
  **Window actions are queued until that window has keyboard focus** (unfocused: its title falls back
  to "Ghostty"; the queue fires when you click in), so `restore` fires each action once and waits —
  click into the target window and it continues. The login service works because the fresh window is
  focused. `new-window` on the app object creates the window at once but its D-Bus object is listed
  late (seconds to a minute); the tool waits for it. The new surface
  starts a plain bash; the command is handed over through `$XDG_RUNTIME_DIR/ghostty-split-run/pending`,
  claimed by the hook at the end of `~/.bashrc` (same as `ghostty-split-run` / `/fork-here`).
  `ghostty-split-run` / `/fork-here` (15 Oct 2026) pick the target window with `ghostty-window-of`:
  AT-SPI frames and D-Bus window numbers are both in creation order and are matched by rank; the window
  is chosen by title (the session's tab title, so the tab must be visible), else by keyboard focus, else
  it refuses. `ghostty-window-of --list` prints the numbers; `GHOSTTY_SPLIT_WINDOW=<n>` overrides.
  Splits are rebuilt as a focus chain (each split from the previously created surface), which covers
  "left + right column stacked" layouts; equal 3-column layouts come back as 50/25/25. No tab titles
  are set (D-Bus has no set-title); the tab-status hook titles the tabs from the sessions.
- Stale codex locks (`~/.codex/thread-writer-locks/*.lock`) are deleted before `codex resume`.
- Codex (20 Oct 2026): the codex TUI keeps no fd to its rollout, so a pane's thread is read from the terminal
  title codex sets (`[ ! ] Action Required | <thread name> | <project>`, `⠋ <name> | <project>`): a tab whose
  title parses that way names its single codex pane; the id is the newest thread of that name in
  `~/.codex/session_index.jsonl`, or comes from `codex resume <id>` argv, or is the named thread created right
  after the pane's process started (ids are UUIDv7). Once known, id + name live in `registry.json` (`codex`) and
  the name anchors the tab like a claude title does. Tab titles are copied from the tab bar for every tab when
  the tab count agrees with AT-SPI, else only for tabs anchored by their title. `program.state` (ask|busy) is
  per tick. A pane resumed through the picker in a tab not shown since stays id-less.

## Ops
    systemctl --user status ghostty-session-save.timer ghostty-session-restore.service
    journalctl --user -u ghostty-session-save -u ghostty-session-restore --since today
    ghostty-session closed         # what was closed, newest first
    ghostty-session reopen --dry-run
    ghostty-session uninstall      # removes the units + the GNOME shortcut, keeps snapshots
Predecessor: `resume-crashed.sh` (hand-written session lists; tmux layout) — superseded.

## 19 Oct 2026 fix: post-boot saves no longer clobber the pre-crash snapshot
After the 15:07 reset the login restore reopened only one empty shell: the 20-s save timer had
already overwritten `current.json` with the fresh post-boot window (1 surface) before
`ghostty-session on-login` read it. `save` now keeps the previous snapshot untouched while it is
from another boot, has no `restored_boot` for this boot and uptime < 15 min; `on-login` always
stamps `restored_boot` (also on the 14-day skip) so the hold is released. Manual recovery used:
`ghostty-session restore ~/.local/state/ghostty-session/history/snap-20261019-150236.json --new-window`.

19 Oct 2026 (sessions sidebar, `sessions install`): program kind `sessions` (detected via `sessions_argv`, flags like
`python3 -I` skipped), restored as a LEFT split and skipped when a sidebar already runs; `split_dir` may return `left`
only for kind `sessions` (every other pane classifies exactly as before); `save` rejects arguments and `-h/--help`
prints usage for every subcommand instead of running it.
