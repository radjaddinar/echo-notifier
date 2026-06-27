<!-- markdownlint-disable MD041 -->
![image alt](https://github.com/radjaddinar/echo-notifier/blob/main/echologo.png?raw=true)
#echo-notifier
*Your AI agents scream into my void. I ping your phone.*

[![CI](https://github.com/dinarradja/cli-notifier/actions/workflows/ci.yml/badge.svg)](https://github.com/dinarradja/cli-notifier/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/cli-notifier)](https://pypi.org/project/cli-notifier/)
[![Python versions](https://img.shields.io/pypi/pyversions/cli-notifier)](https://pypi.org/project/cli-notifier/)
[![License](https://img.shields.io/pypi/l/cli-notifier)](LICENSE)

Three lines and your AI agent will DM you on Telegram when it's done doing whatever you asked it to do.

```
AI Agent → echon → Telegram Bot API → HP
```

## ok but why

Because you're tired of staring at a terminal waiting for something to finish.
Or you told an AI to do something and walked away, and now you're wondering if it's done.

This script just... does that. No server. No cloud. No subscription. Nothing to set on fire.

## fine, install it

```bash
pipx install cli-notifier
echon --init
echon --setup
```

`--init` tells your AI tools (CommandCode, Claude Code, Copilot) to stop being useless and notify you when they're done.

`--setup` hooks you up with the Telegram bot @radjaCLInotifierBOT. Say `/start` to it. That's it.

## what does it do

Wraps a command and yells at you on Telegram when it's done:

```bash
echon "sleep 5 && echo finally"
```

Or if your AI agent wants to brag:

```bash
echon --agent "CommandCode" --message "Deployed to prod. somehow."
echon --agent "Claude Code" --message "Couldn't fix the bug. DNS." --status failed
```

## fine, show me all the flags

| Flag | What it does |
|------|-------------|
| `echon <command>` | Runs your thing, notifies when done |
| `-m, --message` | Just send a notification, don't run anything |
| `-s, --status` | `success` (default) or `failed` |
| `-a, --agent` | Who's sending this (CommandCode, Claude, etc.) |
| `--setup` | Reconfigure from scratch |
| `--init` | Set up global AI agent instructions |
| `--uninstall` | Take me out of this nightmare |
| `--version` | Prints a number |

## i have my own bot or whatever

Set the env var:

```bash
export ECHO_BOT_TOKEN="your_token_here"
echon --setup
```

Or don't. The default bot works fine. I'm not reading your chats. I have enough to read.

## does it work on windows

Yeah probably. It's pure stdlib Python. If it doesn't, file an issue and I'll pretend to care.

## contributing

PRs welcome. Or don't. I'm not your manager.

## structure because someone will ask

```
├── echo.py               ← the whole thing (stdlib, no deps)
├── tests/test_echo.py    ← 20 tests that pass. for now.
├── backend/main.py       ← fastapi server (expo only, you don't need this)
├── App.js                ← expo app (you *really* don't need this)
└── .github/workflows/ci.yml ← github actions does its thing
```

[![Buy me a coffee](https://img.shields.io/badge/buy%20me%20a%20coffee-ffdd00)](https://ko-fi.com/yourlink)
