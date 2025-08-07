#!/usr/bin/env python3
"""
🧠 MySecondMind - Your Personal Second Brain on Telegram

Main entry point for the MySecondMind Telegram bot.
Handles bot initialization, routing, and startup.
"""

import os
import logging
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Update
from telegram.ext import ContextTypes
from telegram.ext import Application

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Import our handlers
from handlers.basic_commands import start_handler, help_handler, status_handler
from handlers.register import register_handler
from handlers.natural_language import process_natural_message

async def health_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Health check handler for monitoring."""
    await update.message.reply_text("🟢 Bot is healthy and running!")

def main():
    """Start the MySecondMind bot."""
    
    # Get bot token
    token = os.getenv('TELEGRAM_TOKEN')
    if not token:
        logger.error("TELEGRAM_TOKEN not found in environment variables!")
        return
    
    # Create application
    application = Application.builder().token(token).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("status", status_handler))
    application.add_handler(CommandHandler("register", register_handler))
    application.add_handler(CommandHandler("health", health_handler))
    
    # Add content viewing commands
    from handlers.content_commands import (
        view_notes_command, view_tasks_command, view_links_command, 
        view_reminders_command, search_command, content_stats_command
    )
    application.add_handler(CommandHandler("notes", view_notes_command))
    application.add_handler(CommandHandler("tasks", view_tasks_command))
    application.add_handler(CommandHandler("links", view_links_command))
    application.add_handler(CommandHandler("reminders", view_reminders_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("stats", content_stats_command))
    
    # Add message handlers for natural language processing
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_natural_message))
    
    logger.info("🧠 MySecondMind bot starting...")
    logger.info("📱 Available commands: /start, /help, /status, /register, /health")
    logger.info("🤖 AI-powered natural language processing enabled")
    
    # Always use webhook mode for production deployment
    port = int(os.getenv('PORT', 10000))  # Default port for local testing
    render_url = os.getenv('RENDER_EXTERNAL_URL', 'https://mymind-924q.onrender.com')
    webhook_url = f"{render_url}/telegram"  # Use /telegram path for webhook
    
    logger.info(f"🌐 Starting webhook mode on port {port}")
    logger.info(f"🔗 Webhook URL: {webhook_url}")
    logger.info(f"🔍 Environment - PORT: {os.getenv('PORT', 'Using default 10000')}")
    logger.info("💚 Health monitoring: Use root URL for health checks")
    
    # Simple webhook mode - health checks via Telegram commands
    logger.info("🚀 Starting webhook mode...")
    logger.info(f"💚 Health monitoring: Use /health command in Telegram or {render_url}/telegram")
    
    # Use run_webhook which handles everything internally
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        webhook_url=webhook_url,
        url_path="/telegram",  # Only handle Telegram webhooks on /telegram
        allowed_updates=None
    )

if __name__ == '__main__':
    main()
