# sessions — spec (19 Oct 2026)

Konrad's ask: a superlight TUI sidebar for Ghostty that shows every Claude Code / Codex session
as the unit of account, with (a) where it is in Ghostty (window → tab → split), (b) live status,
(c) *intent* (active / parked / done) that outlives the tab, and (d) a backlog of sessions that
have no tab but should be picked up later. Plus a sweep that closes tabs of parked/stale sessions.

Design was agreed in chat on 19 Oct 2026 (session 52cc6a02). This file is the brief for the build.

## Hard constraints
- One Python 3 file: `~/.local/bin/sessions`. Stdlib only (no wcwidth, no curses needed; plain ANSI
  on the alternate screen is fine). No root. Start < 1 s, redraw < 50 ms.
- Ghostty is the source of truth for placement. Never store placement; read it each time.
- Never read whole transcripts. Head + tail seeks only, cached by (path, mtime, size) in
  `~/.local/state/sessions/cache.json`.
- The TUI must never auto-open anything (no browser, no artifacts). Printing a URL is fine.
- Do not modify `ghostty-session` behaviour except where this spec says (program kind "sessions").
- Follow the existing pattern of `~/.local/bin/ghostty-session`, `ghostty-split-run`,
  `ghostty-window-of`, `claude-fork-split` (read them first; reuse their process-walking and
  D-Bus helpers by importing or copying, do not reinvent).

## Data sources (all verified on this machine)
1. Placement: `~/.local/state/ghostty-session/current.json`, refreshed every 20 s by the
   `ghostty-session-save.timer`. Shape: `windows[] { title, focused, tabs[] { title, active,
   surfaces[] { program {kind: claude|codex|tmux|shell, id, cwd, pid, label}, pid, tty, size, dir
   (null|right|down), seq } } }`. First surface of a tab is the tab's anchor, later ones are splits
   in the direction `dir`. Window order in the file = registry order (stable); number them 1..n in
   that order. Tab index = position in `tabs` (1-based, matches Ghostty alt+N).
   Hidden-tab split layouts are a best guess (see ghostty-session.md); we only need membership.
2. Live status: `$XDG_RUNTIME_DIR/claude-tab-status/<sid>.state` = idle|busy|done|ask, written by
   `~/.claude/hooks/tab-status.py`; `<sid>.title` = short title. Icons: idle ⚪ busy 🚧 done 🟢 ask 🔴.
   Codex surfaces: `▫` padded to 2 cells, or 🚧/🔴 when ghostty-session read a run state from the codex
   TUI's terminal title (`program.state` = busy|ask in the snapshot).
3. Transcripts: `~/.claude/projects/<project-slug>/<sid>.jsonl` (slug = cwd with `/` → `-`;
   for cwd /home/kkonrad/workspace it is `-home-kkonrad-workspace`; search all project dirs for
   the sid if cwd unknown). Useful records (one JSON object per line):
   - first `type:"user"` line: `message.content` (string or list) = first prompt; `cwd`,
     `timestamp`, and optional `forkedFrom: {sessionId, messageUuid}` → fork lineage.
   - `type:"custom-title"` (from /rename) → title wins; `type:"ai-title"` `aiTitle` (rarely present).
   - `type:"last-prompt"` with `lastPrompt` (tail of file).
   - last `type:"assistant"` line → last assistant text (tail; content list with `text` blocks).
   - file mtime = last activity.
   Title precedence: custom-title > tab-status .title > ai-title > first 48 chars of first prompt.
4. Codex: `~/.codex/sessions/<yyyy>/<mm>/<dd>/rollout-*.jsonl`. The thread id is in the first
   line (`session_meta` / `id`); user turns are `response_item`/`message` role user, the assistant's
   last answer is `event_msg`/`task_complete.last_agent_message`. The TUI process holds no fd to the
   rollout (the app-server daemon does), so ghostty-session gets id + name from the terminal title the
   TUI sets (`<thread name> | <project>`, run state in front) + `~/.codex/session_index.jsonl`, from
   `codex resume <id>` argv, or from the named thread created right after the pane started (UUIDv7).
   `program.label` = thread name, `program.state` = ask|busy. No id → `—` (not parkable/sweepable).
5. Fork lineage: `forkedFrom.sessionId`. A session is drawn as a child of its parent **only when
   both are open in the same tab**; otherwise lineage is shown in the detail pane, not the tree.

## Intent ledger
- `~/.local/state/sessions/events.jsonl`, append-only, one JSON object per line:
  `{"ts": <unix float>, "sid": "<session id>", "kind": "claude"|"codex", "state":
  "active"|"parked"|"done", "wake": <unix int or null>, "note": "<str or empty>", "src":
  "tui"|"skill"|"hook"|"decay"}`. Last event per sid wins.
- Derived states: a session with no ledger entry is **active** if it has a tab open, else
  **unsorted** (stale). Unsorted sessions auto-archive (synthetic `done`, src=decay) 3 days after
  last activity (transcript mtime); write the decay event when the TUI observes it.
- Reactivation: `sessions touch <sid>` sets active (src=hook). Add ONE call to it in
  `~/.claude/hooks/tab-status.py` on `UserPromptSubmit` (detached, never blocking the hook; must
  not break the hook if `sessions` is missing).
- **pinned** (`p`, `/pin` toggle, `sessions pin|unpin SID`): keep for later, no date, never decays; a prompt
  in a pinned session keeps it pinned (the hook writes a `pinned` line); unpin → active if open, else
  unsorted with the countdown restarting now.
- Skills: `~/.claude/skills/park/SKILL.md` (`/park [days] [note]`, default 1 day) and
  `~/.claude/skills/done/SKILL.md` (`/done`), each running `sessions park|done "$CLAUDE_CODE_SESSION_ID" ...`
  and replying in one line. Model: `disable-model-invocation: true`, like fork-here.

## Subcommands
    sessions                      # = `sessions open`: open the TUI in a LEFT split of the focused
                                  #   Ghostty window via `ghostty-split-run left --focused -- sessions tui`
    sessions tui [--once] [--width N]   # the sidebar; --once renders one frame to stdout and exits
                                  #   (used by tests; must produce exactly the mockup format)
    sessions map [--json]         # the merged model (placement + status + intent), JSON
    sessions log                  # git-log style list, newest first: sid8 age status title intent
    sessions park SID [--days N|--someday] [--note TEXT]
    sessions done SID
    sessions touch SID            # → active (hook)
    sessions sweep [--dry-run]    # close every sweepable pane (see below)
    sessions focus SID            # bring that pane to front (see Focus)
    sessions resume SID           # new tab in the focused window running `claude -r SID`
                                  #   (or `codex resume <thread>`), via D-Bus new-tab + pending file
    sessions install              # add the hook line + skills + program kind; idempotent; prints what it did

## TUI rendering — the agreed mockup (56 cols; width = split width, min 40; pinned + titled rules 19 Oct)
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

══ keys ════════════════════════════════════════════════
 ↵ open       r resume     p pin        s snooze
 x done       a active     / filter     ␣ detail
 D show done  m more       ? help       q quit
 c 🧹 5                                                ?
```
Grammar (no legend on screen; `?` key shows it):
- Every section rule is `══ <title> ` + `═` fill to the width: `📌 pinned`, `window N` (registry order),
  `history`. The closing rule of history is `═` fill with `+N` right-aligned = hidden rows (cap 40; `m` lifts it).
  One literal empty line after the pinned section and one before history. The pinned section (rule + rows +
  blank) is omitted entirely when nothing is pinned.
- Search: `/term ↵` adds `══ found N ══` after the history's closing rule (blank line between): the sessions
  whose user/assistant turns or title contain the term (all-time, grep -l over every transcript and rollout;
  tool output, memory and system reminders do not count), minus those already on screen, newest first,
  cap 40 with `+N` (`m` lifts). Row = backlog shape (live emoji when open, `📌 ` before the age when
  pinned, right column = age). A row whose title misses the term is followed by `      › <passage>`, dim,
  the term near its start. Footer while a filter is active: ` /term` left, `c 🧹 N ?` right; the keys grid
  reads `Esc clear` instead of `/ filter`. Filtered windows with no matching tab drop their rule.
- Pinned rows: `📌` (2 cells) in the tree column, then the 2-cell status slot (live emoji when the session has
  a tab, two spaces otherwise), title; right column = age since last activity (`m`/`h`/`d`); sorted by last
  activity, newest first, no cap. Pinned sessions never appear in history.
- Column 0 = cursor gutter: `▶` on the selected row, else space (on a pinned row the `▶` replaces the space
  after `📌`). Column 1 = tree: `├`/`└` + tab index for tabs; ` ├─`/` └─` for splits; ` └⑂` for a split forked
  from its tab parent.
- Status slot is always exactly 2 cells: emoji (⚪🚧🟢🔴) or `▫ ` for codex. Title starts after one space.
  Titles are truncated to fit with `…`.
- Right column, right-aligned to width, meaning by row class:
  - active with tab: blank, except 🟢/🔴 rows show how long they have waited (`12m`, `1h`, `2d`).
  - parked with tab: `🧹` + ` Nd` days until wake (blank after broom if someday).
  - pinned with tab: `🧹 📌` (closable: the session lives in the pinned list, the tab is not the session).
  - stale with tab: `🧹 ?Nd` days until auto-archive. Done with tab: `🧹`. Codex without id: `—`.
    Closed codex threads (non-subagent rollouts touched within the decay) are backlog rows like any other.
  - history (no tab): parked `Nd` (`0d` due today, then 🟢 in the status slot), someday blank, unsorted `?Nd`.
    Order: due → wake ascending → unsorted by recency → someday by recency.
- Footer: a blank line, a dim `══ keys ══` rule, the cheatsheet as a 4-column grid (keys bold yellow; shown
  when the terminal has ≥ 20 rows and ≥ 53 columns; `--once` prints it uncoloured), then ` c 🧹 N` (N = closable panes among the visible rows) left, `?` right. Nothing else.
- Width handling: `unicodedata.east_asian_width` (W/F = 2, everything else 1; U+FE0F, U+200D and combining
  marks 0). Emoji VS16 sequences must not appear; use the exact code points above.
- Redraw triggers: inotify (via `ctypes` libc inotify, stdlib only) on current.json, events.jsonl, lineage.json
  and `*.state` in the claude-tab-status dir; fall back to 2 s polling if inotify is unavailable. Plus a 60 s
  timer for ages.

## Keys
    j/k or arrows  move      ↵   focus hint if open, else resume     r  resume in new tab
    p  pin / unpin           s   snooze (park): "days [1] or s" then "note"; Esc cancels
    c  close (sweep) all visible 🧹 panes (confirm with y when N > 3)
    x  done                  a   re-activate
    /  filter by title while typing; ↵ also greps every transcript + rollout → `found` section; Esc clears
    space  toggle detail pane (bottom 7 rows)
    D  show done sessions    m   whole history    q  quit     ?  help overlay
Detail pane (when open): title · state · age/wake; note, or `fork of <title>` / subagents N · sid · cwd;
`you  <last prompt, 2 lines>`; `claude <last assistant text, 2 lines>`.

## Focus (↵ on an open row) — spike first, then implement the best that works
Ghostty's app object `/com/mitchellh/ghostty` exposes action `present-surface` (param `t`, uint64
surface id). We do not yet know how to map a pane → surface id. Try, in order, and record what
works in `~/fw16-setup/sessions.md`:
1. Any env var / OSC / `/proc` clue on the pane's shell giving the surface id.
2. Ghostty attaches the surface id to notifications it raises (OSC 777/OSC 9): monitor the session
   bus for the notification (`gdbus monitor` or `dbus-monitor`) while emitting one from a known pane,
   and read the action target. If it works, the TUI can fingerprint panes lazily (once per pane,
   cached by pid) by writing the OSC to the pane's tty.
3. Fallback: raise the right window (reuse `ghostty-window-of` rank matching + AT-SPI) and print
   "press alt+N" in the footer for 3 s.
Never leave the user's focus in a broken state; if nothing works, do the fallback.

## Sweep
Sweepable pane = any surface in the tree whose session is parked/done/unsorted (right column has
text or broom). Closing: terminate the pane's program (claude: SIGTERM, wait 2 s, SIGKILL), then
the pane's `/bin/bash` (SIGHUP), so the `/bin/sh -c /bin/bash` wrapper exits and Ghostty closes the
surface. Verify on a throwaway pane that NO confirm dialog appears (config has no
confirm-close-surface override). Never kill a pane whose session is active. `--dry-run` lists.

## ghostty-session integration
Add program kind `sessions` to `~/.local/bin/ghostty-session` detection (a shell whose child is
`python3 …/sessions tui`), restored as `sessions tui`. Keep the change minimal and documented.

## Verification requirements (the builder writes these; the verifier runs them)
- `tests/` next to a fixtures dir under `~/fw16-setup/sessions-tests/`: a frozen `current.json`,
  tab-status dir, a few synthetic transcripts and a ledger that together reproduce the mockup;
  `sessions tui --once --width 56` with env pointing at the fixtures must equal the mockup byte for
  byte (trailing spaces stripped). Env overrides: `SESSIONS_STATE_DIR`, `SESSIONS_GHOSTTY_STATE`,
  `SESSIONS_TAB_STATUS_DIR`, `SESSIONS_CLAUDE_DIR`, `SESSIONS_NOW` (unix time for stable ages).
- Width test at 40 and 120 columns: no line exceeds width, right column stays aligned.
- Ledger round trip: park → map shows parked with the right day count; touch → active; decay after
  3 days with SESSIONS_NOW advanced.
- Live smoke: `sessions map` on the real machine lists every claude surface in current.json with a
  title and a status; `sessions tui --once` on real data renders without exceptions.
- Key handling tested through a pty (`pty.fork` + feeding bytes) for j/k/p/x/q at least.

## Docs
`~/fw16-setup/sessions.md`: what it does, the grammar, keys, how focus/sweep work and what was
verified, ops (state files, how to reset), and the limits found during the build.
