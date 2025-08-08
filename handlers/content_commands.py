#!/usr/bin/env python3
"""
👁️ Content Viewing Commands for MySecondMind

This module provides Telegram commands to view, search, and manage saved content.
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

async def view_notes_command(update, context) -> None:
    """View user's recent notes."""
    user_id = str(update.effective_user.id)
    
    try:
        from handlers.supabase_content import content_handler
        result = await content_handler.get_user_content(user_id, content_type='note', limit=10)
        
        if result["success"] and result["count"] > 0:
            response = f"📝 Your Recent Notes ({result['count']} shown)\n\n"
            
            for i, note in enumerate(result["content"], 1):
                title = note.get('title', 'Untitled')
                content = note.get('content', '')
                created_at = note.get('created_at', '')
                
                # Truncate content for preview
                content_preview = content[:100] + "..." if len(content) > 100 else content
                
                response += f"{i}. {title}\n"
                response += f"📄 {content_preview}\n"
                response += f"📅 {created_at[:10] if created_at else 'Unknown'}\n\n"
            
            response += "💡 Use `/search <term>` to find specific notes!"
        else:
            response = "📝 No Notes Found\n\n"
            response += "You haven't saved any notes yet! Try saying:\n"
            response += "• \"I learned that Python is great for automation\"\n"
            response += "• \"Remember: Meeting notes from today's standup\"\n"
            response += "• \"Idea: Build a personal knowledge bot\""
        
        await update.message.reply_text(response, )
        
    except Exception as e:
        logger.error(f"Error viewing notes: {e}")
        await update.message.reply_text(
            "❌ Error retrieving notes. Please try again later."
        )

async def view_tasks_command(update, context) -> None:
    """View user's recent tasks."""
    user_id = str(update.effective_user.id)
    
    try:
        from handlers.supabase_content import content_handler
        result = await content_handler.get_user_content(user_id, content_type='task', limit=10)
        
        if result["success"] and result["count"] > 0:
            response = f"📋 Your Recent Tasks ({result['count']} shown)\n\n"
            
            for i, task in enumerate(result["content"], 1):
                title = task.get('title', 'Untitled')
                content = task.get('content', '')
                completed = task.get('completed', False)
                due_date = task.get('due_date')
                priority = task.get('priority', 'medium')
                
                status_icon = "✅" if completed else "⏳"
                priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "🟡")
                
                response += f"{i}. {status_icon} {title} {priority_icon}\n"
                response += f"📄 {content[:80]}{'...' if len(content) > 80 else ''}\n"
                
                if due_date:
                    response += f"📅 Due: {due_date[:10]}\n"
                
                response += "\n"
            
            response += "💡 Use `/search tasks` to find specific tasks!"
        else:
            response = "📋 No Tasks Found\n\n"
            response += "You haven't saved any tasks yet! Try saying:\n"
            response += "• \"I need to finish the project report by Friday\"\n"
            response += "• \"Task: Review team performance metrics\"\n"
            response += "• \"Must complete code review before noon\""
        
        await update.message.reply_text(response, )
        
    except Exception as e:
        logger.error(f"Error viewing tasks: {e}")
        await update.message.reply_text(
            "❌ Error retrieving tasks. Please try again later."
        )

async def view_links_command(update, context) -> None:
    """View user's recent links."""
    user_id = str(update.effective_user.id)
    
    try:
        from handlers.supabase_content import content_handler
        result = await content_handler.get_user_content(user_id, content_type='link', limit=10)
        
        if result["success"] and result["count"] > 0:
            response = f"🔗 Your Recent Links ({result['count']} shown)\n\n"
            
            for i, link in enumerate(result["content"], 1):
                title = link.get('title', 'Untitled')
                url = link.get('url', '')
                content = link.get('content', '')
                created_at = link.get('created_at', '')
                
                response += f"{i}. {title}\n"
                response += f"🔗 {url}\n"
                
                # Extract context if available
                context_text = content.replace(url, "").strip()
                if context_text and context_text != url:
                    response += f"📝 {context_text[:60]}{'...' if len(context_text) > 60 else ''}\n"
                
                response += f"📅 {created_at[:10] if created_at else 'Unknown'}\n\n"
            
            response += "💡 Use /search links to find specific links!"
        else:
            response = "🔗 No Links Found\n\n"
            response += "You haven't saved any links yet! Try saying:\n"
            response += "• \"Read later: https://interesting-article.com\"\n"
            response += "• \"Bookmark: https://useful-tool.com for productivity\"\n"
            response += "• \"Save this: https://tutorial.com about Python\""
        
        await update.message.reply_text(response)
        
    except Exception as e:
        logger.error(f"Error viewing links: {e}")
        await update.message.reply_text(
            "❌ Error retrieving links. Please try again later."
        )

async def view_reminders_command(update, context) -> None:
    """View user's recent reminders."""
    user_id = str(update.effective_user.id)
    
    try:
        from handlers.supabase_content import content_handler
        result = await content_handler.get_user_content(user_id, content_type='reminder', limit=10)
        
        if result["success"] and result["count"] > 0:
            response = f"⏰ Your Recent Reminders ({result['count']} shown)\n\n"
            
            for i, reminder in enumerate(result["content"], 1):
                title = reminder.get('title', 'Untitled')
                content = reminder.get('content', '')
                due_date = reminder.get('due_date')
                created_at = reminder.get('created_at', '')
                
                response += f"{i}. ⏰ {title}\n"
                response += f"📄 {content[:80]}{'...' if len(content) > 80 else ''}\n"
                
                if due_date:
                    response += f"📅 Due: {due_date[:16].replace('T', ' ')}\n"
                else:
                    response += f"📅 Created: {created_at[:10] if created_at else 'Unknown'}\n"
                
                response += "\n"
            
            response += "💡 Use `/search reminders` to find specific reminders!"
        else:
            response = "⏰ No Reminders Found\n\n"
            response += "You haven't set any reminders yet! Try saying:\n"
            response += "• \"Remind me to call mom tomorrow at 6pm\"\n"
            response += "• \"Alert me about the meeting at 2pm\"\n"
            response += "• \"Don't forget to submit report by Friday\""
        
        await update.message.reply_text(response, )
        
    except Exception as e:
        logger.error(f"Error viewing reminders: {e}")
        await update.message.reply_text(
            "❌ Error retrieving reminders. Please try again later."
        )

async def search_command(update, context) -> None:
    """Search user's content."""
    user_id = str(update.effective_user.id)
    
    if not context.args:
        response = "🔍 Search Your Content\n\n"
        response += "Usage:\n"
        response += "`/search <query>` - Search all content\n"
        response += "`/search notes <query>` - Search only notes\n"
        response += "`/search tasks <query>` - Search only tasks\n"
        response += "`/search links <query>` - Search only links\n"
        response += "`/search reminders <query>` - Search only reminders\n\n"
        response += "Examples:\n"
        response += "• `/search python` - Find all Python-related content\n"
        response += "• `/search tasks urgent` - Find urgent tasks\n"
        response += "• `/search notes productivity` - Find productivity notes"
        
        await update.message.reply_text(response, )
        return
    
    query_parts = context.args
    
    # Check if first argument is a content type
    content_types = ['notes', 'tasks', 'links', 'reminders']
    content_type = None
    search_query = " ".join(query_parts)
    
    if query_parts[0].lower() in content_types:
        content_type = query_parts[0].lower().rstrip('s')  # Remove 's' to match DB values
        search_query = " ".join(query_parts[1:]) if len(query_parts) > 1 else ""
    
    if not search_query:
        await update.message.reply_text(
            "❌ Please provide a search query after the content type.\n"
            "Example: `/search tasks meeting`"
        )
        return
    
    try:
        from handlers.supabase_content import content_handler
        
        if content_type:
            # Search within specific content type
            all_content = await content_handler.get_user_content(user_id, content_type=content_type, limit=50)
            if all_content["success"]:
                # Simple text search within results
                results = []
                for item in all_content["content"]:
                    title = item.get('title', '').lower()
                    content = item.get('content', '').lower()
                    query_lower = search_query.lower()
                    
                    if query_lower in title or query_lower in content:
                        results.append(item)
                
                search_result = {"success": True, "results": results, "count": len(results)}
            else:
                search_result = all_content
        else:
            # Full-text search across all content
            search_result = await content_handler.search_content(user_id, search_query, limit=20)
        
        if search_result["success"] and search_result.get("count", 0) > 0:
            results = search_result["results"]
            response = f"🔍 Search Results for \"{search_query}\"\n"
            if content_type:
                response += f"Searching in: {content_type}s\n"
            response += f"Found: {len(results)} items\n\n"
            
            for i, item in enumerate(results[:10], 1):  # Limit to 10 results
                title = item.get('title', 'Untitled')
                content = item.get('content', '')
                item_type = item.get('content_type', 'unknown')
                created_at = item.get('created_at', '')
                
                type_icons = {
                    'note': '📝',
                    'task': '📋',
                    'link': '🔗',
                    'reminder': '⏰'
                }
                icon = type_icons.get(item_type, '📄')
                
                response += f"{i}. {icon} {title}\n"
                response += f"📄 {content[:100]}{'...' if len(content) > 100 else ''}\n"
                response += f"📅 {created_at[:10] if created_at else 'Unknown'}\n\n"
            
            if len(results) > 10:
                response += f"... and {len(results) - 10} more results.\n"
                response += "💡 Use more specific search terms to narrow results."
        else:
            response = f"🔍 No Results Found for \"{search_query}\"\n\n"
            response += "Try:\n"
            response += "• Using different keywords\n"
            response += "• Searching in specific types: `/search notes productivity`\n"
            response += "• Checking your saved content with `/notes`, `/tasks`, `/links`"
        
        await update.message.reply_text(response, )
        
    except Exception as e:
        logger.error(f"Error searching content: {e}")
        await update.message.reply_text(
            "❌ Error searching content. Please try again later."
        )

async def content_stats_command(update, context) -> None:
    """Show user's content statistics."""
    user_id = str(update.effective_user.id)
    
    try:
        from handlers.supabase_content import content_handler
        
        # Get counts for each content type
        content_types = ['note', 'task', 'link', 'reminder']
        stats = {}
        total_items = 0
        
        for content_type in content_types:
            result = await content_handler.get_user_content(user_id, content_type=content_type, limit=1000)
            count = result.get("count", 0) if result.get("success") else 0
            stats[content_type] = count
            total_items += count
        
        response = f"📊 Your Content Statistics\n\n"
        response += f"Total Items: {total_items}\n\n"
        
        type_icons = {
            'note': '📝 Notes',
            'task': '📋 Tasks', 
            'link': '🔗 Links',
            'reminder': '⏰ Reminders'
        }
        
        for content_type in content_types:
            count = stats[content_type]
            icon_label = type_icons[content_type]
            response += f"{icon_label}: {count}\n"
        
        if total_items > 0:
            response += f"\n🎯 Your Second Brain is growing!\n"
            response += f"💡 Use `/search` to find your saved knowledge"
        else:
            response += f"\n🌱 Start building your Second Brain!\n"
            response += f"Try saving some notes, tasks, or links to get started."
        
        await update.message.reply_text(response, )
        
    except Exception as e:
        logger.error(f"Error getting content stats: {e}")
        await update.message.reply_text(
            "❌ Error retrieving statistics. Please try again later."
        )
