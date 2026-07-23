#!/usr/bin/env python3
# Fired by herdr on pane.focused. Reports the newly-focused pane's directory
# to cmux via `cmux rpc surface.report_pwd`, so the right-side file viewer
# follows whichever herdr space is currently visible.
#
# Deliberately does NOT use $CMUX_WORKSPACE_ID / $CMUX_SURFACE_ID: in testing
# those env vars were stale and did not match the surface's real UUID
# (cmux list-pane-surfaces showed a different UUID). `cmux identify --json`
# resolves the live target instead.
import json
import os
import subprocess

event = json.loads(os.environ["HERDR_PLUGIN_EVENT_JSON"])
pane_id = event["data"]["pane_id"]

pane_raw = subprocess.run(
    ["herdr", "pane", "get", pane_id], capture_output=True, text=True, check=True
)
pane = json.loads(pane_raw.stdout)["result"]["pane"]
# foreground_cwd tracks the pane's foreground process cwd, which for agent
# panes (Claude, etc.) is unreliable/unrelated to the space's actual
# directory (seen reporting the agent's own subprocess cwd). cwd is the
# pane's assigned working directory and matches the space's git worktree.
path = pane["cwd"]

identify_raw = subprocess.run(
    ["cmux", "identify", "--json"], capture_output=True, text=True, check=True
)
focused = json.loads(identify_raw.stdout)["focused"]
if focused is None or focused.get("is_browser_surface"):
    raise SystemExit(0)

subprocess.run(
    [
        "cmux",
        "rpc",
        "surface.report_pwd",
        json.dumps(
            {
                "workspace_id": focused["workspace_ref"],
                "surface_id": focused["surface_ref"],
                "path": path,
            }
        ),
    ],
    check=True,
)
