# adhd-ghostty

Tooling for running many Claude Code / Codex sessions in parallel in [Ghostty](https://ghostty.org)
without losing track of them. Linux (GNOME/Wayland), Ghostty 1.3, Python 3 stdlib only, no root.

The centre piece is `sessions`, a 56-column sidebar that treats the **session** (not the tab) as the
unit of account:

```
📌 🟢 Lisbon Sailing Research                         2h
📌    Referral v3 success metric                      5d

══ 1 ═══════════════════════════════════════════════════
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
══ 2 ═══════════════════════════════════════════════════
 └1 🔴 Welecja Drive Migration                       40m

≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡
    🟢 Welecja member explainer                       0d
    🟢 Split payment check                            0d
       closed with hook active line                  ?3d
       Fork UX question                              ?2d
       Bitwarden shadow vault                        ?1d
       Competitor UK incorporation
≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡+7
 s 🧹 5                                                ?
```

- Top: `📌` pinned sessions ("keep for later", no date, never decays), newest activity first, age on the right.
- `══ N ══` window N, `├N` tab N (= Ghostty `alt+N`), `├─` split, `└⑂` split forked from its parent.
- Left emoji = live status from the Claude Code hook: ⚪ idle, 🚧 working, 🟢 finished (your turn), 🔴 blocked on you.
- Right column = **your intent**, which outlives the tab: blank = active (🟢/🔴 rows show how long
  they have waited), `Nd` = parked, wakes in N days, `?Nd` = unsorted, auto-archived in N days,
  🧹 = still holds a tab, `s` closes it (`🧹 📌` = pinned session whose tab can go).
- Below the `≡` rule: sessions with no tab anywhere, the backlog (cap 20, `m` shows all). `0d` + 🟢 = due today.

Keys: `j/k` move, `↵` focus/resume, `r` resume in a new tab, `p` park (days, note), `i` pin/unpin, `x` done,
`a` re-activate, `s` sweep, `/` filter, `space` detail pane, `D` show done, `m` expand backlog, `?` help, `q` quit.
In a Claude session: `/park [days|s] [note]`, `/pin` (toggle), `/done`. Typing in a parked session re-activates
it; typing in a pinned session keeps it pinned.

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
| `tests/run_tests.py` | 75 checks: render, ledger, sweep with real processes, pty keys, install idempotency |
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
- Codex rows get a thread id only when it is readable from the process; otherwise they show `—` and
  are never swept.
