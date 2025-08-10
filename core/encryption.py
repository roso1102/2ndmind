#!/usr/bin/env python3
"""
🔐 Encryption Module for MySecondMind

Handles secure encryption/decryption of user tokens using Fernet encryption.
Each user gets a unique encryption key for their sensitive data.
"""

import os
import base64
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional

logger = logging.getLogger(__name__)

class UserEncryption:
    """Handles per-user encryption for sensitive data like Notion tokens."""
    
    def __init__(self):
        # Master encryption key from environment
        self.master_key = self._get_or_create_master_key()
        
    def _get_or_create_master_key(self) -> bytes:
        """Get master encryption key from environment or create one."""
        master_key_b64 = os.getenv('ENCRYPTION_MASTER_KEY')
        
        if master_key_b64:
            try:
                decoded_key = base64.urlsafe_b64decode(master_key_b64)
                logger.info("✅ Using existing master encryption key from environment")
                return decoded_key
            except Exception as e:
                logger.error(f"❌ Invalid master key in environment: {e}")
                logger.error("🔧 Please check your ENCRYPTION_MASTER_KEY environment variable")
                
        # Only generate new key if absolutely necessary
        logger.error("❌ CRITICAL: No valid ENCRYPTION_MASTER_KEY found in environment!")
        logger.error("🚨 This will break encryption for existing users!")
        
        # Generate new master key as last resort
        master_key = Fernet.generate_key()
        master_key_b64 = base64.urlsafe_b64encode(master_key).decode()
        
        logger.warning("🔑 Generated new master encryption key")
        logger.warning(f"🔑 Add this to your Render environment variables: ENCRYPTION_MASTER_KEY={master_key_b64}")
        logger.warning("🔑 Also add to your .env file: ENCRYPTION_MASTER_KEY={master_key_b64}")
        
        return master_key
    
    def _derive_user_key(self, user_id: str) -> Fernet:
        """Derive a unique encryption key for a specific user."""
        # Use user_id as salt for key derivation
        salt = str(user_id).encode('utf-8').ljust(16, b'0')[:16]
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
        return Fernet(key)
    
    def encrypt_token(self, user_id: str, token: str) -> str:
        """Encrypt a token for a specific user."""
        try:
            fernet = self._derive_user_key(user_id)
            encrypted_token = fernet.encrypt(token.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted_token).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to encrypt token for user {user_id}: {e}")
            raise
    
    def decrypt_token(self, user_id: str, encrypted_token: str) -> Optional[str]:
        """Decrypt a token for a specific user."""
        try:
            fernet = self._derive_user_key(user_id)
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_token.encode('utf-8'))
            decrypted_token = fernet.decrypt(encrypted_bytes)
            return decrypted_token.decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to decrypt token for user {user_id}: {e}")
            return None
    
    def test_encryption(self, user_id: str, test_data: str = "test_token_123") -> bool:
        """Test encryption/decryption for a user."""
        try:
            encrypted = self.encrypt_token(user_id, test_data)
            decrypted = self.decrypt_token(user_id, encrypted)
            return decrypted == test_data
        except Exception as e:
            logger.error(f"Encryption test failed for user {user_id}: {e}")
            return False

# Global encryption instance
encryption = UserEncryption()

def encrypt_user_token(user_id: str, token: str) -> str:
    """Convenience function to encrypt a user token."""
    return encryption.encrypt_token(user_id, token)

def decrypt_user_token(user_id: str, encrypted_token: str) -> Optional[str]:
    """Convenience function to decrypt a user token."""
    return encryption.decrypt_token(user_id, encrypted_token)

def test_user_encryption(user_id: str) -> bool:
    """Convenience function to test encryption for a user."""
    return encryption.test_encryption(user_id)
