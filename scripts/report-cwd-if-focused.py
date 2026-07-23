#!/usr/bin/env python3
# Called from the zsh chpwd hook on every `cd` inside a herdr pane. Only
# nudges cmux's file viewer if this pane is the one currently focused/visible
# in herdr -- a background pane cd'ing shouldn't steal the file viewer.
import json
import os
import subprocess
import sys

pane_id = os.environ.get("HERDR_PANE_ID")
if not pane_id:
    sys.exit(0)

pane_raw = subprocess.run(
    ["herdr", "pane", "get", pane_id], capture_output=True, text=True
)
if pane_raw.returncode != 0:
    sys.exit(0)
pane = json.loads(pane_raw.stdout)["result"]["pane"]
if not pane.get("focused"):
    sys.exit(0)

identify_raw = subprocess.run(
    ["cmux", "identify", "--json"], capture_output=True, text=True
)
if identify_raw.returncode != 0:
    sys.exit(0)
focused = json.loads(identify_raw.stdout).get("focused")
if not focused or focused.get("is_browser_surface"):
    sys.exit(0)

subprocess.run(
    [
        "cmux",
        "rpc",
        "surface.report_pwd",
        json.dumps(
            {
                "workspace_id": focused["workspace_ref"],
                "surface_id": focused["surface_ref"],
                "path": pane["cwd"],
            }
        ),
    ],
    capture_output=True,
)
