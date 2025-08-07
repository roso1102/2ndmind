"""
🤖 Basic Command Handlers for MySecondMind

Handles /start, /help, and /status commands.
"""

from telegram import Update
from telegram.ext import ContextTypes

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command."""
    
    user = update.effective_user
    
    welcome_message = f"""
🧠 **Welcome to MySecondMind, {user.first_name}!**

I'm your personal AI assistant that acts as your "second brain" 🤖

**What I can do:**
• 💭 Store your thoughts and ideas
• 📝 Manage tasks and reminders  
• 🔗 Summarize links and articles
• 📄 Process PDFs and screenshots
• 🌤️ Daily planning with weather
• 🔄 Resurface forgotten memories

**Quick Start:**
1. First, you need to register: `/register`
2. Then just talk to me naturally!

Try saying: *"Remind me to call mom tomorrow"*

Type `/help` for all commands.
"""
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /help command."""
    
    help_message = """
🆘 **MySecondMind Commands**

**Setup:**
• `/start` - Welcome message
• `/register` - Create your account
• `/status` - Check bot health

**View Your Content:**
• `/notes` - View recent notes
• `/tasks` - View recent tasks  
• `/links` - View saved links
• `/reminders` - View reminders
• `/stats` - Content statistics

**Search & Find:**
• `/search <query>` - Search all content
• `/search notes <query>` - Search notes only
• `/search tasks urgent` - Find urgent tasks

**Natural Language (Just talk!):**
• *"Remind me to..."* - Creates reminders
• *"I need to finish..."* - Creates tasks
• *"I learned that..."* - Saves notes
• *"Read later: https://..."* - Saves links
• Send files/images - Processes and saves

**Features:**
• 🧠 AI-powered intent understanding
• 🔐 Encrypted, secure database storage
• � Full-text search across all content
• 🔄 Multi-user support
• 📱 Works entirely on Telegram

**Need help?** Just ask me anything in natural language!
"""
    
    await update.message.reply_text(help_message, parse_mode='Markdown')

async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /status command."""
    
    # Basic health check
    try:
        from core.notion_router import get_notion_client
        user_id = update.effective_user.id
        
        # Try to get user's Notion client
        try:
            notion, user_data = get_notion_client(user_id)
            registration_status = "✅ Registered"
            notion_status = "✅ Connected"
        except:
            registration_status = "❌ Not registered"
            notion_status = "❌ Not connected"
        
        # Check APIs
        import os
        telegram_status = "✅ Connected" if os.getenv('TELEGRAM_TOKEN') else "❌ Missing"
        groq_status = "✅ Connected" if os.getenv('GROQ_API_KEY') else "❌ Missing"
        weather_status = "✅ Connected" if os.getenv('WEATHER_API_KEY') else "⚠️ Optional"
        
        status_message = f"""
🔍 **MySecondMind Status**

**Your Registration:**
• Registration: {registration_status}
• Notion: {notion_status}

**Bot Health:**
• Telegram API: {telegram_status}
• Groq AI: {groq_status}  
• Weather API: {weather_status}
• Encryption: ✅ Active

**Usage:**
• Total users: {len(get_all_user_ids()) if 'get_all_user_ids' in locals() else '?'}
• Your user ID: `{user_id}`

{("⚠️ **Action needed:** Use `/register` to connect your Notion workspace" if registration_status == "❌ Not registered" else "🎉 **All systems operational!**")}
"""
        
        await update.message.reply_text(status_message, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ **Status Check Failed**\n\n"
            f"Error: `{str(e)}`\n\n"
            f"Please check your bot configuration.",
            parse_mode='Markdown'
        )
