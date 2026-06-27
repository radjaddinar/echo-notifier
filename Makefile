.PHONY: install server init setup test

install: ## Install echo-notifier via pipx
	pipx install .

init: ## Init global AI agent config (CommandCode, Claude, Copilot)
	echon --init

setup: ## Setup Telegram bot
	echon --setup

test: ## Jalankan semua test
	python -m unittest tests/test_echo.py -v

server: ## Start Expo backend (opsional)
	cd backend && python3 main.py
