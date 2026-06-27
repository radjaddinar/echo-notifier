#!/usr/bin/env python3
"""echo-notifier — push notification on command completion.

Mendukung:
  - Telegram — langsung via Bot API, gak perlu server

Usage:
  echon <command>                          Run a command, notify on completion
  echon --message "text" [--status fail]   Send direct notification
  echon --setup                            Setup notifier
  echon --init                             Setup global AI agent config
  echon --uninstall                        Hapus semua konfigurasi
  echon --version                          Tampilkan versi
"""

import sys
import subprocess
import argparse
import json
import os
import ssl
import platform
import urllib.request
import urllib.parse
import urllib.error

__version__ = "2.0.0"

# Platform-aware paths
if platform.system() == "Windows":
    _base = os.environ.get("APPDATA", os.path.expanduser("~"))
    CONFIG_DIR = os.path.join(_base, "echo")
else:
    CONFIG_DIR = os.path.expanduser("~/.config/echo")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

# Default bot — user tinggal chat @ECHOclibot
# Bisa dioverride via env var: ECHO_BOT_TOKEN
DEFAULT_BOT_TOKEN = os.environ.get(
    "ECHO_BOT_TOKEN",
    "8951600952:AAGaHwa5_LvMpgNDHe-KMBQ_AonK_GwuBPo",
)
DEFAULT_BOT_USERNAME = "ECHOclibot"

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
TELEGRAM_UPDATES = "https://api.telegram.org/bot{token}/getUpdates"

# ── SSL Context ───────────────────────────────────────────────────────────

_SSL_CONTEXT = None


def _get_ssl_context():
    """Buat SSL context — coba certifi, fallback ke system, terakhir unverified."""
    global _SSL_CONTEXT
    if _SSL_CONTEXT is not None:
        return _SSL_CONTEXT

    try:
        import certifi  # type: ignore
        _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
        return _SSL_CONTEXT
    except ImportError:
        pass

    try:
        _SSL_CONTEXT = ssl.create_default_context()
        import urllib.request as _ur
        _ur.urlopen("https://google.com", timeout=3, context=_SSL_CONTEXT)
        return _SSL_CONTEXT
    except Exception:
        pass

    _SSL_CONTEXT = ssl._create_unverified_context()
    return _SSL_CONTEXT


# ── Config ────────────────────────────────────────────────────────────────


# Old paths for migration
_OLD_CONFIG_DIR = os.path.expanduser("~/.config/cli-notifier")
_OLD_CONFIG_PATH = os.path.join(_OLD_CONFIG_DIR, "config.json")


def load_config() -> dict:
    """Load config, auto-create if missing."""
    # Migrate from old path (~/.config/cli-notifier) if exists
    if not os.path.exists(CONFIG_PATH) and os.path.exists(_OLD_CONFIG_PATH):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        os.rename(_OLD_CONFIG_PATH, CONFIG_PATH)
        print("✓ Config migrated from cli-notifier → echo")

    if not os.path.exists(CONFIG_PATH):
        _prompt_channel()
        config = setup_telegram()
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)
        print(f"\n✅ Config disimpan di {CONFIG_PATH}\n")
    with open(CONFIG_PATH) as f:
        return json.load(f)


def _prompt_channel() -> str:
    print("=" * 50)
    print("📡  echo-notifier — First Time Setup")
    print("=" * 50)
    print("\nChannel notifikasi: Telegram (via Bot API — gak perlu server)\n")
    return "telegram"


# ── Setup ─────────────────────────────────────────────────────────────────


def setup_telegram() -> dict:
    """Interaktif setup Telegram — pake default bot atau punya sendiri."""
    print()
    print("=" * 46)
    print("📡  Setup Telegram Notifier")
    print("=" * 46)

    can_use_default = bool(DEFAULT_BOT_TOKEN)
    choice = "n"

    if can_use_default:
        choice = input(
            f"Pakai bot bawaan @{DEFAULT_BOT_USERNAME}? (Enter) atau "
            "bikin sendiri? (ketik s) [Y/n]: "
        ).strip().lower()

    if choice in ("", "y") and can_use_default:
        token = DEFAULT_BOT_TOKEN
        print(f"\n✅ Pake bot: @{DEFAULT_BOT_USERNAME}\n")
    else:
        token = _prompt_custom_bot()

    username = DEFAULT_BOT_USERNAME if choice in ("", "y") else ""
    chat_id = _resolve_chat_id(token, username)
    if chat_id:
        send_telegram(token, chat_id, "✅ echo-notifier berhasil terhubung!")
    return {"channel": "telegram", "bot_token": token, "chat_id": chat_id}


def _prompt_custom_bot() -> str:
    print("\n📖  Cara Bikin Bot Sendiri:")
    print("  1. Buka Telegram, cari @BotFather")
    print("  2. Kirim /newbot, ikutin petunjuk")
    print("  3. Dapet token kayak: 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11\n")
    return input("Masukkan Bot Token: ").strip()


def _resolve_chat_id(token: str, bot_username: str = "") -> str:
    """Coba ambil chat_id otomatis dari getUpdates, fallback ke manual."""
    if not bot_username:
        bot_username = _resolve_bot_username(token)

    for attempt in range(2):
        try:
            url = TELEGRAM_UPDATES.format(token=token)
            ctx = _get_ssl_context()
            with urllib.request.urlopen(url, timeout=10, context=ctx) as resp:
                data = json.loads(resp.read())
            if data.get("result"):
                cid = str(data["result"][-1]["message"]["chat"]["id"])
                print(f"  → Chat ID ditemukan: {cid}")
                return cid
        except Exception:
            pass

        if attempt == 0:
            print(f"\n⚠  Kirim /start ke @{bot_username} dulu,")
            print("   lalu tekan Enter.")
            input("   (Tekan Enter setelah kirim /start)... ")

    return input("Chat ID (gak ketemu otomatis, isi manual): ").strip()


def _resolve_bot_username(token: str) -> str:
    """Cari username bot dari API, fallback ke DEFAULT_BOT_USERNAME."""
    try:
        url = f"https://api.telegram.org/bot{token}/getMe"
        ctx = _get_ssl_context()
        with urllib.request.urlopen(url, timeout=10, context=ctx) as resp:
            data = json.loads(resp.read())
        if data.get("ok") and data["result"].get("username"):
            return data["result"]["username"]
    except Exception:
        pass
    return DEFAULT_BOT_USERNAME


# ── Send ──────────────────────────────────────────────────────────────────


def send_notification(config: dict, agent: str, status: str, summary: str) -> bool:
    """Kirim notifikasi via Telegram."""
    icon = "✅" if status == "success" else "❌"
    text = f"{icon} {agent} — {summary}"
    return send_telegram(config["bot_token"], config["chat_id"], text)


def send_telegram(token: str, chat_id: str, text: str) -> bool:
    """Kirim notifikasi via Telegram Bot API."""
    data = urllib.parse.urlencode({
        "chat_id": chat_id, "text": text, "disable_notification": False,
    }).encode()
    try:
        req = urllib.request.Request(TELEGRAM_API.format(token=token), data=data)
        with urllib.request.urlopen(req, timeout=10, context=_get_ssl_context()) as resp:
            result = json.loads(resp.read())
        if result.get("ok"):
            print("✓ Notification sent (Telegram)", flush=True)
            return True
        print(f"✗ Telegram error: {result}", flush=True)
        return False
    except Exception as e:
        print(f"✗ Gagal kirim Telegram: {e}", flush=True)
        return False


def run_command(command: str) -> int:
    """Run a shell command, streaming output live."""
    with subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, bufsize=1,
    ) as proc:
        for line in proc.stdout:
            print(line, end="", flush=True)
    return proc.returncode


# ── Init (global AI agent config) ─────────────────────────────────────────


def cmd_setup_ai_global():
    """Setup global AI agent config — merge, bukan overwrite."""
    print("🔄 Mengupdate global config AI tools ke echo-notifier...\n")

    taste_path = os.path.expanduser("~/.commandcode/taste/taste.md")
    os.makedirs(os.path.dirname(taste_path), exist_ok=True)
    existing = _safe_read(taste_path)
    line = (
        '- Setelah selesai task, kirim notifikasi dengan '
        '`echon --agent "CommandCode" --message "deskripsi task"` '
        "untuk memberi tahu user. Confidence: 0.90\n"
    )
    if line not in existing:
        section = "# workflow\n"
        if section not in existing:
            existing += "\n" + section
        existing = existing.replace(section, section + line)
        _safe_write(taste_path, existing)
        print(f"  ✓ CommandCode: {taste_path}")
    else:
        print(f"  → CommandCode: sudah ada")

    claude_dir = os.path.expanduser("~/.config/claude")
    os.makedirs(claude_dir, exist_ok=True)
    claude_file = os.path.join(claude_dir, "instructions.md")
    line_cc = 'Setelah selesai task, jalankan: echon --agent "Claude Code" --message "deskripsi task"\n'
    existing_cc = _safe_read(claude_file)
    if line_cc not in existing_cc:
        with open(claude_file, "a") as f:
            f.write("\n" + line_cc if existing_cc.strip() else line_cc)
        print(f"  ✓ Claude Code: {claude_file}")
    else:
        print(f"  → Claude Code: sudah ada")

    copilot_path = os.path.expanduser("~/.vscode/settings.json")
    os.makedirs(os.path.dirname(copilot_path), exist_ok=True)
    settings = {}
    try:
        with open(copilot_path) as f:
            settings = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    entry = {"text": 'echon --agent "Codex" --message "deskripsi task"'}
    existing_instructions = settings.get("github.copilot.chat.instructions", [])
    if entry not in existing_instructions:
        settings["github.copilot.chat.instructions"] = existing_instructions + [entry]
        _safe_write_json(copilot_path, settings)
        print(f"  ✓ Copilot/Codex: {copilot_path}")
    else:
        print(f"  → Copilot/Codex: sudah ada")

    print("\n✅ Selesai! Restart AI tools sekarang.")
    print("Semua AI agent di project MANA PUN bakal otomatis pake echon.\n")


# ── Uninstall ─────────────────────────────────────────────────────────────


def cmd_uninstall():
    """Hapus semua konfigurasi ECHO)))."""
    print("🗑  echo-notifier — Uninstall\n")

    removed = []

    if os.path.exists(CONFIG_DIR):
        import shutil
        shutil.rmtree(CONFIG_DIR)
        removed.append(CONFIG_DIR)

    import subprocess as _sp
    ret = _sp.run(["pipx", "uninstall", "cli-notifier"], capture_output=True)
    if ret.returncode == 0:
        removed.append("pipx package cli-notifier")

    if input("\nHapus juga config AI agent? (y/N): ").strip().lower() == "y":
        paths = [
            os.path.expanduser("~/.commandcode/taste/taste.md"),
            os.path.expanduser("~/.config/claude/instructions.md"),
        ]
        for p in paths:
            if os.path.exists(p):
                os.remove(p)
                removed.append(p)

        copilot_path = os.path.expanduser("~/.vscode/settings.json")
        try:
            with open(copilot_path) as f:
                settings = json.load(f)
            settings.pop("github.copilot.chat.instructions", None)
            _safe_write_json(copilot_path, settings)
            removed.append(f"{copilot_path} (key dihapus)")
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    if removed:
        print("\n✅ Berhasil dihapus:")
        for item in removed:
            print(f"   • {item}")
    else:
        print("\nTidak ada yang dihapus.")

    print("\nSelesai. Install lagi: pipx install cli-notifier\n")


# ── Helpers ───────────────────────────────────────────────────────────────


def _safe_read(path: str) -> str:
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        return ""


def _safe_write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


def _safe_write_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# ── Main ──────────────────────────────────────────────────────────────────


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] in ("--setup", "--init", "--uninstall", "--version"):
        cmd = sys.argv[1]
        if cmd == "--version":
            print(f"echo-notifier v{__version__}")
            return
        if cmd == "--setup":
            if os.path.exists(CONFIG_PATH):
                os.remove(CONFIG_PATH)
            load_config()
            return
        if cmd == "--init":
            cmd_setup_ai_global()
            return
        if cmd == "--uninstall":
            cmd_uninstall()
            return

    config = load_config()

    parser = argparse.ArgumentParser(
        description="echo-notifier — push notification on CLI completion"
    )
    parser.add_argument("command", nargs="*", help="Command to run and notify")
    parser.add_argument("--message", "-m", help="Direct notification message")
    parser.add_argument("--status", "-s", choices=["success", "failed"], default="success")
    parser.add_argument("--agent", "-a", default="AI Agent", help="Nama AI agent")

    args = parser.parse_args()

    if args.message:
        send_notification(config, args.agent, args.status, args.message)
        return

    if not args.command:
        parser.print_help()
        sys.exit(1)

    cmd_str = " ".join(args.command)
    rc = run_command(cmd_str)
    s = "success" if rc == 0 else "failed"
    send_notification(config, args.agent, s, f"Menjalankan: {cmd_str}")
    sys.exit(rc)


if __name__ == "__main__":
    main()
