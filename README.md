# herder-cmux-file-viewer

A [herdr](https://herdr.dev) plugin that syncs cmux's right-side file viewer
to whichever herdr space is currently focused.

## Why

herdr multiplexes many spaces (workspaces/panes) inside a single cmux
terminal surface. cmux's file viewer only knows about the one directory the
surface last reported, so switching herdr spaces normally leaves the file
viewer pointing at whatever repo you were in last — it doesn't follow you.

This plugin tells cmux the correct directory every time the focused herdr
space changes, using cmux's `surface.report_pwd` RPC method.

## How it works

Two pieces, both required:

1. **`herdr-plugin.toml` + `sync.py`** — a herdr plugin subscribed to the
   `pane.focused` event. Fires whenever you switch which herdr space is
   focused (including a newly created space becoming focused).
2. **`scripts/report-cwd-if-focused.py`**, called from a `chpwd` hook in your
   shell config — fires on every `cd`. `pane.focused` only fires on a focus
   *change*; it does not re-fire when you `cd` inside the space you're
   already looking at, so without this piece the file viewer goes stale
   after the first `cd`. The script checks that the pane doing the `cd` is
   actually the one currently focused in herdr before reporting anything, so
   a background pane `cd`-ing elsewhere doesn't steal the file viewer.

Both pieces resolve the current cmux surface/workspace via
`cmux identify --json` at call time rather than trusting
`$CMUX_WORKSPACE_ID` / `$CMUX_SURFACE_ID` — in testing, those env vars were
found stale (pointing at IDs that didn't match the surface's actual current
UUID).

## Requirements

- [herdr](https://herdr.dev) >= 0.7.0, with `HERDR_ENV=1` (i.e. running
  inside a herdr-managed pane)
- [cmux](https://cmux.com), with herdr running inside a cmux terminal surface
- `python3` on `PATH`
- zsh (the chpwd hook below is zsh syntax; adapt for other shells)

## Install

1. Install the plugin:

   ```sh
   herdr plugin install <owner>/herder-cmux-file-viewer
   ```

   (Replace `<owner>` with wherever you cloned this from. For local
   development, use `herdr plugin link /path/to/herder-cmux-file-viewer`
   instead — see [herdr's plugin docs](https://herdr.dev/docs/plugins/).)

2. Add a `chpwd` hook to your shell config so `cd` also keeps the file
   viewer in sync. Add this to `~/.zshrc`:

   ```zsh
   # herder-cmux-file-viewer — keep cmux's file viewer in sync on cd
   if [[ "${HERDR_ENV:-}" = "1" ]]; then
     _herdr_cmux_plugin_root="$(herdr plugin list --plugin linvald.herder-cmux-file-viewer --json 2>/dev/null \
       | python3 -c 'import json,sys; print(json.load(sys.stdin)["result"]["plugins"][0]["plugin_root"])' 2>/dev/null)"
     _herdr_cmux_report_cwd() {
       [[ -n "$_herdr_cmux_plugin_root" ]] || return
       "$_herdr_cmux_plugin_root/scripts/report-cwd-if-focused.py" &>/dev/null &!
     }
     chpwd_functions+=(_herdr_cmux_report_cwd)
     _herdr_cmux_report_cwd
   fi
   ```

   If you forked this repo under a different plugin id, update
   `--plugin linvald.herder-cmux-file-viewer` to match the `id` field in your
   copy of `herdr-plugin.toml`.

3. Reload: `herdr server reload-config` and open a new shell (or
   `source ~/.zshrc`) in any panes you already have open — existing shells
   don't pick up a `.zshrc` change retroactively.

## Verifying it worked

```sh
herdr plugin list --plugin linvald.herder-cmux-file-viewer --json
```

should show `"enabled": true`. Switch herdr spaces and the cmux file viewer
should follow; `cd` around inside a space and it should keep following.

`herdr plugin log list --plugin linvald.herder-cmux-file-viewer` shows the
history of fired events if something looks off.

## Known limitations

- Only tracks the space's assigned working directory (`pane.cwd`), not the
  live cwd of whatever process is running in it — an agent that `cd`s
  internally without your shell's `chpwd` firing won't be reflected.
- `chpwd_functions` and the `[[ "$HERDR_ENV" = "1" ]]` gate are zsh/bash-ish;
  adapt for fish or other shells.
