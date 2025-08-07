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
from telegram import Update
from telegram.ext import ContextTypes

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

1. TASK - Creating todos, assignments, or action items
2. NOTE - Saving information, facts, or thoughts  
3. REMINDER - Setting time-based alerts or notifications
4. QUESTION - Asking for information or help
5. OTHER - Everything else

Message: "{message}"

Respond ONLY with a JSON object like this:
{{"intent": "TASK", "confidence": 0.95, "reasoning": "User wants to create a todo"}}
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
        
        # Task keywords
        task_keywords = ['todo', 'task', 'do', 'need to', 'should', 'must', 'complete', 'finish', 'work on']
        if any(keyword in message_lower for keyword in task_keywords):
            return {"intent": "TASK", "confidence": 0.7, "reasoning": "Keyword match for task"}
        
        # Note keywords  
        note_keywords = ['note', 'remember', 'save', 'keep', 'record', 'write down', 'important']
        if any(keyword in message_lower for keyword in note_keywords):
            return {"intent": "NOTE", "confidence": 0.7, "reasoning": "Keyword match for note"}
        
        # Reminder keywords
        reminder_keywords = ['remind', 'alert', 'tomorrow', 'later', 'at', 'clock', 'time', 'schedule']
        if any(keyword in message_lower for keyword in reminder_keywords):
            return {"intent": "REMINDER", "confidence": 0.7, "reasoning": "Keyword match for reminder"}
        
        # Question keywords
        question_keywords = ['?', 'what', 'how', 'when', 'where', 'why', 'who', 'help', 'explain']
        if any(keyword in message_lower for keyword in question_keywords):
            return {"intent": "QUESTION", "confidence": 0.7, "reasoning": "Keyword match for question"}
        
        return {"intent": "OTHER", "confidence": 0.5, "reasoning": "No keyword matches"}

# Global classifier instance
classifier = IntentClassifier()

async def process_natural_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        if intent == "TASK":
            await handle_task_intent(update, context, user_message, classification)
        elif intent == "NOTE":
            await handle_note_intent(update, context, user_message, classification)
        elif intent == "REMINDER":
            await handle_reminder_intent(update, context, user_message, classification)
        elif intent == "QUESTION":
            await handle_question_intent(update, context, user_message, classification)
        else:
            await handle_other_intent(update, context, user_message, classification)
            
    except Exception as e:
        logger.error(f"Error processing natural message: {e}")
        await update.message.reply_text(
            "🤔 I had trouble understanding that. Could you try rephrasing or use a specific command like /help?"
        )

async def handle_task_intent(update: Update, context: ContextTypes.DEFAULT_TYPE, message: str, classification: Dict) -> None:
    """Handle task creation requests."""
    
    confidence = classification['confidence']
    
    response = f"📋 **Task Detected** (confidence: {confidence:.0%})\n\n"
    response += f"I understand you want to create a task: *{message}*\n\n"
    response += "🚧 Task management is coming soon! For now, I've noted this as:\n"
    response += f"• **Task**: {message}\n"
    response += f"• **Created**: Now\n"
    response += f"• **Status**: Pending\n\n"
    response += "💡 *Soon you'll be able to set due dates, priorities, and get reminders!*"
    
    await update.message.reply_text(response, parse_mode='Markdown')

async def handle_note_intent(update: Update, context: ContextTypes.DEFAULT_TYPE, message: str, classification: Dict) -> None:
    """Handle note saving requests."""
    
    confidence = classification['confidence']
    
    response = f"📝 **Note Detected** (confidence: {confidence:.0%})\n\n"
    response += f"I'll save this note: *{message}*\n\n"
    response += "🚧 Note storage is coming soon! For now, I've temporarily noted:\n"
    response += f"• **Note**: {message}\n"
    response += f"• **Saved**: Now\n"
    response += f"• **Tags**: Auto-generated\n\n"
    response += "💡 *Soon you'll have searchable notes with smart tagging!*"
    
    await update.message.reply_text(response, parse_mode='Markdown')

async def handle_reminder_intent(update: Update, context: ContextTypes.DEFAULT_TYPE, message: str, classification: Dict) -> None:
    """Handle reminder creation requests."""
    
    confidence = classification['confidence']
    
    response = f"⏰ **Reminder Detected** (confidence: {confidence:.0%})\n\n"
    response += f"I want to set a reminder: *{message}*\n\n"
    response += "🚧 Smart reminders are coming soon! For now, I've noted:\n"
    response += f"• **Reminder**: {message}\n"
    response += f"• **Requested**: Now\n"
    response += f"• **Status**: Pending setup\n\n"
    response += "💡 *Soon you'll get intelligent time-based reminders!*"
    
    await update.message.reply_text(response, parse_mode='Markdown')

async def handle_question_intent(update: Update, context: ContextTypes.DEFAULT_TYPE, message: str, classification: Dict) -> None:
    """Handle questions and help requests."""
    
    confidence = classification['confidence']
    
    response = f"❓ **Question Detected** (confidence: {confidence:.0%})\n\n"
    response += f"Your question: *{message}*\n\n"
    response += "🚧 Smart Q&A is coming soon! For now, here's what I can do:\n\n"
    response += "**Available Commands:**\n"
    response += "• `/start` - Get started\n"
    response += "• `/help` - Show help\n"
    response += "• `/status` - Check bot status\n"
    response += "• `/register` - Set up your account\n\n"
    response += "💡 *Soon I'll answer questions using your personal knowledge base!*"
    
    await update.message.reply_text(response, parse_mode='Markdown')

async def handle_other_intent(update: Update, context: ContextTypes.DEFAULT_TYPE, message: str, classification: Dict) -> None:
    """Handle other/unclassified messages."""
    
    confidence = classification['confidence']
    reasoning = classification.get('reasoning', 'Unknown')
    
    response = f"💭 **General Message** (confidence: {confidence:.0%})\n\n"
    response += f"You said: *{message}*\n\n"
    response += "I'm still learning to understand all types of messages! "
    response += "Here are some things you can try:\n\n"
    response += "**For Tasks**: *\"I need to finish my project\"*\n"
    response += "**For Notes**: *\"Remember that the meeting is at 3pm\"*\n"
    response += "**For Reminders**: *\"Remind me to call mom tomorrow\"*\n"
    response += "**For Questions**: *\"What's the weather like?\"*\n\n"
    response += f"🤖 *Classification reasoning: {reasoning}*"
    
    await update.message.reply_text(response, parse_mode='Markdown')