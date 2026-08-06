# Deleted Gift Shop — Setup Guide

## Quick Start

```bash
# 1. Enter the project folder
cd deleted_gifts_sender_bot

# 2. Run the launcher (pass your Telegram numeric ID)
bash start.sh YOUR_TELEGRAM_ID

# Example:
bash start.sh 123456789
```

## Get Your Telegram ID

Message [@userinfobot](https://t.me/userinfobot) on Telegram — it replies with your numeric ID.

## What the launcher does

1. Creates a Python virtual environment
2. Installs all dependencies
3. Starts an ngrok HTTPS tunnel on port 8000
4. Sets your bot's name and description
5. Starts the FastAPI backend (auto-reload on change)

## Set bot webhook on Mini App button

After the server is running, go to [@BotFather](https://t.me/BotFather):
1. `/newapp` → select your bot → paste the Mini App URL shown in the terminal
2. Or set the menu button: `/setmenubutton`

## Add/Change Commission

Open the bot → tap the Mini App → tap ⚙️ Admin  
(only visible if your Telegram ID matches ADMIN_ID)

Per-gift commission can be changed individually.

## Project Structure

```
deleted_gifts_sender_bot/
├── backend/
│   ├── main.py        # FastAPI + webhook + payment
│   ├── db.py          # SQLite database layer
│   ├── config.py      # Bot token, admin ID
│   └── requirements.txt
├── frontend/
│   ├── index.html     # Mini App UI
│   ├── style.css      # Dark premium CSS
│   └── app.js         # All frontend logic
└── start.sh           # One-command launcher
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_ID` | 0 | Your Telegram numeric user ID |
| `BOT_TOKEN` | (set in config.py) | Bot API token |
| `BASE_URL` | auto from ngrok | HTTPS public URL |
| `DEFAULT_COMMISSION` | 10 | Default commission per gift |
