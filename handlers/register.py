"""
🔐 Secure User Registration Handler for MySecondMind

Handles the /register command for multi-user setup with encrypted storage.
"""

import os
import json
import logging
from cryptography.fernet import Fernet
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Initialize encryption
FERNET_KEY = os.getenv("FERNET_KEY")
if FERNET_KEY:
    fernet = Fernet(FERNET_KEY.encode())
else:
    logger.warning("FERNET_KEY not set - registration will not work!")
    fernet = None

def store_user_data(user_id: str, token: str, db_links: str, db_notes: str, db_tasks: str):
    """Store encrypted user data."""
    if not fernet:
        raise Exception("Encryption not configured")
    
    path = "data/user_data.json.enc"
    
    # Load existing data or create new
    try:
        if os.path.exists(path):
            with open(path, "rb") as f:
                decrypted = json.loads(fernet.decrypt(f.read()))
        else:
            decrypted = {}
    except Exception as e:
        logger.warning(f"Could not load existing user data: {e}")
        decrypted = {}
    
    # Add/update user data
    decrypted[str(user_id)] = {
        "token": token,
        "db_links": db_links,
        "db_notes": db_notes,
        "db_tasks": db_tasks
    }
    
    # Save encrypted data
    os.makedirs("data", exist_ok=True)
    with open(path, "wb") as f:
        f.write(fernet.encrypt(json.dumps(decrypted).encode()))
    
    logger.info(f"User {user_id} registered successfully")

async def register_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /register command."""
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Parse command arguments
    args = context.args
    
    if len(args) != 4:
        await update.message.reply_text(
            "❌ **Registration Format:**\n\n"
            "`/register <notion_token> <db_links_id> <db_notes_id> <db_tasks_id>`\n\n"
            "**Steps to get your Notion credentials:**\n"
            "1. Go to https://notion.so/my-integrations\n"
            "2. Create a new integration\n"
            "3. Copy the 'Internal Integration Token'\n"
            "4. Create 3 databases in Notion (Links, Notes, Tasks)\n"
            "5. Share each database with your integration\n"
            "6. Copy each database ID from the URL\n\n"
            "**Security:** Your token is encrypted and never logged.",
            parse_mode='Markdown'
        )
        return
    
    notion_token, db_links, db_notes, db_tasks = args
    
    try:
        # Validate token format (basic check)
        if not notion_token.startswith(('secret_', 'ntn_')):
            await update.message.reply_text("❌ Invalid Notion token format!")
            return
        
        # Store user data
        store_user_data(user_id, notion_token, db_links, db_notes, db_tasks)
        
        await update.message.reply_text(
            "✅ **Registration Successful!**\n\n"
            "🔐 Your Notion credentials are encrypted and stored securely.\n"
            "🧠 You can now start using MySecondMind!\n\n"
            "**Try saying:** *\"Remind me to call mom tomorrow\"*"
        )
        
        # Delete the registration message for security
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=update.message.message_id)
        except:
            pass  # Fail silently if we can't delete
            
    except Exception as e:
        logger.error(f"Registration failed for user {user_id}: {e}")
        await update.message.reply_text(
            "❌ Registration failed. Please check your credentials and try again."
        )
