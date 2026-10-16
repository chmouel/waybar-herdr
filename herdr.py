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
    "working": ("W", "#50fa7b"),
    "blocked": ("B", "#ffb86c"),
    "idle": ("I", "#bd93f9"),
    "done": ("D", "#8be9fd"),
    "unknown": ("?", "#6272a4"),
}

STATE_PRIORITY = ["blocked", "working", "idle", "done", "unknown"]

DISPLAY_ORDER = ["working", "blocked", "idle", "done", "unknown"]

TERMINAL = os.environ.get("HERDR_TERMINAL", "kitty")


def get_agents():
    try:
        result = subprocess.run(
            ["herdr", "agent", "list"],
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        )
        data = json.loads(result.stdout)
        return data.get("result", {}).get("agents", [])
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        json.JSONDecodeError,
        FileNotFoundError,
    ):
        return []


def pick_agent(agents):
    """Pick the most urgent agent: first blocked, then working, then by priority."""
    for state in STATE_PRIORITY:
        for a in agents:
            if a.get("agent_status") == state:
                return a
    return agents[0] if agents else None


def focus_agent(pane_id):
    subprocess.run(["wm-jumpapp", TERMINAL], check=False)
    subprocess.run(
        ["herdr", "agent", "focus", pane_id],
        capture_output=True,
        timeout=2,
        check=False,
    )


def handle_focus():
    agents = get_agents()
    if not agents:
        sys.exit(0)
    agent = pick_agent(agents)
    if agent:
        focus_agent(agent["pane_id"])
    sys.exit(0)


def handle_menu():
    agents = get_agents()
    if not agents:
        sys.exit(0)

    lines = []
    pane_ids = []
    for a in agents:
        status = a.get("agent_status", "unknown")
        icon = STATUS_MAP.get(status, ("?", "#6272a4"))[0]
        agent_type = a.get("agent", "?")
        project = os.path.basename(a.get("cwd", ""))
        title = a.get("terminal_title_stripped", "")
        label = f"{icon} {agent_type:<8s} {status:<8s} {project}"
        if title:
            label += f"  {title}"
        lines.append(label)
        pane_ids.append(a.get("pane_id", ""))

    try:
        result = subprocess.run(
            ["fuzzel", "-d", "--index", "--prompt", "Agent > "],
            input="\n".join(lines),
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            idx = int(result.stdout.strip())
            if 0 <= idx < len(pane_ids) and pane_ids[idx]:
                focus_agent(pane_ids[idx])
    except (ValueError, subprocess.TimeoutExpired):
        pass
    sys.exit(0)


def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "focus":
            handle_focus()
        elif sys.argv[1] == "menu":
            handle_menu()

    agents = get_agents()
    if not agents:
        return

    counts = Counter(a.get("agent_status", "unknown") for a in agents)

    parts = []
    for state in DISPLAY_ORDER:
        c = counts.get(state, 0)
        if c > 0:
            icon = STATUS_MAP.get(state, ("?", "#6272a4"))[0]
            color = STATUS_MAP.get(state, ("?", "#6272a4"))[1]
            parts.append(f"<span foreground='{color}'>{icon}{c}</span>")
    text = (
        "<span foreground='white'>[</span>"
        + "|".join(parts)
        + "<span foreground='white'>]</span>"
    )

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
