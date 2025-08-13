"""
🤖 Basic Command Handlers for MySecondMind

Handles /start, /help, and /status commands.
"""

from telegram import Update
from telegram.ext import ContextTypes
import os
from core.user_prefs import set_user_timezone, get_user_timezone

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command."""
    
    user = update.effective_user
    user_id = str(user.id)
    tz = get_user_timezone(user_id)
    llm_primary = (os.getenv('LLM_PRIMARY') or 'GROQ').upper()
    llm_fallback = (os.getenv('LLM_FALLBACK') or 'GROQ').upper()
    # Check if user has any content to personalize examples
    has_content = False
    try:
        from handlers.supabase_content import content_handler
        res = await content_handler.get_user_content(user_id, limit=1)
        has_content = bool(res.get('success') and res.get('count', 0) > 0)
    except Exception:
        pass
    
    welcome_message = f"""
    🧠 **Welcome to MySecondMind, {user.first_name}!**
    
    I'm your AI "second brain". I remember things for you, help plan your day, and find anything you've saved.
    
    **Personal setup**
    • Timezone: `{tz}`  
    • AI: Primary `{llm_primary}` → Fallback `{llm_fallback}`
    
    **What I can do**
    • 📝 Save notes, tasks, links, reminders
    • 🔎 Search your saved content in natural language
    • ⏰ Morning/evening summaries and reminders
    • 🧠 Resurface older memories
    
    **Quick actions**
    • `/register` to activate your account
    • `/timezone Asia/Kolkata` to set time zone
    • `/help` to see everything I can do
    
    {"Try: /notes or /tasks to see your recent items" if has_content else "Try: say \"I learned that Supabase is awesome\" or \"Remind me to call mom tomorrow\""}
    """
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /help command."""
    
    user = update.effective_user
    user_id = str(user.id)
    tz = get_user_timezone(user_id)
    llm_primary = (os.getenv('LLM_PRIMARY') or 'GROQ').upper()
    llm_fallback = (os.getenv('LLM_FALLBACK') or 'GROQ').upper()
    has_content = False
    try:
        from handlers.supabase_content import content_handler
        res = await content_handler.get_user_content(user_id, limit=1)
        has_content = bool(res.get('success') and res.get('count', 0) > 0)
    except Exception:
        pass

    help_message = f"""
    🆘 **Help & Commands**
    
    **Your setup**
    • Timezone: `{tz}`
    • AI: Primary `{llm_primary}` → Fallback `{llm_fallback}`
    
    **Quick actions**
    • `/notes`, `/tasks`, `/links`, `/reminders`
    • `/search <query>` — e.g., `/search python`, `/search tasks urgent`
    • `/stats` — your content stats
    • `/timezone <IANA_TZ>` — set your time zone (e.g., `/timezone Asia/Kolkata`)
    
    **Saving (just talk)**
    • "I learned that …" → saves a note
    • "I need to …" / "Task: …" → saves a task
    • "Remind me to … at 3pm" → reminder
    • "Read later: https://…" → link
    
    **Managing**
    • "delete 2" / "edit 3 <new text>" after a list
    • "complete 2" to mark a task done
    
    **Tips**
    {"• Try /notes to review recent items\n• Ask: \"what did I save about apples\"" if has_content else "• Start with a note or task\n• Ask me: \"how do I save a link?\""}
    
    I’ll adapt responses to your history and preferences.
    """
    
    await update.message.reply_text(help_message, parse_mode='Markdown')

async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /status command."""
    
    try:
        user_id = update.effective_user.id
        telegram_status = "✅ Connected" if os.getenv('TELEGRAM_TOKEN') else "❌ Missing"
        groq_status = "✅ Connected" if os.getenv('GROQ_API_KEY') else "⚠️ Optional"
        gemini_status = "✅ Connected" if os.getenv('GEMINI_API_KEY') else "⚠️ Optional"
        weather_status = "✅ Connected" if os.getenv('WEATHER_API_KEY') else "⚠️ Optional"
        supabase_status = "✅ Configured" if (os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_ANON_KEY')) else "❌ Missing"
        encryption_status = "✅ Active" if os.getenv('ENCRYPTION_MASTER_KEY') else "⚠️ Missing"
        llm_primary = (os.getenv('LLM_PRIMARY') or 'GROQ').upper()
        llm_fallback = (os.getenv('LLM_FALLBACK') or 'GROQ').upper()

        status_message = f"""
🔍 **MySecondMind Status**

**Your Registration:**
• Use `/register` to activate your account

**Bot Health:**
• Telegram API: {telegram_status}
• Groq AI: {groq_status}
• Gemini AI: {gemini_status}
• Weather API: {weather_status}
• Supabase: {supabase_status}
• Encryption: {encryption_status}

**Info:**
• Your user ID: `{user_id}`
• LLM: Primary `{llm_primary}` → Fallback `{llm_fallback}`

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
