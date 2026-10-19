# sessions — Claude/Codex session sidebar for Ghostty (built 19 Oct 2026, fix pass same day)

Konrad's ask: "visualize sessions (thematically related, forks), a session-based backlog, Ghostty as
source of truth, superlight". Design agreed in chat 19 Oct (spec: `sessions-spec.md`).
Tool: `~/.local/bin/sessions` (python3 stdlib, one file, no root). Tests: `sessions-tests/run_tests.py`.

## What it shows (56-col left split)
```
══ 📌 pinned ═══════════════════════════════════════════   pinned: keep for later, no date, never decays (omitted when empty)
📌 🟢 Lisbon Sailing Research                         2h   open pinned session: live status; right = age since last activity
📌    Referral v3 success metric                      5d   closed pinned session
                                                           (blank line)
══ window 1 ════════════════════════════════════════════   Ghostty window 1 (registry order)
 ├1 ⚪ LP Refresh Competitor                          🧹   ├N = tab N (alt+N in that window)
 ├3 ⚪ Shotgun split tree review                  🧹 ?2d   stale while open: archived in 2d, closable
 │ ├─ ▫  codex                                         —   split; codex has no status; — = no thread id
 │ └⑂ 🟢 Projecting WAU growth                        1h   split forked from the tab's session; 🟢 waiting 1h
 ├5 🟢 Lisbon Sailing Research                     🧹 📌   pinned and still open: the tab can be closed
 └7 🚧 Multi-Session Dashboard                             active: blank right column
                                                           (blank line)
══ history ═════════════════════════════════════════════   nothing below has a tab (pinned ones live above)
    🟢 Split payment check                            0d   parked and due today
       Referral v4 metric                             3d   parked, wakes in 3 days
       Fork UX question                              ?2d   closed, unmarked (or only "active"): archived in 2 days
       Competitor UK incorporation                        parked someday
══════════════════════════════════════════════════════+3   hidden history rows (cap 40; m shows all)
 c 🧹 5                                                ?   c closes the 5 🧹 panes; ? = help
```
Left emoji = live status from `~/.claude/hooks/tab-status.py` (⚪ idle 🚧 working 🟢 finished 🔴 blocked).
Right column = what *you* decided: blank active · `Nd` wake · `?Nd` archive countdown · `🧹` = `c` closes it
(a done session that still has a tab shows `🧹` alone, a pinned one `🧹 📌`). The `s`/sweep wording in older notes = `c` close. `▶` in column 0 = cursor (only on
session rows; on a pinned row it sits right after `📌`).
Titles (uncapped in the model, cut with … at render): /rename > tab-status title > ai-title >
compaction-summary heading > first prompt (48 chars). Footer shows `snapshot stale` when the placement file
is from another boot or older than 60 s; sweeping is then refused.

## Shortcuts

Sidebar keys (cursor moves over session rows only):

| key | action |
|---|---|
| `j` / `k`, `↑` / `↓` | move |
| `↵` | open row: focus hint `→ "window title" · alt+N`; closed row: resume in a new tab |
| `r` | resume in a new tab (closed rows; on an open row same as `↵`) |
| `p` | pin / unpin (📌 section at the top, no date, never decays) |
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
| `/park [days|s] [note]` | snooze: wake in N days (default 1) or someday |
| `/done` | mark done |
| `/fork-here [down]` | fork this session into a new split |

Typing in a parked session re-activates it; typing in a pinned session keeps it pinned.

## States (ledger `~/.local/state/sessions/events.jsonl`, append-only, last valid line per sid wins)
- **active**: an open session that is not parked/done. Every prompt makes the hook run `sessions touch`, which
  appends `{"state":"active","src":"hook"}` (throttled to one line per 10 min).
- **parked** = snoozed (`s`, `/park [days|s] [note]`): wake = local midnight + N days, or none (someday); due when reached.
- **pinned** (`p`, `/pin` toggle, `sessions pin|unpin SID`): "keep this for later", no date, never decays, listed
  at the very top sorted by last activity. Typing in it keeps it pinned (the hook writes a `pinned` line, so only
  the activity time moves). Unpin → active if open, else unsorted with the 3-day countdown restarting now.
  Park/pin/done gestures themselves do not count as activity; prompts (hook lines) do.
- **done** (`x`, `/done`): hidden unless `D`; with a tab still open it shows `🧹` until swept.
- **stale** (derived): open, not parked/done, idle ≥ `SESSIONS_OPEN_GRACE_DAYS` (1) → `🧹 ?Nd`.
- **unsorted** (derived): closed, not parked/done — including sessions whose only ledger line is `active` —
  shown in the backlog as `?Nd`; archived (implicitly done, no event written) `SESSIONS_DECAY_DAYS` (3) after
  last activity. last activity = max(transcript mtime, last ledger ts, .state mtime, program start time), so
  a freshly resumed pane is never stale.
- Ledger lines with a missing/invalid sid, state, ts or wake are skipped. Notes are stored ASCII-escaped
  (U+2028 etc. round-trip).

## How it works
- Placement: `~/.local/state/ghostty-session/current.json` (20 s timer); windows numbered in registry order,
  tabs by index, splits by `seq`. Only claude/codex surfaces are rows; shells/tmux/the sidebar itself are skipped.
- Transcripts: head 256 KB + tail 96 KB per file, cached in `~/.cache/sessions/cache.json` by mtime+size.
- Fork lineage, precedence: `~/.local/state/sessions/lineage.json` {child: parent} > the running claude's argv
  (`claude -r PARENT --fork-session`, i.e. /fork-here; persisted to lineage.json when first seen) > the
  transcript's `forkedFrom`. Drawn as `└⑂` only when parent and child share a tab; the detail pane names the parent.
- Codex thread id: open rollout/lock fd or `codex resume <id>` argv only. No id → `—`, never swept, not parkable.
  Untested live (no codex was running during the build).
- Redraw: inotify (ctypes) on `current.json`, `events.jsonl`, `lineage.json` and `*.state` in the tab-status
  dir, 500 ms debounce; 60 s tick for ages; SIGWINCH via self-pipe; SIGTERM exits 143 with the terminal restored.
- Resume (`r`/`↵` on a closed row): `new-tab` over D-Bus on the focused window + the ghostty-split-run pending
  file; the new bash runs `claude -r <sid>` / `codex resume <id>`. Marks the session active.
- Sweep: refuses on a stale snapshot, re-reading `current.json` at kill time (the TUI model can be minutes old). For each visible 🧹 row it checks that `/proc/<program>/comm` is
  claude/codex and that fd 0 of the program and of the pane's bash is the surface's tty; on any mismatch the
  pane is skipped (nothing signalled). Then SIGTERM all programs, one shared 3 s wait, SIGKILL survivors, SIGHUP the
  shells → the `sh -c bash` wrapper exits and Ghostty closes the pane. **Verified 19 Oct on a throwaway split: no
  confirm dialog.** `SESSIONS_SWEEP_COMMS` overrides the comm set (tests only).

## Focus (↵ on an open row) — what was tried, 19 Oct
Ghostty exposes `present-surface(t surface-id)` on `/com/mitchellh/ghostty`, which would switch window + tab + split.
No way to learn a pane's surface id was found:
1. Not in the pane's environment (`GHOSTTY_*` has no id) or `/proc`.
2. Notifications would carry it as the action target, but `desktop-notifications = false` in the config, so
   Ghostty emits nothing (verified with dbus-monitor; OSC 777 from focused and unfocused panes → no bus traffic).
3. AT-SPI: tabs expose no actions and no Selection; `grab_focus` on tab/terminal/frame → `atspi_error`;
   `org.gnome.Shell.FocusApp` → AccessDenied. GNOME/Wayland allows no outside activation.
So `↵`/`r` on an open row shows `→ "<window title>" · alt+N` for 4 s (alt+1..8 = goto_tab; `alt+9 = last tab`
only when it is the last tab, else `tab N`). If notifications are ever enabled, step 2 is the path.

## CLI
    sessions                                   open the TUI in a left split of the focused window (ghostty-split-run)
    sessions tui [--once [--done] [--all]] [--width N]
    sessions map [--json]      sessions log
    sessions park SID [--days N | --someday] [--note TEXT] [free words…]      (N ≤ 3650)
    sessions park SID --args "N|s note…"       (what the /park skill runs; one quoted string)
    sessions pin SID [--toggle]   sessions unpin SID     (the /pin skill runs `pin --toggle`)
    sessions done SID          sessions touch SID          sessions focus SID
    sessions resume SID        sessions sweep [--dry-run]  sessions install
Env overrides (tests): SESSIONS_STATE_DIR, SESSIONS_CACHE_DIR, SESSIONS_GHOSTTY_STATE, SESSIONS_TAB_STATUS_DIR,
SESSIONS_CLAUDE_DIR, SESSIONS_CODEX_DIR, SESSIONS_NOW, SESSIONS_DECAY_DAYS, SESSIONS_OPEN_GRACE_DAYS, SESSIONS_SWEEP_COMMS.

## Install / uninstall
`sessions install` (idempotent, every piece applied only when absent):
- hook line in `~/.claude/hooks/tab-status.py` (backup `tab-status.py.bak-20261019`): on UserPromptSubmit it spawns
  `sessions touch <sid>` detached, i.e. the hook writes `active` ledger lines;
- `~/.claude/skills/park/SKILL.md` + `pin/SKILL.md` + `done/SKILL.md`;
- the complete `~/.local/bin/ghostty-session` integration (backup `ghostty-session.bak-20261019`): program kind
  `sessions` (`sessions_argv` skips leading interpreter flags such as `python3 -I`), restore as a LEFT split, skip when a
  sidebar already runs, `split_dir` may return `left` only for kind `sessions`, `save` rejects arguments, `-h/--help`
  prints usage for every subcommand. `SESSIONS_GS_BIN` points install at another copy (tests). The test suite runs
  install against a copy of the pristine backup and requires the result to equal the live file byte for byte.
Uninstall: `cp ~/.claude/hooks/tab-status.py.bak-20261019 ~/.claude/hooks/tab-status.py`;
`cp ~/.local/bin/ghostty-session.bak-20261019 ~/.local/bin/ghostty-session`; `rm -r ~/.claude/skills/park
~/.claude/skills/done ~/.local/state/sessions ~/.cache/sessions ~/.local/bin/sessions`.
Reset intent only: delete `~/.local/state/sessions/events.jsonl` (and `lineage.json`).
Tests: `python3 -I tests/run_tests.py` (from the repo ~/workspace/adhd-ghostty) — 75 checks, fixtures in a temp dir, real throwaway
process trees for the sweep checks (including the kill-time snapshot re-check), a pty for keys/SIGWINCH/SIGTERM.

## Deviations from the spec mockup (also listed at the top of run_tests.py)
1. Tab 3 shows `🧹 ?2d`, backlog `?3d ?2d ?1d` (spec `?5d/?6d`): decay is 3 days; numbers were illustrative.
2. Codex pane without id: `—`, no broom, never swept (spec `🧹 ?`): unidentifiable panes must not be killed; `?` is the help key.
3. Backlog order: due (wake, recency, title) → wake ascending → unsorted by recency → someday by recency (spec: unsorted by countdown).
4. A closed session with only an `active` ledger line is in the backlog (spec implied hidden).
5. "Stale while open" (idle ≥ 1 day) was added; the spec's rules did not say how an open session could be unsorted.
6. Implicit archive writes no `decay` events (state is derivable).
7. Detail pane is 7 rows: rule, title · state, note *or* fork/subagents · sid · cwd, you ×2, claude ×2 (no message count).
8. `r` on an open row = focus hint, same as ↵ (spec: always resume).
9. Pinned (19 Oct, second pass): `📌` section at the top, titled `══` rules, blank lines, cap 40; keys p pin / s snooze / c close.

## Limits
- Split membership of hidden tabs is ghostty-session's best guess (see ghostty-session.md).
- Tab-status titles live in $XDG_RUNTIME_DIR and vanish at reboot; closed sessions then fall back to the
  compaction heading or first prompt. (A persistent title sidecar is the obvious next step.)
- `sessions open`, `resume` and the restore-as-left-split path were not exercised against a live Ghostty tab
  during the build (would have opened tabs in Konrad's window); they reuse the D-Bus + pending-file mechanism
  ghostty-split-run / /fork-here use daily. The hook-driven `touch` is live (first real line landed 19 Oct 16:23).
- No programmatic focus (see above). Sweep needs the snapshot ≤ 60 s old, i.e. the ghostty-session timer running.
