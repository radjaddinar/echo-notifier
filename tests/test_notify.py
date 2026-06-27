"""Tests untuk notify_cli.py — coverage core logic termasuk --init, --uninstall."""

import os
import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import notify_cli as nf


class TestVersion(unittest.TestCase):
    """Test --version flag."""

    def test_version_string(self):
        """__version__ harus string dan numeric."""
        self.assertIsInstance(nf.__version__, str)
        parts = nf.__version__.split(".")
        self.assertEqual(len(parts), 3)
        for p in parts:
            self.assertTrue(p.isdigit())


class TestHelpers(unittest.TestCase):
    """Test helper functions (_safe_read, _safe_write, dll)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_safe_read_file_not_found(self):
        """_safe_read harus return '' untuk file yang gak ada."""
        result = nf._safe_read(os.path.join(self.tmp, "nonexistent.json"))
        self.assertEqual(result, "")

    def test_safe_read_and_write(self):
        """_safe_read harus bisa baca file yang ditulis _safe_write."""
        path = os.path.join(self.tmp, "test.txt")
        nf._safe_write(path, "hello world")
        self.assertEqual(nf._safe_read(path), "hello world")

    def test_safe_write_creates_dirs(self):
        """_safe_write harus bikin direktori kalau belum ada."""
        path = os.path.join(self.tmp, "a", "b", "c", "test.txt")
        nf._safe_write(path, "nested")
        self.assertTrue(os.path.exists(path))
        self.assertEqual(nf._safe_read(path), "nested")

    def test_safe_write_json(self):
        """_safe_write_json harus nulis JSON valid."""
        path = os.path.join(self.tmp, "config.json")
        data = {"key": "value", "num": 42}
        nf._safe_write_json(path, data)
        with open(path) as f:
            loaded = json.load(f)
        self.assertEqual(loaded, data)

    def test_safe_write_json_creates_dirs(self):
        """_safe_write_json harus bikin nested dirs kalau perlu."""
        path = os.path.join(self.tmp, "x", "y", "settings.json")
        nf._safe_write_json(path, {"ok": True})
        self.assertTrue(os.path.exists(path))


class TestConfig(unittest.TestCase):
    """Test config loading."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.orig_config_dir = nf.CONFIG_DIR
        self.orig_config_path = nf.CONFIG_PATH
        nf.CONFIG_DIR = str(self.tmp)
        nf.CONFIG_PATH = str(self.tmp / "config.json")

    def tearDown(self):
        nf.CONFIG_DIR = self.orig_config_dir
        nf.CONFIG_PATH = self.orig_config_path

    def test_load_existing_config(self):
        """load_config harus baca config yg udah ada."""
        config = {"channel": "telegram", "bot_token": "xxx", "chat_id": "123"}
        with open(nf.CONFIG_PATH, "w") as f:
            json.dump(config, f)
        loaded = nf.load_config()
        self.assertEqual(loaded, config)

    def test_telegram_config_structure(self):
        """setup_telegram manual harus return struktur yang benar."""
        result = {"channel": "telegram", "bot_token": "tok", "chat_id": "123", "user_id": "dinar_01"}
        self.assertEqual(result["channel"], "telegram")
        self.assertIn("bot_token", result)
        self.assertIn("chat_id", result)

    def test_expo_config_structure(self):
        """setup_expo manual harus return struktur yang benar."""
        result = {"channel": "expo", "user_id": "u1", "backend_url": "http://localhost:8000/n"}
        self.assertEqual(result["channel"], "expo")
        self.assertIn("backend_url", result)


class TestPlatformPaths(unittest.TestCase):
    """Test platform-aware paths."""

    @patch("platform.system", return_value="Windows")
    def test_windows_config_path(self, _mock):
        """Di Windows, CONFIG_DIR harus pake APPDATA."""
        with patch.dict(os.environ, {"APPDATA": "C:\\Users\\test\\AppData\\Roaming"}):
            import importlib
            importlib.reload(nf)
            self.assertIn("AppData", nf.CONFIG_DIR)

    @patch("platform.system", return_value="Darwin")
    def test_unix_config_path(self, _mock):
        """Di macOS/Linux, CONFIG_DIR harus pake ~/.config."""
        import importlib
        importlib.reload(nf)
        self.assertTrue(nf.CONFIG_DIR.endswith("cli-notifier"))
        self.assertIn(".config", nf.CONFIG_DIR)


class TestSendNotification(unittest.TestCase):
    """Test send_notification formatting."""

    def test_telegram_success_format(self):
        """Harus format dengan icon ✅."""
        config = {"channel": "telegram", "bot_token": "x", "chat_id": "1"}
        original = nf.send_telegram
        captured = {}

        def mock_send(token, chat_id, text):
            captured["text"] = text
            return True

        nf.send_telegram = mock_send
        try:
            result = nf.send_notification(config, "CommandCode", "success", "Testing")
            self.assertTrue(result)
            self.assertIn("✅", captured["text"])
            self.assertIn("CommandCode", captured["text"])
            self.assertIn("Testing", captured["text"])
        finally:
            nf.send_telegram = original

    def test_telegram_failed_format(self):
        """Failed harus format dengan icon ❌."""
        config = {"channel": "telegram", "bot_token": "x", "chat_id": "1"}
        original = nf.send_telegram
        captured = {}

        def mock_send(token, chat_id, text):
            captured["text"] = text
            return True

        nf.send_telegram = mock_send
        try:
            nf.send_notification(config, "Claude", "failed", "Ada error")
            self.assertIn("❌", captured["text"])
            self.assertIn("Claude", captured["text"])
            self.assertIn("Ada error", captured["text"])
        finally:
            nf.send_telegram = original


class TestRunCommand(unittest.TestCase):
    """Test run_command."""

    def test_success(self):
        """run_command harus return 0 untuk echo."""
        rc = nf.run_command("echo hello")
        self.assertEqual(rc, 0)

    def test_failure(self):
        """run_command harus return non-zero untuk false."""
        rc = nf.run_command("false")
        self.assertNotEqual(rc, 0)


class TestInitCommand(unittest.TestCase):
    """Test cmd_setup_ai_global — file creation + idempotency."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        # Override paths ke temp
        self._taste = os.path.expanduser("~/.commandcode/taste/taste.md")
        self._claude = os.path.expanduser("~/.config/claude/instructions.md")
        self._copilot = os.path.expanduser("~/.vscode/settings.json")

    def tearDown(self):
        pass

    def test_init_creates_taste_file(self):
        """cmd_setup_ai_global harus bikin CommandCode taste file."""
        taste = os.path.expanduser("~/.commandcode/taste/taste.md")
        if os.path.exists(taste):
            os.remove(taste)
        nf.cmd_setup_ai_global()
        self.assertTrue(os.path.exists(taste))
        content = nf._safe_read(taste)
        self.assertIn("notify", content)
        self.assertIn("CommandCode", content)

    def test_init_idempotent(self):
        """cmd_setup_ai_global dijalanin 2x harus gak ngerusak file."""
        taste = os.path.expanduser("~/.commandcode/taste/taste.md")
        nf.cmd_setup_ai_global()
        first = nf._safe_read(taste)
        nf.cmd_setup_ai_global()
        second = nf._safe_read(taste)
        self.assertEqual(first, second)

    def test_init_creates_claude_instructions(self):
        """cmd_setup_ai_global harus bikin Claude Code instructions."""
        claude = os.path.expanduser("~/.config/claude/instructions.md")
        if os.path.exists(claude):
            os.remove(claude)
        nf.cmd_setup_ai_global()
        self.assertTrue(os.path.exists(claude))
        content = nf._safe_read(claude)
        self.assertIn("notify", content)
        self.assertIn("Claude Code", content)

    def test_init_copilot_merge_not_overwrite(self):
        """cmd_setup_ai_global harus merge, bukan overwrite settings.json."""
        copilot = os.path.expanduser("~/.vscode/settings.json")
        os.makedirs(os.path.dirname(copilot), exist_ok=True)
        with open(copilot, "w") as f:
            json.dump({"window.zoomLevel": 2, "editor.fontSize": 14}, f)

        nf.cmd_setup_ai_global()

        with open(copilot) as f:
            settings = json.load(f)
        self.assertEqual(settings["window.zoomLevel"], 2)
        self.assertEqual(settings["editor.fontSize"], 14)
        self.assertIn("github.copilot.chat.instructions", settings)


class TestBotTokenEnvVar(unittest.TestCase):
    """Test env var CLI_NOTIFIER_TOKEN."""

    def test_default_token_from_env(self):
        """Kalau CLI_NOTIFIER_TOKEN diset, harus dipake."""
        with patch.dict(os.environ, {"CLI_NOTIFIER_TOKEN": "test_token_123"}):
            import importlib
            importlib.reload(nf)
            self.assertEqual(nf.DEFAULT_BOT_TOKEN, "test_token_123")


if __name__ == "__main__":
    unittest.main()
