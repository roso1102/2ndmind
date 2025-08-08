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

# Import handlers
from handlers.registration import handle_register_command, check_user_registration
from handlers.natural_language import process_natural_message

def log(message, level="INFO"):
    """Simple logging function"""
    if level == "ERROR":
        logger.error(message)
    elif level == "WARNING":
        logger.warning(message)
    else:
        logger.info(message)

async def send_message(chat_id: int, text: str):
    """Send message to Telegram chat"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{API_URL}/sendMessage", json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown"
            })
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

# --- Webhook handler ---
@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Handle incoming Telegram webhook"""
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
                    await send_message(chat_id, "👋 Welcome to MySecondMind!\n\nI'm your AI-powered personal assistant. I can help you with:\n• Task management\n• Information storage\n• Smart responses\n\nUse /register to connect your Notion workspace and get started!")
                    return {"ok": True}
                    
                elif cmd == "/help":
                    help_text = """
🤖 *MySecondMind Help*

*Basic Commands:*
• /start - Welcome message
• /register - Connect your Notion workspace
• /help - Show this help
• /status - Bot status
• /health - Health check

*Content Management:*
• /delete 5 - Delete content by ID
• /complete 3 - Mark task as complete
• /edit 7 new content - Edit content
• /remove task 5 - Remove specific task

*Natural Language:*
Just chat with me naturally! I can understand and respond to:
• Notes and ideas to save
• Links to bookmark
• Reminders to set
• Questions about your saved content
• Content management: "delete task 5", "complete 3", "edit note 7"

Try saying things like:
• "I learned something interesting today..."
• "Read later: https://example.com"
• "Remind me to call mom tomorrow"
• "What did I save about productivity?"
• "Delete task 5"
• "Mark task 3 as done"
"""
                    await send_message(chat_id, help_text)
                    return {"ok": True}
                    
                elif cmd == "/register":
                    log(f"🎯 Processing /register for user {user_id}")
                    # Create mock update object for registration handler
                    class MockUpdate:
                        def __init__(self, text, chat_id, user_id, username):
                            self.message = MockMessage(text, chat_id)
                            self.effective_user = MockUser(user_id, username)
                    
                    class MockMessage:
                        def __init__(self, text, chat_id):
                            self.text = text
                            self.chat_id = chat_id
                            
                        async def reply_text(self, response, parse_mode=None, disable_web_page_preview=None):
                            await send_message(self.chat_id, response)
                    
                    class MockUser:
                        def __init__(self, user_id, username):
                            self.id = int(user_id)
                            self.username = username
                    
                    try:
                        mock_update = MockUpdate(text, chat_id, user_id, message.get("from", {}).get("username"))
                        await handle_register_command(mock_update)
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
                
                # Content Management Commands
                elif cmd in ["/delete", "/remove"]:
                    # Handle delete commands like "/delete 5" or "/delete task 3"
                    parts = text.split()[1:] if len(text.split()) > 1 else []
                    if not parts:
                        await send_message(chat_id, "❓ Please specify what to delete.\nExamples:\n• /delete 5\n• /delete task 3")
                        return {"ok": True}
                    
                    # Convert to natural language format
                    delete_message = f"delete {' '.join(parts)}"
                    
                    # Import content manager
                    from handlers.content_management import content_manager
                    result = await content_manager.handle_management_command(user_id, delete_message)
                    
                    if result.get('success'):
                        await send_message(chat_id, result['message'])
                    else:
                        await send_message(chat_id, f"❌ {result.get('error', 'Delete failed')}")
                    return {"ok": True}
                
                elif cmd in ["/complete", "/done"]:
                    # Handle completion commands like "/complete 5" or "/done task 3"
                    parts = text.split()[1:] if len(text.split()) > 1 else []
                    if not parts:
                        await send_message(chat_id, "❓ Please specify which task to complete.\nExamples:\n• /complete 5\n• /done task 3")
                        return {"ok": True}
                    
                    # Convert to natural language format
                    complete_message = f"complete {' '.join(parts)}"
                    
                    from handlers.content_management import content_manager
                    result = await content_manager.handle_management_command(user_id, complete_message)
                    
                    if result.get('success'):
                        await send_message(chat_id, result['message'])
                    else:
                        await send_message(chat_id, f"❌ {result.get('error', 'Complete failed')}")
                    return {"ok": True}
                
                elif cmd in ["/edit", "/update"]:
                    # Handle edit commands like "/edit 5 new content"
                    parts = text.split()[1:] if len(text.split()) > 1 else []
                    if len(parts) < 2:
                        await send_message(chat_id, "❓ Please specify what to edit.\nExamples:\n• /edit 5 new content\n• /update task 3 new description")
                        return {"ok": True}
                    
                    # Convert to natural language format
                    edit_message = f"edit {' '.join(parts)}"
                    
                    from handlers.content_management import content_manager
                    result = await content_manager.handle_management_command(user_id, edit_message)
                    
                    if result.get('success'):
                        await send_message(chat_id, result['message'])
                    else:
                        await send_message(chat_id, f"❌ {result.get('error', 'Edit failed')}")
                    return {"ok": True}
                
                else:
                    # Unknown command
                    await send_message(chat_id, f"❓ Unknown command: {cmd}\n\nUse /help to see available commands.")
                    return {"ok": True}
            
            # For non-commands, use natural language processing
            else:
                log(f"💬 Processing natural language message: {text[:50]}...")
                
                # Create mock update object for natural language handler
                class MockUpdate:
                    def __init__(self, text, chat_id, user_id, username):
                        self.message = MockMessage(text, chat_id)
                        self.effective_user = MockUser(user_id, username)
                
                class MockMessage:
                    def __init__(self, text, chat_id):
                        self.text = text
                        self.chat_id = chat_id
                        
                    async def reply_text(self, response, parse_mode=None, disable_web_page_preview=None):
                        await send_message(self.chat_id, response)
                
                class MockUser:
                    def __init__(self, user_id, username):
                        self.id = int(user_id)
                        self.username = username
                
                try:
                    mock_update = MockUpdate(text, chat_id, user_id, message.get("from", {}).get("username"))
                    await process_natural_message(mock_update)
                    log(f"✅ Natural language processing completed for user {user_id}")
                except Exception as e:
                    log(f"❌ Error in natural language processing: {e}", "ERROR")
                    await send_message(chat_id, "🤔 I had trouble understanding that. Could you try rephrasing or use /help for commands?")
                
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