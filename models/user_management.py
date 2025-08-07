#!/usr/bin/env python3
"""
👤 User Management System for MySecondMind

Handles user registration, authentication, and secure storage of user data
including encrypted Notion tokens and user preferences using Supabase.
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from supabase import create_client, Client

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from core.encryption import encrypt_user_token, decrypt_user_token

logger = logging.getLogger(__name__)

@dataclass
class User:
    """User data model."""
    user_id: str
    telegram_username: Optional[str]
    notion_token: Optional[str]  # This will be encrypted in storage
    db_notes: Optional[str]
    db_links: Optional[str] 
    db_reminders: Optional[str]
    created_at: datetime
    last_active: datetime
    is_active: bool = True

class UserManager:
    """Manages user data and database operations using Supabase."""
    
    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            logger.error("❌ SUPABASE_URL and SUPABASE_ANON_KEY environment variables are required")
            # Don't raise exception, just log error so bot can still start
            self.supabase = None
            return
        
        try:
            # Create Supabase client with minimal parameters to avoid version conflicts
            # Use only essential parameters to avoid proxy/auth issues
            self.supabase: Client = create_client(
                self.supabase_url, 
                self.supabase_key
            )
            logger.info("✅ Supabase client initialized successfully")
        except TypeError as e:
            if "proxy" in str(e):
                # Handle version conflict by using older client initialization
                logger.warning("⚠️ Using fallback Supabase client initialization")
                try:
                    import supabase
                    # Direct client creation without problematic parameters
                    self.supabase = supabase.Client(self.supabase_url, self.supabase_key)
                    logger.info("✅ Supabase client initialized with fallback method")
                except Exception as fallback_error:
                    logger.error(f"❌ Fallback Supabase initialization failed: {fallback_error}")
                    self.supabase = None
            else:
                logger.error(f"❌ Failed to initialize Supabase client: {e}")
                self.supabase = None
        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase client: {e}")
            self.supabase = None
    
    def register_user(self, user_id: str, notion_token: str, 
                     db_notes: str, db_links: str, db_reminders: str,
                     telegram_username: Optional[str] = None) -> bool:
        """Register a new user with their Notion workspace details."""
        if not self.supabase:
            logger.error("❌ Supabase client not initialized - cannot register user")
            return False
            
        try:
            # Encrypt the Notion token
            encrypted_token = encrypt_user_token(user_id, notion_token)
            
            user_data = {
                'user_id': user_id,
                'telegram_username': telegram_username,
                'encrypted_notion_token': encrypted_token,
                'db_notes': db_notes,
                'db_links': db_links,
                'db_reminders': db_reminders,
                'last_active': datetime.utcnow().isoformat(),
                'is_active': True
            }
            
            # Use upsert to handle both insert and update
            result = self.supabase.table('users').upsert(user_data, on_conflict='user_id').execute()
            
            if result.data:
                logger.info(f"✅ User {user_id} registered successfully")
                return True
            else:
                logger.error(f"❌ Failed to register user {user_id}: No data returned")
                return False
            
        except Exception as e:
            logger.error(f"❌ Failed to register user {user_id}: {e}")
            return False
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user data by user ID in format expected by notion_client."""
        try:
            result = self.supabase.table('users').select('*').eq('user_id', user_id).eq('is_active', True).execute()
            
            if not result.data:
                return None
            
            row = result.data[0]
            
            # Decrypt the Notion token
            decrypted_token = None
            if row.get('encrypted_notion_token'):
                decrypted_token = decrypt_user_token(user_id, row['encrypted_notion_token'])
            
            # Return in format expected by notion_client
            return {
                'user_id': row['user_id'],
                'telegram_username': row.get('telegram_username'),
                'notion_token': decrypted_token,
                'notion_databases': {
                    'notes': row.get('db_notes'),
                    'links': row.get('db_links'),
                    'reminders': row.get('db_reminders')
                },
                'created_at': row.get('created_at'),
                'last_active': row.get('last_active'),
                'is_active': bool(row.get('is_active', True))
            }
                
        except Exception as e:
            logger.error(f"❌ Failed to get user {user_id}: {e}")
            return None
    
    def update_last_active(self, user_id: str) -> bool:
        """Update user's last active timestamp."""
        try:
            result = self.supabase.table('users').update({
                'last_active': datetime.utcnow().isoformat()
            }).eq('user_id', user_id).execute()
            
            return bool(result.data)
                
        except Exception as e:
            logger.error(f"❌ Failed to update last active for user {user_id}: {e}")
            return False
    
    def is_user_registered(self, user_id: str) -> bool:
        """Check if a user is registered and has valid Notion token."""
        user = self.get_user(user_id)
        return user is not None and user.notion_token is not None
    
    def deactivate_user(self, user_id: str) -> bool:
        """Deactivate a user (soft delete)."""
        try:
            result = self.supabase.table('users').update({
                'is_active': False
            }).eq('user_id', user_id).execute()
            
            if result.data:
                logger.info(f"✅ User {user_id} deactivated")
                return True
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to deactivate user {user_id}: {e}")
            return False
    
    def get_all_active_users(self) -> List[User]:
        """Get all active users."""
        try:
            result = self.supabase.table('users').select('*').eq('is_active', True).order('last_active', desc=True).execute()
            
            users = []
            for row in result.data:
                decrypted_token = None
                if row.get('encrypted_notion_token'):
                    decrypted_token = decrypt_user_token(row['user_id'], row['encrypted_notion_token'])
                
                users.append(User(
                    user_id=row['user_id'],
                    telegram_username=row.get('telegram_username'),
                    notion_token=decrypted_token,
                    db_notes=row.get('db_notes'),
                    db_links=row.get('db_links'),
                    db_reminders=row.get('db_reminders'),
                    created_at=datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')) if row.get('created_at') else datetime.utcnow(),
                    last_active=datetime.fromisoformat(row['last_active'].replace('Z', '+00:00')) if row.get('last_active') else datetime.utcnow(),
                    is_active=bool(row.get('is_active', True))
                ))
            
            return users
                
        except Exception as e:
            logger.error(f"❌ Failed to get active users: {e}")
            return []
    
    def get_user_stats(self) -> Dict[str, Any]:
        """Get user statistics."""
        try:
            # Get total users
            total_result = self.supabase.table('users').select('user_id', count='exact').execute()
            total_users = total_result.count or 0
            
            # Get active users  
            active_result = self.supabase.table('users').select('user_id', count='exact').eq('is_active', True).execute()
            active_users = active_result.count or 0
            
            # Get registered users (those with tokens)
            registered_result = self.supabase.table('users').select('user_id', count='exact').not_.is_('encrypted_notion_token', 'null').execute()
            registered_users = registered_result.count or 0
            
            return {
                'total_users': total_users,
                'active_users': active_users, 
                'registered_users': registered_users
            }
                
        except Exception as e:
            logger.error(f"❌ Failed to get user stats: {e}")
            return {'total_users': 0, 'active_users': 0, 'registered_users': 0}

# Global user manager instance
user_manager = UserManager()
