#!/usr/bin/env python3
"""Claude Code hook: put a status icon + a short session title in the terminal tab.

  ⚪ session open, nothing happening     🚧 working
  🟢 finished — your turn                🔴 blocked on you (permission / question)

Title = "<icon> <session title>". The title comes from, in order:
  1. a /rename  ("custom-title" record in the transcript)
  2. Claude Code's own ai-title record (only written when its terminal-title
     feature is on; it is OFF here via CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1,
     which also switches that generator off — so in practice this never exists)
  3. a 2–4 word title we generate ourselves from the first prompt with one
     detached `claude -p --model haiku` call (claude.ai login, no API key,
     no session persistence); cached per session in $XDG_RUNTIME_DIR
Until the generated title lands: "<icon> <dir> · <first prompt, cleaned>".

Hooks have no controlling tty, so we walk up the process tree to the first
ancestor holding /dev/pts/N (the claude process) and write OSC 2 there. Inside
tmux that sets the pane title; tmux forwards it (set-titles).
Wired up in ~/.claude/settings.json → hooks. Notes: ~/fw16-setup/ghostty-tab-status.md
"""
import json, os, re, subprocess, sys, time

ICON = {"idle": "⚪", "busy": "🚧", "done": "🟢", "ask": "🔴"}
ASK_TOOLS = {"AskUserQuestion", "ExitPlanMode"}
STATE = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "claude-tab-status")
TITLE_MAX = 48
GEN_RETRY_S = 120          # re-spawn the generator if a pending one is older than this
TAG_RE = re.compile(r"</?[a-zA-Z_][\w-]*(?:\s[^>]*)?>")   # <pasted_content id="1">, </x>, <ide_…>


def state_for(ev):
    name = ev.get("hook_event_name", "")
    if name == "SessionStart":
        return "idle"
    if name in ("UserPromptSubmit", "PostToolUse", "PostToolUseFailure"):
        return "busy"
    if name == "PreToolUse":
        return "ask" if ev.get("tool_name") in ASK_TOOLS else "busy"
    if name == "PermissionRequest":
        return "ask"
    if name == "Notification":
        kind = ev.get("notification_type", "")
        return "ask" if kind in ("permission_prompt", "elicitation_dialog") else None
    if name == "Stop":
        return "done"
    if name == "StopFailure":
        return "ask"
    return None


def find_tty():
    pid = os.getppid()
    while pid > 1:
        for fd in (0, 1, 2):
            try:
                t = os.readlink(f"/proc/{pid}/fd/{fd}")
            except OSError:
                continue
            if re.fullmatch(r"/dev/(pts/\d+|tty\d*)", t):
                return t
        try:
            with open(f"/proc/{pid}/stat") as f:
                pid = int(f.read().rsplit(")", 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            return None
    return None


def sid_of(ev):
    return re.sub(r"[^\w-]", "", ev.get("session_id", "")) or "x"


def read(path):
    try:
        with open(path) as f:
            return f.read()
    except OSError:
        return ""


def write(path, text):
    try:
        os.makedirs(STATE, exist_ok=True)
        with open(path, "w") as f:
            f.write(text)
    except OSError:
        pass


def clean(text, limit):
    """Drop markup tags, control chars and whitespace runs; cut to `limit`."""
    text = TAG_RE.sub(" ", text or "")
    text = " ".join(re.sub(r"[\x00-\x1f\x7f]", " ", text).split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def first_prompt_from_transcript(path):
    """First human prompt in the transcript (resume / compact / clear starts)."""
    try:
        with open(path or "", "rb") as f:
            for raw in f:
                if b'"type":"user"' not in raw:
                    continue
                try:
                    rec = json.loads(raw)
                except ValueError:
                    continue
                if rec.get("type") != "user" or rec.get("isMeta"):
                    continue
                content = (rec.get("message") or {}).get("content")
                if isinstance(content, list):
                    content = " ".join(c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text")
                if not isinstance(content, str):
                    continue
                s = content.strip()
                if not s or s.startswith("<command-") or s.startswith("<local-command") or s.startswith("/"):
                    continue
                return s
    except OSError:
        pass
    return ""


def prompt_text(ev):
    if ev.get("hook_event_name") == "UserPromptSubmit":
        p = (ev.get("prompt") or "").strip()
        return "" if p.startswith("/") else p
    return first_prompt_from_transcript(ev.get("transcript_path"))


def label(ev):
    """Fallback: first prompt of the session, cleaned, remembered per session."""
    path = os.path.join(STATE, sid_of(ev))
    lab = read(path)
    if lab:
        return lab
    text = clean(prompt_text(ev), 32)
    if text:
        write(path, text)
    return text


def transcript_title(ev):
    """Title Claude Code itself recorded: /rename wins over its own ai-title."""
    found = {}
    try:
        with open(ev.get("transcript_path") or "", "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 512 * 1024))
            tail = f.read().decode("utf-8", "replace")
        for m in re.finditer(r'\{"type":"(custom-title|ai-title)","(?:customTitle|aiTitle)":"((?:[^"\\]|\\.)*)"', tail):
            found[m.group(1)] = m.group(2)
    except OSError:
        return ""
    raw = found.get("custom-title") or found.get("ai-title")
    if not raw:
        return ""
    try:
        raw = json.loads(f'"{raw}"')
    except ValueError:
        pass
    return clean(raw, TITLE_MAX)


def generated_title(ev, tty):
    """Cached generated title, or spawn the generator (detached) and return ''."""
    sid = sid_of(ev)
    cache = os.path.join(STATE, sid + ".title")
    t = read(cache)
    if t:
        return t
    pending = os.path.join(STATE, sid + ".pending")
    try:
        if time.time() - os.stat(pending).st_mtime < GEN_RETRY_S:
            return ""
    except OSError:
        pass
    text = prompt_text(ev)
    if len(clean(text, 10_000)) < 8:
        return ""
    write(pending, str(os.getpid()))
    spawn_generator(sid, text, tty)
    return ""


def spawn_generator(sid, text, tty):
    """Double-fork so the hook returns at once and the child outlives it."""
    try:
        if os.fork():
            return                      # the hook itself carries on
    except OSError:
        return
    try:
        os.setsid()
        if os.fork():
            os._exit(0)
        devnull = os.open(os.devnull, os.O_RDWR)
        for fd in (0, 1, 2):
            os.dup2(devnull, fd)
        generate(sid, text, tty)
    except Exception:
        pass
    finally:
        os._exit(0)


def generate(sid, text, tty):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("CLAUDE", "ANTHROPIC"))}
    env["CLAUDE_TAB_TITLE_GENERATOR"] = "1"
    body = clean(text, 3000)
    prompt = ("Write a title of 2 to 4 words for a chat session that starts with the message below. "
              "Name the subject, not the request type. Reply with the title only: no quotes, "
              "no trailing period, no preamble.\n\n<message>\n" + body + "\n</message>\n")
    try:
        out = subprocess.run(
            ["claude", "-p", "--model", "haiku", "--setting-sources", "", "--tools", "",
             "--no-session-persistence"],
            input=prompt, capture_output=True, text=True, env=env, timeout=60, cwd="/",
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return
    title = out.strip().splitlines()[0] if out.strip() else ""
    title = re.sub(r"^(title:\s*)?[\"'“”‘’`]*", "", title, flags=re.I).strip("\"'“”‘’` .:")
    title = clean(title, TITLE_MAX)
    if not title or len(title.split()) > 8:
        return
    write(os.path.join(STATE, sid + ".title"), title)
    st = read(os.path.join(STATE, sid + ".state")) or "busy"
    set_title(tty, f"{ICON.get(st, '🚧')} {title}")


def set_title(tty, title):
    if not tty:
        return
    try:
        fd = os.open(tty, os.O_WRONLY | os.O_NOCTTY | os.O_NONBLOCK)
        os.write(fd, f"\033]2;{title}\007".encode())
        os.close(fd)
    except OSError:
        pass


def main():
    if os.environ.get("CLAUDE_TAB_TITLE_GENERATOR"):
        return
    try:
        ev = json.load(sys.stdin)
    except ValueError:
        return
    st = state_for(ev)
    if not st:
        return
    tty = find_tty()
    if not tty:
        return
    write(os.path.join(STATE, sid_of(ev) + ".state"), st)
    name = transcript_title(ev) or generated_title(ev, tty)
    if name:
        title = f"{ICON[st]} {name}"
    else:
        title = f"{ICON[st]} {os.path.basename(ev.get('cwd') or os.getcwd()) or '/'}"
        lab = label(ev)
        if lab:
            title += f" · {lab}"
    set_title(tty, title)


if __name__ == "__main__":
    main()
