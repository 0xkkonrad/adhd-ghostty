# >>> ghostty-split-run pickup (14 Oct 2026; ~/.local/bin/ghostty-split-run) >>>
# A new split claims a pending command written in the last 15 s and runs it once.
__gsr_pending="${XDG_RUNTIME_DIR:-/tmp}/ghostty-split-run/pending"
__gsr_claimed=
if [[ $- == *i* && "$TERM_PROGRAM" == ghostty && -z "$CLAUDECODE" && -z "$CODEX_THREAD_ID" && -f "$__gsr_pending" ]] \
   && (( $(date +%s) - $(stat -c %Y "$__gsr_pending") < 15 )) \
   && mv "$__gsr_pending" "$__gsr_pending.$$" 2>/dev/null; then
  __gsr_cmd=$(<"$__gsr_pending.$$"); rm -f "$__gsr_pending.$$"; __gsr_claimed=1
  history -s "$__gsr_cmd"; eval "$__gsr_cmd"
fi
# ghostty-session cold start (14 Oct 2026): Ghostty relaunched with a single surface after its windows
# were closed → reopen the last closed windows (first surface runs here, the rest is rebuilt in the background).
if [[ $- == *i* && "$TERM_PROGRAM" == ghostty && -z "$CLAUDECODE" && -z "$CODEX_THREAD_ID" && -z "$__gsr_claimed" ]] \
   && [[ "$(pgrep -c -P "$(pgrep -d, -x ghostty)" 2>/dev/null)" == 1 ]] \
   && __gsr_cmd=$("$HOME/.local/bin/ghostty-session" cold-start $$ 2>>"${XDG_STATE_HOME:-$HOME/.local/state}/ghostty-session/cold-start.log") \
   && [[ -n "$__gsr_cmd" ]]; then
  history -s "$__gsr_cmd"; eval "$__gsr_cmd"
fi
unset __gsr_pending __gsr_cmd __gsr_claimed
# <<< ghostty-split-run pickup <<<
