#!/usr/bin/env python3
"""
🔮 Obsidian Integration Handler for MySecondMind

This module handles direct integration with Obsidian vaults through file system operations.
Creates and manages markdown files in user's Obsidian vault directories.
"""

import os
import logging
import asyncio
from datetime import datetime
from typing import Dict, Optional, List
import re
from pathlib import Path

logger = logging.getLogger(__name__)

class ObsidianVaultHandler:
    """Handles direct file system integration with Obsidian vaults."""
    
    def __init__(self):
        self.default_vault_path = os.getenv('OBSIDIAN_DEFAULT_VAULT_PATH')
        
    async def save_note(self, user_id: str, content: str, classification: Dict) -> Dict:
        """Save a note to user's Obsidian vault."""
        try:
            vault_path = await self.get_user_vault_path(user_id)
            if not vault_path:
                return {"success": False, "error": "Obsidian vault not configured"}
            
            # Create note filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            title = self._extract_title(content)
            filename = f"{timestamp}_{title}.md"
            
            # Create note content with metadata
            note_content = self._create_note_content(content, classification)
            
            # Save to vault
            notes_dir = Path(vault_path) / "Notes"
            notes_dir.mkdir(exist_ok=True)
            
            file_path = notes_dir / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(note_content)
            
            logger.info(f"✅ Note saved to Obsidian: {file_path}")
            return {
                "success": True,
                "file_path": str(file_path),
                "title": title
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to save note to Obsidian: {e}")
            return {"success": False, "error": str(e)}
    
    async def save_link(self, user_id: str, url: str, context: str, classification: Dict) -> Dict:
        """Save a link to user's Obsidian vault."""
        try:
            vault_path = await self.get_user_vault_path(user_id)
            if not vault_path:
                return {"success": False, "error": "Obsidian vault not configured"}
            
            # Extract metadata from URL
            title = await self._extract_url_title(url)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{self._sanitize_filename(title)}.md"
            
            # Create link content
            link_content = self._create_link_content(url, title, context, classification)
            
            # Save to vault
            links_dir = Path(vault_path) / "Links"
            links_dir.mkdir(exist_ok=True)
            
            file_path = links_dir / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(link_content)
            
            logger.info(f"✅ Link saved to Obsidian: {file_path}")
            return {
                "success": True,
                "file_path": str(file_path),
                "title": title,
                "url": url
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to save link to Obsidian: {e}")
            return {"success": False, "error": str(e)}
    
    async def save_task(self, user_id: str, content: str, classification: Dict) -> Dict:
        """Save a task to user's Obsidian vault."""
        try:
            vault_path = await self.get_user_vault_path(user_id)
            if not vault_path:
                return {"success": False, "error": "Obsidian vault not configured"}
            
            # Parse task details
            task_title = self._extract_task_title(content)
            due_date = self._extract_due_date(content)
            
            # Create task content
            task_content = self._create_task_content(content, due_date, classification)
            
            # Save to tasks file (append to daily notes or tasks file)
            tasks_file = Path(vault_path) / "Tasks.md"
            
            # Append to existing tasks file
            with open(tasks_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{task_content}\n")
            
            logger.info(f"✅ Task saved to Obsidian: {tasks_file}")
            return {
                "success": True,
                "file_path": str(tasks_file),
                "title": task_title,
                "due_date": due_date
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to save task to Obsidian: {e}")
            return {"success": False, "error": str(e)}
    
    async def save_reminder(self, user_id: str, content: str, classification: Dict) -> Dict:
        """Save a reminder to user's Obsidian vault."""
        try:
            vault_path = await self.get_user_vault_path(user_id)
            if not vault_path:
                return {"success": False, "error": "Obsidian vault not configured"}
            
            # Parse reminder details
            reminder_title = self._extract_reminder_title(content)
            reminder_date = self._extract_due_date(content)
            
            # Create reminder content
            reminder_content = self._create_reminder_content(content, reminder_date, classification)
            
            # Save to reminders file
            reminders_file = Path(vault_path) / "Reminders.md"
            
            with open(reminders_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{reminder_content}\n")
            
            logger.info(f"✅ Reminder saved to Obsidian: {reminders_file}")
            return {
                "success": True,
                "file_path": str(reminders_file),
                "title": reminder_title,
                "due_date": reminder_date
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to save reminder to Obsidian: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_user_vault_path(self, user_id: str) -> Optional[str]:
        """Get user's Obsidian vault path from database."""
        from models.user_management import user_manager
        
        user = user_manager.get_user(user_id)
        if user and user.get('obsidian_vault_path'):
            return user['obsidian_vault_path']
        
        # Return default vault if user hasn't configured one
        return self.default_vault_path
    
    def _extract_title(self, content: str) -> str:
        """Extract a title from content."""
        # Take first sentence or first 50 characters
        sentences = content.split('.')
        if sentences:
            title = sentences[0].strip()
            if len(title) > 50:
                title = title[:47] + "..."
            return self._sanitize_filename(title)
        return "Note"
    
    def _extract_task_title(self, content: str) -> str:
        """Extract task title from content."""
        # Remove common task prefixes
        cleaned = re.sub(r'^(I need to|I should|I must|Task:|TODO:)\s*', '', content, flags=re.IGNORECASE)
        return self._extract_title(cleaned)
    
    def _extract_reminder_title(self, content: str) -> str:
        """Extract reminder title from content."""
        # Remove reminder prefixes
        cleaned = re.sub(r'^(Remind me to|Remember to|Don\'t forget to)\s*', '', content, flags=re.IGNORECASE)
        return self._extract_title(cleaned)
    
    def _extract_due_date(self, content: str) -> Optional[str]:
        """Extract due date from content using simple patterns."""
        # Simple date patterns
        date_patterns = [
            r'tomorrow',
            r'today',
            r'next week',
            r'Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday',
            r'\d{1,2}/\d{1,2}',
            r'\d{1,2}-\d{1,2}',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group()
        
        return None
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem."""
        # Remove illegal characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '', filename)
        sanitized = re.sub(r'\s+', '_', sanitized)
        return sanitized[:50]  # Limit length
    
    def _create_note_content(self, content: str, classification: Dict) -> str:
        """Create formatted note content for Obsidian."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        confidence = classification.get('confidence', 0)
        
        return f"""---
created: {timestamp}
type: note
confidence: {confidence:.0%}
tags: [myndsecondmind, note]
---

# {self._extract_title(content)}

{content}

---
*Captured via MySecondMind on {timestamp}*
"""
    
    def _create_link_content(self, url: str, title: str, context: str, classification: Dict) -> str:
        """Create formatted link content for Obsidian."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        confidence = classification.get('confidence', 0)
        
        context_section = f"\n\n## Context\n{context}" if context else ""
        
        return f"""---
created: {timestamp}
type: link
url: {url}
confidence: {confidence:.0%}
tags: [myndsecondmind, link, readlater]
---

# {title}

🔗 **URL**: [{url}]({url})

{context_section}

---
*Captured via MySecondMind on {timestamp}*
"""
    
    def _create_task_content(self, content: str, due_date: Optional[str], classification: Dict) -> str:
        """Create formatted task content for Obsidian."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        due_section = f" 📅 Due: {due_date}" if due_date else ""
        
        return f"- [ ] {content}{due_section} #task #myndsecondmind *({timestamp})*"
    
    def _create_reminder_content(self, content: str, reminder_date: Optional[str], classification: Dict) -> str:
        """Create formatted reminder content for Obsidian."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        date_section = f" 🔔 {reminder_date}" if reminder_date else ""
        
        return f"- [ ] {content}{date_section} #reminder #myndsecondmind *({timestamp})*"
    
    async def _extract_url_title(self, url: str) -> str:
        """Extract title from URL (simple implementation)."""
        try:
            import requests
            response = requests.get(url, timeout=5)
            if '<title>' in response.text:
                title_match = re.search(r'<title>(.*?)</title>', response.text, re.IGNORECASE)
                if title_match:
                    return title_match.group(1).strip()
        except:
            pass
        
        # Fallback to URL-based title
        return url.split('/')[-1] or "Link"

# Global instance
obsidian_client = ObsidianVaultHandler()
