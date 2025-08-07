# 🧠 MySecondMind

> Your Personal AI-Powered Second Brain on Telegram

**MySecondMind** is a private, secure Telegram bot that captures, organizes, and resurfaces your thoughts, tasks, and knowledge using AI and Notion as your personal database.

## ✨ Features

- 🧠 **Natural Language Processing** - Just talk to it naturally
- 📝 **Mind Dumping** - Capture thoughts and ideas instantly  
- ✅ **Task Management** - AI-powered task creation with reminders
- 🔗 **Link Summarization** - Auto-summarize articles and content
- 📄 **PDF Processing** - Extract and summarize document content
- 🖼️ **OCR** - Extract text from screenshots and images
- 🌤️ **Daily Planning** - Morning briefings with weather and tasks
- 🔄 **Memory Resurfacing** - Rediscover forgotten notes randomly
- 🔐 **Multi-User Security** - Encrypted, isolated user data
- 📱 **Telegram Native** - Works entirely within Telegram

## 🛠️ Tech Stack

- **AI**: Llama3 via Groq (free tier)
- **Storage**: Notion API (personal workspaces)
- **Bot**: python-telegram-bot
- **Security**: Fernet encryption
- **Processing**: Tesseract OCR, PyMuPDF
- **Scheduling**: APScheduler
- **Hosting**: Render/Railway (free tier)

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Telegram account
- Notion account (free)
- Groq account (free)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/roso1102/msm.git
   cd msm
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. **Get API Keys**
   - **Telegram**: Message @BotFather, create bot, copy token
   - **Groq**: Sign up at groq.com, get free API key
   - **Notion**: Create integration at notion.so/my-integrations
   - **Weather** (optional): Get key from openweathermap.org

5. **Test setup**
   ```bash
   python test_connections.py
   ```

6. **Start the bot**
   ```bash
   python main.py
   ```

## 📱 Usage

1. **Start conversation**: `/start`
2. **Register**: `/register <notion_token> <db_links> <db_notes> <db_tasks>`
3. **Natural language**: 
   - "Remind me to call mom tomorrow"
   - "I have an idea about solar panels"
   - Send links, PDFs, screenshots
   - Ask for daily planning

## 🔧 Development

### Project Structure
```
mysecondmind/
├── main.py              # Bot entry point
├── handlers/            # Feature modules
│   ├── basic_commands.py
│   ├── register.py
│   └── ...
├── core/                # Core utilities
│   ├── notion_router.py
│   └── ...
├── requirements.txt     # Dependencies
└── .env                # Configuration (not in repo)
```

### Adding Features
1. Create handler in `handlers/`
2. Import in `main.py`
3. Add to application handlers
4. Test and commit

## 🚀 Deployment

### Render (Recommended)
1. Connect GitHub repository
2. Set environment variables
3. Deploy automatically

### Manual Deployment
1. Set up server with Python 3.11+
2. Install dependencies
3. Configure environment variables
4. Run with process manager (PM2, systemd)

## 🔐 Security

- All user data is encrypted with Fernet
- API keys stored in environment variables
- Multi-user isolation
- No data sharing between users
- Notion workspaces are user-specific

## 📄 License

MIT License - see LICENSE file for details

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

## 🆘 Support

- Check `/help` in the bot
- Review logs for errors
- Test connections with `test_connections.py`
- Open GitHub issues for bugs

---

**Made with ❤️ for productivity enthusiasts**
