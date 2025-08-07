#!/usr/bin/env python3
"""
📝 User Registration Handler for MySecondMind

Handles the /register command and user onboarding process.
Validates Notion tokens and sets up user workspace connections.
"""

import logging
import re
from typing import Optional

from models.user_management import user_manager
from core.encryption import test_user_encryption

logger = logging.getLogger(__name__)

async def handle_register_command(update, context=None) -> None:
    """Handle the /register command for Notion workspace setup."""
    
    logger.info(f"🔧 Registration handler called with update: {update}")
    
    if not update.message or not update.message.text:
        logger.error("❌ No message or text in update")
        return
    
    user_id = str(update.effective_user.id)
    username = update.effective_user.username
    
    logger.info(f"🔧 Processing registration for user {user_id} ({username})")
    
    # Parse command arguments
    parts = update.message.text.split()
    logger.info(f"🔧 Command parts: {parts}")
    
    if len(parts) == 1:
        # No arguments - show help
        logger.info("📖 Showing registration help")
        await send_registration_help(update)
        return
    
    if len(parts) < 5:
        # Insufficient arguments
        await update.message.reply_text(
            "❌ **Registration Error**\n\n"
            "Insufficient arguments provided.\n\n"
            "Use: `/register <notion_token> <db_notes> <db_links> <db_reminders>`\n\n"
            "For help, use: `/register` with no arguments",
            parse_mode='Markdown'
        )
        return
    
    # Extract arguments
    notion_token = parts[1]
    db_notes = parts[2]
    db_links = parts[3]
    db_reminders = parts[4]
    
    logger.info(f"🔧 Registration attempt with databases: notes={db_notes[:8]}..., links={db_links[:8]}..., reminders={db_reminders[:8]}...")
    
    # Validate input format
    validation_error = validate_registration_inputs(notion_token, db_notes, db_links, db_reminders)
    if validation_error:
        await update.message.reply_text(validation_error, parse_mode='Markdown')
        return
    
    # Set up Notion workspace
    from handlers.notion_client import notion_client
    
    await update.message.reply_text(
        "🔄 **Setting up your Notion workspace...**\n\n"
        "This may take a few seconds while I validate your token and databases.",
        parse_mode='Markdown'
    )
    
    setup_result = notion_client.setup_user_workspace(user_id, notion_token, db_notes, db_links, db_reminders)
    
    if not setup_result["success"]:
        error_msg = "❌ **Notion Workspace Setup Failed**\n\n"
        error_msg += "**Errors encountered:**\n"
        for error in setup_result["errors"]:
            error_msg += f"• {error}\n"
        error_msg += "\n💡 Please check your token and database IDs and try again."
        
        await update.message.reply_text(error_msg, parse_mode='Markdown')
        return
    
    # Save user registration to Supabase
    success = user_manager.register_user(
        user_id=user_id,
        notion_token=notion_token,
        db_notes=db_notes,
        db_links=db_links,
        db_reminders=db_reminders,
        telegram_username=username
    )
    
    if success:
        await update.message.reply_text(
            "🎉 **Registration Successful!**\n\n"
            "✅ Notion token validated\n"
            "✅ All databases accessible\n"
            "✅ Workspace connected\n"
            "✅ User profile created\n\n"
            "🧠 **Your Second Brain is now active!**\n\n"
            "Try sending me:\n"
            "📝 *\"I learned something interesting about quantum computing\"*\n"
            "🔗 *\"Read later: https://example.com\"*\n"
            "⏰ *\"Remind me to call mom tomorrow\"*\n"
            "📋 *\"I need to finish my project by Friday\"*\n\n"
            "Everything will be saved to your Notion workspace! 🚀",
            parse_mode='Markdown'
        )
        logger.info(f"✅ User {user_id} successfully registered with Notion workspace")
    else:
        await update.message.reply_text(
            "❌ **Registration Failed**\n\n"
            "Notion workspace setup was successful, but I couldn't save your profile.\n\n"
            "Please try again or contact support.",
            parse_mode='Markdown'
        )
        logger.error(f"❌ Failed to save user {user_id} to database after successful Notion setup")
        return
    
    # Extract arguments
    notion_token = parts[1]
    db_notes = parts[2] 
    db_links = parts[3]
    db_reminders = parts[4]
    
    # Validate inputs
    validation_error = validate_registration_inputs(notion_token, db_notes, db_links, db_reminders)
    if validation_error:
        await update.message.reply_text(validation_error, parse_mode='Markdown')
        return
    
    # Test encryption for this user
    if not test_user_encryption(user_id):
        await update.message.reply_text(
            "❌ **Security Error**\n\n"
            "Failed to initialize encryption for your account. "
            "Please try again or contact support.",
            parse_mode='Markdown'
        )
        return
    
    # Register the user
    success = user_manager.register_user(
        user_id=user_id,
        notion_token=notion_token,
        db_notes=db_notes,
        db_links=db_links,
        db_reminders=db_reminders,
        telegram_username=username
    )
    
    if success:
        await send_registration_success(update, username or "User")
        logger.info(f"✅ User {user_id} (@{username}) registered successfully")
    else:
        await update.message.reply_text(
            "❌ **Registration Failed**\n\n"
            "Failed to save your registration. Please try again.\n\n"
            "If the problem persists, contact support.",
            parse_mode='Markdown'
        )

async def send_registration_help(update) -> None:
    """Send registration help and setup instructions."""
    
    help_text = """
🔐 **MySecondMind Registration**

To connect your personal Notion workspace, use:

`/register <notion_token> <db_notes> <db_links> <db_reminders>`

**Setup Steps:**

**1. Create Notion Integration** 🔧
• Go to [notion.so/my-integrations](https://notion.so/my-integrations)
• Click "New integration"
• Name it "MySecondMind" 
• Copy the "Internal Integration Token"

**2. Create Notion Databases** 📚
• Create three databases in your Notion workspace:
  - `📝 Notes` (for thoughts, ideas, learnings)
  - `🔗 Links` (for saved articles and resources)  
  - `⏰ Reminders` (for tasks and time-based alerts)

**3. Share Databases** 🔗
• For each database, click "Share" → Add your integration
• Copy each database ID from the URL (32-char string)

**4. Register** ✅
`/register ntn_abc123 db_notes_id db_links_id db_reminders_id`

*Note: Both new format (`ntn_`) and legacy format (`secret_`) tokens are supported.*

**Security:** 🔒
• Your token is encrypted with military-grade security
• Only you can access your Notion workspace  
• Multi-user isolation ensures complete privacy

**Need help?** Type `/help` for more commands.
"""
    
    await update.message.reply_text(help_text, parse_mode='Markdown', disable_web_page_preview=True)

async def send_registration_success(update, username: str) -> None:
    """Send registration success message."""
    
    success_text = f"""
🎉 **Welcome to MySecondMind, {username}!**

✅ **Registration Successful**

Your personal "Second Brain" is now active! Here's what you can do:

**🧠 Natural Language Interaction:**
• *"I learned that quantum computers use qubits"* → Saves as note
• *"Read later: https://article.com"* → Saves link with metadata  
• *"Remind me to call mom at 8pm"* → Creates time-based reminder
• *"What did I save about productivity?"* → Searches your knowledge

**🔐 Security & Privacy:**
• Your Notion token is encrypted and secure
• Only you can access your personal workspace
• Complete data isolation from other users

**🚀 Coming Soon:**
• 🔁 **Resurfacing Engine** - Rediscover forgotten knowledge
• 🌅 **Morning Briefings** - Daily planning with weather & reminders  
• 🌙 **Evening Reflections** - Automated journaling prompts
• 📄 **Smart File Processing** - PDFs, images, OCR

**Start using your Second Brain right now!**
Just chat naturally - I understand what you want to save! 🤖✨
"""
    
    await update.message.reply_text(success_text, parse_mode='Markdown')

def validate_registration_inputs(notion_token: str, db_notes: str, db_links: str, db_reminders: str) -> Optional[str]:
    """Validate registration inputs and return error message if invalid."""
    
    # Validate Notion token format - support both new ntn_ and legacy secret_ formats
    # Allow flexible character length after prefix (Notion tokens can vary)
    legacy_format = re.match(r'^secret_[a-zA-Z0-9]+$', notion_token)
    new_format = re.match(r'^ntn_[a-zA-Z0-9]+$', notion_token)
    
    # Ensure minimum reasonable length (prefix + at least 20 chars)
    min_length_check = len(notion_token) >= 25
    
    if not (legacy_format or new_format) or not min_length_check:
        return (
            "❌ **Invalid Notion Token**\n\n"
            "Notion tokens should start with either:\n"
            "• `ntn_` (new format) followed by alphanumeric characters\n"
            "• `secret_` (legacy format) followed by alphanumeric characters\n\n"
            "Examples:\n"
            "• `ntn_abc123def456...` (new format)\n"
            "• `secret_abc123def456...` (legacy format)\n\n"
            f"Your token length: {len(notion_token)} characters\n"
            f"Token format detected: {'✅' if (legacy_format or new_format) else '❌'}\n\n"
            "Get your token from [notion.so/my-integrations](https://notion.so/my-integrations)"
        )
    
    # Validate database ID format (32 character hex)
    db_pattern = r'^[a-f0-9]{32}$'
    
    if not re.match(db_pattern, db_notes.replace('-', '')):
        return (
            "❌ **Invalid Notes Database ID**\n\n"
            "Database IDs should be 32 hexadecimal characters.\n\n"
            "Copy from your Notion database URL after the last slash."
        )
    
    if not re.match(db_pattern, db_links.replace('-', '')):
        return (
            "❌ **Invalid Links Database ID**\n\n"
            "Database IDs should be 32 hexadecimal characters.\n\n"
            "Copy from your Notion database URL after the last slash."
        )
    
    if not re.match(db_pattern, db_reminders.replace('-', '')):
        return (
            "❌ **Invalid Reminders Database ID**\n\n"
            "Database IDs should be 32 hexadecimal characters.\n\n"
            "Copy from your Notion database URL after the last slash."
        )
    
    return None  # All valid

async def check_user_registration(update, context=None) -> bool:
    """Check if user is registered and prompt registration if not."""
    
    user_id = str(update.effective_user.id)
    
    if user_manager.is_user_registered(user_id):
        # Update last active timestamp
        user_manager.update_last_active(user_id)
        return True
    
    # User not registered - send prompt
    await update.message.reply_text(
        "🔐 **Registration Required**\n\n"
        "To use your personal Second Brain, you need to connect your Notion workspace.\n\n"
        "Use `/register` to get started with the setup process.\n\n"
        "This only takes 2 minutes and gives you a powerful AI-powered knowledge management system!",
        parse_mode='Markdown'
    )
    
    return False
