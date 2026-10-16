#!/usr/bin/env python3
# Author: Chmouel Boudjnah <chmouel@chmouel.com>
"""Waybar module for Herdr agent session status"""

import html
import json
import os
import subprocess
import sys
from collections import Counter

STATUS_MAP = {
    "working": ("󰑮", "#50fa7b"),
    "blocked": ("󰏤", "#ffb86c"),
    "idle": ("󰒲", "#bd93f9"),
    "done": ("󰄬", "#8be9fd"),
    "unknown": ("?", "#6272a4"),
}

STATE_PRIORITY = ["blocked", "working", "idle", "done", "unknown"]

DISPLAY_ORDER = ["working", "blocked", "idle", "done", "unknown"]


def handle_focus():
    subprocess.run(["wm-jump", "--all"], check=False)
    sys.exit(0)


def handle_jumpapp():
    subprocess.run(["wm-jumpapp", "kitty"], check=False)
    sys.exit(0)


def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "focus":
            handle_focus()
        elif sys.argv[1] == "jumpapp":
            handle_jumpapp()

    try:
        result = subprocess.run(
            ["herdr", "agent", "list"],
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        )
        data = json.loads(result.stdout)
        agents = data.get("result", {}).get("agents", [])
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return

    if not agents:
        return

    counts = Counter(a.get("agent_status", "unknown") for a in agents)

    parts = []
    for state in DISPLAY_ORDER:
        c = counts.get(state, 0)
        if c > 0:
            icon = STATUS_MAP.get(state, ("?", "#6272a4"))[0]
            parts.append(f"{icon}{c}")
    text = "󰚩 " + " ".join(parts)

    css_class = "unknown"
    for state in STATE_PRIORITY:
        if counts.get(state, 0) > 0:
            css_class = state
            break

    tooltip_lines = [f"<b>Herdr Agents ({len(agents)})</b>", ""]
    for a in agents:
        status = a.get("agent_status", "unknown")
        icon, color = STATUS_MAP.get(status, ("?", "#6272a4"))
        agent_type = html.escape(a.get("agent", "?"))
        project = html.escape(os.path.basename(a.get("cwd", "")))
        title = html.escape(a.get("terminal_title_stripped", ""))
        tooltip_lines.append(
            f"<span foreground='{color}'>{icon}</span> {agent_type:<8s} {status:<8s} {project}"
        )
        if title:
            tooltip_lines.append(f"  <span foreground='#6272a4'>{title}</span>")

    output = {"text": text, "tooltip": "\n".join(tooltip_lines), "class": css_class}
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
