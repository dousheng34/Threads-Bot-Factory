# Threads Bot Factory

Telegram bot for mass Threads account management.

## Features
- Account management (add, delete, bulk import)
- Posting (quick, mass, scheduled)
- Automation (auto-post, auto-reply, warmup)
- Proxy manager
- Templates with Spintax
- Statistics

## Setup
```
pip install -r requirements.txt
cp .env.example .env
python bot.py
```

## Commands
- /start - Main menu
- /add user:token:id - Add account
- /post ID text - Quick post
- /mass text - Mass post to all accounts
- /stats - Statistics

## Bot: @thrds_factorybot
