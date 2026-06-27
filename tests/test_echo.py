"""Tests untuk echo.py (ECHO))) — 20+ unit tests."""

import os
import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import echo as eco


class TestVersion(unittest.TestCase):
    def test_version_string(self):
        self.assertIsInstance(eco.__version__, str)
        parts = eco.__version__.split(".")
        self.assertEqual(len(parts), 3)


class TestHelpers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_safe_read_file_not_found(self):
        self.assertEqual(eco._safe_read(os.path.join(self.tmp, "x.json")), "")

    def test_safe_read_and_write(self):
        path = os.path.join(self.tmp, "test.txt")
        eco._safe_write(path, "hello")
        self.assertEqual(eco._safe_read(path), "hello")

    def test_safe_write_creates_dirs(self):
        path = os.path.join(self.tmp, "a", "b", "c", "test.txt")
        eco._safe_write(path, "nested")
        self.assertTrue(os.path.exists(path))

    def test_safe_write_json(self):
        path = os.path.join(self.tmp, "config.json")
        data = {"key": "value"}
        eco._safe_write_json(path, data)
        with open(path) as f:
            self.assertEqual(json.load(f), data)

    def test_safe_write_json_creates_dirs(self):
        path = os.path.join(self.tmp, "x", "y", "s.json")
        eco._safe_write_json(path, {"ok": True})
        self.assertTrue(os.path.exists(path))


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.orig_dir = eco.CONFIG_DIR
        self.orig_path = eco.CONFIG_PATH
        eco.CONFIG_DIR = str(self.tmp)
        eco.CONFIG_PATH = str(self.tmp / "config.json")

    def tearDown(self):
        eco.CONFIG_DIR = self.orig_dir
        eco.CONFIG_PATH = self.orig_path

    def test_load_existing_config(self):
        config = {"channel": "telegram", "bot_token": "x", "chat_id": "123"}
        with open(eco.CONFIG_PATH, "w") as f:
            json.dump(config, f)
        self.assertEqual(eco.load_config(), config)

    def test_config_structure(self):
        r = {"channel": "telegram", "bot_token": "t", "chat_id": "1", "user_id": "dinar_01"}
        self.assertIn("bot_token", r)
        self.assertIn("chat_id", r)

    def test_expo_config_structure(self):
        r = {"channel": "expo", "user_id": "u", "backend_url": "http://local.host/n"}
        self.assertEqual(r["channel"], "expo")


class TestPlatformPaths(unittest.TestCase):
    @patch("platform.system", return_value="Windows")
    def test_windows_path_uses_appdata(self, _mock):
        with patch.dict(os.environ, {"APPDATA": "C:\\Users\\t\\AppData\\Roaming"}):
            import importlib
            importlib.reload(eco)
            self.assertIn("AppData", eco.CONFIG_DIR)

    @patch("platform.system", return_value="Darwin")
    def test_unix_path(self, _mock):
        import importlib
        importlib.reload(eco)
        self.assertTrue(eco.CONFIG_DIR.endswith("echo"))


class TestSendNotification(unittest.TestCase):
    def test_telegram_success_format(self):
        config = {"channel": "telegram", "bot_token": "x", "chat_id": "1"}
        original = eco.send_telegram
        captured = {}

        def mock_send(token, chat_id, text):
            captured["text"] = text
            return True

        eco.send_telegram = mock_send
        try:
            r = eco.send_notification(config, "CommandCode", "success", "Testing")
            self.assertTrue(r)
            self.assertIn("✅", captured["text"])
            self.assertIn("CommandCode", captured["text"])
            self.assertIn("Testing", captured["text"])
        finally:
            eco.send_telegram = original

    def test_telegram_failed_format(self):
        config = {"channel": "telegram", "bot_token": "x", "chat_id": "1"}
        original = eco.send_telegram
        captured = {}

        def mock_send(token, chat_id, text):
            captured["text"] = text
            return True

        eco.send_telegram = mock_send
        try:
            eco.send_notification(config, "Claude", "failed", "Error")
            self.assertIn("❌", captured["text"])
            self.assertIn("Claude", captured["text"])
        finally:
            eco.send_telegram = original


class TestRunCommand(unittest.TestCase):
    def test_success(self):
        self.assertEqual(eco.run_command("echo hi"), 0)

    def test_failure(self):
        self.assertNotEqual(eco.run_command("false"), 0)


class TestInitCommand(unittest.TestCase):
    def test_init_creates_taste_file(self):
        taste = os.path.expanduser("~/.commandcode/taste/taste.md")
        if os.path.exists(taste):
            os.remove(taste)
        eco.cmd_setup_ai_global()
        self.assertTrue(os.path.exists(taste))
        content = eco._safe_read(taste)
        self.assertIn("echon", content)
        self.assertIn("CommandCode", content)

    def test_init_idempotent(self):
        taste = os.path.expanduser("~/.commandcode/taste/taste.md")
        eco.cmd_setup_ai_global()
        first = eco._safe_read(taste)
        eco.cmd_setup_ai_global()
        second = eco._safe_read(taste)
        self.assertEqual(first, second)

    def test_init_creates_claude_file(self):
        claude = os.path.expanduser("~/.config/claude/instructions.md")
        if os.path.exists(claude):
            os.remove(claude)
        eco.cmd_setup_ai_global()
        self.assertTrue(os.path.exists(claude))
        content = eco._safe_read(claude)
        self.assertIn("echon", content)
        self.assertIn("Claude Code", content)

    def test_init_copilot_merge(self):
        copilot = os.path.expanduser("~/.vscode/settings.json")
        os.makedirs(os.path.dirname(copilot), exist_ok=True)
        with open(copilot, "w") as f:
            json.dump({"window.zoomLevel": 2}, f)
        eco.cmd_setup_ai_global()
        with open(copilot) as f:
            s = json.load(f)
        self.assertEqual(s["window.zoomLevel"], 2)
        self.assertIn("github.copilot.chat.instructions", s)


class TestBotTokenEnvVar(unittest.TestCase):
    def test_token_from_env(self):
        with patch.dict(os.environ, {"ECHO_BOT_TOKEN": "custom_token"}):
            import importlib
            importlib.reload(eco)
            self.assertEqual(eco.DEFAULT_BOT_TOKEN, "custom_token")


if __name__ == "__main__":
    unittest.main()
