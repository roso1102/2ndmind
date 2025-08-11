#!/usr/bin/env python3
"""
🧠 MySecondMind - FastAPI Implementation
Simple and effective webhook handler with health monitoring
"""

import os
import logging
import httpx
import time
from datetime import datetime
from fastapi import FastAPI, Request, BackgroundTasks
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="MySecondMind Bot", version="1.0.0")

# Get configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_TOKEN')
WEBHOOK_URL = os.getenv('RENDER_EXTERNAL_URL', 'https://mymind-924q.onrender.com')
API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

def log(message, level="INFO"):
    """Simple logging function"""
    if level == "ERROR":
        logger.error(message)
    elif level == "WARNING":
        logger.warning(message)
    else:
        logger.info(message)

# Import handlers
from handlers.register import register_handler
from handlers.natural_language import process_natural_message
from models.user_management import user_manager

# Initialize advanced AI features
log("🚀 Initializing Advanced AI Features...")

# Initialize semantic search engine
try:
    from core.semantic_search import get_semantic_engine
    semantic_engine = get_semantic_engine()
    log("✅ Semantic search engine initialized")
except Exception as e:
    log(f"⚠️ Semantic search initialization failed: {e}", "WARNING")

# Initialize notification scheduler
try:
    from core.notification_scheduler import get_notification_scheduler
    notification_scheduler = get_notification_scheduler()
    log("✅ Notification scheduler initialized")
except Exception as e:
    log(f"⚠️ Notification scheduler initialization failed: {e}", "WARNING")

# Initialize advanced AI
try:
    from core.advanced_ai import advanced_ai
    log("✅ Advanced AI conversation engine initialized")
except Exception as e:
    log(f"⚠️ Advanced AI initialization failed: {e}", "WARNING")

log("🎉 Advanced features initialization complete!")

async def check_user_registration(mock_update, chat_id):
    """Check if user is registered, send registration prompt if not."""
    user_id = str(mock_update.effective_user.id)
    
    if user_manager.is_user_registered(user_id):
        return True
    else:
        # Send registration prompt
        await send_message(chat_id, 
            "🔑 **Welcome to MySecondMind!**\n\n"
            "Please register first by typing:\n"
            "`/register`\n\n"
            "This will activate your account and set up your personal Second Brain! 🧠")
        return False

async def send_message(chat_id, text, parse_mode=None):
    """Send a message to Telegram chat."""
    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "chat_id": chat_id,
                "text": text
            }
            if parse_mode:
                payload["parse_mode"] = parse_mode
                
            response = await client.post(f"{API_URL}/sendMessage", json=payload)
            return response.json()
    except Exception as e:
        log(f"Error sending message: {e}", level="ERROR")
        return None

# --- Health check endpoints ---
@app.get("/")
async def health_check():
    """Root health check for UptimeRobot"""
    return {
        "status": "healthy",
        "service": "MySecondMind Bot",
        "timestamp": datetime.now().isoformat(),
        "message": "🟢 Bot is online and ready!"
    }

@app.get("/health")
async def health_status():
    """Detailed health status"""
    return {
        "status": "healthy",
        "bot_configured": bool(TELEGRAM_BOT_TOKEN),
        "webhook_url": WEBHOOK_URL,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/ping")
async def ping():
    """Simple ping endpoint"""
    return {"ping": "pong", "timestamp": time.time()}

@app.head("/")
async def health_check_head():
    """HEAD request support for UptimeRobot"""
    return {}

@app.head("/health")
async def health_status_head():
    """HEAD request support for UptimeRobot"""
    return {}

@app.head("/ping")
async def ping_head():
    """HEAD request support for UptimeRobot"""
    return {}

@app.get("/status")
async def simple_status():
    """Ultra simple status endpoint for UptimeRobot"""
    return {"status": "ok"}

@app.get("/ok")
async def simple_ok():
    """Ultra simple OK endpoint"""
    return "OK"

@app.get("/debug/routes")
async def debug_routes():
    """Debug endpoint to see all registered routes"""
    routes = []
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            routes.append({
                "path": route.path,
                "methods": list(route.methods) if route.methods else [],
                "name": getattr(route, 'name', 'Unknown')
            })
    return {"routes": routes, "total_routes": len(routes)}

# Add webhook debugging endpoints
@app.get("/webhook")
async def webhook_get():
    """Debug: Webhook called with GET method"""
    log("⚠️ Webhook called with GET method - this might be the 405 issue!")
    return {"error": "Webhook should use POST method", "method": "GET"}

@app.options("/webhook")
async def webhook_options():
    """Handle OPTIONS requests for webhook"""
    return {"methods": ["POST"], "endpoint": "webhook"}

@app.head("/webhook")
async def webhook_head():
    """Handle HEAD requests for webhook"""
    return {"ok": True}

@app.get("/reset-webhook")
async def reset_webhook():
    """Manually reset the Telegram webhook"""
    webhook_url = f"{WEBHOOK_URL}/webhook"
    try:
        async with httpx.AsyncClient() as client:
            # First delete existing webhook
            delete_response = await client.post(f"{API_URL}/deleteWebhook")
            delete_result = delete_response.json()
            
            # Then set new webhook
            set_response = await client.post(f"{API_URL}/setWebhook", json={
                "url": webhook_url
            })
            set_result = set_response.json()
            
            return {
                "delete_webhook": delete_result,
                "set_webhook": set_result,
                "new_webhook_url": webhook_url
            }
    except Exception as e:
        return {"error": str(e)}

# --- Webhook handler ---
@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Handle incoming Telegram webhook"""
    log("🔍 Webhook endpoint hit via POST method")
    return await handle_telegram_webhook(request)

@app.post("/telegram")
async def telegram_webhook_alt(request: Request):
    """Alternative webhook endpoint for telegram-bot compatibility"""
    log("🔍 /telegram endpoint hit via POST method")
    return await handle_telegram_webhook(request)

aSYNC_TOKEN = object()  # prevent accidental typos in edits

async def handle_telegram_webhook(request: Request):
    """Actual webhook processing logic"""
    chat_id = None
    user_id = None
    
    try:
        # Parse the incoming webhook data
        data = await request.json()
        log(f"Received webhook: {data}")
        
        if "message" not in data:
            log("No message in webhook data", level="WARNING")
            return {"ok": True}
        
        message = data["message"]
        chat_id = message["chat"]["id"]
        user_id = str(message["from"]["id"])
        
        # Process different message types
        if "text" in message:
            # Handle text messages
            text = message["text"]
            log(f"🚀 NEW VERSION: Handling message: {text} from user {user_id}")
            
            # CRITICAL DEBUG: Check text properties
            log(f"🔍 DEBUG: text='{text}', type={type(text)}, repr={repr(text)}")
            log(f"🔍 DEBUG: text.startswith('/')={text.startswith('/')}")
            log(f"🔍 DEBUG: len(text)={len(text)}, first_char='{text[0] if text else 'EMPTY'}'")
            
            # Process commands
            if text.startswith("/"):
                cmd = text.split()[0].lower()
                log(f"🎯 COMMAND DETECTED: {cmd}")
                log(f"🎯 ENTERING COMMAND PROCESSING BLOCK")
                
                if cmd == "/start":
                    await send_message(chat_id, "👋 Welcome to MySecondMind!\n\nI'm your AI-powered personal assistant. I can help you with:\n• Task management\n• Information storage\n• Smart responses\n\nUse /register to activate your account and get started!")
                    return {"ok": True}
                    
                elif cmd == "/help":
                    help_text = """
🤖 **MySecondMind Help**

**📋 Commands:**
• `/start` - Welcome message and introduction
• `/register` - Activate your account
• `/help` - Show this help menu

**👁️ View Your Content:**
• `/notes` - Show your recent notes  
• `/tasks` - Show your recent tasks
• `/links` - Show your saved links
• `/reminders` - Show your reminders
• `/stats` - Show content statistics

**➕ Create Content:**
• `/add note <text>`
• `/add task <text>`
• `/add link <url> [context]`
• `/add reminder <text>`

**✏️ Edit / 🗑️ Delete / ✅ Complete:**
• `/edit <id> <new text>` or `/edit note <id> <new text>`
• `/delete <id>` or `/delete task <id>`
• `/complete <id>` or `/complete task <id>`

**🔍 Search & Find:**
• `/search <query>` - Search all your content
• `/search notes <query>` - Search only notes
• `/search tasks <query>` - Search only tasks
• `/search links <query>` - Search only links

**🗣️ Natural Language:**
Just talk to me naturally! I understand:

*💭 Notes & Ideas:*
• "I learned that Supabase is awesome!"
• "Remember: Python is great for automation"
• "Note: Meeting insights from today"

*📋 Tasks & TODOs:*
• "I need to finish the project by Friday"
• "Task: Review team performance metrics"
• "Must complete code review before noon"

*🔗 Links & Articles:*
• "Read later: https://interesting-article.com"
• "Bookmark: https://useful-tool.com for productivity"
• "Save this: https://tutorial.com about Python"

*⏰ Reminders:*
• "Remind me to call mom tomorrow at 6pm"
• "Alert me about the meeting at 2pm"
• "Don't forget to submit report by Friday"

**🧠 Your Second Brain is ready to help!**
"""
                    await send_message(chat_id, help_text)
                    return {"ok": True}
                    
                elif cmd == "/register":
                    log(f"🎯 Processing /register for user {user_id}")
                    # Create mock update object for registration handler
                    class MockUpdate:
                        def __init__(self, text, chat_id, user_id, username, first_name=None, last_name=None):
                            self.message = MockMessage(text, chat_id)
                            self.effective_user = MockUser(user_id, username, first_name, last_name)
                    
                    class MockMessage:
                        def __init__(self, text, chat_id):
                            self.text = text
                            self.chat_id = chat_id
                            
                        async def reply_text(self, response, parse_mode=None, disable_web_page_preview=None):
                            await send_message(self.chat_id, response, parse_mode)
                    
                    class MockUser:
                        def __init__(self, user_id, username, first_name=None, last_name=None):
                            self.id = int(user_id)
                            self.username = username
                            self.first_name = first_name
                            self.last_name = last_name
                    
                    try:
                        user_data = message.get("from", {})
                        mock_update = MockUpdate(
                            text, 
                            chat_id, 
                            user_id, 
                            user_data.get("username"),
                            user_data.get("first_name"),
                            user_data.get("last_name")
                        )
                        await register_handler(mock_update, None)
                        log(f"✅ /register completed for user {user_id}")
                    except Exception as e:
                        log(f"❌ Error in /register: {e}", "ERROR")
                        await send_message(chat_id, f"❌ Registration failed: {str(e)}")
                    return {"ok": True}
                    
                elif cmd == "/status":
                    await send_message(chat_id, 
                        "🟢 MySecondMind Status: ONLINE\n"
                        f"🕐 Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        "💚 All systems operational!")
                    return {"ok": True}
                    
                elif cmd == "/health":
                    await send_message(chat_id, "🟢 Bot is healthy and running!")
                    return {"ok": True}
                
                # View commands
                elif cmd == "/notes":
                    log(f"🗒️ Processing /notes for user {user_id}")
                    # Create mock update for content commands
                    class MockUpdate:
                        def __init__(self, text, chat_id, user_id, username, first_name=None, last_name=None):
                            self.message = MockMessage(text, chat_id)
                            self.effective_user = MockUser(user_id, username, first_name, last_name)
                    
                    class MockMessage:
                        def __init__(self, text, chat_id):
                            self.text = text
                            self.chat_id = chat_id
                            
                        async def reply_text(self, response, parse_mode=None, disable_web_page_preview=None):
                            await send_message(self.chat_id, response, parse_mode)
                    
                    class MockUser:
                        def __init__(self, user_id, username, first_name=None, last_name=None):
                            self.id = int(user_id)
                            self.username = username
                            self.first_name = first_name
                            self.last_name = last_name
                    
                    try:
                        from handlers.content_commands import view_notes_command
                        user_data = message.get("from", {})
                        mock_update = MockUpdate(
                            text, chat_id, user_id, user_data.get("username"),
                            user_data.get("first_name"), user_data.get("last_name")
                        )
                        
                        # Check registration first
                        if not await check_user_registration(mock_update, chat_id):
                            return {"ok": True}
                            
                        await view_notes_command(mock_update, None)
                        log(f"✅ /notes completed for user {user_id}")
                    except Exception as e:
                        log(f"❌ Error in /notes: {e}", "ERROR")
                        await send_message(chat_id, f"❌ Error retrieving notes: {str(e)}")
                    return {"ok": True}
                
                elif cmd == "/tasks":
                    log(f"📋 Processing /tasks for user {user_id}")
                    try:
                        from handlers.content_commands import view_tasks_command
                        user_data = message.get("from", {})
                        
                        class MockUpdate:
                            def __init__(self, text, chat_id, user_id, username, first_name=None, last_name=None):
                                self.message = MockMessage(text, chat_id)
                                self.effective_user = MockUser(user_id, username, first_name, last_name)
                        
                        class MockMessage:
                            def __init__(self, text, chat_id):
                                self.text = text
                                self.chat_id = chat_id
                                
                            async def reply_text(self, response, parse_mode=None, disable_web_page_preview=None):
                                await send_message(self.chat_id, response, parse_mode)
                        
                        class MockUser:
                            def __init__(self, user_id, username, first_name=None, last_name=None):
                                self.id = int(user_id)
                                self.username = username
                                self.first_name = first_name
                                self.last_name = last_name
                        
                        mock_update = MockUpdate(
                            text, chat_id, user_id, user_data.get("username"),
                            user_data.get("first_name"), user_data.get("last_name")
                        )
                        
                        # Check registration first
                        if not await check_user_registration(mock_update, chat_id):
                            return {"ok": True}
                            
                        await view_tasks_command(mock_update, None)
                        log(f"✅ /tasks completed for user {user_id}")
                    except Exception as e:
                        log(f"❌ Error in /tasks: {e}", "ERROR")
                        await send_message(chat_id, f"❌ Error retrieving tasks: {str(e)}")
                    return {"ok": True}
                
                elif cmd == "/links":
                    log(f"🔗 Processing /links for user {user_id}")
                    try:
                        from handlers.content_commands import view_links_command
                        user_data = message.get("from", {})
                        
                        class MockUpdate:
                            def __init__(self, text, chat_id, user_id, username, first_name=None, last_name=None):
                                self.message = MockMessage(text, chat_id)
                                self.effective_user = MockUser(user_id, username, first_name, last_name)
                        
                        class MockMessage:
                            def __init__(self, text, chat_id):
                                self.text = text
                                self.chat_id = chat_id
                                
                            async def reply_text(self, response, parse_mode=None, disable_web_page_preview=None):
                                await send_message(self.chat_id, response, parse_mode)
                        
                        class MockUser:
                            def __init__(self, user_id, username, first_name=None, last_name=None):
                                self.id = int(user_id)
                                self.username = username
                                self.first_name = first_name
                                self.last_name = last_name
                        
                        mock_update = MockUpdate(
                            text, chat_id, user_id, user_data.get("username"),
                            user_data.get("first_name"), user_data.get("last_name")
                        )
                        
                        # Check registration first
                        if not await check_user_registration(mock_update, chat_id):
                            return {"ok": True}
                            
                        await view_links_command(mock_update, None)
                        log(f"✅ /links completed for user {user_id}")
                    except Exception as e:
                        log(f"❌ Error in /links: {e}", "ERROR")
                        await send_message(chat_id, f"❌ Error retrieving links: {str(e)}")
                    return {"ok": True}
                
                elif cmd == "/reminders":
                    log(f"⏰ Processing /reminders for user {user_id}")
                    try:
                        from handlers.content_commands import view_reminders_command
                        user_data = message.get("from", {})
                        
                        class MockUpdate:
                            def __init__(self, text, chat_id, user_id, username, first_name=None, last_name=None):
                                self.message = MockMessage(text, chat_id)
                                self.effective_user = MockUser(user_id, username, first_name, last_name)
                        
                        class MockMessage:
                            def __init__(self, text, chat_id):
                                self.text = text
                                self.chat_id = chat_id
                                
                            async def reply_text(self, response, parse_mode=None, disable_web_page_preview=None):
                                await send_message(self.chat_id, response, parse_mode)
                        
                        class MockUser:
                            def __init__(self, user_id, username, first_name=None, last_name=None):
                                self.id = int(user_id)
                                self.username = username
                                self.first_name = first_name
                                self.last_name = last_name
                        
                        mock_update = MockUpdate(
                            text, chat_id, user_id, user_data.get("username"),
                            user_data.get("first_name"), user_data.get("last_name")
                        )
                        
                        if not await check_user_registration(mock_update, chat_id):
                            return {"ok": True}
                        
                        await view_reminders_command(mock_update, None)
                        log(f"✅ /reminders completed for user {user_id}")
                    except Exception as e:
                        log(f"❌ Error in /reminders: {e}", "ERROR")
                        await send_message(chat_id, f"❌ Error retrieving reminders: {str(e)}")
                    return {"ok": True}
                
                # CRUD via slash commands
                elif cmd == "/add":
                    log(f"➕ Processing /add for user {user_id}")
                    try:
                        from handlers.content_commands import add_command
                        user_data = message.get("from", {})
                        
                        class MockUpdate:
                            def __init__(self, text, chat_id, user_id, username, first_name=None, last_name=None):
                                self.message = MockMessage(text, chat_id)
                                self.effective_user = MockUser(user_id, username, first_name, last_name)
                        
                        class MockMessage:
                            def __init__(self, text, chat_id):
                                self.text = text
                                self.chat_id = chat_id
                                
                            async def reply_text(self, response, parse_mode=None, disable_web_page_preview=None):
                                await send_message(self.chat_id, response, parse_mode)
                        
                        class MockUser:
                            def __init__(self, user_id, username, first_name=None, last_name=None):
                                self.id = int(user_id)
                                self.username = username
                                self.first_name = first_name
                                self.last_name = last_name
                        
                        class MockContext:
                            def __init__(self, args):
                                self.args = args
                        
                        # Parse args after /add
                        parts = text.split()[1:]
                        mock_update = MockUpdate(text, chat_id, user_id, user_data.get("username"), user_data.get("first_name"), user_data.get("last_name"))
                        mock_context = MockContext(parts)
                        
                        if not await check_user_registration(mock_update, chat_id):
                            return {"ok": True}
                        
                        await add_command(mock_update, mock_context)
                        log(f"✅ /add completed for user {user_id}")
                    except Exception as e:
                        log(f"❌ Error in /add: {e}", "ERROR")
                        await send_message(chat_id, f"❌ Error adding content: {str(e)}")
                    return {"ok": True}
                
                elif cmd == "/delete":
                    log(f"🗑️ Processing /delete for user {user_id}")
                    try:
                        from handlers.content_commands import delete_command
                        user_data = message.get("from", {})
                        
                        class MockUpdate:
                            def __init__(self, text, chat_id, user_id, username, first_name=None, last_name=None):
                                self.message = MockMessage(text, chat_id)
                                self.effective_user = MockUser(user_id, username, first_name, last_name)
                        
                        class MockMessage:
                            def __init__(self, text, chat_id):
                                self.text = text
                                self.chat_id = chat_id
                                
                            async def reply_text(self, response, parse_mode=None, disable_web_page_preview=None):
                                await send_message(self.chat_id, response, parse_mode)
                        
                        class MockUser:
                            def __init__(self, user_id, username, first_name=None, last_name=None):
                                self.id = int(user_id)
                                self.username = username
                                self.first_name = first_name
                                self.last_name = last_name
                        
                        class MockContext:
                            def __init__(self, args):
                                self.args = args
                        
                        parts = text.split()[1:]
                        mock_update = MockUpdate(text, chat_id, user_id, user_data.get("username"), user_data.get("first_name"), user_data.get("last_name"))
                        mock_context = MockContext(parts)
                        
                        if not await check_user_registration(mock_update, chat_id):
                            return {"ok": True}
                        
                        await delete_command(mock_update, mock_context)
                        log(f"✅ /delete completed for user {user_id}")
                    except Exception as e:
                        log(f"❌ Error in /delete: {e}", "ERROR")
                        await send_message(chat_id, f"❌ Error deleting content: {str(e)}")
                    return {"ok": True}
                
                elif cmd == "/complete":
                    log(f"✅ Processing /complete for user {user_id}")
                    try:
                        from handlers.content_commands import complete_command
                        user_data = message.get("from", {})
                        
                        class MockUpdate:
                            def __init__(self, text, chat_id, user_id, username, first_name=None, last_name=None):
                                self.message = MockMessage(text, chat_id)
                                self.effective_user = MockUser(user_id, username, first_name, last_name)
                        
                        class MockMessage:
                            def __init__(self, text, chat_id):
                                self.text = text
                                self.chat_id = chat_id
                                
                            async def reply_text(self, response, parse_mode=None, disable_web_page_preview=None):
                                await send_message(self.chat_id, response, parse_mode)
                        
                        class MockUser:
                            def __init__(self, user_id, username, first_name=None, last_name=None):
                                self.id = int(user_id)
                                self.username = username
                                self.first_name = first_name
                                self.last_name = last_name
                        
                        class MockContext:
                            def __init__(self, args):
                                self.args = args
                        
                        parts = text.split()[1:]
                        mock_update = MockUpdate(text, chat_id, user_id, user_data.get("username"), user_data.get("first_name"), user_data.get("last_name"))
                        mock_context = MockContext(parts)
                        
                        if not await check_user_registration(mock_update, chat_id):
                            return {"ok": True}
                        
                        await complete_command(mock_update, mock_context)
                        log(f"✅ /complete completed for user {user_id}")
                    except Exception as e:
                        log(f"❌ Error in /complete: {e}", "ERROR")
                        await send_message(chat_id, f"❌ Error completing task: {str(e)}")
                    return {"ok": True}
                
                elif cmd == "/edit":
                    log(f"✏️ Processing /edit for user {user_id}")
                    try:
                        from handlers.content_commands import edit_command
                        user_data = message.get("from", {})
                        
                        class MockUpdate:
                            def __init__(self, text, chat_id, user_id, username, first_name=None, last_name=None):
                                self.message = MockMessage(text, chat_id)
                                self.effective_user = MockUser(user_id, username, first_name, last_name)
                        
                        class MockMessage:
                            def __init__(self, text, chat_id):
                                self.text = text
                                self.chat_id = chat_id
                                
                            async def reply_text(self, response, parse_mode=None, disable_web_page_preview=None):
                                await send_message(self.chat_id, response, parse_mode)
                        
                        class MockUser:
                            def __init__(self, user_id, username, first_name=None, last_name=None):
                                self.id = int(user_id)
                                self.username = username
                                self.first_name = first_name
                                self.last_name = last_name
                        
                        class MockContext:
                            def __init__(self, args):
                                self.args = args
                        
                        parts = text.split()[1:]
                        mock_update = MockUpdate(text, chat_id, user_id, user_data.get("username"), user_data.get("first_name"), user_data.get("last_name"))
                        mock_context = MockContext(parts)
                        
                        if not await check_user_registration(mock_update, chat_id):
                            return {"ok": True}
                        
                        await edit_command(mock_update, mock_context)
                        log(f"✅ /edit completed for user {user_id}")
                    except Exception as e:
                        log(f"❌ Error in /edit: {e}", "ERROR")
                        await send_message(chat_id, f"❌ Error editing content: {str(e)}")
                    return {"ok": True}
                
                else:
                    # Unknown command
                    await send_message(chat_id, f"❓ Unknown command: {cmd}\n\nUse /help to see available commands.")
                    return {"ok": True}
            
            # Process non-command messages with natural language
            else:
                log(f"💬 Processing natural language: {text}")
                try:
                    # Create a mock update object for the handler
                    class MockUpdate:
                        def __init__(self, text, chat_id, user_id, username, first_name=None, last_name=None):
                            self.message = MockMessage(text, chat_id, user_id)
                            self.effective_user = MockEffectiveUser(user_id, username, first_name, last_name)
                    
                    class MockMessage:
                        def __init__(self, text, chat_id, user_id):
                            self.text = text
                            self.chat_id = chat_id
                            self.from_user = MockUser(user_id)
                            
                        async def reply_text(self, response, parse_mode=None):
                            await send_message(self.chat_id, response, parse_mode)
                    
                    class MockUser:
                        def __init__(self, user_id):
                            self.id = user_id

                    class MockEffectiveUser:
                        def __init__(self, user_id, username, first_name=None, last_name=None):
                            self.id = int(user_id)
                            self.username = username
                            self.first_name = first_name
                            self.last_name = last_name
                    
                    # Check if user is registered before processing natural language
                    user_data = message.get("from", {})
                    mock_update = MockUpdate(
                        text, 
                        chat_id, 
                        user_id, 
                        user_data.get("username"),
                        user_data.get("first_name"),
                        user_data.get("last_name")
                    )
                    
                    # For natural language processing, check registration first
                    if not await check_user_registration(mock_update, chat_id):
                        return {"ok": True}  # Registration prompt already sent
                    
                    # Process with natural language handler
                    await process_natural_message(mock_update, None)
                    log(f"✅ Natural language processing completed for user {user_id}")
                    
                except Exception as e:
                    log(f"❌ Error processing natural language: {e}", level="ERROR")
                    await send_message(chat_id, 
                        "I understand your message, but I'm having trouble processing it right now. "
                        "Please try again!")
                return {"ok": True}
        
        else:
            # Handle non-text messages
            await send_message(chat_id, 
                "I received your message! Currently I work best with text messages. "
                "More features coming soon! 🚀")
            
    except Exception as e:
        log(f"Error in webhook handler: {e}", level="ERROR")
        if chat_id:
            try:
                await send_message(chat_id, 
                    "Sorry, I encountered an error. Please try again!")
            except:
                pass
    
    # Always return success to Telegram
    return {"ok": True}

# --- Startup event ---
@app.on_event("startup")
async def startup_event():
    """Set up webhook on startup"""
    if TELEGRAM_BOT_TOKEN:
        webhook_url = f"{WEBHOOK_URL}/webhook"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{API_URL}/setWebhook", json={
                    "url": webhook_url
                })
                result = response.json()
                if result.get("ok"):
                    log(f"✅ Webhook set successfully: {webhook_url}")
                else:
                    log(f"❌ Failed to set webhook: {result}", level="ERROR")
        except Exception as e:
            log(f"Error setting webhook: {e}", level="ERROR")
    
    log("🚀 MySecondMind bot started successfully!")
    log(f"💚 Health endpoints: {WEBHOOK_URL}/, {WEBHOOK_URL}/health, {WEBHOOK_URL}/ping")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 10000))
    log(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
