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
async def health_check(request: Request):
    """Root health check for UptimeRobot"""
    user_agent = request.headers.get("user-agent", "")
    log(f"Health check request from: {user_agent}")
    
    return {
        "status": "healthy",
        "service": "MySecondMind Bot",
        "timestamp": datetime.now().isoformat(),
        "message": "🟢 Bot is online and ready!",
        "user_agent": user_agent
    }

@app.get("/health")
async def health_status(request: Request):
    """Detailed health status"""
    user_agent = request.headers.get("user-agent", "")
    
    return {
        "status": "healthy",
        "bot_configured": bool(TELEGRAM_BOT_TOKEN),
        "webhook_url": WEBHOOK_URL,
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "endpoints": ["GET /", "GET /health", "GET /ping", "POST /webhook"],
        "user_agent": user_agent
    }

# Add HEAD method support for UptimeRobot
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

@app.get("/ping")
async def ping():
    """Simple ping endpoint"""
    return {"ping": "pong", "timestamp": time.time()}

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

# --- Webhook handler ---
@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Handle incoming Telegram webhook"""
    chat_id = None
    
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
        
        # Handle text messages
        if "text" in message:
            text = message["text"]
            log(f"Handling message: {text} from user {user_id}")
            
            # Handle commands
            if text.startswith("/"):
                cmd = text.split()[0].lower()
                
                if cmd == "/start":
                    await send_message(chat_id, 
                        "👋 Welcome to MySecondMind!\n\n"
                        "I'm your AI-powered personal assistant. I can help you with:\n"
                        "• Natural conversation\n"
                        "• Task management\n"
                        "• Information storage\n"
                        "• Smart responses\n\n"
                        "Just start chatting with me naturally!")
                    return {"ok": True}
                    
                elif cmd == "/help":
                    help_text = """
🤖 *MySecondMind Help*

*Commands:*
• /start - Welcome message
• /help - Show this help
• /status - Bot status
• /health - Health check

*Natural Language:*
Just chat with me naturally! I can understand and respond to:
• Questions and conversations
• Task requests
• Information queries
• General assistance

Try saying things like:
• "How are you?"
• "What can you do?"
• "Tell me a joke"
"""
                    await send_message(chat_id, help_text)
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
            
            # Process non-command messages with AI
            try:
                # Create a mock update object for the handler
                class MockUpdate:
                    def __init__(self, text, chat_id, user_id):
                        self.message = MockMessage(text, chat_id, user_id)
                        self.effective_user = MockUser(user_id)
                
                class MockMessage:
                    def __init__(self, text, chat_id, user_id):
                        self.text = text
                        self.chat_id = chat_id
                        self.from_user = MockUser(user_id)
                        
                    async def reply_text(self, response, parse_mode=None):
                        await send_message(self.chat_id, response)
                
                class MockUser:
                    def __init__(self, user_id):
                        self.id = int(user_id)
                
                # Process with natural language handler
                mock_update = MockUpdate(text, chat_id, user_id)
                await process_natural_message(mock_update, None)
                
            except Exception as e:
                log(f"Error processing natural language: {e}", level="ERROR")
                await send_message(chat_id, 
                    "I understand your message, but I'm having trouble processing it right now. "
                    "Please try again!")
        
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
