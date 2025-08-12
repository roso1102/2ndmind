## 🧠 MySecondMind – Your AI-Powered Second Brain (Full Setup Guide)

This guide takes you from zero to running MySecondMind locally and in the cloud. It assumes no prior setup and includes Windows- and macOS/Linux-specific steps.

### What is MySecondMind?
MySecondMind is a private, secure Telegram bot that lets you capture and manage notes, links, tasks, and reminders via natural language. It stores your data securely per user and lets you search and manage your content with simple commands or plain language.

### Core features
- Natural-language understanding (Groq LLaMA-3) for classifying messages
- Content storage and retrieval (Supabase PostgreSQL with RLS)
- Slash commands: /start, /help, /register, /notes, /tasks, /links, /reminders, /search, /stats
- Privacy-friendly actions: “delete 3”, “complete 2”, etc., without exposing UUIDs
- Advanced search with fuzzy matching and snippets
- FastAPI health endpoints and Telegram webhook handling


## 1) Prerequisites

Install the following tools first.

### 1.1 Install VS Code
- Download and install Visual Studio Code: `https://code.visualstudio.com`
- Recommended extensions:
  - Python (Microsoft)
  - Pylance (Microsoft)
  - dotenv (to highlight .env files)

### 1.2 Install Git
- Download: `https://git-scm.com/downloads`
- After installation, verify:
  ```powershell
git --version
  ```

### 1.3 Install Python 3.11+
- Download: `https://www.python.org/downloads/`
- On Windows installer, check “Add Python to PATH”.
- Verify:
  ```powershell
python --version
pip --version
  ```

### 1.4 Optional: Tesseract OCR (for image text extraction)
- Windows: `https://github.com/UB-Mannheim/tesseract/wiki`
- macOS: `brew install tesseract`
- Linux (Debian/Ubuntu): `sudo apt-get install tesseract-ocr`

### 1.5 Accounts you’ll need
- Telegram account (to create a bot via BotFather)
- Supabase project (PostgreSQL database)
- Groq account (free API key for LLaMA-3)


## 2) Get the code

Open a terminal/PowerShell and clone your repository or download the ZIP.

```powershell
# Choose a folder to hold the project
cd E:\  # or any folder you like

# Clone your repo
# Example:
# git clone https://github.com/your-username/your-repo.git mymind
# Or if you already have the code, just cd into it
cd mymind
```


## 3) Create and activate a virtual environment

### Windows (PowerShell)
```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
```
If PowerShell blocks script execution, allow local scripts:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
# Then re-run the activation command above
```

### macOS/Linux (bash/zsh)
```bash
python3 -m venv .venv
source .venv/bin/activate
```


## 4) Install dependencies

Use the full requirements file:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```
If you’re on a minimal environment, you can use `requirements-minimal.txt` instead.


## 5) Configure environment variables

Create a `.env` file in the project root. You can open it in VS Code for easier editing.

```ini
# Telegram
TELEGRAM_TOKEN=your_telegram_bot_token_here

# Supabase (primary storage)
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your_anon_public_key

# AI (Groq – optional but recommended for best NLP)
GROQ_API_KEY=your_groq_api_key

# Webhook base URL (for cloud deploys or tunnels like ngrok)
# Example: https://your-app.onrender.com or https://abcd-1234.ngrok-free.app
RENDER_EXTERNAL_URL=https://your-public-url-here

# Encryption (required). Generate a Fernet key (see below) and paste it here.
ENCRYPTION_MASTER_KEY=base64_fernet_key_here

# Optional integrations
WEATHER_API_KEY=
```

How to generate ENCRYPTION_MASTER_KEY (Fernet key):
```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```
Copy the printed value into `ENCRYPTION_MASTER_KEY`.

Environment variables used by the app (detected in code):
- `TELEGRAM_TOKEN`
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`
- `GROQ_API_KEY` (optional; enables better NLP)
- `RENDER_EXTERNAL_URL` (public base URL for webhooks)
- `ENCRYPTION_MASTER_KEY` (required; base64 Fernet key)
- Optional: `WEATHER_API_KEY`, `PORT`


## 6) Set up Supabase

This project uses Supabase PostgreSQL with Row Level Security (RLS) for user isolation.

Follow the dedicated guide in `SUPABASE_SETUP.md`:
- Create a Supabase project
- Obtain `SUPABASE_URL` and `SUPABASE_ANON_KEY`
- Open the SQL editor and apply the schema from `supabase_content_schema.sql` and `supabase_schema.sql`
- Verify RLS policies

Troubleshooting and examples are included in `SUPABASE_SETUP.md`.


## 7) Create your Telegram bot

1) Open Telegram and message `@BotFather`.
2) Send `/newbot` and follow the prompts to name your bot.
3) Copy the bot token and paste it into `.env` as `TELEGRAM_TOKEN`.


## 8) Running locally (with webhooks)

The bot uses webhooks to receive updates from Telegram. You need a public URL to forward Telegram updates to your local machine. Two options:

- ngrok: `https://ngrok.com` (simple and popular)
- Cloud (Render): skip tunneling and deploy directly (see Section 10)

### 8.1 Using ngrok (recommended for local dev)
1) Install ngrok and sign in
2) Start a tunnel to your local port (default 10000):
   ```bash
   ngrok http 10000
   ```
3) Copy the public URL (e.g., `https://abcd-1234.ngrok-free.app`) and set it as `RENDER_EXTERNAL_URL` in `.env`.

Run the FastAPI webhook server:
```bash
python main.py
```
Health endpoints when running:
- `GET /` – basic health
- `GET /health` – detailed health
- `GET /ping` – ping

Set the Telegram webhook (two ways):
- Call the helper endpoint once in your browser: `{RENDER_EXTERNAL_URL}/reset-webhook`
- Or set via Telegram API (replace placeholders):
  ```bash
  curl -X POST https://api.telegram.org/bot<TELEGRAM_TOKEN>/setWebhook \
    -H "Content-Type: application/json" \
    -d '{"url": "<RENDER_EXTERNAL_URL>/webhook"}'
  ```


## 9) Using the bot

Open your bot chat in Telegram and try:
- `/start` – introduction
- `/help` – commands and usage
- `/register` – activate your user account
- `/notes`, `/tasks`, `/links`, `/reminders` – view content
- `/search <query>` – search across your content
- `/stats` – content statistics

Natural language examples:
- “I learned something interesting today about vector databases”
- “Read later: https://example.com/awesome-article”
- “Remind me to call mom tomorrow at 6pm”
- “delete 3” or “complete task 2”


## 10) Deploy to Render (cloud)

1) Push your code to a GitHub repository (or fork your source)
2) Create a Render Web Service: `https://render.com`
3) Set build and start commands (Render autodetects Python; if needed):
   - Start command: `python main.py`
4) Add environment variables in Render (same as your `.env`):
   - `TELEGRAM_TOKEN`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `ENCRYPTION_MASTER_KEY`, `GROQ_API_KEY` (optional), `RENDER_EXTERNAL_URL`
5) Deploy, then visit `{RENDER_EXTERNAL_URL}/reset-webhook` to register your webhook with Telegram.

## 11) Simple Web Dashboard (no React)

Open your dashboard (temporary auth via query param for testing):

- URL: `/dashboard?user_id=YOUR_TELEGRAM_ID`
- Tech: FastAPI + Jinja2 + HTMX (CDN) + Tailwind (CDN)
- Features: latest items, sidebar filters (notes/tasks/links/reminders), search, create/delete

This avoids heavy frontend builds and keeps memory low on Render free tier.


## 11) Project structure (high level)

```
mymind/
  core/
    encryption.py          # Fernet-based encryption helper
    search_engine.py       # Advanced search (preprocess + fuzzy + ranking)
    supabase_rest.py       # Supabase REST client
  handlers/
    basic_commands.py      # /start, /help, /status, etc.
    content_commands.py    # /notes, /tasks, /links, /search, /stats
    content_management.py  # delete/complete/edit via NL commands
    natural_language.py    # Intent classification and routing (Groq)
    register.py            # Registration flow (Supabase-only)
    session_manager.py     # Numeric ID ↔ UUID session mapping
    supabase_content.py    # Content operations to Supabase
  models/
    user_management.py     # User manager and RLS expectations
  main.py                  # FastAPI webhook + health endpoints
  SUPABASE_SETUP.md        # Detailed Supabase setup guide
  supabase_content_schema.sql  # Content schema
  supabase_schema.sql          # Users schema
```


## 12) Troubleshooting

- Bot not responding
  - Ensure the process is running (check terminal logs)
  - Verify `TELEGRAM_TOKEN` is correct
  - Confirm webhook is set to your public URL (`/webhook`)
  - Try visiting `{RENDER_EXTERNAL_URL}/health`

- Webhook returns 405 or GET requests
  - Telegram must send POST requests; ensure you used the correct endpoint

- Supabase errors (401/403/connection)
  - Re-check `SUPABASE_URL` and `SUPABASE_ANON_KEY`
  - Make sure schemas from `supabase_content_schema.sql` and `supabase_schema.sql` are applied

- Encryption key missing
  - Generate via the snippet above and set `ENCRYPTION_MASTER_KEY`

- PowerShell activation fails (Windows)
  - Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, reopen terminal, re-activate venv


## 13) Security & privacy

- Each user’s data is isolated via Supabase RLS policies
- No UUID exposure; users see session-scoped numeric IDs
- Encryption utilities included; protect your keys and `.env`
- Keep your Telegram, Supabase, and Groq keys private


## 14) Contributing

1) Fork the repository
2) Create a feature branch
3) Make changes with clear commits
4) Test locally (run bot, try commands)
5) Open a pull request


## 15) License

MIT License. Add a `LICENSE` file if not present.


## 16) Quick commands reference

Commands:
- `/start`, `/help`, `/status`, `/health`, `/register`
- `/notes`, `/tasks`, `/links`, `/reminders`, `/stats`
- `/search <query>`

Natural language:
- Notes: “I learned that Supabase is awesome!”
- Links: “Read later: https://example.com”
- Tasks: “Task: Review metrics” / “complete 2” / “delete 3”
- Reminders: “Remind me to call mom at 6pm tomorrow”

---
Made with ❤️ to help you remember, organize, and resurface what matters.
