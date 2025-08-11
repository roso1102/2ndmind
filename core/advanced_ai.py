#!/usr/bin/env python3
"""
🧠 Advanced AI Conversation Engine for MySecondMind

This module provides ChatGPT-level intelligence using free AI models:
- Enhanced Groq Llama-3.1 integration with advanced prompting
- Conversation memory and context awareness
- Multi-turn conversations with intelligent followups
- Content transformation and smart routing
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class ConversationContext:
    """Context for maintaining conversation state."""
    user_id: str
    conversation_id: Optional[str] = None
    recent_messages: List[Dict] = None
    user_preferences: Dict = None
    current_intent: Optional[str] = None
    awaiting_followup: bool = False
    followup_context: Dict = None
    
    def __post_init__(self):
        if self.recent_messages is None:
            self.recent_messages = []
        if self.user_preferences is None:
            self.user_preferences = {}
        if self.followup_context is None:
            self.followup_context = {}

@dataclass
class AIResponse:
    """Structured AI response."""
    text: str
    intent: str
    confidence: float
    needs_followup: bool = False
    followup_question: Optional[str] = None
    suggested_actions: List[str] = None
    content_to_save: Optional[Dict] = None
    
    def __post_init__(self):
        if self.suggested_actions is None:
            self.suggested_actions = []

class AdvancedAI:
    """Advanced AI conversation engine with ChatGPT-level intelligence."""
    
    def __init__(self):
        self.groq_client = None
        self.conversation_contexts = {}  # In-memory cache for active conversations
        
        # Initialize Groq client
        if os.getenv('GROQ_API_KEY'):
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))
                logger.info("✅ Advanced AI initialized with Groq Llama-3.1")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Groq: {e}")
        else:
            logger.warning("⚠️ GROQ_API_KEY not found. Advanced AI features disabled.")
    
    async def process_message(self, user_id: str, message: str, context: Optional[ConversationContext] = None) -> AIResponse:
        """Process user message with advanced AI understanding."""
        
        if not self.groq_client:
            return self._fallback_response(message)
        
        try:
            # Get or create conversation context
            if context is None:
                context = await self._get_conversation_context(user_id)
            
            # Add message to context
            context.recent_messages.append({
                "role": "user",
                "content": message,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            # Keep only last 10 messages for context
            if len(context.recent_messages) > 10:
                context.recent_messages = context.recent_messages[-10:]
            
            # Generate advanced AI response
            ai_response = await self._generate_advanced_response(message, context)
            
            # Add AI response to context
            context.recent_messages.append({
                "role": "assistant",
                "content": ai_response.text,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "intent": ai_response.intent
            })
            
            # Update context cache
            self.conversation_contexts[user_id] = context
            
            # Save conversation to database
            await self._save_conversation(user_id, message, ai_response)
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Advanced AI processing failed: {e}")
            return self._fallback_response(message)
    
    async def _generate_advanced_response(self, message: str, context: ConversationContext) -> AIResponse:
        """Generate advanced AI response using enhanced prompting."""
        
        # Build conversation history for context
        conversation_history = ""
        if context.recent_messages:
            for msg in context.recent_messages[-6:]:  # Last 3 exchanges
                role = "User" if msg["role"] == "user" else "Assistant"
                conversation_history += f"{role}: {msg['content']}\n"
        
        # Get user preferences for personalization
        user_prefs = context.user_preferences
        personality = user_prefs.get('ai_personality', 'helpful')
        timezone = user_prefs.get('timezone', 'UTC')
        
        # Enhanced system prompt with personality and context
        system_prompt = self._build_system_prompt(personality, timezone, context)
        
        # Main conversation prompt
        main_prompt = f"""
CONVERSATION CONTEXT:
{conversation_history}

CURRENT USER MESSAGE: "{message}"

INSTRUCTIONS:
1. Analyze the user's intent deeply - are they trying to save content, ask questions, get help, or just chat?
2. Provide a helpful, intelligent response that feels natural and conversational
3. If they want to save something, identify what type (note, task, link, reminder) and extract the key information
4. If they're asking about their content, help them search or browse effectively  
5. If information is missing (like time for reminders), ask intelligent followup questions
6. Be proactive - suggest useful actions they might want to take
7. Match their tone and communication style

RESPOND WITH VALID JSON:
{{
    "text": "Your conversational response here",
    "intent": "CHAT|SAVE_NOTE|SAVE_TASK|SAVE_LINK|SAVE_REMINDER|SEARCH|HELP|FOLLOWUP",
    "confidence": 0.95,
    "needs_followup": false,
    "followup_question": null,
    "suggested_actions": ["action1", "action2"],
    "content_to_save": {{"type": "note", "title": "extracted title", "content": "extracted content"}}
}}

Remember: Be conversational, helpful, and intelligent. Think like ChatGPT!
"""

        try:
            # Try larger models first, fallback to smaller ones
            models_to_try = [
                "llama-3.1-70b-versatile",  # Try original first
                "llama-3.2-90b-text-preview",  # Newer large model
                "llama-3.2-70b-preview",     # Alternative 70B
                "mixtral-8x7b-32768",        # Mixtral (effective ~56B)
                "llama-3.1-8b-instant"       # Fallback to 8B
            ]
            
            last_error = None
            for model in models_to_try:
                try:
                    response = self.groq_client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": main_prompt}
                        ],
                        model=model,
                        temperature=0.3,
                        max_tokens=500
                    )
                    logger.info(f"✅ Successfully using model: {model}")
                    break  # Success, exit the loop
                except Exception as e:
                    last_error = e
                    logger.debug(f"Model {model} failed: {e}")
                    continue  # Try next model
            else:
                # All models failed
                raise last_error
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            try:
                result = json.loads(result_text)
                return AIResponse(**result)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(0))
                    return AIResponse(**result)
                else:
                    # Fallback to simple response
                    return AIResponse(
                        text=result_text,
                        intent="CHAT",
                        confidence=0.7
                    )
                    
        except Exception as e:
            logger.error(f"Groq API call failed: {e}")
            raise
    
    def _build_system_prompt(self, personality: str, timezone: str, context: ConversationContext) -> str:
        """Build personalized system prompt based on user preferences."""
        
        personality_traits = {
            'helpful': "You are a helpful, professional AI assistant focused on productivity and organization.",
            'casual': "You are a friendly, casual AI buddy who speaks naturally and uses emojis occasionally.",
            'professional': "You are a professional, business-focused AI assistant with formal communication style."
        }
        
        base_personality = personality_traits.get(personality, personality_traits['helpful'])
        
        return f"""
{base_personality}

You are MySecondMind, an advanced AI-powered personal assistant and "second brain" for the user.

CORE CAPABILITIES:
• Save and organize notes, tasks, links, and reminders
• Search through saved content intelligently  
• Provide contextual help and suggestions
• Maintain conversation context and memory
• Ask intelligent followup questions when needed

PERSONALITY & STYLE:
• Be conversational and natural, like ChatGPT
• Show understanding of context from previous messages
• Proactively suggest helpful actions
• Ask clarifying questions when information is incomplete
• Match the user's communication style and energy

USER CONTEXT:
• Timezone: {timezone}
• Current conversation context: {context.current_intent or 'General conversation'}
• Awaiting followup: {context.awaiting_followup}

CONTENT TYPES YOU CAN SAVE:
• NOTES: Ideas, thoughts, learnings, information to remember
• TASKS: TODOs, action items, things to complete
• LINKS: URLs, articles, resources for later reading
• REMINDERS: Time-based alerts, appointments, deadlines

RESPONSE GUIDELINES:
• Always respond in valid JSON format as specified
• Be helpful and intelligent in your text responses
• Correctly identify user intent (what they want to accomplish)
• Extract structured data when they want to save content
• Ask followup questions when key information is missing
• Suggest relevant actions they might want to take next

Remember: You're not just classifying intent - you're having an intelligent conversation!
"""
    
    async def _get_conversation_context(self, user_id: str) -> ConversationContext:
        """Get or create conversation context for user."""
        
        # Check in-memory cache first
        if user_id in self.conversation_contexts:
            return self.conversation_contexts[user_id]
        
        # Load from database if available
        try:
            from handlers.supabase_content import content_handler
            
            # Get recent conversation history
            # This would query the conversation_history table
            # For now, create a fresh context
            
            # Get user preferences
            user_prefs = await self._get_user_preferences(user_id)
            
            context = ConversationContext(
                user_id=user_id,
                user_preferences=user_prefs
            )
            
            self.conversation_contexts[user_id] = context
            return context
            
        except Exception as e:
            logger.error(f"Error loading conversation context: {e}")
            return ConversationContext(user_id=user_id)
    
    async def _get_user_preferences(self, user_id: str) -> Dict:
        """Get user preferences from database."""
        try:
            # This would query the user_preferences table
            # For now, return defaults
            return {
                'ai_personality': 'helpful',
                'timezone': 'UTC',
                'notification_frequency': 'normal'
            }
        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            return {}
    
    async def _save_conversation(self, user_id: str, message: str, response: AIResponse) -> None:
        """Save conversation to database."""
        try:
            # This would save to conversation_history table
            # For now, just log
            logger.info(f"💬 Conversation: {user_id} -> {response.intent}")
        except Exception as e:
            logger.error(f"Error saving conversation: {e}")
    
    def _fallback_response(self, message: str) -> AIResponse:
        """Fallback response when AI is not available."""
        
        message_lower = message.lower()
        
        # Simple intent detection
        if any(word in message_lower for word in ['hello', 'hi', 'hey']):
            return AIResponse(
                text="👋 Hello! I'm MySecondMind, your AI assistant. How can I help you today?",
                intent="CHAT",
                confidence=0.8
            )
        elif any(word in message_lower for word in ['help', 'what can you do']):
            return AIResponse(
                text="I can help you save notes, manage tasks, bookmark links, set reminders, and search your content. Try saying something like 'I learned something interesting today' or 'Remind me to call mom tomorrow'!",
                intent="HELP",
                confidence=0.9
            )
        else:
            return AIResponse(
                text="I understand you want to interact with me, but I'm having trouble with my AI processing right now. Try using specific commands like /help, /notes, or /search for now.",
                intent="CHAT",
                confidence=0.5
            )
    
    async def handle_followup_response(self, user_id: str, message: str) -> AIResponse:
        """Handle followup responses for incomplete requests."""
        
        context = self.conversation_contexts.get(user_id)
        if not context or not context.awaiting_followup:
            return await self.process_message(user_id, message, context)
        
        # Process the followup in context
        followup_context = context.followup_context
        original_intent = followup_context.get('original_intent')
        
        if original_intent == 'SAVE_REMINDER':
            # They were setting a reminder but missing time
            return await self._complete_reminder_with_time(user_id, message, followup_context)
        elif original_intent == 'SAVE_TASK':
            # They were creating a task but missing details
            return await self._complete_task_with_details(user_id, message, followup_context)
        
        # Default: process as new message
        context.awaiting_followup = False
        context.followup_context = {}
        return await self.process_message(user_id, message, context)
    
    async def _complete_reminder_with_time(self, user_id: str, time_input: str, followup_context: Dict) -> AIResponse:
        """Complete reminder creation with time information."""
        
        try:
            # Parse time using parsedatetime (will be implemented later)
            from core.time_parser import parse_time_expression
            
            parsed_time = await parse_time_expression(time_input)
            
            if parsed_time:
                # Create the reminder with parsed time
                reminder_data = followup_context.get('reminder_data', {})
                reminder_data['scheduled_time'] = parsed_time
                
                # Save reminder to database
                from handlers.supabase_content import content_handler
                result = await content_handler.save_reminder(user_id, reminder_data)
                
                if result.get('success'):
                    return AIResponse(
                        text=f"✅ Perfect! I've set your reminder for {parsed_time.strftime('%B %d, %Y at %I:%M %p')}. You'll get a notification then!",
                        intent="SAVE_REMINDER",
                        confidence=0.95
                    )
            
            # If parsing failed, ask for clarification
            return AIResponse(
                text="I'm having trouble understanding that time. Could you try something like 'tomorrow at 3pm', 'in 2 hours', or 'next Monday morning'?",
                intent="FOLLOWUP",
                confidence=0.8,
                needs_followup=True
            )
            
        except Exception as e:
            logger.error(f"Error completing reminder: {e}")
            return AIResponse(
                text="Sorry, I had trouble setting up that reminder. Let's try again - what would you like to be reminded about and when?",
                intent="CHAT",
                confidence=0.7
            )
    
    async def _complete_task_with_details(self, user_id: str, details: str, followup_context: Dict) -> AIResponse:
        """Complete task creation with additional details."""
        
        try:
            task_data = followup_context.get('task_data', {})
            
            # Add the additional details
            if 'content' in task_data:
                task_data['content'] += f" {details}"
            else:
                task_data['content'] = details
            
            # Save task to database
            from handlers.supabase_content import content_handler
            result = await content_handler.save_task(user_id, task_data)
            
            if result.get('success'):
                return AIResponse(
                    text=f"✅ Great! I've added that task to your list: '{task_data.get('title', task_data['content'][:50])}'",
                    intent="SAVE_TASK",
                    confidence=0.95
                )
            else:
                return AIResponse(
                    text="I had trouble saving that task. Let me try again - what do you need to get done?",
                    intent="CHAT",
                    confidence=0.7
                )
                
        except Exception as e:
            logger.error(f"Error completing task: {e}")
            return AIResponse(
                text="Sorry, I had trouble saving that task. What would you like to add to your task list?",
                intent="CHAT",
                confidence=0.7
            )
    
    def clear_conversation_context(self, user_id: str) -> None:
        """Clear conversation context for user."""
        if user_id in self.conversation_contexts:
            del self.conversation_contexts[user_id]

# Global AI instance
advanced_ai = AdvancedAI()

async def process_with_advanced_ai(user_id: str, message: str) -> AIResponse:
    """Main entry point for advanced AI processing."""
    return await advanced_ai.process_message(user_id, message)

async def handle_ai_followup(user_id: str, message: str) -> AIResponse:
    """Handle followup responses."""
    return await advanced_ai.handle_followup_response(user_id, message)
