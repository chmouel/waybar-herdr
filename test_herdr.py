#!/usr/bin/env python3
import json
import os
import subprocess
import unittest
from unittest.mock import patch, MagicMock

import herdr


SAMPLE_AGENTS = {
    "id": "cli:agent:list",
    "result": {
        "agents": [
            {
                "agent": "claude",
                "agent_status": "working",
                "cwd": "/home/user/project-a",
                "pane_id": "w1:p1",
                "terminal_title_stripped": "implement feature X",
                "focused": True,
            },
            {
                "agent": "pi",
                "agent_status": "blocked",
                "cwd": "/home/user/project-b",
                "pane_id": "w1:p2",
                "terminal_title_stripped": "review PR",
                "focused": False,
            },
            {
                "agent": "codex",
                "agent_status": "idle",
                "cwd": "/home/user/project-c",
                "pane_id": "w1:p3",
                "terminal_title_stripped": "",
                "focused": False,
            },
        ],
        "type": "agent_list",
    },
}


def mock_agent_list(agents_response):
    result = MagicMock()
    result.stdout = json.dumps(agents_response)
    return patch("herdr.subprocess.run", return_value=result)


class TestGetAgents(unittest.TestCase):
    def test_returns_agents(self):
        with mock_agent_list(SAMPLE_AGENTS):
            agents = herdr.get_agents()
            self.assertEqual(len(agents), 3)
            self.assertEqual(agents[0]["agent"], "claude")

    def test_herdr_not_running(self):
        with patch("herdr.subprocess.run", side_effect=FileNotFoundError):
            self.assertEqual(herdr.get_agents(), [])

    def test_herdr_timeout(self):
        with patch("herdr.subprocess.run", side_effect=subprocess.TimeoutExpired("herdr", 2)):
            self.assertEqual(herdr.get_agents(), [])

    def test_bad_json(self):
        result = MagicMock()
        result.stdout = "not json"
        with patch("herdr.subprocess.run", return_value=result):
            self.assertEqual(herdr.get_agents(), [])

    def test_empty_agents(self):
        with mock_agent_list({"result": {"agents": [], "type": "agent_list"}}):
            self.assertEqual(herdr.get_agents(), [])


class TestPickAgent(unittest.TestCase):
    def test_blocked_takes_priority(self):
        agents = SAMPLE_AGENTS["result"]["agents"]
        picked = herdr.pick_agent(agents)
        self.assertEqual(picked["agent_status"], "blocked")

    def test_working_over_idle(self):
        agents = [
            {"agent_status": "idle", "pane_id": "p1"},
            {"agent_status": "working", "pane_id": "p2"},
        ]
        self.assertEqual(herdr.pick_agent(agents)["pane_id"], "p2")

    def test_empty_list(self):
        self.assertIsNone(herdr.pick_agent([]))

    def test_all_idle(self):
        agents = [
            {"agent_status": "idle", "pane_id": "p1"},
            {"agent_status": "idle", "pane_id": "p2"},
        ]
        picked = herdr.pick_agent(agents)
        self.assertEqual(picked["pane_id"], "p1")


class TestMainOutput(unittest.TestCase):
    def run_main(self, agents_response, icon_mode="text", brackets="0"):
        with patch.dict(os.environ, {"HERDR_ICONS": icon_mode, "HERDR_BRACKETS": brackets}):
            import importlib
            importlib.reload(herdr)
            with mock_agent_list(agents_response):
                with patch("builtins.print") as mock_print:
                    herdr.main()
                    if mock_print.called:
                        return json.loads(mock_print.call_args[0][0])
                    return None

    def test_output_format(self):
        output = self.run_main(SAMPLE_AGENTS)
        self.assertIn("text", output)
        self.assertIn("tooltip", output)
        self.assertIn("class", output)

    def test_text_mode(self):
        output = self.run_main(SAMPLE_AGENTS, "text")
        self.assertIn("<span foreground=", output["text"])
        self.assertIn("W1", output["text"])
        self.assertIn("B1", output["text"])
        self.assertIn("I1", output["text"])

    def test_nerd_mode(self):
        output = self.run_main(SAMPLE_AGENTS, "nerd")
        self.assertIn("<span foreground=", output["text"])
        self.assertIn("󰑮1", output["text"])
        self.assertIn("󰏤1", output["text"])
        self.assertIn("󰒲1", output["text"])

    def test_invalid_mode_falls_back_to_nerd(self):
        output = self.run_main(SAMPLE_AGENTS, "bogus")
        self.assertIn("󰑮1", output["text"])

    def test_brackets_enabled(self):
        output = self.run_main(SAMPLE_AGENTS, brackets="1")
        self.assertIn("[", output["text"])
        self.assertIn("]", output["text"])
        self.assertIn("|", output["text"])

    def test_no_brackets_by_default(self):
        output = self.run_main(SAMPLE_AGENTS)
        self.assertNotIn("[", output["text"])
        self.assertNotIn("]", output["text"])

    def test_css_class_blocked_priority(self):
        output = self.run_main(SAMPLE_AGENTS)
        self.assertEqual(output["class"], "blocked")

    def test_css_class_working_when_no_blocked(self):
        data = {
            "result": {
                "agents": [
                    {"agent": "claude", "agent_status": "working", "cwd": "/a", "terminal_title_stripped": ""},
                    {"agent": "pi", "agent_status": "idle", "cwd": "/b", "terminal_title_stripped": ""},
                ],
                "type": "agent_list",
            }
        }
        output = self.run_main(data)
        self.assertEqual(output["class"], "working")

    def test_tooltip_has_agent_info(self):
        output = self.run_main(SAMPLE_AGENTS)
        self.assertIn("claude", output["tooltip"])
        self.assertIn("pi", output["tooltip"])
        self.assertIn("codex", output["tooltip"])
        self.assertIn("project-a", output["tooltip"])

    def test_tooltip_has_title(self):
        output = self.run_main(SAMPLE_AGENTS)
        self.assertIn("implement feature X", output["tooltip"])

    def test_no_agents_no_output(self):
        output = self.run_main({"result": {"agents": [], "type": "agent_list"}})
        self.assertIsNone(output)

    def test_only_nonzero_states_shown(self):
        data = {
            "result": {
                "agents": [
                    {"agent": "claude", "agent_status": "idle", "cwd": "/a", "terminal_title_stripped": ""},
                ],
                "type": "agent_list",
            }
        }
        output = self.run_main(data, "text")
        self.assertIn("I1", output["text"])
        self.assertNotIn("W", output["text"])
        self.assertNotIn("B", output["text"])
        self.assertNotIn("D", output["text"])

    def test_html_escape_in_tooltip(self):
        data = {
            "result": {
                "agents": [
                    {
                        "agent": "claude",
                        "agent_status": "working",
                        "cwd": "/home/user/<script>",
                        "terminal_title_stripped": "fix <b>bug</b>",
                    },
                ],
                "type": "agent_list",
            }
        }
        output = self.run_main(data)
        self.assertNotIn("<script>", output["tooltip"])
        self.assertIn("&lt;script&gt;", output["tooltip"])


if __name__ == "__main__":
    unittest.main()
