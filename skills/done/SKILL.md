---
name: done
description: Mark this session done in the sessions ledger (never resume it). Use only when the user types /done.
disable-model-invocation: true
---

Run exactly this, with no other steps first (it takes no arguments):

```bash
sessions done "$CLAUDE_CODE_SESSION_ID"
```

Reply with one line: done, and that the tab can be swept from the sessions sidebar (`s`). If it fails, show the error verbatim.
