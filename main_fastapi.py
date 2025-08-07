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
from handlers.natural_language import process_natural_message
from handlers.registration import handle_register_command, check_user_registration

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
    
    try:
        # Parse the incoming webhook data
        data = await request.json()
        log(f"🔍 Received webhook: {data}")
        
        if "message" not in data:
            log("⚠️ No message in webhook data", level="WARNING")
            return {"ok": True}
        
        message = data["message"]
        chat_id = message["chat"]["id"]
        user_id = str(message["from"]["id"])
        
        # Handle text messages
        if "text" in message:
            text = message["text"]
            log(f"📝 Raw text received: '{text}' (type: {type(text)})")
            log(f"📝 Text starts with '/': {text.startswith('/')}")
            log(f"📝 Text length: {len(text)}")
            log(f"📝 First character: '{text[0] if text else 'EMPTY'}'")
            
            # ENHANCED DEBUG: Check for hidden characters
            text_repr = repr(text)
            log(f"📝 Text repr: {text_repr}")
            
            # Clean the text of any potential hidden characters
            clean_text = text.strip()
            log(f"📝 Clean text: '{clean_text}'")
            log(f"📝 Clean text starts with '/': {clean_text.startswith('/')}")
            
            # Handle commands - USE CLEAN TEXT
            if clean_text.startswith("/"):
                cmd = clean_text.split()[0].lower()
                log(f"🎯 COMMAND DETECTED: '{cmd}' from clean text: '{clean_text}'")
                
                if cmd == "/start":
                    log("🚀 Processing /start command")
                    await send_message(chat_id, 
                        "👋 Welcome to MySecondMind!\n\n"
                        "I'm your AI-powered personal assistant. I can help you with:\n"
                        "• Natural conversation\n"
                        "• Task management\n"
                        "• Information storage\n"
                        "• Smart responses\n\n"
                        "Just start chatting with me naturally!")
                    
                elif cmd == "/help":
                    log("❓ Processing /help command")
                    help_text = """
🤖 *MySecondMind Help*

*Commands:*
• /start - Welcome message
• /register - Connect your Notion workspace
• /help - Show this help
• /status - Bot status
• /health - Health check

*Natural Language:*
Just chat with me naturally! I can understand and respond to:
• Notes and ideas to save
• Links to bookmark
• Reminders to set
• Questions about your saved content

Try saying things like:
• "I learned something interesting today..."
• "Read later: https://example.com"
• "Remind me to call mom tomorrow"
• "What did I save about productivity?"
"""
                    await send_message(chat_id, help_text)

                elif cmd == "/register":
                    log(f"🎯 REGISTER COMMAND DETECTED - Processing for user {user_id}")
                    
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
                            log(f"📤 REGISTER: Sending reply: {response[:100]}...")
                            await send_message(self.chat_id, response)
                    
                    class MockUser:
                        def __init__(self, user_id, username):
                            self.id = int(user_id)
                            self.username = username
                    
                    try:
                        log(f"🔧 Creating mock update for /register")
                        mock_update = MockUpdate(clean_text, chat_id, user_id, message.get("from", {}).get("username"))
                        log(f"🔧 Calling handle_register_command")
                        await handle_register_command(mock_update)
                        log(f"✅ /register command completed successfully")
                    except Exception as e:
                        log(f"❌ Error in /register command: {e}", "ERROR")
                        await send_message(chat_id, f"❌ Registration failed: {str(e)}")
                    
                elif cmd == "/status":
                    log("📊 Processing /status command")
                    await send_message(chat_id, 
                        "🟢 MySecondMind Status: ONLINE\n"
                        f"🕐 Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        "💚 All systems operational!")
                    
                elif cmd == "/health":
                    log("🏥 Processing /health command")
                    await send_message(chat_id, "🟢 Bot is healthy and running!")
                
                else:
                    log(f"❓ Unknown command: {cmd}")
                    await send_message(chat_id, f"❓ Unknown command: {cmd}\n\nUse /help to see available commands.")
                
                log(f"✅ Command '{cmd}' processing complete - RETURNING")
                # CRITICAL: Return here after handling ANY command
                return {"ok": True}
            
            # Process non-command messages with AI
            else:
                log(f"💭 NATURAL LANGUAGE: Processing non-command text: '{clean_text}'")
                try:
                    # Create a mock update object for the handler
                    class MockUpdate:
                        def __init__(self, text, chat_id, user_id, username):
                            self.message = MockMessage(text, chat_id, user_id)
                            self.effective_user = MockEffectiveUser(user_id, username)
                    
                    class MockMessage:
                        def __init__(self, text, chat_id, user_id):
                            self.text = text
                            self.chat_id = chat_id
                            self.from_user = MockUser(user_id)
                            
                        async def reply_text(self, response, parse_mode=None):
                            await send_message(self.chat_id, response)
                    
                    class MockUser:
                        def __init__(self, user_id):
                            self.id = user_id

                    class MockEffectiveUser:
                        def __init__(self, user_id, username):
                            self.id = int(user_id)
                            self.username = username
                    
                    # Check if user is registered before processing natural language
                    mock_update = MockUpdate(clean_text, chat_id, user_id, message.get("from", {}).get("username"))
                    
                    # For natural language processing, check registration first
                    if not await check_user_registration(mock_update):
                        log("📝 User not registered - registration prompt sent")
                        return {"ok": True}  # Registration prompt already sent
                    
                    log("🤖 Processing with natural language handler")
                    # Process with natural language handler
                    await process_natural_message(mock_update, None)
                    
                except Exception as e:
                    log(f"❌ Error processing natural language: {e}", level="ERROR")
                    await send_message(chat_id, 
                        "I understand your message, but I'm having trouble processing it right now. "
                        "Please try again!")
        
        else:
            log("📎 Non-text message received")
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