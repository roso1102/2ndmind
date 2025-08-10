#!/usr/bin/env python3
"""
🗑️ Content Management Handler for MySecondMind

This module handles CRUD operations (Create, Read, Update, Delete) for all content types.
Provides natural language commands for managing notes, links, tasks, and reminders.
"""

import logging
import re
from typing import Dict, List, Optional
from handlers.supabase_content import content_handler

logger = logging.getLogger(__name__)

class ContentManager:
    """Handles content management operations with natural language interface."""
    
    def __init__(self):
        self.content_handler = content_handler
    
    async def handle_delete_command(self, user_id: str, message: str) -> Dict:
        """Handle delete commands like 'delete task 5' or 'remove note about AI'."""
        try:
            from handlers.session_manager import session_manager
            
            # Parse delete command patterns (support both sequential numbers and UUIDs)
            delete_patterns = [
                r'delete\s+(task|note|link|reminder)\s+(\d+)',  # delete task 5 (sequential)
                r'remove\s+(task|note|link|reminder)\s+(\d+)',  # remove note 3 (sequential)
                r'delete\s+(\d+)',  # delete 5 (sequential)
                r'remove\s+(\d+)',  # remove 3 (sequential)
                r'delete\s+(task|note|link|reminder)\s+([a-f0-9-]+)',  # delete task uuid (fallback)
                r'remove\s+(task|note|link|reminder)\s+([a-f0-9-]+)',  # remove note uuid (fallback)
                r'delete\s+([a-f0-9-]+)',  # delete uuid (fallback)
                r'remove\s+([a-f0-9-]+)',  # remove uuid (fallback)
            ]
            
            content_type = None
            content_id = None
            is_sequential = False
            
            for pattern in delete_patterns:
                match = re.search(pattern, message.lower())
                if match:
                    if len(match.groups()) == 2:
                        content_type = match.group(1)
                        content_id = match.group(2)
                    else:
                        content_id = match.group(1)
                    
                    # Check if it's a sequential number
                    is_sequential = content_id.isdigit()
                    break
            
            if not content_id:
                return {
                    "success": False,
                    "error": "Please specify what to delete. Examples:\n• delete task 5\n• remove note 3\n• delete 7"
                }
            
            # Convert sequential number to actual UUID if needed
            actual_id = content_id
            if is_sequential:
                actual_id = session_manager.get_actual_id(user_id, int(content_id))
                if not actual_id:
                    return {
                        "success": False,
                        "error": f"Item #{content_id} not found. Please view your content first to get current numbers."
                    }
            
            # Get content details first
            get_result = await self.content_handler.get_content_by_id(user_id, actual_id)
            
            if not get_result.get('success'):
                return {
                    "success": False,
                    "error": f"Content with ID {content_id} not found"
                }
            
            content = get_result['content']
            
            # Verify content type if specified
            if content_type and content['content_type'] != content_type:
                return {
                    "success": False,
                    "error": f"ID {content_id} is a {content['content_type']}, not a {content_type}"
                }
            
            # Delete the content
            delete_result = await self.content_handler.delete_content(user_id, content_id)
            
            if delete_result.get('success'):
                return {
                    "success": True,
                    "message": f"🗑️ {delete_result['message']}"
                }
            else:
                return delete_result
            
        except Exception as e:
            logger.error(f"❌ Delete command failed: {e}")
            return {"success": False, "error": "Failed to delete content"}
    
    async def handle_complete_command(self, user_id: str, message: str) -> Dict:
        """Handle task completion commands like 'complete task 5' or 'done 3'."""
        try:
            from handlers.session_manager import session_manager
            
            # Parse completion command patterns (support both sequential numbers and UUIDs)
            complete_patterns = [
                r'(complete|done|finish)\s+task\s+(\d+)',  # complete task 5 (sequential)
                r'(complete|done|finish)\s+(\d+)',  # done 3 (sequential)
                r'mark\s+(\d+)\s+(complete|done)',  # mark 5 complete (sequential)
                r'task\s+(\d+)\s+(complete|done)',  # task 5 done (sequential)
                r'(complete|done|finish)\s+task\s+([a-f0-9-]+)',  # complete task uuid (fallback)
                r'(complete|done|finish)\s+([a-f0-9-]+)',  # done uuid (fallback)
                r'mark\s+([a-f0-9-]+)\s+(complete|done)',  # mark uuid complete (fallback)
                r'task\s+([a-f0-9-]+)\s+(complete|done)',  # task uuid done (fallback)
            ]
            
            task_id = None
            is_sequential = False
            
            for pattern in complete_patterns:
                match = re.search(pattern, message.lower())
                if match:
                    groups = match.groups()
                    # Find the ID group (sequential number or UUID)
                    for group in groups:
                        if group and (group.isdigit() or re.match(r'^[a-f0-9-]+$', group)):
                            task_id = group
                            is_sequential = group.isdigit()
                            break
                    if task_id:
                        break
            
            if not task_id:
                return {
                    "success": False,
                    "error": "Please specify which task to complete. Examples:\n• complete task 5\n• done 3\n• mark 7 complete"
                }
            
            # Convert sequential number to actual UUID if needed
            actual_id = task_id
            if is_sequential:
                actual_id = session_manager.get_actual_id(user_id, int(task_id))
                if not actual_id:
                    return {
                        "success": False,
                        "error": f"Task #{task_id} not found. Please view your tasks first to get current numbers."
                    }
            
            # Get task details first
            get_result = await self.content_handler.get_content_by_id(user_id, actual_id)
            
            if not get_result.get('success'):
                return {
                    "success": False,
                    "error": f"Task with ID {task_id} not found"
                }
            
            content = get_result['content']
            
            # Verify it's a task
            if content['content_type'] != 'task':
                return {
                    "success": False,
                    "error": f"ID {task_id} is a {content['content_type']}, not a task"
                }
            
            # Check if already completed
            if content.get('completed', False):
                return {
                    "success": False,
                    "error": f"Task '{content['title']}' is already completed ✅"
                }
            
            # Mark as complete
            complete_result = await self.content_handler.mark_task_complete(user_id, task_id, True)
            
            if complete_result.get('success'):
                return {
                    "success": True,
                    "message": f"✅ Task completed: {content['title']}"
                }
            else:
                return complete_result
            
        except Exception as e:
            logger.error(f"❌ Complete command failed: {e}")
            return {"success": False, "error": "Failed to complete task"}
    
    async def handle_edit_command(self, user_id: str, message: str) -> Dict:
        """Handle edit commands like 'edit note 5 new content'."""
        try:
            # Parse edit command patterns (support both numeric IDs and UUIDs)
            edit_patterns = [
                r'edit\s+(task|note|link|reminder)\s+([a-f0-9-]+)\s+(.+)',  # edit note uuid new content
                r'update\s+(task|note|link|reminder)\s+([a-f0-9-]+)\s+(.+)',  # update task uuid new title
                r'edit\s+([a-f0-9-]+)\s+(.+)',  # edit uuid new content
                r'update\s+([a-f0-9-]+)\s+(.+)',  # update uuid new content
                r'edit\s+(task|note|link|reminder)\s+(\d+)\s+(.+)',  # edit note 5 new content (legacy)
                r'update\s+(task|note|link|reminder)\s+(\d+)\s+(.+)',  # update task 3 new title (legacy)
                r'edit\s+(\d+)\s+(.+)',  # edit 5 new content (legacy)
                r'update\s+(\d+)\s+(.+)',  # update 3 new content (legacy)
            ]
            
            content_type = None
            content_id = None
            new_content = None
            
            for pattern in edit_patterns:
                match = re.search(pattern, message, re.IGNORECASE)
                if match:
                    groups = match.groups()
                    if len(groups) == 3:
                        content_type = groups[0]
                        content_id = groups[1]
                        new_content = groups[2]
                    else:
                        content_id = groups[0]
                        new_content = groups[1]
                    break
            
            if not content_id or not new_content:
                return {
                    "success": False,
                    "error": "Please specify what to edit. Examples:\n• edit note 5 New title here\n• update task 3 Updated task description"
                }
            
            # Get content details first
            get_result = await self.content_handler.get_content_by_id(user_id, content_id)
            
            if not get_result.get('success'):
                return {
                    "success": False,
                    "error": f"Content with ID {content_id} not found"
                }
            
            content = get_result['content']
            
            # Verify content type if specified
            if content_type and content['content_type'] != content_type:
                return {
                    "success": False,
                    "error": f"ID {content_id} is a {content['content_type']}, not a {content_type}"
                }
            
            # Prepare updates based on content type
            updates = {}
            
            if content['content_type'] in ['note', 'task', 'reminder']:
                # For notes, tasks, reminders - update title or content
                if len(new_content) < 100:
                    updates['title'] = new_content
                else:
                    updates['content'] = new_content
                    updates['title'] = new_content[:97] + "..."
            
            elif content['content_type'] == 'link':
                # For links - update description/notes
                updates['content'] = new_content
            
            # Update the content
            update_result = await self.content_handler.update_content(user_id, content_id, updates)
            
            if update_result.get('success'):
                return {
                    "success": True,
                    "message": f"✏️ Updated {content['content_type']}: {content['title']}"
                }
            else:
                return update_result
            
        except Exception as e:
            logger.error(f"❌ Edit command failed: {e}")
            return {"success": False, "error": "Failed to edit content"}
    
    def is_management_command(self, message: str) -> bool:
        """Check if message is a content management command."""
        management_keywords = [
            'delete', 'remove', 'complete', 'done', 'finish', 
            'edit', 'update', 'mark', 'task.*complete'
        ]
        
        message_lower = message.lower()
        return any(re.search(keyword, message_lower) for keyword in management_keywords)
    
    async def handle_management_command(self, user_id: str, message: str) -> Dict:
        """Route management commands to appropriate handlers."""
        try:
            message_lower = message.lower()
            
            # Delete/Remove commands
            if re.search(r'\b(delete|remove)\b', message_lower):
                return await self.handle_delete_command(user_id, message)
            
            # Complete/Done commands
            elif re.search(r'\b(complete|done|finish|mark.*complete)\b', message_lower):
                return await self.handle_complete_command(user_id, message)
            
            # Edit/Update commands
            elif re.search(r'\b(edit|update)\b', message_lower):
                return await self.handle_edit_command(user_id, message)
            
            else:
                return {
                    "success": False,
                    "error": "Unknown management command. Try:\n• delete task 5\n• complete task 3\n• edit note 7 new content"
                }
            
        except Exception as e:
            logger.error(f"❌ Management command failed: {e}")
            return {"success": False, "error": "Failed to process management command"}

# Global instance
content_manager = ContentManager()
