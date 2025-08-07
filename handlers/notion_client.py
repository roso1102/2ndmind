#!/usr/bin/env python3
"""
🗃️ Notion Client Handler for MySecondMind

Handles all Notion API interactions including:
- Database creation and management
- Content saving (notes, links, reminders, tasks)
- User workspace setup and validation
- Encrypted token management
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import httpx

logger = logging.getLogger(__name__)

try:
    from notion_client import Client
    NOTION_AVAILABLE = True
except ImportError:
    NOTION_AVAILABLE = False
    logger.warning("notion-client not available. Install with: pip install notion-client")

class NotionClientHandler:
    """Handles Notion API operations for user workspaces."""
    
    def __init__(self):
        self.clients = {}  # user_id -> notion_client mapping
        logger.info("🗃️ Notion client handler initialized")
    
    def create_client(self, notion_token: str) -> Optional[Client]:
        """Create and validate a Notion client."""
        if not NOTION_AVAILABLE:
            logger.error("❌ Notion client not available")
            return None
        
        try:
            client = Client(auth=notion_token)
            # Test the connection
            client.users.me()
            logger.info("✅ Notion client created successfully")
            return client
        except Exception as e:
            logger.error(f"❌ Failed to create Notion client: {e}")
            return None
    
    def validate_database_id(self, client: Client, database_id: str) -> bool:
        """Validate that a database ID exists and is accessible."""
        try:
            client.databases.retrieve(database_id)
            return True
        except Exception as e:
            logger.error(f"❌ Database validation failed for {database_id}: {e}")
            return False
    
    def setup_user_workspace(self, user_id: str, notion_token: str, 
                           db_notes: str, db_links: str, db_reminders: str) -> Dict[str, Any]:
        """Set up and validate user's Notion workspace."""
        
        result = {
            "success": False,
            "client": None,
            "databases": {},
            "errors": []
        }
        
        # Create client
        client = self.create_client(notion_token)
        if not client:
            result["errors"].append("Invalid Notion token")
            return result
        
        # Validate databases
        databases = {
            "notes": db_notes,
            "links": db_links,
            "reminders": db_reminders
        }
        
        valid_databases = {}
        for db_type, db_id in databases.items():
            if self.validate_database_id(client, db_id):
                valid_databases[db_type] = db_id
                logger.info(f"✅ {db_type} database validated: {db_id}")
            else:
                result["errors"].append(f"Invalid {db_type} database ID: {db_id}")
        
        if len(valid_databases) == 3:
            # All databases valid
            self.clients[user_id] = client
            result["success"] = True
            result["client"] = client
            result["databases"] = valid_databases
            logger.info(f"✅ User {user_id} workspace setup completed")
        
        return result
    
    def get_client(self, user_id: str) -> Optional[Client]:
        """Get Notion client for a user."""
        return self.clients.get(user_id)
    
    async def save_note(self, user_id: str, content: str, intent_data: Dict) -> Dict[str, Any]:
        """Save a note to user's Notion notes database."""
        
        client = self.get_client(user_id)
        if not client:
            return {"success": False, "error": "User not registered with Notion"}
        
        # Get user's databases from user_management
        from models.user_management import user_manager
        user_data = user_manager.get_user(user_id)
        if not user_data or "notion_databases" not in user_data:
            return {"success": False, "error": "User databases not found"}
        
        notes_db = user_data["notion_databases"]["notes"]
        
        try:
            # Create note page in Notion
            page_data = {
                "parent": {"database_id": notes_db},
                "properties": {
                    "Title": {
                        "title": [{"text": {"content": content[:100] + "..." if len(content) > 100 else content}}]
                    },
                    "Content": {
                        "rich_text": [{"text": {"content": content}}]
                    },
                    "Created": {
                        "date": {"start": datetime.now().isoformat()}
                    },
                    "Type": {
                        "select": {"name": "Note"}
                    },
                    "Confidence": {
                        "number": intent_data.get("confidence", 0.5)
                    }
                }
            }
            
            response = client.pages.create(**page_data)
            
            logger.info(f"✅ Note saved to Notion for user {user_id}")
            return {
                "success": True,
                "notion_page_id": response["id"],
                "url": response["url"]
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to save note to Notion: {e}")
            return {"success": False, "error": str(e)}
    
    async def save_link(self, user_id: str, url: str, context: str, intent_data: Dict) -> Dict[str, Any]:
        """Save a link to user's Notion links database."""
        
        client = self.get_client(user_id)
        if not client:
            return {"success": False, "error": "User not registered with Notion"}
        
        from models.user_management import user_manager
        user_data = user_manager.get_user(user_id)
        if not user_data or "notion_databases" not in user_data:
            return {"success": False, "error": "User databases not found"}
        
        links_db = user_data["notion_databases"]["links"]
        
        try:
            # Extract link metadata
            title = await self._extract_link_title(url)
            
            page_data = {
                "parent": {"database_id": links_db},
                "properties": {
                    "Title": {
                        "title": [{"text": {"content": title or url}}]
                    },
                    "URL": {
                        "url": url
                    },
                    "Context": {
                        "rich_text": [{"text": {"content": context}}]
                    },
                    "Created": {
                        "date": {"start": datetime.now().isoformat()}
                    },
                    "Status": {
                        "select": {"name": "To Read"}
                    },
                    "Confidence": {
                        "number": intent_data.get("confidence", 0.5)
                    }
                }
            }
            
            response = client.pages.create(**page_data)
            
            logger.info(f"✅ Link saved to Notion for user {user_id}")
            return {
                "success": True,
                "notion_page_id": response["id"],
                "url": response["url"],
                "title": title
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to save link to Notion: {e}")
            return {"success": False, "error": str(e)}
    
    async def save_reminder(self, user_id: str, content: str, intent_data: Dict) -> Dict[str, Any]:
        """Save a reminder to user's Notion reminders database."""
        
        client = self.get_client(user_id)
        if not client:
            return {"success": False, "error": "User not registered with Notion"}
        
        from models.user_management import user_manager
        user_data = user_manager.get_user(user_id)
        if not user_data or "notion_databases" not in user_data:
            return {"success": False, "error": "User databases not found"}
        
        reminders_db = user_data["notion_databases"]["reminders"]
        
        try:
            # Parse due date from content (basic implementation)
            due_date = self._parse_due_date(content)
            
            page_data = {
                "parent": {"database_id": reminders_db},
                "properties": {
                    "Title": {
                        "title": [{"text": {"content": content[:100] + "..." if len(content) > 100 else content}}]
                    },
                    "Description": {
                        "rich_text": [{"text": {"content": content}}]
                    },
                    "Created": {
                        "date": {"start": datetime.now().isoformat()}
                    },
                    "Status": {
                        "select": {"name": "Pending"}
                    },
                    "Confidence": {
                        "number": intent_data.get("confidence", 0.5)
                    }
                }
            }
            
            # Add due date if parsed
            if due_date:
                page_data["properties"]["Due Date"] = {
                    "date": {"start": due_date}
                }
            
            response = client.pages.create(**page_data)
            
            logger.info(f"✅ Reminder saved to Notion for user {user_id}")
            return {
                "success": True,
                "notion_page_id": response["id"],
                "url": response["url"],
                "due_date": due_date
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to save reminder to Notion: {e}")
            return {"success": False, "error": str(e)}
    
    async def save_task(self, user_id: str, content: str, intent_data: Dict) -> Dict[str, Any]:
        """Save a task to user's Notion notes database with task type."""
        
        client = self.get_client(user_id)
        if not client:
            return {"success": False, "error": "User not registered with Notion"}
        
        from models.user_management import user_manager
        user_data = user_manager.get_user(user_id)
        if not user_data or "notion_databases" not in user_data:
            return {"success": False, "error": "User databases not found"}
        
        notes_db = user_data["notion_databases"]["notes"]  # Using notes DB for tasks
        
        try:
            page_data = {
                "parent": {"database_id": notes_db},
                "properties": {
                    "Title": {
                        "title": [{"text": {"content": content[:100] + "..." if len(content) > 100 else content}}]
                    },
                    "Content": {
                        "rich_text": [{"text": {"content": content}}]
                    },
                    "Created": {
                        "date": {"start": datetime.now().isoformat()}
                    },
                    "Type": {
                        "select": {"name": "Task"}
                    },
                    "Confidence": {
                        "number": intent_data.get("confidence", 0.5)
                    }
                }
            }
            
            response = client.pages.create(**page_data)
            
            logger.info(f"✅ Task saved to Notion for user {user_id}")
            return {
                "success": True,
                "notion_page_id": response["id"],
                "url": response["url"]
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to save task to Notion: {e}")
            return {"success": False, "error": str(e)}
    
    async def _extract_link_title(self, url: str) -> Optional[str]:
        """Extract title from a URL."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=5)
                if response.status_code == 200:
                    content = response.text
                    # Simple title extraction
                    import re
                    title_match = re.search(r'<title[^>]*>([^<]+)</title>', content, re.IGNORECASE)
                    if title_match:
                        return title_match.group(1).strip()
        except Exception as e:
            logger.warning(f"Failed to extract title from {url}: {e}")
        return None
    
    def _parse_due_date(self, content: str) -> Optional[str]:
        """Basic due date parsing from reminder content."""
        # This is a simple implementation - can be enhanced with dateutil
        import re
        from datetime import datetime, timedelta
        
        content_lower = content.lower()
        
        if "tomorrow" in content_lower:
            return (datetime.now() + timedelta(days=1)).isoformat()
        elif "today" in content_lower:
            return datetime.now().isoformat()
        elif "next week" in content_lower:
            return (datetime.now() + timedelta(weeks=1)).isoformat()
        
        # Look for time patterns like "at 3pm", "at 15:00"
        time_pattern = r'at (\d{1,2}):?(\d{0,2})\s*(am|pm)?'
        time_match = re.search(time_pattern, content_lower)
        if time_match:
            # Basic time parsing - can be enhanced
            return datetime.now().isoformat()
        
        return None

# Global instance
notion_client = NotionClientHandler()
