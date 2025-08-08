"""
🔐 Secure User Registration Handler for MySecondMind

Handles the /register command for Supabase-based multi-user setup.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def register_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /register command for Supabase-based system."""
    
    user_id = str(update.effective_user.id)
    username = update.effective_user.username
    first_name = update.effective_user.first_name or "User"
    
    try:
        # Use the user management system to register user
        from models.user_management import user_manager
        
        # Simple registration - just create user record
        success = user_manager.register_user(
            user_id=user_id,
            telegram_username=username,
            first_name=first_name,
            last_name=update.effective_user.last_name
        )
        
        if success:
            response = f"🎉 **Welcome to MySecondMind, {first_name}!**\n\n"
            response += "✅ **Your account is now active**\n\n"
            response += "🚀 **Ready to use:**\n"
            response += "• Just talk naturally to save notes, tasks, reminders\n"
            response += "• Use /notes, /tasks, /links to view your content\n"
            response += "• Use /search to find anything you've saved\n"
            response += "• Use /stats to see your content statistics\n\n"
            response += "💡 **Try saying:**\n"
            response += "• \"I learned that Supabase is awesome!\"\n"
            response += "• \"I need to finish my project by Friday\"\n"
            response += "• \"Remind me to call mom tomorrow\"\n\n"
            response += "🧠 **Your Second Brain is ready!**"
        else:
            response = "❌ **Registration Failed**\n\n"
            response += "There was an issue setting up your account. Please try again.\n\n"
            response += "If the problem persists, please contact support."
            
    except Exception as e:
        logger.error(f"Registration error for user {user_id}: {e}")
        response = "❌ **Registration Error**\n\n"
        response += "An unexpected error occurred. Please try again later.\n\n"
        response += "If the problem persists, please contact support."
    
    await update.message.reply_text(response, parse_mode='Markdown')
