#!/usr/bin/env python3
"""
💾 Supabase Content Handler for MySecondMind

This module handles all content storage operations using Supabase instead of Notion.
Provides a unified interface for saving and retrieving notes, links, tasks, reminders, and files.
"""

import os
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class SupabaseContentHandler:
    """Handles content storage operations using Supabase."""
    
    def __init__(self):
        self.supabase = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Supabase client."""
        try:
            from core.supabase_rest import supabase_rest
            self.supabase = supabase_rest
            if self.supabase.ready:
                logger.info("✅ Supabase content handler initialized with REST client")
            else:
                logger.error("❌ Supabase REST client not ready")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase content handler: {e}")
    
    async def save_note(self, user_id: str, content: str, classification: Dict) -> Dict:
        """Save a note to Supabase."""
        try:
            if not self.supabase:
                return {"success": False, "error": "Supabase not initialized"}
            
            # Extract title from content
            title = self._extract_title_from_content(content)
            
            # Prepare note data
            note_data = {
                'user_id': user_id,
                'content_type': 'note',
                'title': title,
                'content': content,
                'ai_confidence': classification.get('confidence', 0.0),
                'ai_reasoning': classification.get('reasoning', ''),
                'tags': self._extract_tags_from_content(content),
                'category': 'general'
            }
            
            # Insert into database
            result = self.supabase.table('user_content').insert(note_data).execute()
            
            if result.get('data') and len(result['data']) > 0:
                note_id = result['data'][0]['id']
                logger.info(f"✅ Note saved for user {user_id}: {note_id}")
                
                return {
                    "success": True,
                    "id": note_id,
                    "title": title,
                    "content": content,
                    "message": f"Note '{title}' saved successfully!"
                }
            else:
                return {"success": False, "error": "Failed to save note to database"}
                
        except Exception as e:
            logger.error(f"❌ Failed to save note: {e}")
            return {"success": False, "error": str(e)}
    
    async def save_link(self, user_id: str, url: str, context: str, classification: Dict) -> Dict:
        """Save a link to Supabase."""
        try:
            if not self.supabase:
                return {"success": False, "error": "Supabase not initialized"}
            
            # Extract metadata from URL
            url_title = await self._extract_url_title(url)
            title = url_title or self._extract_domain_from_url(url)
            
            # Combine URL and context for content
            content = f"{context}\n\nURL: {url}" if context else url
            
            # Prepare link data
            link_data = {
                'user_id': user_id,
                'content_type': 'link',
                'title': title,
                'content': content,
                'url': url,
                'url_title': url_title,
                'ai_confidence': classification.get('confidence', 0.0),
                'ai_reasoning': classification.get('reasoning', ''),
                'tags': self._extract_tags_from_content(content) + ['readlater'],
                'category': 'links'
            }
            
            # Insert into database
            result = self.supabase.table('user_content').insert(link_data).execute()
            
            if result.get('data') and len(result['data']) > 0:
                link_id = result['data'][0]['id']
                logger.info(f"✅ Link saved for user {user_id}: {link_id}")
                
                return {
                    "success": True,
                    "id": link_id,
                    "title": title,
                    "url": url,
                    "message": f"Link '{title}' saved successfully!"
                }
            else:
                error_msg = result.get('error', 'Failed to save link to database')
                logger.error(f"❌ Database error: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"❌ Failed to save link: {e}")
            return {"success": False, "error": str(e)}
    
    async def save_task(self, user_id: str, content: str, classification: Dict) -> Dict:
        """Save a task to Supabase."""
        try:
            if not self.supabase:
                return {"success": False, "error": "Supabase not initialized"}
            
            # Extract task details
            title = self._extract_task_title(content)
            due_date = self._extract_due_date(content)
            priority = self._extract_priority(content)
            
            # Prepare task data
            task_data = {
                'user_id': user_id,
                'content_type': 'task',
                'title': title,
                'content': content,
                'completed': False,
                'due_date': due_date.isoformat() if due_date else None,
                'priority': priority,
                'ai_confidence': classification.get('confidence', 0.0),
                'ai_reasoning': classification.get('reasoning', ''),
                'tags': self._extract_tags_from_content(content) + ['task'],
                'category': 'tasks'
            }
            
            # Insert into database
            result = self.supabase.table('user_content').insert(task_data).execute()
            
            if result.get('data') and len(result['data']) > 0:
                task_id = result['data'][0]['id']
                logger.info(f"✅ Task saved for user {user_id}: {task_id}")
                
                return {
                    "success": True,
                    "id": task_id,
                    "title": title,
                    "due_date": due_date.strftime("%Y-%m-%d") if due_date else None,
                    "priority": priority,
                    "message": f"Task '{title}' saved successfully!"
                }
            else:
                return {"success": False, "error": "Failed to save task to database"}
                
        except Exception as e:
            logger.error(f"❌ Failed to save task: {e}")
            return {"success": False, "error": str(e)}
    
    async def save_reminder(self, user_id: str, content: str, classification: Dict) -> Dict:
        """Save a reminder to Supabase."""
        try:
            if not self.supabase:
                return {"success": False, "error": "Supabase not initialized"}
            
            # Extract reminder details
            title = self._extract_reminder_title(content)
            due_date = self._extract_due_date(content)
            
            # Prepare reminder data
            reminder_data = {
                'user_id': user_id,
                'content_type': 'reminder',
                'title': title,
                'content': content,
                'due_date': due_date.isoformat() if due_date else None,
                'ai_confidence': classification.get('confidence', 0.0),
                'ai_reasoning': classification.get('reasoning', ''),
                'tags': self._extract_tags_from_content(content) + ['reminder'],
                'category': 'reminders'
            }
            
            # Insert into database
            result = self.supabase.table('user_content').insert(reminder_data).execute()
            
            if result.get('data') and len(result['data']) > 0:
                reminder_id = result['data'][0]['id']
                logger.info(f"✅ Reminder saved for user {user_id}: {reminder_id}")
                
                return {
                    "success": True,
                    "id": reminder_id,
                    "title": title,
                    "due_date": due_date.strftime("%Y-%m-%d %H:%M") if due_date else None,
                    "message": f"Reminder '{title}' saved successfully!"
                }
            else:
                return {"success": False, "error": "Failed to save reminder to database"}
                
        except Exception as e:
            logger.error(f"❌ Failed to save reminder: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_user_content(self, user_id: str, content_type: Optional[str] = None, 
                              limit: int = 10) -> Dict:
        """Get user's content with optional filtering."""
        try:
            if not self.supabase:
                return {"success": False, "error": "Supabase not initialized"}
            
            # Build query
            query = self.supabase.table('user_content').select('*').eq('user_id', user_id)
            
            if content_type:
                query = query.eq('content_type', content_type)
            
            query = query.order('created_at', desc=True).limit(limit)
            
            result = query.execute()
            
            if result.get('data') is not None:
                return {
                    "success": True,
                    "content": result.get('data'),
                    "count": len(result.get('data'))
                }
            else:
                return {"success": False, "error": "Failed to fetch content"}
                
        except Exception as e:
            logger.error(f"❌ Failed to get user content: {e}")
            return {"success": False, "error": str(e)}
    
    async def search_content(self, user_id: str, query: str, limit: int = 10) -> Dict:
        """Search user's content using full-text search."""
        try:
            if not self.supabase:
                return {"success": False, "error": "Supabase not initialized"}

            # Try multiple search strategies:
            # 1. Full-text search on search_vector
            # 2. Domain-specific search for URLs (if query looks like a domain)
            # 3. Fallback to ILIKE search
            
            # Strategy 1: Full-text search
            search_query = self.supabase.table('user_content').select('*').eq('user_id', user_id)
            search_query = search_query.text_search('search_vector', query)
            search_query = search_query.order('created_at', desc=True).limit(limit)
            
            result = search_query.execute()
            
            # If we got results, return them
            if result.get('data') and len(result['data']) > 0:
                return {
                    "success": True,
                    "results": result.get('data'),
                    "count": len(result.get('data')),
                    "query": query
                }
            
            # Strategy 2: If query might be a domain search, try URL matching
            if any(domain in query.lower() for domain in ['youtube', 'instagram', 'twitter', 'github', 'linkedin']):
                url_search = await self._search_by_domain(user_id, query, limit)
                if url_search.get('success') and url_search.get('results'):
                    return url_search
            
            # Strategy 3: Fallback to ILIKE search
            return await self._fallback_search(user_id, query, limit)
                
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            # Fallback to simple text search
            return await self._fallback_search(user_id, query, limit)
    
    async def _search_by_domain(self, user_id: str, query: str, limit: int) -> Dict:
        """Search specifically for URLs containing the domain."""
        try:
            # Map common terms to URL patterns
            domain_patterns = {
                'youtube': ['youtube.com', 'youtu.be'],
                'instagram': ['instagram.com'],
                'twitter': ['twitter.com', 'x.com'],
                'github': ['github.com'],
                'linkedin': ['linkedin.com'],
                'medium': ['medium.com']
            }
            
            # Build URL search conditions
            url_conditions = []
            query_lower = query.lower()
            
            for domain, patterns in domain_patterns.items():
                if domain in query_lower:
                    for pattern in patterns:
                        url_conditions.append(f"url.ilike.%{pattern}%")
            
            if url_conditions:
                search_query = self.supabase.table('user_content').select('*').eq('user_id', user_id)
                search_query = search_query.or_(','.join(url_conditions))
                search_query = search_query.order('created_at', desc=True).limit(limit)
                
                result = search_query.execute()
                
                return {
                    "success": True,
                    "results": result.get('data', []),
                    "count": len(result.get('data', [])),
                    "query": query,
                    "search_type": "domain"
                }
            
            return {"success": False, "results": []}
                
        except Exception as e:
            logger.error(f"❌ Domain search failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _fallback_search(self, user_id: str, query: str, limit: int) -> Dict:
        """Fallback search using ILIKE."""
        try:
            search_query = self.supabase.table('user_content').select('*').eq('user_id', user_id)
            
            # Enhanced search that includes URL field for link content
            # Search in title, content, and URL (for links)
            search_conditions = f"title.ilike.%{query}%,content.ilike.%{query}%,url.ilike.%{query}%"
            search_query = search_query.or_(search_conditions)
            search_query = search_query.order('created_at', desc=True).limit(limit)
            
            result = search_query.execute()
            
            return {
                "success": True,
                "results": result.get('data', []),
                "count": len(result.get('data', [])),
                "query": query
            }
        except Exception as e:
            logger.error(f"❌ Fallback search failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _extract_title_from_content(self, content: str) -> str:
        """Extract title from content."""
        sentences = content.split('.')
        title = sentences[0].strip()
        return title[:50] + "..." if len(title) > 50 else title
    
    def _extract_task_title(self, content: str) -> str:
        """Extract task title from content."""
        # Remove common task prefixes
        cleaned = re.sub(r'^(I need to|I should|I must|Task:|TODO:)\s*', '', content, flags=re.IGNORECASE)
        return self._extract_title_from_content(cleaned)
    
    def _extract_reminder_title(self, content: str) -> str:
        """Extract reminder title from content."""
        # Remove reminder prefixes
        cleaned = re.sub(r'^(Remind me to|Remember to|Don\'t forget to)\s*', '', content, flags=re.IGNORECASE)
        return self._extract_title_from_content(cleaned)
    
    def _extract_due_date(self, content: str) -> Optional[datetime]:
        """Extract due date from content using simple patterns."""
        # This is a basic implementation - can be enhanced with NLP libraries
        today = datetime.now(timezone.utc)
        
        if 'tomorrow' in content.lower():
            return today.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
        elif 'today' in content.lower():
            return today.replace(hour=17, minute=0, second=0, microsecond=0)
        
        # Look for time patterns like "at 3pm", "at 15:00"
        time_pattern = r'at (\d{1,2}):?(\d{0,2})\s*(pm|am)?'
        match = re.search(time_pattern, content.lower())
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2) or 0)
            ampm = match.group(3)
            
            if ampm == 'pm' and hour != 12:
                hour += 12
            elif ampm == 'am' and hour == 12:
                hour = 0
            
            return today.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        return None
    
    def _extract_priority(self, content: str) -> str:
        """Extract priority from content."""
        content_lower = content.lower()
        if any(word in content_lower for word in ['urgent', 'asap', 'critical', 'high priority']):
            return 'high'
        elif any(word in content_lower for word in ['low priority', 'when possible', 'someday']):
            return 'low'
        return 'medium'
    
    def _extract_tags_from_content(self, content: str) -> List[str]:
        """Extract tags from content."""
        tags = []
        
        # Look for hashtags
        hashtag_pattern = r'#(\w+)'
        hashtags = re.findall(hashtag_pattern, content)
        tags.extend(hashtags)
        
        # Add automatic tags based on keywords
        content_lower = content.lower()
        if any(word in content_lower for word in ['work', 'project', 'meeting']):
            tags.append('work')
        if any(word in content_lower for word in ['personal', 'family', 'home']):
            tags.append('personal')
        if any(word in content_lower for word in ['idea', 'brainstorm', 'concept']):
            tags.append('idea')
        
        return list(set(tags))  # Remove duplicates
    
    async def _extract_url_title(self, url: str) -> Optional[str]:
        """Extract title from URL with better handling for video sites."""
        try:
            # Special handling for YouTube
            if 'youtu.be' in url or 'youtube.com' in url:
                return await self._extract_youtube_title(url)
            
            # Special handling for Instagram
            if 'instagram.com' in url:
                return await self._extract_instagram_title(url)
            
            # General web scraping
            import httpx
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive'
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers, follow_redirects=True)
                
                if response.status_code == 200:
                    # Try to parse with BeautifulSoup
                    try:
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Try different title extraction methods
                        title = None
                        
                        # Method 1: Standard title tag
                        title_tag = soup.find('title')
                        if title_tag:
                            title = title_tag.get_text().strip()
                        
                        # Method 2: Open Graph title
                        if not title or len(title) < 3:
                            og_title = soup.find('meta', property='og:title')
                            if og_title:
                                title = og_title.get('content', '').strip()
                        
                        # Method 3: Twitter title
                        if not title or len(title) < 3:
                            twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
                            if twitter_title:
                                title = twitter_title.get('content', '').strip()
                        
                        if title and len(title) > 3:
                            # Clean up the title
                            title = title.replace('\n', ' ').replace('\r', ' ')
                            title = ' '.join(title.split())  # Remove extra whitespace
                            return title[:100]  # Limit length
                            
                    except ImportError:
                        logger.warning("BeautifulSoup not available, using simple parsing")
                        # Fallback: simple regex title extraction
                        import re
                        title_match = re.search(r'<title[^>]*>([^<]*)</title>', response.text, re.IGNORECASE)
                        if title_match:
                            title = title_match.group(1).strip()
                            if title and len(title) > 3:
                                return title[:100]
                        
        except Exception as e:
            logger.debug(f"Could not extract title from {url}: {e}")
        
        return self._extract_domain_from_url(url)
    
    async def _extract_youtube_title(self, url: str) -> Optional[str]:
        """Extract YouTube video title."""
        try:
            # Extract video ID from URL
            import re
            video_id = None
            
            # Handle different YouTube URL formats
            patterns = [
                r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
                r'youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    video_id = match.group(1)
                    break
            
            if video_id:
                # Try to get title using oembed API (doesn't require API key)
                import httpx
                oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
                
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(oembed_url)
                    if response.status_code == 200:
                        data = response.json()
                        title = data.get('title', '')
                        if title:
                            return title[:100]
                            
        except Exception as e:
            logger.debug(f"Could not extract YouTube title from {url}: {e}")
        
        return "YouTube Video"
    
    async def _extract_instagram_title(self, url: str) -> Optional[str]:
        """Extract Instagram post title/description."""
        try:
            # Instagram is very restrictive, so we'll try basic scraping
            import httpx
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url, headers=headers, follow_redirects=True)
                
                if response.status_code == 200:
                    try:
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Try to get Open Graph title
                        og_title = soup.find('meta', property='og:title')
                        if og_title:
                            title = og_title.get('content', '').strip()
                            if title and title != 'Instagram':
                                return title[:100]
                        
                        # Try to get description
                        og_desc = soup.find('meta', property='og:description')
                        if og_desc:
                            desc = og_desc.get('content', '').strip()
                            if desc and len(desc) > 10:
                                return desc[:100]
                                
                    except ImportError:
                        pass
                        
        except Exception as e:
            logger.debug(f"Could not extract Instagram title from {url}: {e}")
        
        return "Instagram Post"
    
    def _extract_domain_from_url(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path
            return domain.replace('www.', '')
        except:
            return url[:50]

# Global instance
content_handler = SupabaseContentHandler()
