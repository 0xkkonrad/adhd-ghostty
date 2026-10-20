#!/usr/bin/env python3
"""Tests for ~/.local/bin/sessions. Builds fixtures in a temp dir, renders, compares to the agreed
mockup (see MOCKUP CORRECTIONS), checks widths, the ledger, decay, sweep safety with real processes,
fork lineage, and keys through a pty.            python3 -I run_tests.py

MOCKUP CORRECTIONS — every difference between the spec mockup (sessions-spec.md) and EXPECTED below:
  1. tab 3 right column `🧹 ?2d` (spec: `?5d`): the fixture is 1.5 days idle and decay is 3 days, so 1.5 days
     remain → ceil = 2d. The spec number was illustrative.
  2. codex split right column `—` (spec: `🧹 ?`): a codex pane without a thread id cannot be identified, so it is
     never sweepable (no broom) and `?` collides with the help key.
  3. backlog countdowns `?3d ?2d ?1d` (spec: `?5d ?6d`): 3-day decay, see 1.
  4. backlog order: due (wake, then recency: Welecja's transcript is newer than Split's; park/pin/done gestures do
     not count as activity), then wake ascending, then unsorted by recency, then someday by recency.
     Spec listed unsorted by countdown.
  7. pinned (19 Oct; moved 20 Oct): two pinned rows between the windows and the history (Lisbon = open, shows its live 🟢 and `🧹 📌` in the
     tree; Referral = closed, 5d since last activity), titled `══ … ═` rules (`📌 pinned`, `window N`, `history`),
     blank lines between sections, history cap 40 so no +N here. Keys: p pin, s snooze, c close.
  5. extra rows: "closed with hook active line" (a closed session whose only ledger line is `active` must show
     in the backlog) and "someday item q" (fixture filler to exercise the +N cap).
  6. titles come from the fixture (e.g. "Split payment check please"), not the spec's shortened labels.
"""
import fcntl
import functools
import json
import os
import pty
import select
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

json.dumps = functools.partial(json.dumps, separators=(",", ":"))
REPO = Path(__file__).resolve().parent.parent
EXE = os.environ.get("SESSIONS_EXE") or str(REPO / "bin/sessions")
ROOT = Path(tempfile.mkdtemp(prefix="sessions-test-"))
NOW = time.time()
DAY = 86400
CWD = "/home/kkonrad/workspace"
PROJ = ROOT / "claude/projects/-home-kkonrad-workspace"
TAB = ROOT / "tab-status"
GS = ROOT / "ghostty-session"
ST = ROOT / "state"
BOOT = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
for d in (PROJ, TAB, GS, ST, ROOT / "codex/sessions", ROOT / "claude/sessions", ROOT / "cache"):
    d.mkdir(parents=True)
SIDS = {k: f"{i:08x}-{i:04x}-{i:04x}-{i:04x}-{i:012x}" for i, k in enumerate("abcdefghijklmnopqrstuvwxyz", 1)}
CHILDREN = []


def write_transcript(sid, first, last_prompt, last_assistant, mtime, forked_from=None, compact=None):
    lines = []
    if compact:
        lines.append(json.dumps({"type": "user", "isCompactSummary": True, "cwd": CWD, "sessionId": sid,
                                 "message": {"role": "user", "content": "This session is being continued from a previous conversation.\n\nSummary:\n# Session summary: " + compact + " — continued\n"}}))
    first_rec = {"parentUuid": None, "type": "user", "cwd": CWD, "sessionId": sid, "timestamp": "2026-10-18T09:00:00.000Z",
                 "message": {"role": "user", "content": first}}
    if forked_from:
        first_rec["forkedFrom"] = {"sessionId": forked_from, "messageUuid": "x"}
    lines.append(json.dumps(first_rec))
    lines.append(json.dumps({"type": "assistant", "sessionId": sid, "message": {"role": "assistant", "content": [{"type": "text", "text": last_assistant}]}}))
    lines.append(json.dumps({"type": "last-prompt", "lastPrompt": last_prompt, "sessionId": sid}))
    p = PROJ / f"{sid}.jsonl"
    p.write_text("\n".join(lines) + "\n")
    os.utime(p, (mtime, mtime))


def status(sid, st, since_ago, title):
    p = TAB / f"{sid}.state"
    p.write_text(st)
    os.utime(p, (NOW - since_ago, NOW - since_ago))
    (TAB / f"{sid}.title").write_text(title)


def midnight_plus(days):
    d = datetime.fromtimestamp(NOW).date() + timedelta(days=days)
    return int(datetime(d.year, d.month, d.day).timestamp())


T = {"a": ("LP Refresh Competitor", "idle", 2 * 3600), "b": ("Design system landing page", "busy", 60),
     "c": ("Shotgun split tree review", "idle", 1.5 * DAY), "d": ("Startup Valuation Multiples", "done", 3 * 3600),
     "e": ("UGC Rate Negotiation", "done", 12 * 60), "f": ("Projecting WAU growth", "done", 3600),
     "g": ("Lisbon Sailing Research", "done", 2 * 3600), "h": ("Stale Docs Cleanup", "done", 5 * 60),
     "i": ("Multi-Session Dashboard", "busy", 10), "j": ("Welecja Drive Migration", "ask", 40 * 60)}
for k, (title, st, ago) in T.items():
    status(SIDS[k], st, ago, title)
    write_transcript(SIDS[k], f"first prompt of {title}", f"last prompt of {title} with several words to wrap around the pane",
                     f"answer about {title} that is long enough to need wrapping onto a second line of the detail pane",
                     NOW - (1.5 * DAY if k == "c" else 2 * 3600 if k == "g" else 600), forked_from=SIDS["e"] if k == "f" else None)
write_transcript(SIDS["k"], "Split payment check please", "pay kanad", "paid 7/12", NOW - 2 * DAY)
write_transcript(SIDS["l"], "Welecja member explainer", "draft it", "drafted", NOW - DAY)
write_transcript(SIDS["m"], "Referral v3 success metric", "which metric", "activation", NOW - 5 * DAY)
write_transcript(SIDS["n"], "i just forked a session using /fork how do i pick it up", "ok", "use -r", NOW - 1.2 * DAY)
write_transcript(SIDS["o"], "set up a bitwarden shadow vault for secrets", "ok", "done", NOW - 2.2 * DAY)
write_transcript(SIDS["p"], "map competitor UK incorporations", "ok", "38 mapped", NOW - 1800, compact="Competitor UK incorporation")
for k in "qrstu":
    write_transcript(SIDS[k], f"someday item {k}", "ok", "ok", NOW - 3600)
write_transcript(SIDS["v"], "a finished thing", "ok", "ok", NOW - 3600)
write_transcript(SIDS["w"], "closed with hook active line", "ok", "ok", NOW - 2 * 3600)

ev = []
def park(k, days=None, note=""):
    ev.append({"ts": NOW - 100, "sid": SIDS[k], "kind": "claude", "state": "parked",
               "wake": midnight_plus(days) if days is not None else None, "note": note, "src": "tui"})
park("a"); park("d", 4, "before Hugo call"); park("h")
park("k", 0, "aleks owes"); park("l", 0, "after takeout"); park("p")
ev.append({"ts": NOW - 3 * 3600, "sid": SIDS["g"], "kind": "claude", "state": "pinned", "wake": None, "note": "", "src": "tui"})
ev.append({"ts": NOW - 5 * DAY, "sid": SIDS["m"], "kind": "claude", "state": "pinned", "wake": None, "note": "", "src": "skill"})
for k in "qrstu":
    park(k)
ev.append({"ts": NOW - 50, "sid": SIDS["v"], "kind": "claude", "state": "done", "wake": None, "note": "", "src": "tui"})
ev.append({"ts": NOW - 3600, "sid": SIDS["w"], "kind": "claude", "state": "active", "wake": None, "note": "", "src": "hook"})
ev.append({"ts": NOW, "state": "parked", "wake": None})                          # missing sid → ignored
ev.append({"ts": "bad", "sid": SIDS["b"], "state": "done"})                       # bad ts → ignored
(ST / "events.jsonl").write_text("\n".join(json.dumps(e) for e in ev) + "\nnot json\n")


def surf(k, kind="claude", pid=1, dir_=None, prog_pid=None, wrapper=None, tty=None, label=None):
    sid = SIDS[k] if k else None
    return {"program": {"kind": kind, "id": sid, "cwd": CWD, "pid": prog_pid or 999990 + pid,
                        "label": label or (T.get(k, ("",))[0] if k else None)},
            "pid": wrapper or 999900 + pid, "tty": tty, "size": None, "dir": dir_, "seq": pid}


def snapshot(windows, saved_at=NOW, boot=BOOT):
    return {"saved_at": saved_at, "boot_id": boot, "windows": windows}


WINDOWS = [
    {"title": "🟢 Competitor Positioning Analysis", "focused": True, "tabs": [
        {"title": "t1", "active": False, "surfaces": [surf("a", pid=1)]},
        {"title": "t2", "active": False, "surfaces": [surf("b", pid=2)]},
        {"title": "t3", "active": False, "surfaces": [surf("c", pid=3), surf(None, "codex", 4, "right"), surf("d", pid=5, dir_="right")]},
        {"title": "t4", "active": False, "surfaces": [surf("e", pid=6), surf("f", pid=7, dir_="right")]},
        {"title": "t5", "active": False, "surfaces": [surf("g", pid=8)]},
        {"title": "t6", "active": False, "surfaces": [surf("h", pid=9)]},
        {"title": "t7", "active": True, "surfaces": [surf("i", pid=10)]},
    ]},
    {"title": "🔴 Welecja Drive Migration", "focused": False, "tabs": [{"title": "t1", "active": True, "surfaces": [surf("j", pid=11)]}]},
]
(GS / "current.json").write_text(json.dumps(snapshot(WINDOWS)))

EXPECTED = """\
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
 └7 🚧 Multi-Session Dashboard
══ window 2 ════════════════════════════════════════════
 └1 🔴 Welecja Drive Migration                       40m

══ 📌 pinned ═══════════════════════════════════════════
📌 🟢 Lisbon Sailing Research                         2h
📌    Referral v3 success metric                      5d

══ history ═════════════════════════════════════════════
    🟢 Welecja member explainer                       0d
    🟢 Split payment check please                     0d
       closed with hook active line                  ?3d
       i just forked a session using /fork how do i… ?2d
       set up a bitwarden shadow vault for secrets   ?1d
       Competitor UK incorporation
       someday item q
       someday item r
       someday item s
       someday item t
       someday item u
════════════════════════════════════════════════════════

══ keys ════════════════════════════════════════════════
 ↵ open  r resume  p pin  s snooze  x done  a active
 / filter  ␣ detail  D show done  m more  ? help  q quit
 c 🧹 5                                                ?"""


def env(now=NOW, state=ST, gs=GS, extra=None):
    e = dict(os.environ)
    e.update({"SESSIONS_STATE_DIR": str(state), "SESSIONS_GHOSTTY_STATE": str(gs), "SESSIONS_TAB_STATUS_DIR": str(TAB),
              "SESSIONS_CLAUDE_DIR": str(ROOT / "claude"), "SESSIONS_CODEX_DIR": str(ROOT / "codex"),
              "SESSIONS_CACHE_DIR": str(ROOT / "cache"), "SESSIONS_NOW": str(now)})
    e.update(extra or {})
    return e


def run(*args, now=NOW, state=ST, gs=GS, extra=None):
    r = subprocess.run([EXE, *args], capture_output=True, text=True, env=env(now, state, gs, extra), timeout=60)
    return r.returncode, r.stdout, r.stderr


def cells(s):
    return sum(0 if (c in "️‍" or unicodedata.category(c) == "Mn") else (2 if unicodedata.east_asian_width(c) in "WF" else 1) for c in s)


def backlog_lines(out):
    """Rows between the opening ≡ rule and the closing ≡ rule (which may carry +N)."""
    lines = out.splitlines()
    i = next(i for i, l in enumerate(lines) if l.startswith("══ history "))
    j = next(j for j, l in enumerate(lines) if j > i and l.startswith("═" * 20))
    return [l for l in lines[i + 1:j] if l.strip()]


def strip_ansi(s):
    import re
    return re.sub(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07", "", s)


fails = 0
def check(name, ok, detail=""):
    global fails
    print(("PASS " if ok else "FAIL ") + name + (("\n" + detail) if (detail and not ok) else ""))
    if not ok:
        fails += 1


def cleanup():
    for p in CHILDREN:
        try:
            os.killpg(p.pid, signal.SIGKILL) if isinstance(p, subprocess.Popen) else os.kill(p, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            pass


try:
    # 1. mockup
    rc, out, err = run("tui", "--once", "--width", "56")
    got = "\n".join(l.rstrip() for l in out.rstrip("\n").splitlines())
    check("mockup 56 cols (see MOCKUP CORRECTIONS)", rc == 0 and got == EXPECTED, f"rc={rc}\n--- got ---\n{out}\n--- expected ---\n{EXPECTED}\n{err}")

    # 2. widths
    import re
    for w in (40, 120):
        rc, out, err = run("tui", "--once", "--width", str(w))
        lines = out.rstrip("\n").splitlines()
        over = [l for l in lines if cells(l) > w]
        right = [l for l in lines[:-1] if re.search(r"(\s\d+[dmh]|\s\?\d+d|\s🧹( \S+)?|\s—)$", l)]
        bad = [l for l in right if cells(l) != w]
        check(f"width {w}: no overflow, right column aligned", rc == 0 and not over and not bad and len(lines) == len(EXPECTED.splitlines()) - (4 if w < 56 else 0),
              f"over={over[:3]} bad={bad[:3]} n={len(lines)}\n{out}")

    # 3. ledger round trip (scratch state)
    st2 = ROOT / "state2"
    shutil.copytree(ST, st2)
    sid = SIDS["b"]
    rc, out, err = run("park", sid, "--days", "2", "--note", "tomorrow-ish", state=st2)
    m = json.loads(run("map", "--json", state=st2)[1])["sessions"][sid]
    check("park → parked, 2d, note", rc == 0 and m["state"] == "parked" and m["note"] == "tomorrow-ish"
          and (datetime.fromtimestamp(m["wake"]).date() - datetime.fromtimestamp(NOW).date()).days == 2, f"{out}{err} {m}")
    rc, out, _ = run("tui", "--once", "--width", "56", state=st2)
    check("park shows 🧹 2d in tree", re.search(r"^ ├2 🚧 Design system landing page\s+🧹 2d$", out, re.M) is not None, out)
    run("touch", sid, state=st2)
    check("touch → active", json.loads(run("map", "--json", state=st2)[1])["sessions"][sid]["state"] == "active")
    run("done", sid, state=st2)
    check("done → done", json.loads(run("map", "--json", state=st2)[1])["sessions"][sid]["state"] == "done")
    rc, out, _ = run("tui", "--once", "--width", "56", state=st2)
    check("done with tab → 🧹 alone", re.search(r"Design system landing page\s+🧹$", out, re.M) is not None, out)
    rc, out, err = run("sweep", "--dry-run", state=st2)
    check("sweep --dry-run lists the done pane (identity check fails on fake pids)", "Design system landing page" in out and "skipped" in out, out + err)
    rc, out, err = run("park", sid, "--days", "x", state=st2)
    check("park --days x → usage error", rc == 2 and "usage" in err, f"{rc} {err}")
    rc, out, err = run("park", sid, "--days", "99999", state=st2)
    check("park --days 99999 → rejected", rc == 2, f"{rc} {err}")
    note = "line one line two"
    run("park", sid, "--note", note, state=st2)
    check("U+2028 in note survives", json.loads(run("map", "--json", state=st2)[1])["sessions"][sid]["note"] == note)
    rc, out, _ = run("park", sid, "--args", "3 before hugo call", state=st2)
    check("skill form --args '3 before hugo call'", "in 3d" in out and "before hugo call" in out, out)
    rc, out, _ = run("park", sid, "--args", "s", state=st2)
    check("skill form --args 's' → someday", "someday" in out, out)

    # 4. state model
    S4 = json.loads(run("map", "--json", now=NOW + 4 * DAY)[1])["sessions"]
    check("decay branch taken: 'w' (ledger-active, closed) → done + hidden after 3d",
          S4.get(SIDS["w"], {}).get("state") == "done" and S4[SIDS["w"]].get("hidden") is True, str(S4.get(SIDS["w"])))
    check("decay: unmarked 'o' out of the universe (or done) after 3d", SIDS["o"] not in S4 or S4[SIDS["o"]]["state"] == "done")
    check("decay: parked 'k' survives and is due", S4[SIDS["k"]]["state"] == "parked" and S4[SIDS["k"]]["due"])
    S30 = json.loads(run("map", "--json", now=NOW + 30 * DAY)[1])["sessions"]
    check("pinned never decays (30 d): 'm' still pinned, not hidden", S30[SIDS["m"]]["state"] == "pinned" and not S30[SIDS["m"]].get("hidden"), str(S30.get(SIDS["m"])))
    rc, out, _ = run("tui", "--once", "--width", "56")
    body = "\n".join(backlog_lines(out))
    check("pinned sessions absent from the backlog", "Referral v3" not in body and "Lisbon" not in body, body)
    check("pinned + open → 🧹 📌 in the tree and 🟢 in the section", re.search(r"^ ├5 🟢 Lisbon Sailing Research\s+🧹 📌$", out, re.M) and re.search(r"^📌 🟢 Lisbon", out, re.M), out)
    stp = ROOT / "state-pin"; shutil.copytree(ST, stp)
    run("touch", SIDS["g"], state=stp)
    Sp = json.loads(run("map", "--json", state=stp)[1])["sessions"]
    lastp = [json.loads(l) for l in (stp / "events.jsonl").read_text().split("\n") if l.strip().startswith("{")][-1]
    check("touch keeps pinned (hook writes a pinned line)", Sp[SIDS["g"]]["state"] == "pinned" and lastp["state"] == "pinned" and lastp["src"] == "hook", str(lastp))
    run("unpin", SIDS["g"], state=stp); run("unpin", SIDS["m"], state=stp)
    Sp = json.loads(run("map", "--json", state=stp)[1])["sessions"]
    check("unpin open → active; unpin closed → unsorted with countdown restarted (3d)",
          Sp[SIDS["g"]]["state"] == "active" and Sp[SIDS["m"]]["state"] == "unsorted" and Sp[SIDS["m"]]["archive_in"] == 3, f"{Sp[SIDS['g']]['state']} {Sp[SIDS['m']]['state']} {Sp[SIDS['m']]['archive_in']}")
    rc, out, _ = run("tui", "--once", "--width", "56", state=stp)
    check("nothing pinned → no section, no leading blank line", out.startswith("══ window 1 ") and "📌" not in out, out[:120])
    run("pin", SIDS["m"], state=stp)
    rc, out, _ = run("tui", "--once", "--width", "56", state=stp)
    L = out.splitlines(); pi = next((i for i, l in enumerate(L) if l.startswith("══ 📌 pinned ═")), -1)
    check("pin CLI → titled section between the windows and the history, with age", pi > 0 and L[0].startswith("══ window 1 ") and L[pi - 1] == ""
          and L[pi + 1].startswith("📌    Referral v3 success metric") and L[pi + 1].endswith("5d") and L[pi + 2] == "" and L[pi + 3].startswith("══ history "), out[:600])
    rc, out, _ = run("pin", SIDS["m"], "--toggle", state=stp)
    check("pin --toggle on a pinned session unpins", "unpinned" in out, out)
    stc = ROOT / "state-cap"; shutil.copytree(ST, stc)
    with open(stc / "events.jsonl", "a") as fh:
        for i in range(50):
            fh.write(json.dumps({"ts": NOW - 100, "sid": f"{900 + i:08x}-0000-0000-0000-000000000000", "kind": "claude", "state": "parked", "wake": None, "note": "", "src": "tui"}) + "\n")
    rc, out, _ = run("tui", "--once", "--width", "56", state=stc)
    check("history cap 40 with +N", len(backlog_lines(out)) == 40 and re.search(r"═+\+\d+$", out, re.M), str(len(backlog_lines(out))) + out[-80:])
    rc, out2, _ = run("tui", "--once", "--width", "56", "--all", state=stc)
    check("--all lifts the cap", len(backlog_lines(out2)) > 40)
    S = json.loads(run("map", "--json")[1])["sessions"]
    check("closed + hook-active line → unsorted in backlog", S[SIDS["w"]]["state"] == "unsorted" and S[SIDS["w"]]["archive_in"] == 3, str(S[SIDS["w"]]))
    check("bad ledger lines ignored (b still active)", S[SIDS["b"]]["state"] == "active")
    rc, out, _ = run("tui", "--once", "--width", "56", "--done")
    check("--done shows closed done row with blank right column", re.search(r"^       a finished thing$", out, re.M) is not None, out)
    rc, out, _ = run("tui", "--once", "--width", "56", "--all")
    check("--all expands the backlog", "someday item u" in out and not re.search(r"═\+\d", out), out)
    rc, out, _ = run("tui", "--once", "--width", "56", extra={"SESSIONS_OPEN_GRACE_DAYS": "5"})
    check("SESSIONS_OPEN_GRACE_DAYS=5 → tab 3 not stale", re.search(r"Shotgun split tree review$", out, re.M) is not None, out)

    # 5. fork lineage: lineage.json beats transcript; argv --fork-session is persisted
    st4 = ROOT / "state4"
    shutil.copytree(ST, st4)
    (st4 / "lineage.json").write_text(json.dumps({SIDS["d"]: SIDS["c"]}))
    rc, out, _ = run("tui", "--once", "--width", "56", state=st4)
    check("lineage.json → ⑂ on Startup Valuation", " │ └⑂ 🟢 Startup Valuation Multiples" in out, out)
    # real process with fork argv as the program of pane f
    forkproc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)", "-r", SIDS["e"], "--fork-session"],
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    CHILDREN.append(forkproc)
    gs5 = ROOT / "gs5"; gs5.mkdir()
    W5 = json.loads(json.dumps(WINDOWS))
    W5[0]["tabs"][3]["surfaces"][1]["program"]["pid"] = forkproc.pid
    (gs5 / "current.json").write_text(json.dumps(snapshot(W5)))
    st5 = ROOT / "state5"; shutil.copytree(ST, st5)
    # remove the transcript fork edge for f to prove argv alone works
    pf = PROJ / f"{SIDS['f']}.jsonl"; orig = pf.read_text(); mt = os.stat(pf).st_mtime
    pf.write_text(orig.replace(',"forkedFrom":{"sessionId":"' + SIDS["e"] + '","messageUuid":"x"}', "")); os.utime(pf, (mt, mt))
    rc, out, _ = run("tui", "--once", "--width", "56", state=st5, gs=gs5)
    lin = json.loads((st5 / "lineage.json").read_text()) if (st5 / "lineage.json").exists() else {}
    check("argv --fork-session → ⑂ and lineage.json persisted", " │ └⑂ 🟢 Projecting WAU growth" in out and lin.get(SIDS["f"]) == SIDS["e"], out + str(lin))
    pf.write_text(orig); os.utime(pf, (mt, mt))

    # 6. sweep safety with real process trees:  wrapper bash → bash → sleep   (comm override for tests only)
    def tree():
        p = subprocess.Popen(["bash", "-c", "bash -c 'sleep 300; sleep 1'; sleep 1"], stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        CHILDREN.append(p)
        time.sleep(0.4)
        inner = int(open(f"/proc/{p.pid}/task/{p.pid}/children").read().split()[0])
        prog = int(open(f"/proc/{inner}/task/{inner}/children").read().split()[0])
        return p.pid, inner, prog
    wa, ia, pa = tree()      # active pane
    wp, ip, pp = tree()      # parked pane
    gs6 = ROOT / "gs6"; gs6.mkdir()
    W6 = [{"title": "w", "focused": True, "tabs": [
        {"title": "t1", "active": True, "surfaces": [surf("b", pid=1, prog_pid=pa, wrapper=wa, tty="/dev/null")]},
        {"title": "t2", "active": False, "surfaces": [surf("a", pid=2, prog_pid=pp, wrapper=wp, tty="/dev/null")]}]}]
    (gs6 / "current.json").write_text(json.dumps(snapshot(W6)))
    st6 = ROOT / "state6"; shutil.copytree(ST, st6)
    comms = {"SESSIONS_SWEEP_COMMS": "sleep"}
    rc, out, err = run("sweep", "--dry-run", state=st6, gs=gs6, extra=comms)
    check("dry-run names only the parked pane", "LP Refresh" in out and "Design system" not in out and f"TERM {pp}" in out, out + err)
    rc, out, err = run("sweep", state=st6, gs=gs6, extra=comms)
    time.sleep(0.5)
    alive = lambda p: os.path.exists(f"/proc/{p}") and open(f"/proc/{p}/stat").read().split()[2] != "Z"
    check("sweep: parked pane's program + shell gone", not alive(pp) and not alive(ip), f"{out}{err} prog={alive(pp)} sh={alive(ip)}")
    check("sweep: active pane untouched", alive(pa) and alive(ia), f"prog={alive(pa)} sh={alive(ia)}")
    # refusal on stale snapshot (saved_at old) and on boot_id mismatch; parked pane re-created
    wp2, ip2, pp2 = tree()
    W6[0]["tabs"][1]["surfaces"] = [surf("a", pid=2, prog_pid=pp2, wrapper=wp2, tty="/dev/null")]
    (gs6 / "current.json").write_text(json.dumps(snapshot(W6, saved_at=NOW - 120)))
    rc, out, err = run("sweep", state=st6, gs=gs6, extra=comms)
    check("sweep refuses on saved_at > 60 s", rc == 1 and "stale" in err and alive(pp2), f"{rc} {out} {err}")
    (gs6 / "current.json").write_text(json.dumps(snapshot(W6, boot="00000000-0000-0000-0000-000000000000")))
    rc, out, err = run("sweep", state=st6, gs=gs6, extra=comms)
    check("sweep refuses on boot_id mismatch", rc == 1 and "stale" in err and alive(pp2), f"{rc} {out} {err}")
    rc, out, _ = run("tui", "--once", "--width", "56", state=st6, gs=gs6, extra=comms)
    check("footer shows 'snapshot stale'", "snapshot stale" in out.splitlines()[-1], out)
    (gs6 / "current.json").write_text(json.dumps(snapshot(W6)))
    rc, out, err = run("sweep", state=st6, gs=gs6, extra={"SESSIONS_SWEEP_COMMS": "claude"})
    time.sleep(0.3)
    check("comm mismatch → skipped, nothing killed", "skipped" in out and alive(pp2) and alive(ip2), f"{out}{err}")
    W6[0]["tabs"][1]["surfaces"][0]["tty"] = "/dev/pts/999"
    (gs6 / "current.json").write_text(json.dumps(snapshot(W6)))
    rc, out, err = run("sweep", state=st6, gs=gs6, extra=comms)
    time.sleep(0.3)
    check("tty mismatch → skipped, nothing killed", "skipped" in out and alive(pp2) and alive(ip2), f"{out}{err}")

    # 6b. sweep re-checks the snapshot at kill time (module-level: model built fresh, file goes stale, then sweep)
    import importlib.machinery, importlib.util
    os.environ.update(env(NOW, st6, gs6, comms))
    loader = importlib.machinery.SourceFileLoader("sessions_mod", EXE)
    spec = importlib.util.spec_from_loader("sessions_mod", loader); smod = importlib.util.module_from_spec(spec); loader.exec_module(smod)
    wp3, ip3, pp3 = tree()
    W6[0]["tabs"][1]["surfaces"] = [surf("a", pid=2, prog_pid=pp3, wrapper=wp3, tty="/dev/null")]
    (gs6 / "current.json").write_text(json.dumps(snapshot(W6)))
    model6 = smod.build_model()
    check("module: model fresh + 1 sweepable", model6["fresh"] and len(smod.sweep(model6, None, True)[0]) == 1)
    (gs6 / "current.json").write_text(json.dumps(snapshot(W6, saved_at=NOW - 120)))
    res, err = smod.sweep(model6, None, False)
    time.sleep(0.3)
    check("sweep re-reads current.json at kill time → refused, nothing killed", err == "snapshot stale" and res == [] and alive(pp3) and alive(ip3), f"{err} {res}")
    (gs6 / "current.json").write_text(json.dumps(snapshot(W6)))
    res, err = smod.sweep(model6, None, False)
    time.sleep(0.5)
    check("same model, fresh file again → sweeps", err is None and not alive(pp3), f"{err} {res}")

    # 6c. ghostty-session integration: install on a copy of the pristine backup must equal the live file
    GSB = Path(os.environ.get("SESSIONS_GS_SRC") or REPO / "bin/ghostty-session")
    bak = Path(os.environ.get("SESSIONS_GS_PRISTINE") or REPO / "tests/fixtures/ghostty-session.pristine")
    scratch_gs = ROOT / "gs-bin"; shutil.copy(bak, scratch_gs)
    scratch_claude = ROOT / "claude-scratch"; (scratch_claude / "hooks").mkdir(parents=True)
    shutil.copy(Path(os.environ.get("SESSIONS_HOOK_PRISTINE") or REPO / "tests/fixtures/tab-status.pristine.py"), scratch_claude / "hooks/tab-status.py")
    ie = env(NOW, ROOT / "state-install"); ie.update({"SESSIONS_GS_BIN": str(scratch_gs), "SESSIONS_CLAUDE_DIR": str(scratch_claude)})
    r1 = subprocess.run([EXE, "install"], capture_output=True, text=True, env=ie)
    r2 = subprocess.run([EXE, "install"], capture_output=True, text=True, env=ie)
    check("install on pristine backup == live ghostty-session", scratch_gs.read_text() == GSB.read_text() and "applied" in r1.stdout,
          r1.stdout + r1.stderr + "\n" + subprocess.run(["diff", str(scratch_gs), str(GSB)], capture_output=True, text=True).stdout[:800])
    check("install is idempotent (second run: already complete, file unchanged)", "already complete" in r2.stdout and scratch_gs.read_text() == GSB.read_text(), r2.stdout)
    check("install reproduces the hook line", "# sessions-touch" in (scratch_claude / "hooks/tab-status.py").read_text() and (scratch_claude / "skills/park/SKILL.md").exists())
    gloader = importlib.machinery.SourceFileLoader("gs_mod", str(GSB))
    gspec = importlib.util.spec_from_loader("gs_mod", gloader); gmod = importlib.util.module_from_spec(gspec); gloader.exec_module(gmod)
    check("sessions_argv skips leading flags", gmod.sessions_argv(["python3", "-I", "/x/sessions", "tui"]) and gmod.sessions_argv(["/usr/bin/python3", "/x/sessions", "tui", "--width", "56"])
          and not gmod.sessions_argv(["python3", "-I", "/x/other", "tui"]) and not gmod.sessions_argv(["python3", "/x/sessions", "map"]))
    rects = [(0, 0, 500, 1000), (600, 0, 1000, 1000)]       # anchor (1000 wide) on the right, new pane (500) on the left
    prev = {"size": {"px_w": 1000, "px_h": 1000}}
    left_shell = {"size": {"px_w": 500, "px_h": 1000}, "program": {"kind": "shell"}}
    left_side = {"size": {"px_w": 500, "px_h": 1000}, "program": {"kind": "sessions"}}
    check("split_dir: a pane left of its anchor is 'right' unless it is the sidebar",
          gmod.split_dir(left_shell, prev, rects, 1000) == "right" and gmod.split_dir(left_side, prev, rects, 1000) == "left",
          f"{gmod.split_dir(left_shell, prev, rects, 1000)} {gmod.split_dir(left_side, prev, rects, 1000)}")
    r = subprocess.run([str(GSB), "save", "--help"], capture_output=True, text=True)
    check("ghostty-session save --help prints usage, no save", r.returncode == 0 and "ghostty-session —" in r.stdout and "saved:" not in r.stdout)
    r = subprocess.run([str(GSB), "save", "bogus"], capture_output=True, text=True)
    check("ghostty-session save bogus → exit 2", r.returncode == 2 and "takes no arguments" in r.stderr)

    # 8. codex: thread names from the TUI's terminal title / the index, ids by name or start time, rollouts
    def uuid7(t):
        ms = int(t * 1000)
        return f"{ms >> 16:08x}-{ms & 0xffff:04x}-7000-8000-000000000000"

    cx_root = ROOT / "codex8"; cx_root.mkdir()          # own dir: the shared fixtures must not gain codex rows
    cx8 = {"SESSIONS_CODEX_DIR": str(cx_root)}
    def rollout(tid, started, cwd=CWD, source="user", first="", last_prompt="", last_assistant="", mtime=None, day="2026/10/19"):
        d = cx_root / "sessions" / day; d.mkdir(parents=True, exist_ok=True)
        meta = {"id": tid, "cwd": cwd, "thread_source": source, "timestamp": "2026-10-19T21:54:37.758Z"}
        if source == "subagent":
            meta["source"] = {"subagent": {"thread_spawn": {"parent_thread_id": SIDS["a"]}}}
            meta["parent_thread_id"] = SIDS["a"]
        lines = [json.dumps({"timestamp": "x", "type": "session_meta", "payload": meta}),
                 json.dumps({"type": "response_item", "payload": {"type": "message", "role": "developer", "content": [{"type": "input_text", "text": "<skills_instructions>…"}]}}),
                 json.dumps({"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "<environment_context>cwd</environment_context>"}]}}),
                 json.dumps({"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": first}]}}),
                 json.dumps({"type": "event_msg", "payload": {"type": "task_complete", "last_agent_message": "earlier answer"}}),
                 json.dumps({"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": last_prompt}]}}),
                 json.dumps({"type": "event_msg", "payload": {"type": "task_complete", "last_agent_message": last_assistant}}),
                 json.dumps({"type": "event_msg", "payload": {"type": "token_count"}})]
        f = d / f"rollout-2026-10-19T21-54-37-{tid}.jsonl"
        f.write_text("\n".join(lines) + "\n")
        os.utime(f, (mtime or started, mtime or started))
        return f

    T0 = NOW - 2 * 3600
    CA, CB, CC, CD, CE, CF = uuid7(T0 + 3), uuid7(T0 + 102), uuid7(T0 + 200), uuid7(T0 - 5 * DAY), uuid7(T0 + 300), uuid7(T0 + 400)
    rollout(CA, T0 + 3, first="audit the content for seo trust issues please", last_prompt="and the footer?", last_assistant="Footer fixed, three links added.", mtime=NOW - 600)
    rollout(CB, T0 + 102, first="propose peanut growth plans", mtime=NOW - 3000)
    rollout(CC, T0 + 200, first="old closed thread", mtime=NOW - 3600)
    rollout(CD, T0 - 5 * DAY, first="ancient thread", mtime=NOW - 5 * DAY, day="2026/10/14")
    rollout(CE, T0 + 300, source="subagent", first="subagent work", mtime=NOW - 100)
    rollout(CF, T0 + 400, first="never named, closed", mtime=NOW - 200)
    (cx_root / "session_index.jsonl").write_text("".join(json.dumps(r) + "\n" for r in [
        {"id": CA, "thread_name": "Audit content SEO trust issues", "updated_at": "2026-10-19T21:56:12Z"},
        {"id": CB, "thread_name": "Propose Peanut growth plans", "updated_at": "2026-10-19T21:57:10Z"},
        {"id": CC, "thread_name": "Audit bill-splitting slop", "updated_at": "2026-10-19T21:59:30Z"},
        {"id": CD, "thread_name": "Ancient codex thread", "updated_at": "2026-10-14T09:00:00Z"},
        {"id": CE, "thread_name": "Subagent thread", "updated_at": "2026-10-19T22:00:00Z"},
        {"bad": 1}]) + "not json\n")

    cp = gmod.codex_title_parts
    check("codex title: run state + name + project", cp("[ ! ] Action Required | Audit content SEO trust issues | workspace") == {"name": "Audit content SEO trust issues", "id": None, "state": "ask"}, str(cp("[ ! ] Action Required | Audit content SEO trust issues | workspace")))
    check("codex title: spinner frame → busy", cp("⠏ Deslop key marketing surfaces | workspace") == {"name": "Deslop key marketing surfaces", "id": None, "state": "busy"})
    check("codex title: plain name | project", cp("Propose Peanut growth plans | workspace") == {"name": "Propose Peanut growth plans", "id": None, "state": None})
    check("codex title: id as name", cp(f"{CA} | workspace")["id"] == CA)
    check("codex title: claude / shell / project-only titles are not codex titles",
          cp("🟢 Shotgun Split Tree Review") is None and cp("⚪ ~/workspace") is None and cp("workspace") is None and cp("") is None)
    check("codex title: state with no name", cp("[ . ] Action Required | workspace") == {"name": None, "id": None, "state": "ask"})
    check("uuid7_time round-trips", abs(gmod.uuid7_time(CA) - (T0 + 3)) < 0.001 and gmod.uuid7_time("zz") is None)

    gmod.CODEX_INDEX = cx_root / "session_index.jsonl"
    def gsurf(pid, start, tab, kind="codex", tid=None, label=None):
        return {"pid": pid, "start": start, "program": {"kind": kind, "id": tid, "label": label, "cwd": CWD, "pid": pid + 1}}, {f"{pid}:{start}": {"tab": tab}}
    surfs, regs = [], {}
    for sf, rg in (gsurf(10, T0, "t1"),                                    # tab titled "Action Required | Audit…" → CA by name, ask
                   gsurf(11, T0 + 100, "t2"),                              # untitled tab (count mismatch), started 2 s before CB → CB by start
                   gsurf(12, T0 + 5, "t3"), gsurf(13, T0 + 6, "t3", kind="claude", tid=SIDS["a"], label="Claude thing"),   # mixed tab titled by claude → nothing
                   gsurf(14, T0 + 198, "t4", tid=CC),                      # resume CC in argv: label from the index; tab title names CA → misfiled, skipped
                   gsurf(15, T0 - 50000, "t5")):                           # unnamed / resumed via picker: nothing, never guessed
        surfs.append(sf); regs.update(rg)
    gwin = [{"tabs": [{"id": "t1", "title": "[ ! ] Action Required | Audit content SEO trust issues | workspace"}, {"id": "t2", "title": ""},
                      {"id": "t3", "title": "🟢 Claude thing"}, {"id": "t4", "title": "Audit content SEO trust issues | workspace"}, {"id": "t5", "title": "workspace"}]}]
    known = {}
    gmod.codex_resolve(gwin, surfs, regs, known)
    P = [sf["program"] for sf in surfs]
    check("codex_resolve: title names the single codex pane of its tab (id by name, state ask)", P[0]["id"] == CA and P[0]["label"] == "Audit content SEO trust issues" and P[0]["state"] == "ask", str(P[0]))
    check("codex_resolve: untitled pane takes the thread created right after it started", P[1]["id"] == CB and P[1]["label"] == "Propose Peanut growth plans" and "state" not in P[1], str(P[1]))
    check("codex_resolve: codex pane in a claude-titled tab stays unresolved", P[2]["id"] is None and P[2].get("label") is None, str(P[2]))
    check("codex_resolve: known id gets the index name; a tab title naming another thread is ignored", P[4]["id"] == CC and P[4]["label"] == "Audit bill-splitting slop" and "state" not in P[4], str(P[4]))
    check("codex_resolve: old pane with no title match is never guessed", P[5]["id"] is None and P[5].get("label") is None, str(P[5]))
    check("codex_resolve: resolved panes persist in the registry", set(known) == {f"10:{T0}", f"11:{T0 + 100}", f"14:{T0 + 198}"} and known[f"10:{T0}"] == {"id": CA, "label": "Audit content SEO trust issues"}, str(known))
    check("codex_title_parts anchors a codex tab in reconcile (name vs tab title)",
          gmod.codex_title_parts("⠋ Audit content SEO trust issues | workspace")["name"] == P[0]["label"])

    # the sidebar: titles, status from the title, closed threads in history (subagents and unnamed-but-recent too)
    gs8 = ROOT / "gs8"; gs8.mkdir(); st8 = ROOT / "state8"; st8.mkdir()
    def csurf(pid, tid=None, label=None, state=None, dir_=None):
        prog = {"kind": "codex", "id": tid, "cwd": CWD, "pid": 999990 + pid, "label": label}
        if state:
            prog["state"] = state
        return {"program": prog, "pid": 999900 + pid, "tty": None, "size": None, "dir": dir_, "seq": pid}
    W8 = [{"title": "x", "focused": True, "tabs": [
        {"title": "[ ! ] Action Required | Audit content SEO trust issues | workspace", "active": True, "surfaces": [csurf(1, CA, "Audit content SEO trust issues", "ask")]},
        {"title": "", "active": False, "surfaces": [csurf(2, CB, "Propose Peanut growth plans", "busy")]},
        {"title": "", "active": False, "surfaces": [csurf(3, None, "Named but unresolved")]},
        {"title": "", "active": False, "surfaces": [surf("a", pid=4), csurf(5, dir_="right")]},
    ]}]
    (gs8 / "current.json").write_text(json.dumps(snapshot(W8)))
    rc, out, err = run("tui", "--once", state=st8, gs=gs8, extra=cx8)
    lines8 = out.split("\n")
    check("codex rows: thread name + 🔴 from the title", " ├1 🔴 Audit content SEO trust issues" in lines8, out)
    check("codex rows: 🚧 busy", " ├2 🚧 Propose Peanut growth plans" in lines8, out)
    check("codex rows: named but id-less → name, ▫, —", any(l.startswith(" ├3 ▫  Named but unresolved") and l.rstrip().endswith("—") for l in lines8), out)
    check("codex rows: no name, no id → codex, —", any(re.match(r"^\s+└─ ▫  codex\s+—$", l.rstrip()) for l in lines8), out)
    hist8 = out.split("══ history")[1] if "══ history" in out else ""
    check("history: closed codex threads by name (index) with ?3d", re.search(r"^\s+Audit bill-splitting slop\s+\?3d$", hist8, re.M), hist8)
    check("history: unnamed closed codex thread → first prompt", "never named, closed" in hist8, hist8)
    check("history: subagent threads and threads older than the decay are not listed", "Subagent thread" not in out and "subagent work" not in out and "Ancient" not in out and "ancient" not in out, out)
    rc, out, err = run("map", "--json", state=st8, gs=gs8, extra=cx8)
    m8 = json.loads(out)["sessions"]
    check("map --json: codex session kind/title/cwd/status", m8[CA]["kind"] == "codex" and m8[CA]["title"] == "Audit content SEO trust issues" and m8[CA]["cwd"] == CWD and m8[CA]["status"] == "ask", json.dumps(m8.get(CA), default=str)[:400])
    smod.CODEX_DIR = cx_root
    ci = smod.codex_info(CA, {})
    check("codex_info: first/last user turn + last task_complete, wrappers skipped", ci and ci["first_prompt"] == "audit the content for seo trust issues please" and ci["last_prompt"] == "and the footer?" and ci["last_assistant"] == "Footer fixed, three links added." and not ci["subagent"], str(ci))
    check("codex_info: subagent flagged", smod.codex_info(CE, {})["subagent"] is True)
    # pinned stays pinned through activity: touch (hook) and resume both go through mark_active
    stq = ROOT / "state-pinned"; stq.mkdir()
    smod.LEDGER, keep_ledger = stq / "events.jsonl", smod.LEDGER
    smod.ledger_append(SIDS["m"], "pinned", "claude", src="tui")
    evq = smod.mark_active(SIDS["m"], "claude", "tui")
    evt = smod.mark_active(SIDS["n"], "claude", "tui")
    smod.LEDGER = keep_ledger
    check("mark_active (resume) keeps a pinned session pinned; a plain one becomes active", evq["state"] == "pinned" and evt["state"] == "active", f"{evq} {evt}")
    rc, out, err = run("touch", CA, state=st8, gs=gs8, extra=cx8)
    ev8 = [json.loads(l) for l in (st8 / "events.jsonl").read_text().split("\n") if l.strip()]
    check("touch on a codex id writes kind codex", rc == 0 and ev8 and ev8[-1]["kind"] == "codex" and ev8[-1]["sid"] == CA, str(ev8))
    rc, out, err = run("tui", "--once", state=st8, gs=gs8, extra=cx8)
    check("detail pane source: codex rows render after touch", rc == 0 and " ├1 🔴 Audit content SEO trust issues" in out, out)

    # 7. keys through a pty
    def spawn_tui(state, rows=40, cols=56):
        pid, fdm = pty.fork()
        if pid == 0:
            os.environ.update(env(NOW, state))
            os.execv(EXE, [EXE, "tui", "--width", str(cols)])
        fcntl.ioctl(fdm, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
        CHILDREN.append(pid)
        return pid, fdm

    def send(fdm, b, wait=0.4):
        if b:
            os.write(fdm, b)
        time.sleep(wait)
        buf = b""
        while True:
            r, _, _ = select.select([fdm], [], [], 0.2)
            if not r:
                break
            try:
                buf += os.read(fdm, 65536)
            except OSError:
                break
        return buf.decode("utf-8", "replace")

    st3 = ROOT / "state3"; shutil.copytree(ST, st3)
    ledger3 = lambda: [json.loads(l) for l in (st3 / "events.jsonl").read_text().split("\n") if l.strip() and l.startswith("{") and '"sid"' in l and '"ts":"bad"' not in l]
    n0 = len(ledger3())
    pid, fdm = spawn_tui(st3)
    time.sleep(1.2)
    first = strip_ansi(send(fdm, b"", 0.1))
    check("pty: first frame, cursor on first selectable row (tab 1)", "▶├1 ⚪ LP Refresh Competitor" in first, first[:400])
    scr = strip_ansi(send(fdm, b"k"))
    check("pty: k at top stays on a selectable row", "▶├1" in scr, scr[:200])
    scr = strip_ansi(send(fdm, b"j"))
    check("pty: j lands on tab 2", "▶├2" in scr, scr[:400])
    scr = strip_ansi(send(fdm, b"s"))
    check("pty: s opens the snooze (park) prompt", "snooze: days" in scr, scr[-300:])
    scr = strip_ansi(send(fdm, b"\x1b"))
    check("pty: Esc cancels the snooze prompt, no ledger line", "snooze: days" not in scr and len(ledger3()) == n0, scr[-200:])
    send(fdm, b"s"); scr = strip_ansi(send(fdm, b"abc\r"))
    check("pty: bad days value re-prompts", "days: number or s" in scr, scr[-300:])
    send(fdm, b"2\r"); send(fdm, b"note from pty"); scr = strip_ansi(send(fdm, b"\r", 0.8))
    last = ledger3()[-1]
    check("pty: s snooze writes ledger (2d, note)", last["sid"] == SIDS["b"] and last["state"] == "parked" and last["note"] == "note from pty"
          and (datetime.fromtimestamp(last["wake"]).date() - datetime.fromtimestamp(NOW).date()).days == 2, str(last))
    send(fdm, b"k"); scr = strip_ansi(send(fdm, b"x", 0.8))
    last = ledger3()[-1]
    check("pty: x writes done", last["sid"] == SIDS["a"] and last["state"] == "done", str(last))
    send(fdm, b"a")                                  # back to active so the i-toggle test below starts clean
    n1 = len(ledger3())
    scr = strip_ansi(send(fdm, b"r", 0.6))
    check("pty: r on an open row → focus hint, no resume", '→ "Competitor Positioning Analysis" · alt+1' in scr and len(ledger3()) == n1, scr[-300:])
    scr = strip_ansi(send(fdm, b"\r", 0.6))
    check("pty: ↵ on an open row → same hint", "alt+1" in scr, scr[-300:])
    n2 = len(ledger3())
    scr = strip_ansi(send(fdm, b"p", 0.8))
    lp = ledger3()[-1]
    check("pty: p pins the selected row (LP Refresh: 🧹 📌 in the tree, row in the 📌 section, cursor stays)", lp["sid"] == SIDS["a"] and lp["state"] == "pinned"
          and "▶├1 ⚪ LP Refresh Competitor" in scr and "🧹 📌" in scr and "📌 ⚪ LP Refresh Competitor" in scr, str(lp) + scr[:200])
    scr = strip_ansi(send(fdm, b"p", 0.8))
    lp = ledger3()[-1]
    check("pty: p again unpins (active line)", lp["sid"] == SIDS["a"] and lp["state"] == "active" and len(ledger3()) == n2 + 2, str(lp))
    time.sleep(4.2)                                   # let the 4 s focus hint expire so the footer shows the count
    send(fdm, b"/"); send(fdm, b"Startup"); scr = strip_ansi(send(fdm, b"\r", 0.6))
    lines = [l for l in scr.split("\n") if l.strip()]
    check("pty: filter keeps the tab anchor + matching split, count 2 (anchor is stale)", "├3 ⚪ Shotgun split tree review" in scr and "Startup Valuation" in scr
          and "LP Refresh" not in scr and " c 🧹 2" in scr, scr)
    scr = strip_ansi(send(fdm, b"c", 0.8))
    check("pty: c on filtered rows closes the same 2 (identity fails on fake pids → 0 of 2)", "of 2" in scr, scr[-200:])
    scr = strip_ansi(send(fdm, b"\x1b", 0.6))
    check("pty: Esc clears filter", "LP Refresh" in scr, scr[-400:])
    scr = strip_ansi(send(fdm, b"D", 0.6))
    check("pty: D shows done rows", "a finished thing" in scr, scr)
    scr = strip_ansi(send(fdm, b"D", 0.6))
    check("pty: D again hides them", "a finished thing" not in scr, scr)
    scr = strip_ansi(send(fdm, b"m", 0.6))
    check("pty: m toggles backlog expansion (no +N either way here)", "someday item u" in scr and not re.search(r"═\+\d", scr), scr[-300:])
    send(fdm, b"m")
    scr = strip_ansi(send(fdm, b" ", 0.6))
    check("pty: space opens the 7-row detail pane (above the keys block)", scr.count("═" * 56) >= 1 and re.search(r"^ you    \S", scr, re.M) and re.search(r"^ claude \S", scr, re.M)
          and scr.index("claude ") < scr.index("══ keys "), scr)
    fcntl.ioctl(fdm, termios.TIOCSWINSZ, struct.pack("HHHH", 12, 56, 0, 0))
    os.kill(pid, signal.SIGWINCH)
    scr = strip_ansi(send(fdm, b"", 0.8))
    check("pty: SIGWINCH to 12 rows drops the detail pane and the keys block", "═" * 56 not in scr and "══ keys " not in scr and "══ window 1 " in scr, scr)
    fcntl.ioctl(fdm, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 56, 0, 0))
    os.kill(pid, signal.SIGWINCH)
    send(fdm, b" ")
    scr = strip_ansi(send(fdm, b"?"))
    check("pty: ? shows help", "keys" in scr and "alt+N" in scr, scr[-300:])
    send(fdm, b"q"); scr = send(fdm, b"q", 0.6)
    check("pty: q leaves alternate screen + resets title", "\x1b[?1049l" in scr and "\x1b]2;\x07" in scr, repr(scr[-100:]))
    os.waitpid(pid, 0)

    pid, fdm = spawn_tui(st3)
    time.sleep(1.2); send(fdm, b"", 0.1)
    os.kill(pid, signal.SIGTERM)
    scr = send(fdm, b"", 0.8)
    _, status_ = os.waitpid(pid, 0)
    check("pty: SIGTERM restores the terminal, exit 143", "\x1b[?1049l" in scr and os.WEXITSTATUS(status_) == 143, repr(scr[-80:]) + f" status={status_}")
finally:
    cleanup()

print(f"\n{'ALL PASS' if fails == 0 else str(fails) + ' FAILED'}  (fixtures in {ROOT})")
sys.exit(1 if fails else 0)
