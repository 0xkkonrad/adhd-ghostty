---
name: pin
description: Pin or unpin this session (keep it for later at the top of the sessions sidebar, no date, never decays). Use only when the user types /pin.
disable-model-invocation: true
---

Run exactly this, with no other steps first (it toggles):

```bash
sessions pin "$CLAUDE_CODE_SESSION_ID" --toggle
```

Reply with one line: pinned (kept at the top of the sidebar until unpinned) or unpinned. If it fails, show the error verbatim.
