# adhd-ghostty

Tooling for running many Claude Code / Codex sessions in parallel in [Ghostty](https://ghostty.org)
without losing track of them. Linux (GNOME/Wayland), Ghostty 1.3, Python 3 stdlib only, no root.

The centre piece is `sessions`, a 56-column sidebar that treats the **session** (not the tab) as the
unit of account:

```
══ window 1 ════════════════════════════════════════════
 ├1 ⚪ LP Refresh Competitor                          🧹
 ├2 🚧 Design system landing page
 ├3 ⚪ Shotgun split tree review                  🧹 ?2d
 │ ├─ ▫  codex                                         —
 │ └─ 🟢 Startup Valuation Multiples               🧹 4d
 ├4 🟢 UGC Rate Negotiation                          12m
 │ └⑂ 🟢 Projecting WAU growth                        1h
 ├5 🟢 Lisbon Sailing Research                     🧹 📌
 ├6 🟢 Stale Docs Cleanup                             🧹
▶└7 🚧 Multi-Session Dashboard
══ window 2 ════════════════════════════════════════════
 └1 🔴 Welecja Drive Migration                       40m

══ 📌 pinned ═══════════════════════════════════════════
📌 🟢 Lisbon Sailing Research                         2h
📌    Referral v3 success metric                      5d

══ history ═════════════════════════════════════════════
    🟢 Welecja member explainer                       0d
    🟢 Split payment check                            0d
       closed with hook active line                  ?3d
       Fork UX question                              ?2d
       Bitwarden shadow vault                        ?1d
       Competitor UK incorporation
══════════════════════════════════════════════════════+7
 c 🧹 5                                                ?
```

- `══ 📌 pinned ══`: sessions kept for later (no date, never decays), between the windows and the history,
  newest activity first, age on the right.
- `══ window N ══`, `├N` tab N (= Ghostty `alt+N`), `├─` split, `└⑂` split forked from its parent.
- Left emoji = live status from the Claude Code hook: ⚪ idle, 🚧 working, 🟢 finished (your turn), 🔴 blocked on you.
  Codex rows show `▫`, or 🚧 / 🔴 when the codex TUI's terminal title says so (spinner / `Action Required`).
- Right column = **your intent**, which outlives the tab: blank = active (🟢/🔴 rows show how long
  they have waited), `Nd` = parked, wakes in N days, `?Nd` = unsorted, auto-archived in N days,
  🧹 = still holds a tab, `c` closes it (`🧹 📌` = pinned session whose tab can go).
- `══ history ══`: sessions with no tab anywhere (cap 40, `m` shows all). `0d` + 🟢 = due today.

## Shortcuts

Sidebar keys (cursor moves over session rows only):

| key | action |
|---|---|
| `j` / `k`, `↑` / `↓` | move |
| `↵` | open row: focus hint `→ "window title" · alt+N`; closed row: resume in a new tab |
| `r` | resume in a new tab (closed rows; on an open row same as `↵`) |
| `p` | pin / unpin (📌 section above the history, no date, never decays) |
| `s` | snooze = park: days (number, `s` = someday), then a note |
| `c` | close = sweep every visible 🧹 pane (confirms above 3) |
| `x` | done (hidden; `D` shows) |
| `a` | re-activate |
| `/` … `↵`, `Esc` | filter rows by text / clear the filter |
| `space` | detail pane (7 rows; off when the terminal is under 15 rows) |
| `D` | show done sessions |
| `m` | whole history (cap 40 otherwise) |
| `?` | help overlay |
| `q` | quit |

In a Claude Code session:

| command | action |
|---|---|
| `/pin` | pin / unpin this session (toggle) |
| `/park [days\|s] [note]` | snooze: wake in N days (default 1) or someday |
| `/done` | mark done |
| `/fork-here [down]` | fork this session into a new split |

Typing in a parked session re-activates it. A pinned session stays pinned through typing, closing its tab
and resuming it; only `p`, `/pin`, `x` or `/done` change that.

## Layout

| path | what |
|---|---|
| `bin/sessions` | the sidebar + ledger CLI (`tui`, `map`, `log`, `park`, `pin`, `unpin`, `done`, `touch`, `sweep`, `focus`, `resume`, `install`) |
| `bin/ghostty-session` | 20 s snapshots of windows → tabs → splits and what runs in them; restore at login; reopen closed windows |
| `bin/ghostty-split-run`, `bin/ghostty-window-of` | open a split in the right window over D-Bus and run a command in it |
| `bin/claude-fork-split`, `bin/codex-fork-split` | `/fork-here`: fork the current session into a new split |
| `hooks/tab-status.py` | Claude Code hook: status icon + short title in the tab, `.state` files the sidebar reads |
| `skills/` | `/park`, `/pin`, `/done`, `/fork-here` for Claude Code |
| `shell/bashrc-snippet.sh` | the `~/.bashrc` block that lets a fresh split pick up its command |
| `tests/run_tests.py` | 102 checks: render, ledger, sweep with real processes, pty keys, install idempotency |
| `docs/` | `sessions.md` (operate, reset, limits), `sessions-spec.md` (the agreed design), ghostty-session and tab-status notes |

## Install

```
./install.sh            # copies bin/ hooks/ skills/ into place with dated backups, prints what is left to do
sessions install        # wires the hook line, skills and ghostty-session integration (idempotent)
ghostty-session install # systemd user timer + login restore + Super+Shift+T (once)
```

Then append `shell/bashrc-snippet.sh` to `~/.bashrc` if it is not there yet, and wire
`hooks/tab-status.py` into `~/.claude/settings.json` hooks (see `docs/ghostty-tab-status.md`).
Open the sidebar with `sessions` (left split of the focused window) or `sessions tui` in any pane.

## Tests

```
python3 -I tests/run_tests.py
```

Runs against `bin/` in the repo, builds its fixtures in a temp dir, never touches real state.

## State

`~/.local/state/sessions/events.jsonl` (append-only intent ledger, last event per session wins),
`~/.local/state/sessions/lineage.json`, `~/.cache/sessions/`, `~/.local/state/ghostty-session/`.
Reset the intent of everything by deleting `events.jsonl`.

## Limits

- No programmatic focus of a pane on GNOME/Wayland. Ghostty's `present-surface` needs a surface id
  nothing exposes, so `↵` on an open row shows the window title and the `alt+N` to press.
- Split layouts of tabs you have not displayed since splitting them are a best guess (AT-SPI only
  exposes the visible tab); membership is right, direction may not be.
- Codex names come from the terminal title the codex TUI sets (`<thread name> | <project>`) and from
  `~/.codex/session_index.jsonl`; ids are matched by name, by `codex resume <id>` argv, or by the thread
  created right after the pane started. A codex pane that resumed a thread through the picker in a tab
  that has not been shown since stays `codex —` (no id: never swept, not parkable) until its tab is visible.
