#!/usr/bin/env python3
"""
🧠 Natural Language Processing Handler for MySecondMind

This module handles AI-powered intent classification and natural language processing
using Groq's Llama3 model for understanding user messages and routing them appropriately.
"""

import os
import logging
import asyncio
import re
from typing import Dict, Optional

# Import content management
from handlers.content_management import content_manager

# Configure logging
logger = logging.getLogger(__name__)

def extract_search_term(message: str) -> Optional[str]:
    """Extract search term from natural language questions."""
    message_lower = message.lower().strip()
    
    # Common patterns for "what did I save about X"
    patterns = [
        r'what did i save about (.+)',
        r'what did i save (.+)',
        r'find (.+)',
        r'search for (.+)',
        r'show me (.+)',
        r'what do i have about (.+)',
        r'do i have anything about (.+)',
        r'saved about (.+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, message_lower)
        if match:
            search_term = match.group(1).strip()
            # Remove common stop words from the end
            stop_words = ['?', 'please', 'thanks', 'thank you']
            for stop_word in stop_words:
                if search_term.endswith(stop_word):
                    search_term = search_term[:-len(stop_word)].strip()
            return search_term if search_term else None
    
    return None

# --- Deterministic pre-classifier (runs before AI) ---
def pre_classify_message(message: str) -> Optional[Dict]:
    """Lightweight, deterministic detection of links, reminders, tasks, notes.
    Returns a dict with keys: type, title, content, url, time, confidence.
    """
    if not message:
        return None

    msg = message.strip()
    lower = msg.lower()

    # Detect URL (preserve full URL string)
    url_match = re.search(r'https?://\S+', msg)
    if url_match:
        url = url_match.group(0)
        context = msg.replace(url, '').strip()
        return {
            'type': 'link',
            'title': context or url,
            'content': context,
            'url': url,
            'confidence': 0.95
        }

    # Detect reminder phrases
    reminder_triggers = ['remind me', 'reminder', 'alert me', 'notify me']
    time_patterns = [
        r'in\s+\d+\s+(minute|minutes|hour|hours)',
        r'at\s+\d{1,2}:\d{2}(\s*(am|pm))?',
        r'(tomorrow|today|tonight|next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday))',
    ]
    if any(t in lower for t in reminder_triggers) or any(re.search(p, lower) for p in time_patterns):
        time_text = None
        for p in time_patterns:
            m = re.search(p, lower)
            if m:
                time_text = m.group(0)
                break
        if not time_text:
            m = re.search(r'in\s+(\d+)\b', lower)
            if m:
                time_text = f"in {m.group(1)} minutes"
        # Extract title after "remind me to"
        title = msg
        m2 = re.search(r'remind\s+me\s+(to\s+)?(.+)', lower)
        if m2 and m2.group(2):
            start = lower.find(m2.group(2))
            if start >= 0:
                title = msg[start:].strip()
        return {
            'type': 'reminder',
            'title': title,
            'content': title,
            'time': time_text,
            'confidence': 0.85
        }

    # Detect tasks
    task_keywords = ['todo', 'task', 'need to', 'should', 'must', 'complete', 'finish']
    if any(k in lower for k in task_keywords):
        return {
            'type': 'task',
            'title': msg,
            'content': msg,
            'confidence': 0.8
        }

    # Default to note for sentence-like
    if len(msg.split()) >= 3:
        return {
            'type': 'note',
            'title': msg[:60],
            'content': msg,
            'confidence': 0.6
        }
    return None

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
Classify this message into ONE of these intents. Follow these STRICT rules:

1. LINK - ONLY if message contains http:// or https:// URLs
2. NOTE - Ideas, thoughts, facts to remember, "I have an idea", learning notes
3. TASK - TODOs, "I need to", "remember to do", action items
4. REMINDER - Time-based alerts, "remind me at", "meeting tomorrow"
5. QUESTION - Asking for information, "what did I save", searching content
6. GREETING - Hello, hi, greetings, casual conversation
7. FILE - File uploads, document references
8. OTHER - Everything else

CRITICAL CLASSIFICATION RULES:
- "I have an idea about X" = NOTE (NOT LINK!)
- "I learned about X" = NOTE (unless URL present)
- "Remember this: X" = NOTE
- URLs with context = LINK only
- NO URL present = NEVER classify as LINK

EXAMPLES:
- "I have an idea about solar panels" → NOTE
- "https://example.com solar panels" → LINK
- "I need to call mom" → TASK
- "What did I save today?" → QUESTION

Message: "{message}"

RESPOND WITH VALID JSON ONLY:
{{"intent": "NOTE", "confidence": 0.95, "reasoning": "Saving an idea or thought - no URL present"}}
"""

        # Try larger models first for better intent classification
        models_to_try = [
            "llama-3.2-90b-text-preview",  # Try newest large model
            "llama-3.2-70b-preview",       # Alternative 70B
            "mixtral-8x7b-32768",          # Mixtral (effective ~56B)
            "llama-3.1-8b-instant"         # Fallback to 8B
        ]
        
        last_error = None
        for model in models_to_try:
            try:
                response = self.groq_client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=model,
                    temperature=0.1,
                    max_tokens=100
                )
                logger.debug(f"Using model: {model}")
                break  # Success, exit the loop
            except Exception as e:
                last_error = e
                continue  # Try next model
        else:
            # All models failed
            raise last_error
        
        result_text = response.choices[0].message.content.strip()
        
        # Parse JSON response
        import json
        import re
        try:
            # First try direct JSON parsing
            result = json.loads(result_text)
            logger.info(f"🤖 AI classified '{message[:30]}...' as {result['intent']} (confidence: {result['confidence']})")
            return result
        except json.JSONDecodeError:
            # Try to extract JSON from response text
            try:
                # Look for JSON pattern in the response
                json_match = re.search(r'\{[^}]*"intent"[^}]*\}', result_text)
                if json_match:
                    json_str = json_match.group(0)
                    result = json.loads(json_str)
                    logger.info(f"🤖 AI classified '{message[:30]}...' as {result['intent']} (extracted from text)")
                    return result
            except json.JSONDecodeError:
                pass
            
            # Log the actual AI response for debugging
            logger.warning(f"❌ AI returned invalid JSON: {result_text}")
            
            # Try to extract intent from text response
            result_lower = result_text.lower()
            if "link" in result_lower:
                return {"intent": "LINK", "confidence": 0.8, "reasoning": "AI mentioned link in response"}
            elif "note" in result_lower:
                return {"intent": "NOTE", "confidence": 0.8, "reasoning": "AI mentioned note in response"}
            elif "task" in result_lower:
                return {"intent": "TASK", "confidence": 0.8, "reasoning": "AI mentioned task in response"}
            elif "question" in result_lower:
                return {"intent": "QUESTION", "confidence": 0.8, "reasoning": "AI mentioned question in response"}
            elif "reminder" in result_lower:
                return {"intent": "REMINDER", "confidence": 0.8, "reasoning": "AI mentioned reminder in response"}
            elif "greeting" in result_lower:
                return {"intent": "GREETING", "confidence": 0.8, "reasoning": "AI mentioned greeting in response"}
            
            # Ultimate fallback to keyword classification
            logger.info("🔄 Falling back to keyword classification")
            return self._classify_with_keywords(message)
    
    def _classify_with_keywords(self, message: str) -> Dict[str, any]:
        """Fallback keyword-based classification."""
        
        message_lower = message.lower()
        
        # Link detection (ONLY for actual URLs)
        import re
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        
        # Only classify as LINK if actual URL is present
        if re.search(url_pattern, message):
            return {"intent": "LINK", "confidence": 0.9, "reasoning": "URL detected in message"}
        
        # Additional link patterns only if no URL found yet
        link_keywords = ['read later', 'save link', 'bookmark this', 'www.', '.com/', '.org/', '.net/']
        if any(keyword in message_lower for keyword in link_keywords):
            return {"intent": "LINK", "confidence": 0.8, "reasoning": "Link-related keywords detected"}
        
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
        note_keywords = ['note', 'remember', 'save', 'keep', 'record', 'write down', 'important', 'idea', 'thought', 'learned', 'i have an idea', 'thinking about', 'discovered']
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
    """Process natural language messages with advanced AI."""
    
    if not update.message or not update.message.text:
        return
    
    user_message = update.message.text
    user_id = str(update.effective_user.id)
    
    logger.info(f"🧠 Processing with Advanced AI - user {user_id}: '{user_message[:50]}...'")
    
    try:
        # Deterministic pre-classification first
        pre = pre_classify_message(user_message)
        if pre:
            logger.info(f"🔎 Pre-classified message as {pre['type']} with confidence {pre['confidence']}")
            ctype = pre['type']
            if ctype == 'link':
                from handlers.supabase_content import content_handler
                result = await content_handler.save_link(user_id, pre['url'], pre.get('content',''), {'confidence': pre['confidence'], 'reasoning': 'pre-classifier'})
                if result.get('success'):
                    await update.message.reply_text(f"✅ Saved link: {result.get('title', 'Untitled')}")
                    return
            elif ctype == 'reminder' and pre.get('time'):
                # Build content_data for advanced reminder saver
                content_data = {
                    'type': 'reminder',
                    'title': pre.get('title', user_message),
                    'content': pre.get('content', user_message),
                    'time': pre.get('time')
                }
                await handle_advanced_reminder_saving(update, content_data)
                return
            elif ctype == 'task':
                from handlers.supabase_content import content_handler
                result = await content_handler.save_task(user_id, pre['content'], {'confidence': pre['confidence'], 'reasoning': 'pre-classifier'})
                if result.get('success'):
                    await update.message.reply_text(f"✅ Saved task: {result.get('title', 'Untitled')}")
                    return
            elif ctype == 'note':
                from handlers.supabase_content import content_handler
                result = await content_handler.save_note(user_id, pre['content'], {'confidence': pre['confidence'], 'reasoning': 'pre-classifier'})
                if result.get('success'):
                    await update.message.reply_text(f"✅ Saved note: {result.get('title', 'Untitled')}")
                    return

        # First check if it's a content management command (delete, complete, edit)
        if content_manager.is_management_command(user_message):
            result = await content_manager.handle_management_command(user_id, user_message)
            
            if result.get('success'):
                await update.message.reply_text(result['message'])
            else:
                await update.message.reply_text(f"❌ {result.get('error', 'Management command failed')}")
            return
        
        # Use Advanced AI for processing
        try:
            from core.advanced_ai import process_with_advanced_ai
            ai_response = await process_with_advanced_ai(user_id, user_message)
            
            # Handle the AI response
            await handle_advanced_ai_response(update, context, ai_response)
            return
            
        except Exception as ai_error:
            logger.warning(f"Advanced AI failed: {ai_error}. Falling back to basic classification.")
        
        # Fallback to basic classification if Advanced AI fails
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

async def handle_advanced_ai_response(update, context, ai_response) -> None:
    """Handle response from advanced AI system."""
    
    try:
        user_id = str(update.effective_user.id)
        
        # Send the main AI response
        await update.message.reply_text(ai_response.text, parse_mode='Markdown')
        
        # Handle content saving if needed
        if ai_response.content_to_save:
            content_data = ai_response.content_to_save
            content_type = content_data.get('type')
            
            # Save content based on type
            from handlers.supabase_content import content_handler
            
            if content_type == 'note':
                result = await content_handler.save_note(user_id, content_data.get('content', ''), {})
            elif content_type == 'task':
                result = await content_handler.save_task(user_id, content_data.get('content', ''), {})
            elif content_type == 'link':
                result = await content_handler.save_link(user_id, content_data.get('url', ''), content_data.get('context', ''), {})
            elif content_type == 'reminder':
                # Handle reminder with time parsing
                await handle_advanced_reminder_saving(update, content_data)
                return
            
            # Confirm save result
            if result and result.get('success'):
                await update.message.reply_text(f"✅ Saved {content_type}: {result.get('title', 'Untitled')}")
        
        # Handle followup questions
        if ai_response.needs_followup and ai_response.followup_question:
            # Mark user as awaiting followup
            from core.advanced_ai import advanced_ai
            context_obj = advanced_ai.conversation_contexts.get(user_id)
            if context_obj:
                context_obj.awaiting_followup = True
                context_obj.followup_context = {
                    'original_intent': ai_response.intent,
                    'content_data': ai_response.content_to_save
                }
        
        # Show suggested actions if available
        if ai_response.suggested_actions:
            suggestions = "\n".join([f"• {action}" for action in ai_response.suggested_actions[:3]])
            await update.message.reply_text(f"💡 **Suggestions:**\n{suggestions}", parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Error handling advanced AI response: {e}")
        await update.message.reply_text("I processed your message but had trouble with some follow-up actions.")

async def handle_advanced_reminder_saving(update, content_data: dict) -> None:
    """Handle reminder saving with time parsing."""
    
    try:
        user_id = str(update.effective_user.id)
        
        # Debug: Log the content_data to see what the AI extracted
        logger.info(f"🔍 DEBUG: Advanced AI reminder data: {content_data}")
        
        # Check if time is specified and normalize type (AI may pass number)
        raw_time = content_data.get('time')
        logger.info(f"🔍 DEBUG: Extracted time raw: '{raw_time}' ({type(raw_time)})")

        time_str = None
        if raw_time is None or raw_time == "":
            time_str = None
        elif isinstance(raw_time, (int, float)):
            # Assume minutes for bare numbers, e.g., 2 -> "in 2 minutes"
            minutes_val = int(raw_time)
            time_str = f"in {minutes_val} minutes"
        else:
            time_str = str(raw_time)

        logger.info(f"🔍 DEBUG: Normalized time string: '{time_str}'")

        if not time_str:
            # Ask for time
            await update.message.reply_text(
                "⏰ When would you like to be reminded? \n\nTry: 'tomorrow at 3pm', 'in 2 hours', 'next Monday morning'"
            )
            
            # Set up followup context
            from core.advanced_ai import advanced_ai
            context_obj = advanced_ai.conversation_contexts.get(user_id)
            if context_obj:
                context_obj.awaiting_followup = True
                context_obj.followup_context = {
                    'original_intent': 'SAVE_REMINDER',
                    'reminder_data': content_data
                }
            return
        
        # Parse the time with user's timezone and normalize to UTC
        from core.time_parser import parse_time_expression
        import pytz as _pytz
        logger.info(f"🔍 DEBUG: About to parse time: '{time_str}' (tz=Asia/Kolkata)")
        parsed_time = await parse_time_expression(time_str, user_timezone='Asia/Kolkata')
        logger.info(f"🔍 DEBUG: Parsed time result: {parsed_time}")
        
        if parsed_time and parsed_time.get('datetime'):
            # Save reminder with parsed time
            from handlers.supabase_content import content_handler
            from datetime import timezone as _tz
            
            reminder_content = f"{content_data.get('title', '')} - {content_data.get('content', '')}"
            _dt = parsed_time['datetime']
            if _dt.tzinfo is None:
                try:
                    _dt = _pytz.timezone('Asia/Kolkata').localize(_dt)
                except Exception:
                    pass
            dt_utc = _dt.astimezone(_pytz.UTC)
            result = await content_handler.save_reminder(user_id, reminder_content, {
                'scheduled_time': dt_utc.isoformat()
            })
            
            if result.get('success'):
                formatted_time = parsed_time['datetime'].strftime('%B %d, %Y at %I:%M %p')
                await update.message.reply_text(f"⏰ Reminder set for {formatted_time}!")
                
                # Schedule the actual notification
                logger.info(f"🔍 DEBUG: About to schedule notification for {dt_utc} (UTC)")
                from core.notification_scheduler import schedule_reminder
                success = await schedule_reminder(
                    user_id,
                    content_data.get('title', 'Reminder'),
                    content_data.get('content', ''),
                    dt_utc
                )
                logger.info(f"🔍 DEBUG: Notification scheduling result: {success}")
            else:
                await update.message.reply_text("❌ Failed to save reminder. Please try again.")
        else:
            await update.message.reply_text(
                "I couldn't understand that time. Try: 'tomorrow at 3pm', 'in 2 hours', or 'next Monday'"
            )
    
    except Exception as e:
        logger.error(f"Error handling advanced reminder: {e}")
        await update.message.reply_text("❌ Error setting up reminder. Please try again.")

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
        # Try to extract search term from the question
        search_term = extract_search_term(message_lower)
        
        if search_term:
            # Perform actual search using the dedicated search engine
            try:
                from core.search_engine import get_search_engine
                search_engine = get_search_engine()
                
                # Use the advanced search engine
                search_result = await search_engine.search(user_id, search_term, limit=5)
                
                if search_result.get("success") and search_result.get("results"):
                    results = search_result["results"]
                    response = f"🔍 Found {len(results)} result(s) for '{search_term}':\n\n"
                    
                    for item in results:
                        content_type = item.get('content_type', 'unknown')
                        content_id = item.get('id', 'unknown')
                        title = item.get('title', 'Untitled')
                        snippet = item.get('snippet', item.get('content', ''))
                        created_at = item.get('created_at', '')
                        
                        # Aggressive text cleaning and safety measures
                        def clean_text(text):
                            if not text:
                                return ""
                            # Convert to string and handle None values
                            text = str(text)
                            # Remove problematic characters
                            text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
                            # Remove multiple spaces
                            text = ' '.join(text.split())
                            # Encode/decode to handle special characters
                            text = text.encode('utf-8', 'ignore').decode('utf-8')
                            # Limit length
                            return text[:100] if len(text) > 100 else text
                        
                        title = clean_text(title)
                        snippet = clean_text(snippet)
                        
                        # Format based on type with safer formatting
                        if content_type == 'note':
                            response += f"📝 Note [{content_id}]: {title}\n"
                            response += f"   {snippet}\n"
                        elif content_type == 'link':
                            url = clean_text(item.get('url', ''))
                            response += f"🔗 Link [{content_id}]: {title}\n"
                            response += f"   {url}\n"
                        elif content_type == 'task':
                            completed = item.get('completed', False)
                            status_emoji = '✅' if completed else '📋'
                            response += f"{status_emoji} Task [{content_id}]: {title}\n"
                            response += f"   {snippet}\n"
                        elif content_type == 'reminder':
                            response += f"⏰ Reminder [{content_id}]: {title}\n"
                            response += f"   {snippet}\n"
                        else:
                            response += f"📄 {title}\n"
                            response += f"   {snippet}\n"
                        
                        # Add date safely
                        date_str = created_at[:10] if created_at and len(created_at) >= 10 else 'Unknown'
                        response += f"   📅 {date_str}\n\n"
                        
                        # Prevent message from getting too long (more conservative limit)
                        if len(response) > 3000:
                            remaining = len(results) - (results.index(item) + 1)
                            if remaining > 0:
                                response += f"... and {remaining} more results.\n"
                                response += f"Use /search {search_term} for complete results."
                            break
                    
                    # Only add "see more" if we haven't already truncated
                    if len(results) >= 5 and len(response) <= 3000:
                        response += f"Use /search {search_term} to see more results."
                else:
                    response = f"🔍 No results found for '{search_term}'.\n\n"
                    response += "Try:\n"
                    response += "• Different keywords\n"
                    response += "• /notes, /tasks, /links to browse all content\n"
                    response += "• /search for search help"
                    
            except Exception as e:
                logger.error(f"Search error: {e}")
                response = "❌ Error searching your content. Please try again."
        else:
            # Fallback to help text if we can't extract a search term
            response = f"🔍 Great question! Here's how to find your content:\n\n"
            
            # Check if they have any content first
            try:
                from handlers.supabase_content import content_handler
                result = await content_handler.get_user_content(user_id, limit=1)
                has_content = result.get("success") and result.get("count", 0) > 0
            except:
                has_content = False
            
            if has_content:
                response += "🎯 Quick Commands:\n"
                response += "• /notes - Show your recent notes\n"
                response += "• /tasks - Show your tasks and TODOs\n"
                response += "• /links - Show your saved links\n"
                response += "• /stats - See your content statistics\n\n"
                response += "🔍 Search Commands:\n"
                response += "• /search productivity - Find all productivity content\n"
                response += "• /search notes python - Find Python-related notes\n"
                response += "• /search tasks urgent - Find urgent tasks\n\n"
                response += "💡 Try these examples:\n"
                response += "• /search today - Content from today\n"
                response += "• /search fastapi - FastAPI-related content\n"
                response += "• /search meeting - Meeting-related items"
            else:
                response += "📱 You haven't saved any content yet!\n\n"
                response += "Get started by saying:\n"
                response += "• \"I learned that Supabase is awesome\"\n"
                response += "• \"Task: Finish the project report\"\n"
                response += "• \"https://fastapi.tiangolo.com great framework\"\n"
                response += "• \"Remind me to call mom tomorrow\"\n\n"
                response += "Once you save some content, use /search, /notes, /tasks, /links to find it!"
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
    
    # Enhanced safe message sending with comprehensive error handling
    try:
        # Log the response for debugging
        logger.info(f"Attempting to send response (length: {len(response)})")
        logger.debug(f"Response content preview: {response[:200]}...")
        
        # Additional text cleaning for safety
        safe_response = response.encode('utf-8', 'ignore').decode('utf-8')
        safe_response = safe_response.replace('\r\n', '\n').replace('\r', '\n')
        
        # Ensure response isn't too long
        if len(safe_response) > 4000:
            safe_response = safe_response[:3900] + "\n\n... (truncated for length)"
        
        await update.message.reply_text(safe_response, parse_mode='Markdown')
        logger.info("✅ Successfully sent response with Markdown")
        
    except Exception as e:
        logger.warning(f"Failed to send with Markdown: {str(e)}")
        try:
            # More aggressive cleaning for plain text
            plain_response = response.replace('*', '').replace('_', '').replace('`', '').replace('#', '')
            plain_response = plain_response.replace('[', '').replace(']', '').replace('(', '').replace(')', '')
            plain_response = plain_response.encode('ascii', 'ignore').decode('ascii')
            
            # Ensure it's not too long
            if len(plain_response) > 4000:
                plain_response = plain_response[:3900] + "\n\n... (truncated)"
                
            await update.message.reply_text(plain_response)
            logger.info("✅ Successfully sent response as plain text")
            
        except Exception as e2:
            logger.error(f"Failed to send message entirely: {str(e2)}")
            try:
                # Final fallback - very simple message
                await update.message.reply_text("🔍 Search completed! Found results for your query.")
                logger.info("✅ Sent fallback message")
            except Exception as e3:
                logger.error(f"Even fallback message failed: {str(e3)}")
                # Don't try to send anything else

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
    response += "💬 Just chat naturally with me!\n"
    response += "📋 \"I need to finish my report by Friday\"\n"
    response += "📝 \"Remember my doctor's appointment is at 3pm\"\n"
    response += "⏰ \"Remind me to call mom tomorrow\"\n"
    response += "🔗 \"Read later: https://example.com\"\n"
    response += "❓ \"What did I save about productivity?\"\n\n"
    response += "Or use commands like /help to see all options!"
    
    await update.message.reply_text(response)

async def handle_link_intent(update, context, message: str, classification: Dict) -> None:
    """Handle link saving requests."""
    
    confidence = classification['confidence']
    user_id = str(update.effective_user.id)
    
    # Extract URL if present (preserve full URL including query params)
    import re
    url_pattern = r'https?://\S+'
    urls = re.findall(url_pattern, message)
    
    if urls:
        url = urls[0]
        context_text = message.replace(url, "").strip()
        
        # Save to Supabase database
        from handlers.supabase_content import content_handler
        result = await content_handler.save_link(user_id, url, context_text, classification)
        
        if result["success"]:
            response = f"🔗 Link Saved Successfully! (confidence: {confidence:.0%})\n\n"
            response += f"💾 URL: {url}\n"
            response += f"📄 Title: {result['title'] or 'No title'}\n"
            if context_text:
                response += f"📝 Context: {context_text}\n"
            response += f"🔗 ID: {result['id']}\n\n"
            response += "🌟 Your link is now saved in your read-later collection!"
        else:
            response = f"🔗 Link Detected (confidence: {confidence:.0%})\n\n"
            response += f"URL: {url}\n\n"
            response += f"❌ Save failed: {result.get('error', 'Unknown error')}\n\n"
            response += "💡 Make sure you're registered with /register and the database is configured correctly."
    else:
        response = f"🔗 Link Intent Detected (confidence: {confidence:.0%})\n\n"
        response += f"Message: {message}\n\n"
        response += "❌ No URL found in your message.\n\n"
        response += "💡 Include a URL like: https://example.com or Read later: https://article.com"
    
    await update.message.reply_text(response)

async def handle_file_intent(update, context, message: str, classification: Dict) -> None:
    """Handle file upload and processing requests."""
    
    confidence = classification['confidence']
    
    response = f"📄 File Intent Detected (confidence: {confidence:.0%})\n\n"
    response += f"Message: {message}\n\n"
    response += "🚧 Advanced file processing is coming soon!\n\n"
    response += "Planned Features:\n"
    response += "• 📄 PDF Processing: Auto-compress and extract text\n"
    response += "• 🖼️ Image OCR: Extract text from screenshots\n"
    response += "• 📁 Smart Organization: Auto-categorize and tag files\n"
    response += "• 🔍 Content Search: Find text within uploaded documents\n\n"
    response += "For now, you can upload files directly and I'll acknowledge them!"
    
    await update.message.reply_text(response)

async def handle_other_intent(update, context, message: str, classification: Dict) -> None:
    """Handle other/unclassified messages with smart detection."""
    
    confidence = classification['confidence']
    reasoning = classification.get('reasoning', 'Unknown')
    message_lower = message.lower()
    
    # Last-chance smart detection for common missed patterns
    if any(word in message_lower for word in ['search', 'find', 'what did i save', 'show me', 'how do i']):
        # This should have been a question - redirect to question handler
        logger.info(f"� Redirecting missed question to question handler: {message}")
        classification['intent'] = 'QUESTION'
        classification['confidence'] = 0.8
        await handle_question_intent(update, context, message, classification)
        return
    
    elif any(word in message_lower for word in ['hello', 'hi', 'hey', 'good morning', 'good afternoon']):
        # This should have been a greeting - redirect to greeting handler
        logger.info(f"🔄 Redirecting missed greeting to greeting handler: {message}")
        classification['intent'] = 'GREETING'
        classification['confidence'] = 0.8
        await handle_greeting_intent(update, context, message, classification)
        return
    
    # For truly unclassified messages, be more helpful
    response = f"🤔 **I'm not quite sure how to help with that** (confidence: {confidence:.0%})\n\n"
    response += f"You said: *{message}*\n\n"
    
    # Check if user has content to give better suggestions
    user_id = str(update.effective_user.id)
    try:
        from handlers.supabase_content import content_handler
        result = await content_handler.get_user_content(user_id, limit=1)
        has_content = result.get("success") and result.get("count", 0) > 0
    except:
        has_content = False
    
    if has_content:
        response += "**� Here's what I can definitely help with:**\n\n"
        response += "• `/notes` - Show your saved notes\n"
        response += "• `/tasks` - Show your tasks\n"
        response += "• `/links` - Show your saved links\n"
        response += "• `/search <query>` - Search your content\n"
        response += "• `/help` - See all commands\n\n"
        response += "**Or try saying:**\n"
        response += "• \"Show me my recent notes\"\n"
        response += "• \"What did I save today?\"\n"
        response += "• \"I learned something new...\"\n"
    else:
        response += "**� Let's get you started! Try:**\n\n"
        response += "• \"I learned that Python is great for automation\"\n"
        response += "• \"Task: Finish my project by Friday\"\n"
        response += "• \"https://example.com interesting article\"\n"
        response += "• \"Remind me to call mom tomorrow\"\n"
        response += "• `/help` - See all features\n\n"
        response += "Once you save some content, I'll be much more helpful!"
    
    response += f"\n🤖 *Why I'm unsure: {reasoning}*"
    
    await update.message.reply_text(response, parse_mode='Markdown')
