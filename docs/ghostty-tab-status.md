# Ghostty tab status icons (7 Oct 2026)

| icon | shell                  | Claude Code                                   |
|------|------------------------|-----------------------------------------------|
| ⚪   | idle at prompt (`⚪ ~/dir`) | session open, no prompt yet                 |
| 🚧   | command running (`🚧 cmd`) | working (prompt submitted / tool calls)     |
| 🟢   | —                      | finished, your turn (Stop)                    |
| 🔴   | —                      | needs you: permission prompt, AskUserQuestion, ExitPlanMode, API error |

Claude title (9 Oct 2026): `<icon> <session title>`, where the title is, in order: a /rename (custom-title
record in the transcript) → Claude Code's own ai-title record → a 2–4 word title the hook generates itself
from the first prompt (one detached `claude -p --model haiku --setting-sources '' --tools '' --no-session-persistence`
on the claude.ai login, ANTHROPIC_API_KEY stripped; ~3 s; cached as $XDG_RUNTIME_DIR/claude-tab-status/<session>.title).
Until it lands: `<icon> <dir> · <first prompt, 32 chars, markup tags stripped>`.
Why the hook generates its own title: CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1 (needed so Claude does not fight the
hook for the tab) also switches off Claude Code's ai-title generator (title manager is built with
disabled=that env), so the 7 Oct "use the ai-title" design never produced a title except in sessions started
without the env. Found 9 Oct when every tab read `<dir> · <first prompt>`. Resumed/compacted sessions take the
first human prompt from the transcript. A .pending marker stops double spawns; retry after 120 s.

Pieces
- ~/.claude/hooks/tab-status.py — hook; walks up /proc to the claude process's /dev/pts/N and writes OSC 2
- ~/.claude/settings.json — hooks on SessionStart, UserPromptSubmit, Pre/PostToolUse(+Failure), PermissionRequest,
  Notification, Stop, StopFailure; env CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1 (else Claude overwrites the title). Backup settings.json.bak-2026-10-07
- ~/.bashrc — Debian title block replaced: PS1 sets ⚪, PS0 sets 🚧 <command>. Backup .bashrc.bak-2026-10-07
- ~/.config/ghostty/config — shell-integration-features = no-title (Ghostty would overwrite with cwd/command)
- ~/.tmux.conf — set-titles-string '#T' so ccw workers' pane titles reach the Ghostty tab (was '#S:#W  tmux')

Limits: a tab shows only its focused split's title. Undo = restore the backups, drop the config line, delete the hook.
