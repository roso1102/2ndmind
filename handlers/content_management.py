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
            # Parse delete command patterns (support both numeric IDs and UUIDs)
            delete_patterns = [
                r'delete\s+(task|note|link|reminder)\s+([a-f0-9-]+)',  # delete task uuid
                r'remove\s+(task|note|link|reminder)\s+([a-f0-9-]+)',  # remove note uuid
                r'delete\s+([a-f0-9-]+)',  # delete uuid
                r'remove\s+([a-f0-9-]+)',  # remove uuid
                r'delete\s+(task|note|link|reminder)\s+(\d+)',  # delete task 5 (legacy)
                r'remove\s+(task|note|link|reminder)\s+(\d+)',  # remove note 3 (legacy)
                r'delete\s+(\d+)',  # delete 5 (legacy)
                r'remove\s+(\d+)',  # remove 3 (legacy)
            ]
            
            content_type = None
            content_id = None
            
            for pattern in delete_patterns:
                match = re.search(pattern, message.lower())
                if match:
                    if len(match.groups()) == 2:
                        content_type = match.group(1)
                        content_id = match.group(2)
                    else:
                        content_id = match.group(1)
                    break
            
            if not content_id:
                return {
                    "success": False,
                    "error": "Please specify what to delete. Examples:\n• delete task 5\n• remove note 3\n• delete 7"
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
            # Parse completion command patterns (support both numeric IDs and UUIDs)
            complete_patterns = [
                r'(complete|done|finish)\s+task\s+([a-f0-9-]+)',  # complete task uuid
                r'(complete|done|finish)\s+([a-f0-9-]+)',  # done uuid
                r'mark\s+([a-f0-9-]+)\s+(complete|done)',  # mark uuid complete
                r'task\s+([a-f0-9-]+)\s+(complete|done)',  # task uuid done
                r'(complete|done|finish)\s+task\s+(\d+)',  # complete task 5 (legacy)
                r'(complete|done|finish)\s+(\d+)',  # done 3 (legacy)
                r'mark\s+(\d+)\s+(complete|done)',  # mark 5 complete (legacy)
                r'task\s+(\d+)\s+(complete|done)',  # task 5 done (legacy)
            ]
            
            task_id = None
            
            for pattern in complete_patterns:
                match = re.search(pattern, message.lower())
                if match:
                    groups = match.groups()
                    # Find the ID group (UUID or digit)
                    for group in groups:
                        if group and (group.isdigit() or re.match(r'^[a-f0-9-]+$', group)):
                            task_id = group
                            break
                    if task_id:
                        break
            
            if not task_id:
                return {
                    "success": False,
                    "error": "Please specify which task to complete. Examples:\n• complete task 5\n• done 3\n• mark 7 complete"
                }
            
            # Get task details first
            get_result = await self.content_handler.get_content_by_id(user_id, task_id)
            
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
