#!/usr/bin/env python3
"""Idempotently installs the post-cd hook into zsh, bash, and fish rc files.

Invoked as a herdr plugin action:
    herdr plugin action invoke install-shell-hook --plugin linvald.herdr-cmux-file-viewer

Safe to re-run: each rc file gets a single marked block, skipped if already
present rather than duplicated.
"""
import os
import shutil

PLUGIN_ID = "linvald.herdr-cmux-file-viewer"
BEGIN = f"# >>> herdr-cmux-file-viewer >>>"
END = f"# <<< herdr-cmux-file-viewer <<<"

ZSH_SNIPPET = f"""{BEGIN}
if [[ "${{HERDR_ENV:-}}" = "1" ]]; then
  _herdr_cmux_plugin_root="$(herdr plugin list --plugin {PLUGIN_ID} --json 2>/dev/null \\
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["result"]["plugins"][0]["plugin_root"])' 2>/dev/null)"
  _herdr_cmux_report_cwd() {{
    [[ -n "$_herdr_cmux_plugin_root" ]] || return
    "$_herdr_cmux_plugin_root/scripts/report-cwd-if-focused.py" &>/dev/null &!
  }}
  chpwd_functions+=(_herdr_cmux_report_cwd)
  _herdr_cmux_report_cwd
fi
{END}
"""

BASH_SNIPPET = f"""{BEGIN}
if [[ "${{HERDR_ENV:-}}" = "1" ]]; then
  _herdr_cmux_plugin_root="$(herdr plugin list --plugin {PLUGIN_ID} --json 2>/dev/null \\
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["result"]["plugins"][0]["plugin_root"])' 2>/dev/null)"
  _herdr_cmux_last_pwd=""
  _herdr_cmux_report_cwd() {{
    [[ -n "$_herdr_cmux_plugin_root" ]] || return
    if [[ "$PWD" != "$_herdr_cmux_last_pwd" ]]; then
      _herdr_cmux_last_pwd="$PWD"
      ( "$_herdr_cmux_plugin_root/scripts/report-cwd-if-focused.py" &>/dev/null & )
    fi
  }}
  PROMPT_COMMAND="_herdr_cmux_report_cwd${{PROMPT_COMMAND:+; $PROMPT_COMMAND}}"
fi
{END}
"""

FISH_SNIPPET = f"""{BEGIN}
if test "$HERDR_ENV" = "1"
    set -g _herdr_cmux_plugin_root (herdr plugin list --plugin {PLUGIN_ID} --json 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["result"]["plugins"][0]["plugin_root"])' 2>/dev/null)
    function _herdr_cmux_report_cwd --on-variable PWD
        if test -n "$_herdr_cmux_plugin_root"
            $_herdr_cmux_plugin_root/scripts/report-cwd-if-focused.py &>/dev/null &
            disown
        end
    end
    _herdr_cmux_report_cwd
end
{END}
"""


def install(rc_path: str, snippet: str, create_parent: bool = False) -> None:
    display = rc_path.replace(os.path.expanduser("~"), "~", 1)
    if create_parent:
        parent = os.path.dirname(rc_path)
        if not os.path.isdir(parent):
            print(f"skip {display}: {parent} does not exist (shell not installed)")
            return
    existing = ""
    if os.path.exists(rc_path):
        with open(rc_path) as f:
            existing = f.read()
    if BEGIN in existing:
        print(f"skip {display}: already installed")
        return
    with open(rc_path, "a") as f:
        if existing and not existing.endswith("\n"):
            f.write("\n")
        f.write("\n" + snippet)
    print(f"installed into {display}")


install(os.path.expanduser("~/.zshrc"), ZSH_SNIPPET)
install(os.path.expanduser("~/.bashrc"), BASH_SNIPPET)
if shutil.which("fish"):
    install(os.path.expanduser("~/.config/fish/config.fish"), FISH_SNIPPET, create_parent=True)
else:
    print("skip ~/.config/fish/config.fish: fish not found on PATH")

print("\nReload your shell (open a new pane/tab, or `source` the rc file) for the hook to take effect.")
