---
name: park
description: Park this session (keep it in the sessions backlog, pick it up later). Use only when the user types /park.
argument-hint: "[days|s] [note]"
disable-model-invocation: true
---

Run exactly this, with no other steps first (`$ARGUMENTS` = optional day count or `s` for someday, then a note):

```bash
sessions park "$CLAUDE_CODE_SESSION_ID" --args "$ARGUMENTS"
```

Reply with one line: parked, when it wakes (N days or someday) and the note. If it fails, show the error verbatim.
Tooling: `~/.local/bin/sessions` (docs: ~/fw16-setup/sessions.md).
