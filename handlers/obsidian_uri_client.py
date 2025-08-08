#!/usr/bin/env python3
"""
🔮 Obsidian Advanced URI Integration for MySecondMind

This module provides integration with Obsidian through the Advanced URI plugin,
allowing remote creation and manipulation of notes in Obsidian.
"""

import logging
import urllib.parse
import requests
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class ObsidianAdvancedURIHandler:
    """Handles Obsidian integration through Advanced URI plugin."""
    
    def __init__(self):
        self.base_uri = "obsidian://advanced-uri"
        
    async def save_note(self, user_id: str, content: str, classification: Dict) -> Dict:
        """Save note using Obsidian Advanced URI."""
        try:
            vault_name = await self.get_user_vault_name(user_id)
            if not vault_name:
                return {"success": False, "error": "Obsidian vault not configured"}
            
            # Create note filename and content
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            title = self._extract_title(content)
            filename = f"Notes/{timestamp}_{title}"
            
            note_content = self._create_note_content(content, classification)
            
            # Build Advanced URI
            uri_params = {
                'vault': vault_name,
                'file': filename,
                'content': note_content,
                'mode': 'new'
            }
            
            uri = self._build_uri('note', uri_params)
            
            # Execute URI (opens Obsidian and creates note)
            success = await self._execute_uri(uri)
            
            if success:
                return {
                    "success": True,
                    "file_path": filename,
                    "title": title,
                    "uri": uri
                }
            else:
                return {"success": False, "error": "Failed to execute Obsidian URI"}
                
        except Exception as e:
            logger.error(f"❌ Failed to save note via Obsidian URI: {e}")
            return {"success": False, "error": str(e)}
    
    async def save_link(self, user_id: str, url: str, context: str, classification: Dict) -> Dict:
        """Save link using Obsidian Advanced URI."""
        try:
            vault_name = await self.get_user_vault_name(user_id)
            if not vault_name:
                return {"success": False, "error": "Obsidian vault not configured"}
            
            title = await self._extract_url_title(url)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"Links/{timestamp}_{self._sanitize_filename(title)}"
            
            link_content = self._create_link_content(url, title, context, classification)
            
            uri_params = {
                'vault': vault_name,
                'file': filename,
                'content': link_content,
                'mode': 'new'
            }
            
            uri = self._build_uri('note', uri_params)
            success = await self._execute_uri(uri)
            
            if success:
                return {
                    "success": True,
                    "file_path": filename,
                    "title": title,
                    "url": url,
                    "uri": uri
                }
            else:
                return {"success": False, "error": "Failed to execute Obsidian URI"}
                
        except Exception as e:
            logger.error(f"❌ Failed to save link via Obsidian URI: {e}")
            return {"success": False, "error": str(e)}
    
    async def save_task(self, user_id: str, content: str, classification: Dict) -> Dict:
        """Save task by appending to tasks file."""
        try:
            vault_name = await self.get_user_vault_name(user_id)
            if not vault_name:
                return {"success": False, "error": "Obsidian vault not configured"}
            
            task_content = self._create_task_content(content, classification)
            
            # Append to Tasks.md file
            uri_params = {
                'vault': vault_name,
                'file': 'Tasks',
                'content': f"\n{task_content}",
                'mode': 'append'
            }
            
            uri = self._build_uri('note', uri_params)
            success = await self._execute_uri(uri)
            
            if success:
                return {
                    "success": True,
                    "file_path": "Tasks.md",
                    "title": self._extract_title(content),
                    "uri": uri
                }
            else:
                return {"success": False, "error": "Failed to execute Obsidian URI"}
                
        except Exception as e:
            logger.error(f"❌ Failed to save task via Obsidian URI: {e}")
            return {"success": False, "error": str(e)}
    
    def _build_uri(self, action: str, params: Dict) -> str:
        """Build Obsidian Advanced URI."""
        encoded_params = {k: urllib.parse.quote(str(v)) for k, v in params.items()}
        param_string = '&'.join([f"{k}={v}" for k, v in encoded_params.items()])
        return f"{self.base_uri}?{param_string}"
    
    async def _execute_uri(self, uri: str) -> bool:
        """Execute Obsidian URI (platform-specific)."""
        try:
            import subprocess
            import platform
            
            system = platform.system().lower()
            
            if system == "windows":
                subprocess.run(['start', uri], shell=True, check=True)
            elif system == "darwin":  # macOS
                subprocess.run(['open', uri], check=True)
            elif system == "linux":
                subprocess.run(['xdg-open', uri], check=True)
            else:
                logger.warning(f"Unsupported platform for URI execution: {system}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute URI: {e}")
            return False
    
    async def get_user_vault_name(self, user_id: str) -> Optional[str]:
        """Get user's Obsidian vault name from database."""
        from models.user_management import user_manager
        
        user = user_manager.get_user(user_id)
        if user and user.get('obsidian_vault_name'):
            return user['obsidian_vault_name']
        
        # Return default vault name
        return "MySecondMind"
    
    def _extract_title(self, content: str) -> str:
        """Extract title from content."""
        sentences = content.split('.')
        if sentences:
            title = sentences[0].strip()
            if len(title) > 50:
                title = title[:47] + "..."
            return self._sanitize_filename(title)
        return "Note"
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for Obsidian."""
        import re
        sanitized = re.sub(r'[<>:"/\\|?*]', '', filename)
        sanitized = re.sub(r'\s+', '_', sanitized)
        return sanitized[:50]
    
    def _create_note_content(self, content: str, classification: Dict) -> str:
        """Create formatted note content."""
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
        """Create formatted link content."""
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
    
    def _create_task_content(self, content: str, classification: Dict) -> str:
        """Create formatted task content."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        due_date = self._extract_due_date(content)
        due_section = f" 📅 {due_date}" if due_date else ""
        
        return f"- [ ] {content}{due_section} #task #myndsecondmind *({timestamp})*"
    
    def _extract_due_date(self, content: str) -> Optional[str]:
        """Extract due date from content."""
        import re
        date_patterns = [
            r'tomorrow', r'today', r'next week',
            r'Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday',
            r'\d{1,2}/\d{1,2}', r'\d{1,2}-\d{1,2}',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group()
        return None
    
    async def _extract_url_title(self, url: str) -> str:
        """Extract title from URL."""
        try:
            import requests
            import re
            response = requests.get(url, timeout=5)
            if '<title>' in response.text:
                title_match = re.search(r'<title>(.*?)</title>', response.text, re.IGNORECASE)
                if title_match:
                    return title_match.group(1).strip()
        except:
            pass
        return url.split('/')[-1] or "Link"

# Global instance
obsidian_uri_client = ObsidianAdvancedURIHandler()
