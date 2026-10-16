# waybar-herdr

A Waybar module that shows the status of your [Herdr](https://herdr.dev) agent sessions.

![screenshot](screenshot.png)

Herdr tracks AI coding agents (Claude, Pi, Codex, Copilot, etc.) running in terminal panes. This module polls `herdr agent list` and displays a compact summary in Waybar: which agents are working, blocked, idle, or done.

## What it shows

The bar text shows an icon per state with a count, only for states that have agents in them:

```
󰚩 󰑮3 󰏤1 󰒲2
```

| State | Icon | Color |
|-------|------|-------|
| working | 󰑮 | green |
| blocked | 󰏤 | orange |
| idle | 󰒲 | purple |
| done | 󰄬 | cyan |
| unknown | ? | grey |

Hovering shows a tooltip listing each agent with its type, status, project directory, and terminal title.

The module disappears from the bar when Herdr isn't running or has no agents.

## Install

Copy `herdr.py` somewhere on your machine:

```sh
cp herdr.py ~/.local/share/waybar-herdr/herdr.py
chmod +x ~/.local/share/waybar-herdr/herdr.py
```

Add the module to your Waybar `modules.jsonc` (or inline in your config):

```jsonc
"custom/herdr": {
  "format": "{}",
  "return-type": "json",
  "interval": 5,
  "exec": "~/.local/share/waybar-herdr/herdr.py",
  "exec-if": "herdr status --json 2>/dev/null | jq -e '.server.running == true' >/dev/null 2>&1",
  "on-click": "~/.local/share/waybar-herdr/herdr.py focus",
  "on-click-right": "~/.local/share/waybar-herdr/herdr.py jumpapp",
},
```

Add `"custom/herdr"` to whichever bar section you want (e.g. `modules-left`).

Add to your `style.css`:

```css
#custom-herdr {
  padding: 0 2px;
}
#custom-herdr.working { color: @green; }
#custom-herdr.blocked { color: @orange; }
#custom-herdr.idle { color: @purple; }
#custom-herdr.done { color: @cyan; }
#custom-herdr.unknown { color: @comment; }
```

Adjust the colors to match your theme.

Reload Waybar:

```sh
killall -SIGUSR2 waybar
```

## Click actions

Left-click runs `wm-jump --all` (a fuzzy window picker that shows Herdr tabs). Right-click runs `wm-jumpapp kitty` to focus the terminal. Change these in the module config or edit the script to suit your setup.

## Requirements

- [Herdr](https://herdr.dev) with at least one agent integration installed (`herdr integration status`)
- Python 3
- `jq` (for `exec-if`)
- A Nerd Font in your Waybar config

## License

MIT
