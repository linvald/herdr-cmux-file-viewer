# herdr-cmux-file-viewer

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
2. **`scripts/report-cwd-if-focused.py`**, called from a post-`cd` hook in
   your shell config — fires on every `cd`. `pane.focused` only fires on a
   focus *change*; it does not re-fire when you `cd` inside the space you're
   already looking at, so without this piece the file viewer goes stale
   after the first `cd`. The script checks that the pane doing the `cd` is
   actually the one currently focused in herdr before reporting anything, so
   a background pane `cd`-ing elsewhere doesn't steal the file viewer.
   `install_hook.py` installs this hook into zsh (`chpwd_functions`), bash
   (`PROMPT_COMMAND`, since bash has no native post-cd hook), and fish
   (`--on-variable PWD`) — see Install below.

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
- zsh, bash, and/or fish — the shell hook installer supports all three

## Install

1. Install the plugin:

   ```sh
   herdr plugin install <owner>/herdr-cmux-file-viewer
   ```

   (Replace `<owner>` with wherever you cloned this from. For local
   development, use `herdr plugin link /path/to/herdr-cmux-file-viewer`
   instead — see [herdr's plugin docs](https://herdr.dev/docs/plugins/).)

2. Install the shell hook:

   ```sh
   herdr plugin action invoke install-shell-hook --plugin linvald.herdr-cmux-file-viewer
   ```

   This appends a marked block to `~/.zshrc` and `~/.bashrc` (and
   `~/.config/fish/config.fish` if `fish` is on `PATH`), so `cd` also keeps
   the file viewer in sync — see [How it works](#how-it-works) for why this
   is needed on top of the plugin event. Safe to re-run: each rc file is
   checked for the marker and skipped if already installed, never
   duplicated. If you forked this repo under a different plugin id, edit
   `PLUGIN_ID` at the top of `install_hook.py` first.

   Prefer to do it by hand, or don't use any of zsh/bash/fish? See
   `install_hook.py` for the exact snippet per shell and adapt it.

3. Reload: `herdr server reload-config` and open a new shell (or `source`
   the rc file) in any panes you already have open — existing shells don't
   pick up an rc file change retroactively.

## Verifying it worked

```sh
herdr plugin list --plugin linvald.herdr-cmux-file-viewer --json
```

should show `"enabled": true`. Switch herdr spaces and the cmux file viewer
should follow; `cd` around inside a space and it should keep following.

`herdr plugin log list --plugin linvald.herdr-cmux-file-viewer` shows the
history of fired events if something looks off.

## Known limitations

- Only tracks the space's assigned working directory (`pane.cwd`), not the
  live cwd of whatever process is running in it — an agent that `cd`s
  internally without your shell's hook firing won't be reflected.
- The bash hook only patches `~/.bashrc`. On macOS, interactive login shells
  source `~/.bash_profile` instead — source `~/.bashrc` from there if you
  rely on bash and use login shells.
- Only zsh, bash, and fish are supported. Other shells need a hand-written
  equivalent of the snippets in `install_hook.py`.
