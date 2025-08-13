"""
🤖 Basic Command Handlers for MySecondMind

Handles /start, /help, and /status commands.
"""

from telegram import Update
from telegram.ext import ContextTypes
import os
from core.user_prefs import set_user_timezone

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command."""
    
    user = update.effective_user
    
    welcome_message = f"""
🧠 **Welcome to MySecondMind, {user.first_name}!**

I'm your personal AI assistant that acts as your "second brain" 🤖

**What I can do:**
• 💭 Store your thoughts and ideas
• 📝 Manage tasks and reminders  
• 🔗 Save and search links and articles
• 📄 Process PDFs and screenshots
• 🌤️ Daily planning with weather
• 🔄 Resurface forgotten memories

**Quick Start:**
1. Register with one simple command: `/register`
2. Start saving your thoughts immediately!

Try saying: *"I learned that AI is revolutionizing productivity"*

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
• 🔎 Full-text search across all content
• 🔄 Multi-user support
• 📱 Works entirely on Telegram

**Need help?** Just ask me anything in natural language!
"""
    
    await update.message.reply_text(help_message, parse_mode='Markdown')

async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /status command."""
    
    try:
        user_id = update.effective_user.id
        telegram_status = "✅ Connected" if os.getenv('TELEGRAM_TOKEN') else "❌ Missing"
        groq_status = "✅ Connected" if os.getenv('GROQ_API_KEY') else "⚠️ Optional"
        weather_status = "✅ Connected" if os.getenv('WEATHER_API_KEY') else "⚠️ Optional"
        supabase_status = "✅ Configured" if (os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_ANON_KEY')) else "❌ Missing"
        encryption_status = "✅ Active" if os.getenv('ENCRYPTION_MASTER_KEY') else "⚠️ Missing"

        status_message = f"""
🔍 **MySecondMind Status**

**Your Registration:**
• Use `/register` to activate your account

**Bot Health:**
• Telegram API: {telegram_status}
• Groq AI: {groq_status}  
• Weather API: {weather_status}
• Supabase: {supabase_status}
• Encryption: {encryption_status}

**Info:**
• Your user ID: `{user_id}`

🎉 **All systems ready!**
"""
        await update.message.reply_text(status_message, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(
            f"❌ **Status Check Failed**\n\n"
            f"Error: `{str(e)}`\n\n"
            f"Please check your bot configuration.",
            parse_mode='Markdown'
        )

async def timezone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /timezone <IANA_TZ>. Example: /timezone Asia/Kolkata"""
    user_id = str(update.effective_user.id)
    if not context.args:
        await update.message.reply_text("Usage: /timezone Asia/Kolkata")
        return
    tz_name = " ".join(context.args).strip()
    ok = set_user_timezone(user_id, tz_name)
    if ok:
        await update.message.reply_text(f"✅ Timezone set to {tz_name}")
    else:
        await update.message.reply_text("❌ Invalid timezone. Please provide a valid IANA timezone like Asia/Kolkata")
