#!/usr/bin/env python3
"""
🗂️ Session Manager for MySecondMind

Manages user session data including content ID mappings for privacy-friendly display.
Maps user-friendly sequential numbers (1,2,3,4) to actual database UUIDs.
"""

import logging
from typing import Dict, List, Optional
import time

logger = logging.getLogger(__name__)

class SessionManager:
    """Manages user sessions and content ID mappings."""
    
    def __init__(self):
        # Store user sessions: user_id -> session_data
        self.sessions = {}
        # Session timeout (30 minutes)
        self.session_timeout = 30 * 60
    
    def create_content_mapping(self, user_id: str, content_list: List[Dict]) -> Dict[int, str]:
        """
        Create a mapping from sequential numbers to actual content IDs.
        
        Args:
            user_id: User identifier
            content_list: List of content items with 'id' field
            
        Returns:
            Dict mapping display_number -> actual_uuid
        """
        try:
            # Create sequential mapping
            mapping = {}
            for i, content in enumerate(content_list, 1):
                mapping[i] = content.get('id')
            
            # Store in user session
            if user_id not in self.sessions:
                self.sessions[user_id] = {}
            
            self.sessions[user_id].update({
                'content_mapping': mapping,
                'last_activity': time.time(),
                'content_type': content_list[0].get('content_type', 'unknown') if content_list else 'unknown'
            })
            
            logger.info(f"✅ Created mapping for user {user_id}: {len(mapping)} items")
            return mapping
            
        except Exception as e:
            logger.error(f"❌ Error creating content mapping: {e}")
            return {}
    
    def get_actual_id(self, user_id: str, display_number: int) -> Optional[str]:
        """
        Get the actual UUID from a display number.
        
        Args:
            user_id: User identifier
            display_number: Sequential number shown to user (1,2,3,4)
            
        Returns:
            Actual UUID string or None if not found
        """
        try:
            # Check if session exists and is not expired
            if user_id not in self.sessions:
                return None
            
            session = self.sessions[user_id]
            
            # Check session timeout
            if time.time() - session.get('last_activity', 0) > self.session_timeout:
                del self.sessions[user_id]
                return None
            
            # Update activity
            session['last_activity'] = time.time()
            
            # Get actual ID
            mapping = session.get('content_mapping', {})
            return mapping.get(display_number)
            
        except Exception as e:
            logger.error(f"❌ Error getting actual ID: {e}")
            return None
    
    def clear_session(self, user_id: str):
        """Clear user session data."""
        try:
            if user_id in self.sessions:
                del self.sessions[user_id]
                logger.info(f"🗑️ Cleared session for user {user_id}")
        except Exception as e:
            logger.error(f"❌ Error clearing session: {e}")
    
    def get_session_info(self, user_id: str) -> Dict:
        """Get current session information for debugging."""
        try:
            session = self.sessions.get(user_id, {})
            return {
                'has_mapping': 'content_mapping' in session,
                'mapping_size': len(session.get('content_mapping', {})),
                'last_activity': session.get('last_activity'),
                'content_type': session.get('content_type')
            }
        except Exception as e:
            logger.error(f"❌ Error getting session info: {e}")
            return {}

# Global session manager instance
session_manager = SessionManager()
