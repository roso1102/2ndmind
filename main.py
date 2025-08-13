#!/usr/bin/env python3
"""
🧠 MySecondMind - FastAPI Implementation
Simple and effective webhook handler with health monitoring
"""

import os
import logging
import httpx
import time
import secrets
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
from contextlib import asynccontextmanager
from fastapi import Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # Log initial memory usage
    try:
        from core.enhanced_semantic import log_memory_usage
        log_memory_usage("startup")
    except ImportError:
        pass

    # Configure webhook
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

    # Start background poller and init scheduler
    try:
        from core.notification_scheduler import get_notification_scheduler
        scheduler = get_notification_scheduler()
        import asyncio as _asyncio
        _asyncio.create_task(scheduler.run_background_poller(poll_interval_seconds=15, grace_seconds=30))
        await scheduler._ensure_scheduler_initialized()
        log("🛎️ Background notification poller started (15s interval, 30s grace)")
    except Exception as e:
        log(f"⚠️ Failed to start background poller/scheduler: {e}", level="WARNING")

    log("🚀 MySecondMind bot started successfully!")
    log(f"💚 Health endpoints: {WEBHOOK_URL}/, {WEBHOOK_URL}/health, {WEBHOOK_URL}/ping")

    yield

    # Shutdown
    try:
        log("🛑 Shutting down MySecondMind bot...")
    except Exception:
        pass

app = FastAPI(title="MySecondMind Bot", version="1.0.0", lifespan=lifespan)

# Templates
templates = Jinja2Templates(directory="templates")

# CORS (for external dashboard like Vercel)
try:
    _origins = []
    for key in ("DASHBOARD_ORIGIN", "VERCEL_ORIGIN"):
        val = (os.getenv(key) or "").strip()
        if val:
            _origins.append(val)
    if _origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PATCH", "DELETE"],
            allow_headers=["*"],
        )
except Exception:
    pass

# ------------------------------
# Auth helpers (Telegram Login + signed session cookie)
# ------------------------------

import hmac as _hmac
import hashlib as _hashlib
from time import time as _time
from typing import Tuple as _Tuple

_COOKIE_NAME = "ms2_session"
_COOKIE_MAX_AGE = 30 * 24 * 60 * 60  # 30 days


def _get_signing_key() -> bytes:
    # Prefer ENCRYPTION_MASTER_KEY else TELEGRAM_TOKEN
    key = (os.getenv("ENCRYPTION_MASTER_KEY") or os.getenv("TELEGRAM_TOKEN") or "").encode()
    if not key:
        # Fallback fixed dev key (non-production)
        key = b"dev-key"
    return _hashlib.sha256(key).digest()


def _sign_session(user_id: str, expires: int) -> str:
    payload = f"{user_id}|{expires}".encode()
    sig = _hmac.new(_get_signing_key(), payload, _hashlib.sha256).hexdigest()
    return f"{user_id}|{expires}|{sig}"


def _verify_session(token: str) -> str:
    try:
        user_id, exp_str, sig = token.split("|", 2)
        expires = int(exp_str)
        if expires < int(_time()):
            return ""
        expected = _hmac.new(_get_signing_key(), f"{user_id}|{expires}".encode(), _hashlib.sha256).hexdigest()
        if _hmac.compare_digest(expected, sig):
            return user_id
    except Exception:
        return ""
    return ""


def _verify_telegram_login(params: dict) -> _Tuple[bool, str]:
    """Verify Telegram Login payload. Returns (ok, user_id)."""
    try:
        received_hash = params.get("hash", "")
        data = {k: v for k, v in params.items() if k != "hash"}
        # Build data-check-string (keys sorted alphabetically)
        check_lines = [f"{k}={data[k]}" for k in sorted(data.keys())]
        data_check_string = "\n".join(check_lines)
        # Secret key = sha256(bot_token)
        bot_token = os.getenv("TELEGRAM_TOKEN") or ""
        secret_key = _hashlib.sha256(bot_token.encode()).digest()
        computed_hash = _hmac.new(secret_key, data_check_string.encode(), _hashlib.sha256).hexdigest()
        if not _hmac.compare_digest(computed_hash, received_hash):
            return False, ""
        user = data.get("id") or data.get("user[id]") or ""
        return True, str(user)
    except Exception:
        return False, ""


@app.get("/api/me")
async def api_me(request: Request):
    token = request.cookies.get(_COOKIE_NAME, "")
    user_id = _verify_session(token) if token else ""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"user_id": user_id}


@app.get("/auth/telegram")
async def auth_telegram(request: Request):
    # Telegram passes all params on query string
    params = dict(request.query_params)
    ok, user_id = _verify_telegram_login(params)
    if not ok or not user_id:
        raise HTTPException(status_code=401, detail="Telegram verification failed")

    # Issue session cookie
    expires = int(_time()) + _COOKIE_MAX_AGE
    token = _sign_session(user_id, expires)

    target = os.getenv("DASHBOARD_ORIGIN", "") or os.getenv("VERCEL_ORIGIN", "") or "/"
    # Prefer redirect to /app.html on dashboard
    redirect_url = f"{target.rstrip('/')}/app.html" if target.startswith("http") else "/dashboard"
    resp = RedirectResponse(url=redirect_url, status_code=302)
    resp.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        max_age=_COOKIE_MAX_AGE,
        expires=_COOKIE_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
    )
    return resp

_LINK_TTL_SECONDS = 10 * 60  # 10 minutes
_link_codes = {}


def _generate_link_code() -> str:
    # Human-friendly 6-digit numeric code
    return f"{secrets.randbelow(10**6):06d}"


@app.post("/auth/start-link")
async def auth_start_link():
    """Create a short-lived link code for manual account linking.
    Frontend shows this code; user sends '/link CODE' to the bot to complete.
    """
    code = _generate_link_code()
    _link_codes[code] = {
        "created": int(time.time()),
        "user_id": None,
        "used": False,
    }
    return {"code": code, "expires_in": _LINK_TTL_SECONDS}


@app.get("/auth/check-link")
async def auth_check_link(code: str):
    """If the code has been confirmed by the bot, set session cookie and redirect."""
    entry = _link_codes.get(code)
    now = int(time.time())
    if not entry:
        raise HTTPException(status_code=404, detail="Invalid code")
    if entry["used"] or now - entry["created"] > _LINK_TTL_SECONDS:
        # Expired or already used
        _link_codes.pop(code, None)
        raise HTTPException(status_code=410, detail="Code expired")
    if not entry["user_id"]:
        # Not linked yet
        return {"linked": False}

    # Linked: issue cookie and redirect
    expires = int(_time()) + _COOKIE_MAX_AGE
    token = _sign_session(entry["user_id"], expires)
    entry["used"] = True
    target = os.getenv("DASHBOARD_ORIGIN", "") or os.getenv("VERCEL_ORIGIN", "") or "/"
    redirect_url = f"{target.rstrip('/')}/app.html" if target.startswith("http") else "/dashboard"
    resp = RedirectResponse(url=redirect_url, status_code=302)
    resp.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        max_age=_COOKIE_MAX_AGE,
        expires=_COOKIE_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
    )
    return resp

# --- Session helper: prefer signed cookie; fallback to query param for legacy URLs ---
def get_current_user_id(request: Request) -> str:
    # 1) Try session cookie set by /auth/telegram or /auth/check-link
    token = request.cookies.get(_COOKIE_NAME, "")
    if token:
        uid = _verify_session(token)
        if uid:
            return uid
    # 2) Fallback: allow explicit user_id in query for manual testing
    user_id = request.query_params.get("user_id")
    return user_id or ""

# --- Dashboard routes ---
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user_id: str = Depends(get_current_user_id)):
    if not user_id:
        return HTMLResponse("<p>Missing user_id. Append ?user_id=YOUR_TELEGRAM_ID temporarily.</p>", status_code=400)
    return templates.TemplateResponse("dashboard.html", {"request": request, "user_id": user_id})

@app.get("/partials/list", response_class=HTMLResponse)
async def partial_list(request: Request, type: str = "all", q: str = "", user_id: str = Depends(get_current_user_id)):
    from handlers.supabase_content import content_handler
    if not user_id:
        # Try to read from referer query (htmx requests may lose query params)
        ref = request.headers.get("referer", "")
        import urllib.parse as _up
        try:
            qs = _up.urlparse(ref).query
            user_id = _up.parse_qs(qs).get("user_id", [""])[0]
        except Exception:
            user_id = ""
    if not user_id:
        return HTMLResponse("<p>Missing user</p>", status_code=400)
    if q:
        data = await content_handler.search_content(user_id, q, limit=50)
        items = data.get("results", []) if data.get("success") else []
    elif type != "all":
        data = await content_handler.get_user_content(user_id, content_type=type, limit=50)
        items = data.get("content", []) if data.get("success") else []
    else:
        data = await content_handler.get_user_content(user_id, content_type=None, limit=50)
        items = data.get("content", []) if data.get("success") else []
    return templates.TemplateResponse("_list.html", {"request": request, "items": items})

@app.post("/api/content", response_class=HTMLResponse)
async def create_content(request: Request,
                         ctype: str = Form(...),
                         title: str = Form(""),
                         content: str = Form(""),
                         url: str = Form(""),
                         user_id: str = Depends(get_current_user_id)):
    from handlers.supabase_content import content_handler
    if not user_id:
        return HTMLResponse("<p>Missing user</p>", status_code=400)
    if ctype == "note":
        await content_handler.save_note(user_id, content or title, {"confidence": 0.99, "reasoning": "dashboard"})
    elif ctype == "task":
        await content_handler.save_task(user_id, content or title, {"confidence": 0.99, "reasoning": "dashboard"})
    elif ctype == "link":
        await content_handler.save_link(user_id, url, content, {"confidence": 0.99, "reasoning": "dashboard"})
    elif ctype == "reminder":
        await content_handler.save_reminder(user_id, content or title, {"confidence": 0.99, "reasoning": "dashboard"})
    # Return refreshed list
    return RedirectResponse(url=f"/dashboard?user_id={user_id}", status_code=303)

@app.post("/api/content/{item_id}/delete", response_class=HTMLResponse)
async def delete_content_route(request: Request, item_id: str, user_id: str = Depends(get_current_user_id)):
    from handlers.supabase_content import content_handler
    if not user_id:
        return HTMLResponse("<p>Missing user</p>", status_code=400)
    await content_handler.delete_content(user_id, item_id)
    return HTMLResponse("Deleted", status_code=200)

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

# Initialize semantic search engine with multiple fallbacks
try:
    from core.enhanced_semantic import get_enhanced_engine, log_memory_usage
    semantic_engine = get_enhanced_engine()
    log("✅ Enhanced semantic search engine initialized (scikit-learn)")
    log_memory_usage("after enhanced semantic init")
except ImportError:
    try:
        from core.semantic_search import get_semantic_engine
        semantic_engine = get_semantic_engine()
        log("✅ Full semantic search engine initialized")
    except ImportError:
        try:
            from core.lightweight_semantic import get_lightweight_engine
            semantic_engine = get_lightweight_engine()
            log("✅ Lightweight semantic search initialized (memory optimized)")
        except ImportError:
            try:
                from core.basic_semantic import get_basic_engine
                semantic_engine = get_basic_engine()
                log("✅ Ultra-basic semantic search initialized (pure Python)")
            except Exception as e3:
                log(f"⚠️ All semantic search engines failed: {e3}", "WARNING")
        except Exception as e2:
            log(f"⚠️ Lightweight semantic search failed: {e2}", "WARNING")
    except Exception as e:
        log(f"⚠️ Full semantic search failed: {e}", "WARNING")
except Exception as e:
    log(f"⚠️ Enhanced semantic search failed: {e}", "WARNING")

# Initialize notification scheduler (optional)
try:
    from core.notification_scheduler import get_notification_scheduler
    notification_scheduler = get_notification_scheduler()
    log("✅ Notification scheduler initialized")
except ImportError:
    log("⚠️ Notification scheduler not available (APScheduler not installed)", "WARNING")
    notification_scheduler = None
except Exception as e:
    log(f"⚠️ Notification scheduler initialization failed: {e}", "WARNING")
    notification_scheduler = None

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

                elif cmd == "/link":
                    try:
                        parts = text.split()
                        if len(parts) < 2:
                            await send_message(chat_id, "Usage: /link 123456\nGet a code from the web dashboard login page and send it here.")
                            return {"ok": True}
                        code = parts[1].strip()
                        entry = _link_codes.get(code)
                        now = int(_time())
                        if not entry:
                            await send_message(chat_id, "❌ Invalid code. Please create a new one from the web page and try again.")
                            return {"ok": True}
                        if entry.get("used") or now - entry.get("created", 0) > _LINK_TTL_SECONDS:
                            _link_codes.pop(code, None)
                            await send_message(chat_id, "⌛ Code expired. Please generate a new code on the web page and try again.")
                            return {"ok": True}
                        # Link this code to current Telegram user
                        entry["user_id"] = str(user_id)
                        await send_message(chat_id, "✅ Linked! Return to the website and continue. You can close this chat if you like.")
                    except Exception as e:
                        log(f"❌ Error in /link: {e}", "ERROR")
                        await send_message(chat_id, "❌ Failed to link. Please create a new code and try again.")
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

                elif cmd == "/timezone":
                    log(f"🌍 Processing /timezone for user {user_id}")
                    try:
                        from handlers.basic_commands import timezone_handler
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
                        
                        await timezone_handler(mock_update, mock_context)
                        log(f"✅ /timezone completed for user {user_id}")
                    except Exception as e:
                        log(f"❌ Error in /timezone: {e}", "ERROR")
                        await send_message(chat_id, f"❌ Error setting timezone: {str(e)}")
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

# (deprecated startup event removed in favor of lifespan)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 10000))
    log(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
