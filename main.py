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
    
    # Add message handlers for natural language processing
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_natural_message))
    
    logger.info("🧠 MySecondMind bot starting...")
    logger.info("📱 Available commands: /start, /help, /status, /register")
    logger.info("🤖 AI-powered natural language processing enabled")
    
    # Check if running on Render (production) or locally
    port = int(os.getenv('PORT', 0))
    if port:
        # Production mode: Use webhooks
        webhook_url = f"https://mymind.onrender.com"
        logger.info(f"🌐 Starting webhook mode on port {port}")
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            webhook_url=webhook_url,
            allowed_updates=None
        )
    else:
        # Development mode: Use polling
        logger.info("🔄 Starting polling mode for development")
        application.run_polling(allowed_updates=None)

if __name__ == '__main__':
    main()
