#!/usr/bin/env python3
"""
🧠 Natural Language Processing Handler for MySecondMind

This module handles AI-powered intent classification and natural language processing
using Groq's Llama3 model for understanding user messages and routing them appropriately.
"""

import os
import logging
import asyncio
from typing import Dict, Optional

# Configure logging
logger = logging.getLogger(__name__)

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    logger.warning("Groq not available. Natural language processing will use keyword fallback.")

class IntentClassifier:
    """AI-powered intent classification using Groq/Llama3."""
    
    def __init__(self):
        self.groq_client = None
        if GROQ_AVAILABLE and os.getenv('GROQ_API_KEY'):
            try:
                # Initialize Groq client with explicit parameters only
                api_key = os.getenv('GROQ_API_KEY')
                # Create client with minimal parameters to avoid conflicts
                self.groq_client = Groq(api_key=api_key)
                logger.info("✅ Groq AI initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Groq: {e}")
                logger.info("🔄 Falling back to keyword-based classification")
                self.groq_client = None
        else:
            logger.warning("⚠️ Groq API key not found. Using keyword fallback.")
    
    async def classify_message(self, message: str) -> Dict[str, any]:
        """Classify message intent using AI or keyword fallback."""
        
        if self.groq_client:
            try:
                return await self._classify_with_ai(message)
            except Exception as e:
                logger.error(f"AI classification failed: {e}. Using keyword fallback.")
        
        return self._classify_with_keywords(message)
    
    async def _classify_with_ai(self, message: str) -> Dict[str, any]:
        """Use Groq/Llama3 for intent classification."""
        
        prompt = f"""
Classify this message into ONE of these intents with HIGH priority for URLs:

1. LINK - URLs, web addresses, "read later", links to save (HIGHEST PRIORITY if URL present)
2. GREETING - Hello, hi, greetings, casual conversation starters  
3. NOTE - Saving information, ideas, thoughts, facts to remember
4. TASK - Creating todos, assignments, action items, things to do
5. REMINDER - Setting time-based alerts, "remind me", scheduled notifications
6. QUESTION - Asking for information, help, searching saved content ("what did I save about...")
7. FILE - References to uploading, sharing, or processing files/documents
8. OTHER - Everything else that doesn't fit above categories

IMPORTANT RULES:
- If message contains http:// or https://, classify as LINK even if it has other content
- "I learned about https://..." = LINK (not NOTE)
- "Check out https://..." = LINK (not NOTE)
- URLs with context should be LINK, the context will be saved with the URL

Message: "{message}"

Respond ONLY with a JSON object like this:
{{"intent": "LINK", "confidence": 0.95, "reasoning": "Contains URL - should be saved as link with context"}}
"""

        response = self.groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8192",
            temperature=0.1,
            max_tokens=100
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Parse JSON response
        import json
        try:
            result = json.loads(result_text)
            logger.info(f"🤖 AI classified '{message[:30]}...' as {result['intent']} (confidence: {result['confidence']})")
            return result
        except json.JSONDecodeError:
            # Fallback if AI returns invalid JSON
            return {"intent": "OTHER", "confidence": 0.5, "reasoning": "AI response parsing failed"}
    
    def _classify_with_keywords(self, message: str) -> Dict[str, any]:
        """Fallback keyword-based classification."""
        
        message_lower = message.lower()
        
        # Link detection (URLs, read later patterns)
        import re
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        link_keywords = ['read later', 'save link', 'bookmark', 'check out', 'www.', '.com', '.org', '.net']
        if re.search(url_pattern, message) or any(keyword in message_lower for keyword in link_keywords):
            return {"intent": "LINK", "confidence": 0.9, "reasoning": "URL or link-related keywords detected"}
        
        # Greeting keywords
        greeting_keywords = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening', 'greetings', 'howdy', 'sup', 'yo']
        if any(keyword in message_lower for keyword in greeting_keywords):
            return {"intent": "GREETING", "confidence": 0.8, "reasoning": "Greeting detected"}
        
        # Reminder keywords (time-based, scheduling)
        reminder_keywords = ['remind me', 'alert me', 'tomorrow', 'later', 'at ', 'clock', 'schedule', 'appointment', 'meeting', 'deadline', 'due']
        if any(keyword in message_lower for keyword in reminder_keywords):
            return {"intent": "REMINDER", "confidence": 0.8, "reasoning": "Time-based reminder keywords detected"}
        
        # Task keywords (action-oriented)
        task_keywords = ['todo', 'task', 'need to do', 'should do', 'must do', 'complete', 'finish', 'work on', 'get done']
        if any(keyword in message_lower for keyword in task_keywords):
            return {"intent": "TASK", "confidence": 0.7, "reasoning": "Task/action keywords detected"}
        
        # Question keywords (seeking information)
        question_keywords = ['?', 'what did i save', 'find', 'search', 'what', 'how', 'when', 'where', 'why', 'who', 'help me find']
        if any(keyword in message_lower for keyword in question_keywords):
            return {"intent": "QUESTION", "confidence": 0.7, "reasoning": "Question or search keywords detected"}
        
        # Note keywords (saving information, ideas)
        note_keywords = ['note', 'remember', 'save', 'keep', 'record', 'write down', 'important', 'idea', 'thought', 'learned']
        if any(keyword in message_lower for keyword in note_keywords):
            return {"intent": "NOTE", "confidence": 0.7, "reasoning": "Note/save keywords detected"}
        
        # File keywords (document handling)
        file_keywords = ['file', 'document', 'pdf', 'image', 'upload', 'attach', 'photo', 'screenshot']
        if any(keyword in message_lower for keyword in file_keywords):
            return {"intent": "FILE", "confidence": 0.7, "reasoning": "File/document keywords detected"}
        
        return {"intent": "OTHER", "confidence": 0.5, "reasoning": "No specific keyword patterns matched"}

# Global classifier instance
classifier = IntentClassifier()

async def get_user_storage_preference(user_id: str) -> str:
    """Get user's storage preference (notion or obsidian)."""
    from models.user_management import user_manager
    
    user = user_manager.get_user(user_id)
    if user and user.get('storage_preference'):
        return user['storage_preference']
    
    # Default to notion for backward compatibility
    return "notion"

async def process_natural_message(update, context=None) -> None:
    """Process natural language messages with AI intent classification."""
    
    if not update.message or not update.message.text:
        return
    
    user_message = update.message.text
    user_id = update.effective_user.id
    
    logger.info(f"📝 Processing message from user {user_id}: '{user_message[:50]}...'")
    
    try:
        # Classify the message intent
        classification = await classifier.classify_message(user_message)
        intent = classification['intent']
        confidence = classification['confidence']
        
        # Route based on intent
        if intent == "GREETING":
            await handle_greeting_intent(update, context, user_message, classification)
        elif intent == "LINK":
            await handle_link_intent(update, context, user_message, classification)
        elif intent == "NOTE":
            await handle_note_intent(update, context, user_message, classification)
        elif intent == "TASK":
            await handle_task_intent(update, context, user_message, classification)
        elif intent == "REMINDER":
            await handle_reminder_intent(update, context, user_message, classification)
        elif intent == "QUESTION":
            await handle_question_intent(update, context, user_message, classification)
        elif intent == "FILE":
            await handle_file_intent(update, context, user_message, classification)
        else:
            await handle_other_intent(update, context, user_message, classification)
            
    except Exception as e:
        logger.error(f"Error processing natural message: {e}")
        await update.message.reply_text(
            "🤔 I had trouble understanding that. Could you try rephrasing or use a specific command like /help?"
        )

async def handle_note_intent(update, context, message: str, classification: Dict) -> None:
    """Handle note saving requests."""
    
    confidence = classification['confidence']
    user_id = str(update.effective_user.id)
    
    # Save to Supabase database
    from handlers.supabase_content import content_handler
    result = await content_handler.save_note(user_id, message, classification)
    
    if result["success"]:
        response = f"📝 **Note Saved Successfully!** (confidence: {confidence:.0%})\n\n"
        response += f"💾 **Saved to Database**: *{result['title']}*\n\n"
        response += f"🔗 **ID**: {result['id']}\n\n"
        response += "✨ Your note is now part of your Second Brain and will be available for search and retrieval!"
    else:
        response = f"📝 **Note Detected** (confidence: {confidence:.0%})\n\n"
        response += f"I want to save: *{message}*\n\n"
        response += f"❌ **Save failed**: {result.get('error', 'Unknown error')}\n\n"
        response += "💡 Make sure you're registered with `/register` and the database is configured correctly."
    
    await update.message.reply_text(response, parse_mode='Markdown')

async def handle_task_intent(update, context, message: str, classification: Dict) -> None:
    """Handle task creation requests."""
    
    confidence = classification['confidence']
    user_id = str(update.effective_user.id)
    
    # Save to Supabase database
    from handlers.supabase_content import content_handler
    result = await content_handler.save_task(user_id, message, classification)
    
    if result["success"]:
        response = f"📋 **Task Saved Successfully!** (confidence: {confidence:.0%})\n\n"
        response += f"✅ **Added to your task list**: *{result['title']}*\n\n"
        response += f"🔗 **ID**: {result['id']}\n\n"
        if result.get('due_date'):
            response += f"📅 **Due Date**: {result['due_date']}\n\n"
        if result.get('priority'):
            response += f"🎯 **Priority**: {result['priority']}\n\n"
        response += "🎯 Your task is now tracked in your database!"
    else:
        response = f"📋 **Task Detected** (confidence: {confidence:.0%})\n\n"
        response += f"I understand you need to: *{message}*\n\n"
        response += f"❌ **Save failed**: {result.get('error', 'Unknown error')}\n\n"
        response += "💡 Make sure you're registered with `/register` and the database is configured correctly."
    
    await update.message.reply_text(response, parse_mode='Markdown')

async def handle_reminder_intent(update, context, message: str, classification: Dict) -> None:
    """Handle reminder creation requests."""
    
    confidence = classification['confidence']
    user_id = str(update.effective_user.id)
    
    # Save to Supabase database
    from handlers.supabase_content import content_handler
    result = await content_handler.save_reminder(user_id, message, classification)
    
    if result["success"]:
        response = f"⏰ **Reminder Saved Successfully!** (confidence: {confidence:.0%})\n\n"
        response += f"🔔 **Reminder set**: *{result['title']}*\n\n"
        response += f"🔗 **ID**: {result['id']}\n\n"
        if result.get('due_date'):
            response += f"📅 **Due Date**: {result['due_date']}\n\n"
        response += "⏱️ Your reminder is now stored in your database!"
    else:
        response = f"⏰ **Reminder Detected** (confidence: {confidence:.0%})\n\n"
        response += f"I want to remind you: *{message}*\n\n"
        response += f"❌ **Save failed**: {result.get('error', 'Unknown error')}\n\n"
        response += "💡 Make sure you're registered with `/register` and the database is configured correctly."
    
    await update.message.reply_text(response, parse_mode='Markdown')

async def handle_question_intent(update, context, message: str, classification: Dict) -> None:
    """Handle questions about saved content and general inquiries."""
    
    confidence = classification['confidence']
    user_id = str(update.effective_user.id)
    message_lower = message.lower()
    
    # Check if it's a search-related question
    search_keywords = ['what did i save', 'search', 'find', 'show me', 'what do i have', 'content', 'saved']
    is_search_question = any(keyword in message_lower for keyword in search_keywords)
    
    if is_search_question:
        response = f"🔍 **Great question!** Here's how to find your content:\n\n"
        
        # Check if they have any content first
        try:
            from handlers.supabase_content import content_handler
            result = await content_handler.get_user_content(user_id, limit=1)
            has_content = result.get("success") and result.get("count", 0) > 0
        except:
            has_content = False
        
        if has_content:
            response += "**🎯 Quick Commands:**\n"
            response += "• `/notes` - Show your recent notes\n"
            response += "• `/tasks` - Show your tasks and TODOs\n"
            response += "• `/links` - Show your saved links\n"
            response += "• `/stats` - See your content statistics\n\n"
            response += "**🔍 Search Commands:**\n"
            response += "• `/search productivity` - Find all productivity content\n"
            response += "• `/search notes python` - Find Python-related notes\n"
            response += "• `/search tasks urgent` - Find urgent tasks\n\n"
            response += "**💡 Try these examples:**\n"
            response += "• `/search today` - Content from today\n"
            response += "• `/search fastapi` - FastAPI-related content\n"
            response += "• `/search meeting` - Meeting-related items"
        else:
            response += "**📱 You haven't saved any content yet!**\n\n"
            response += "**Get started by saying:**\n"
            response += "• \"I learned that Supabase is awesome\"\n"
            response += "• \"Task: Finish the project report\"\n"
            response += "• \"https://fastapi.tiangolo.com great framework\"\n"
            response += "• \"Remind me to call mom tomorrow\"\n\n"
            response += "Once you save some content, use `/search`, `/notes`, `/tasks`, `/links` to find it!"
    else:
        # General help response
        response = f"❓ **I'm here to help!** (confidence: {confidence:.0%})\n\n"
        response += "**🤖 What I can do:**\n"
        response += "• 📝 Save your notes and ideas\n"
        response += "• 📋 Manage tasks and reminders\n"
        response += "• 🔗 Bookmark links for later\n"
        response += "• 🔍 Search your saved content\n\n"
        response += "**� Try asking:**\n"
        response += "• \"How do I save a note?\"\n"
        response += "• \"What commands are available?\"\n"
        response += "• \"Show me my recent content\"\n\n"
        response += "Or just type `/help` for a complete guide!"
    
    await update.message.reply_text(response, parse_mode='Markdown')

async def handle_greeting_intent(update, context, message: str, classification: Dict) -> None:
    """Handle greetings and casual conversation starters."""
    
    confidence = classification['confidence']
    
    greetings = [
        "👋 Hello there! Great to see you!",
        "🌟 Hi! I'm MySecondMind, your AI assistant.",
        "💫 Hey! Ready to boost your productivity?",
        "🤖 Greetings! How can I help you today?",
        "✨ Hello! Let's make your day more organized!"
    ]
    
    import random
    greeting = random.choice(greetings)
    
    response = f"{greeting}\n\n"
    response += "Here are some things you can try:\n\n"
    response += "💬 **Just chat naturally with me!**\n"
    response += "📋 *\"I need to finish my report by Friday\"*\n"
    response += "📝 *\"Remember my doctor's appointment is at 3pm\"*\n"
    response += "⏰ *\"Remind me to call mom tomorrow\"*\n"
    response += "🔗 *\"Read later: https://example.com\"*\n"
    response += "❓ *\"What did I save about productivity?\"*\n\n"
    response += "Or use commands like `/help` to see all options!"
    
    await update.message.reply_text(response)

async def handle_link_intent(update, context, message: str, classification: Dict) -> None:
    """Handle link saving requests."""
    
    confidence = classification['confidence']
    user_id = str(update.effective_user.id)
    
    # Extract URL if present
    import re
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    urls = re.findall(url_pattern, message)
    
    if urls:
        url = urls[0]
        context_text = message.replace(url, "").strip()
        
        # Save to Supabase database
        from handlers.supabase_content import content_handler
        result = await content_handler.save_link(user_id, url, context_text, classification)
        
        if result["success"]:
            response = f"🔗 **Link Saved Successfully!** (confidence: {confidence:.0%})\n\n"
            response += f"💾 **URL**: {url}\n"
            response += f"📄 **Title**: {result['title']}\n"
            if context_text:
                response += f"📝 **Context**: {context_text}\n"
            response += f"🔗 **ID**: {result['id']}\n\n"
            response += "🌟 Your link is now saved in your read-later collection!"
        else:
            response = f"🔗 **Link Detected** (confidence: {confidence:.0%})\n\n"
            response += f"URL: {url}\n\n"
            response += f"❌ **Save failed**: {result.get('error', 'Unknown error')}\n\n"
            response += "💡 Make sure you're registered with `/register` and the database is configured correctly."
    else:
        response = f"🔗 **Link Intent Detected** (confidence: {confidence:.0%})\n\n"
        response += f"Message: *{message}*\n\n"
        response += "❌ **No URL found** in your message.\n\n"
        response += "💡 Include a URL like: `https://example.com` or `Read later: https://article.com`"
    
    await update.message.reply_text(response, parse_mode='Markdown')

async def handle_file_intent(update, context, message: str, classification: Dict) -> None:
    """Handle file upload and processing requests."""
    
    confidence = classification['confidence']
    
    response = f"📄 **File Intent Detected** (confidence: {confidence:.0%})\n\n"
    response += f"Message: *{message}*\n\n"
    response += "🚧 Advanced file processing is coming soon!\n\n"
    response += "**Planned Features:**\n"
    response += "• 📄 **PDF Processing**: Auto-compress and extract text\n"
    response += "• 🖼️ **Image OCR**: Extract text from screenshots\n"
    response += "• 📁 **Smart Organization**: Auto-categorize and tag files\n"
    response += "• 🔍 **Content Search**: Find text within uploaded documents\n\n"
    response += "For now, you can upload files directly and I'll acknowledge them!"
    
    await update.message.reply_text(response, parse_mode='Markdown')

async def handle_other_intent(update, context, message: str, classification: Dict) -> None:
    """Handle other/unclassified messages."""
    
    confidence = classification['confidence']
    reasoning = classification.get('reasoning', 'Unknown')
    
    response = f"💭 **Processing Your Message** (confidence: {confidence:.0%})\n\n"
    response += f"You said: *{message}*\n\n"
    response += "I'm still learning to understand all types of messages! Here's how you can help me:\n\n"
    response += "**📝 For Notes/Ideas**: *\"I learned that quantum computers use qubits\"*\n"
    response += "**📋 For Tasks**: *\"I need to finish my project by Friday\"*\n"
    response += "**⏰ For Reminders**: *\"Remind me to call mom tomorrow at 6pm\"*\n"
    response += "**🔗 For Links**: *\"Read later: https://interesting-article.com\"*\n"
    response += "**❓ For Questions**: *\"What did I save about productivity?\"*\n"
    response += "**👋 For Chat**: *\"Hello!\" or \"How are you?\"*\n\n"
    response += f"🤖 *Why I'm unsure: {reasoning}*\n\n"
    response += "💡 *The more specific you are, the better I can help organize your Second Brain!*"
    
    await update.message.reply_text(response, parse_mode='Markdown')
