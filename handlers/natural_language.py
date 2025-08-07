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
Classify this message into ONE of these intents:

1. GREETING - Hello, hi, greetings, casual conversation starters
2. LINK - URLs, "read later", "save this link", web addresses
3. NOTE - Saving information, ideas, thoughts, facts to remember
4. TASK - Creating todos, assignments, action items, things to do
5. REMINDER - Setting time-based alerts, "remind me", scheduled notifications
6. QUESTION - Asking for information, help, searching saved content ("what did I save about...")
7. FILE - References to uploading, sharing, or processing files/documents
8. OTHER - Everything else that doesn't fit above categories

Message: "{message}"

Respond ONLY with a JSON object like this:
{{"intent": "NOTE", "confidence": 0.95, "reasoning": "User wants to save information for later"}}
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
    
    # Try to save to Notion
    from handlers.notion_client import notion_client
    result = await notion_client.save_note(user_id, message, classification)
    
    if result["success"]:
        response = f"📝 **Note Saved Successfully!** (confidence: {confidence:.0%})\n\n"
        response += f"💾 **Saved to Notion**: *{message}*\n\n"
        response += f"🔗 **Page URL**: {result['url']}\n\n"
        response += "✨ Your note is now part of your Second Brain and will be available for future search and resurfacing!"
    else:
        response = f"📝 **Note Detected** (confidence: {confidence:.0%})\n\n"
        response += f"I want to save: *{message}*\n\n"
        response += f"❌ **Save failed**: {result.get('error', 'Unknown error')}\n\n"
        response += "💡 Make sure you're registered with `/register` and your Notion workspace is set up correctly."
    
    await update.message.reply_text(response, parse_mode='Markdown')

async def handle_task_intent(update, context, message: str, classification: Dict) -> None:
    """Handle task creation requests."""
    
    confidence = classification['confidence']
    user_id = str(update.effective_user.id)
    
    # Try to save to Notion
    from handlers.notion_client import notion_client
    result = await notion_client.save_task(user_id, message, classification)
    
    if result["success"]:
        response = f"📋 **Task Saved Successfully!** (confidence: {confidence:.0%})\n\n"
        response += f"✅ **Added to your task list**: *{message}*\n\n"
        response += f"🔗 **Page URL**: {result['url']}\n\n"
        response += "🎯 Your task is now tracked in your Notion workspace!"
    else:
        response = f"📋 **Task Detected** (confidence: {confidence:.0%})\n\n"
        response += f"I understand you need to: *{message}*\n\n"
        response += f"❌ **Save failed**: {result.get('error', 'Unknown error')}\n\n"
        response += "💡 Make sure you're registered with `/register` and your Notion workspace is set up correctly."
    
    await update.message.reply_text(response, parse_mode='Markdown')

async def handle_reminder_intent(update, context, message: str, classification: Dict) -> None:
    """Handle reminder creation requests."""
    
    confidence = classification['confidence']
    user_id = str(update.effective_user.id)
    
    # Try to save to Notion
    from handlers.notion_client import notion_client
    result = await notion_client.save_reminder(user_id, message, classification)
    
    if result["success"]:
        response = f"⏰ **Reminder Saved Successfully!** (confidence: {confidence:.0%})\n\n"
        response += f"🔔 **Reminder set**: *{message}*\n\n"
        response += f"🔗 **Page URL**: {result['url']}\n\n"
        if result.get('due_date'):
            response += f"📅 **Due Date**: {result['due_date']}\n\n"
        response += "⏱️ Your reminder is now stored in your Notion workspace!"
    else:
        response = f"⏰ **Reminder Detected** (confidence: {confidence:.0%})\n\n"
        response += f"I want to remind you: *{message}*\n\n"
        response += f"❌ **Save failed**: {result.get('error', 'Unknown error')}\n\n"
        response += "💡 Make sure you're registered with `/register` and your Notion workspace is set up correctly."
    
    await update.message.reply_text(response, parse_mode='Markdown')

async def handle_question_intent(update, context, message: str, classification: Dict) -> None:
    """Handle questions and help requests."""
    
    confidence = classification['confidence']
    
    response = f"❓ **Question/Search Detected** (confidence: {confidence:.0%})\n\n"
    response += f"Your question: *{message}*\n\n"
    response += "🚧 **Personal Knowledge Search** coming soon!\n\n"
    response += "**What I'll be able to do:**\n"
    response += f"• 🧠 **Search Memory**: \"What did I save about productivity?\"\n"
    response += f"• 🔍 **Semantic Search**: Find related ideas and concepts\n"
    response += f"• 📊 **Smart Insights**: Summarize patterns in your data\n"
    response += f"• 🎯 **Contextual Answers**: Responses based on your saved knowledge\n\n"
    response += "**For now, try these commands:**\n"
    response += "• `/help` - Available features\n"
    response += "• `/status` - Bot health\n\n"
    response += "💡 *Soon I'll be your personal knowledge search engine!*"
    
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
        
        # Try to save to Notion
        from handlers.notion_client import notion_client
        result = await notion_client.save_link(user_id, url, context_text, classification)
        
        if result["success"]:
            response = f"🔗 **Link Saved Successfully!** (confidence: {confidence:.0%})\n\n"
            response += f"💾 **URL**: {url}\n"
            if result.get('title'):
                response += f"📄 **Title**: {result['title']}\n"
            if context_text:
                response += f"📝 **Context**: {context_text}\n"
            response += f"\n🔗 **Notion Page**: {result['url']}\n\n"
            response += "🌟 Your link is now saved in your read-later collection!"
        else:
            response = f"🔗 **Link Detected** (confidence: {confidence:.0%})\n\n"
            response += f"URL: {url}\n\n"
            response += f"❌ **Save failed**: {result.get('error', 'Unknown error')}\n\n"
            response += "💡 Make sure you're registered with `/register` and your Notion workspace is set up correctly."
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
