"""
🔗 Notion Router for MySecondMind

Handles per-user Notion client routing and authentication.
"""

import os
import json
import logging
from cryptography.fernet import Fernet
from notion_client import Client as NotionClient

logger = logging.getLogger(__name__)

# Initialize encryption
FERNET_KEY = os.getenv("FERNET_KEY")
if FERNET_KEY:
    fernet = Fernet(FERNET_KEY.encode())
else:
    logger.warning("FERNET_KEY not set!")
    fernet = None

def get_notion_client(user_id: str):
    """Get Notion client and user data for a specific user."""
    if not fernet:
        raise Exception("Encryption not configured")
    
    path = "data/user_data.json.enc"
    
    if not os.path.exists(path):
        raise Exception("No users registered yet")
    
    try:
        with open(path, "rb") as f:
            decrypted = json.loads(fernet.decrypt(f.read()))
    except Exception as e:
        raise Exception(f"Could not decrypt user data: {e}")
    
    user = decrypted.get(str(user_id))
    if not user:
        raise Exception("User not registered")
    
    # Create Notion client
    notion = NotionClient(auth=user['token'])
    
    return notion, user

def get_all_user_ids():
    """Get list of all registered user IDs."""
    if not fernet:
        return []
    
    path = "data/user_data.json.enc"
    
    if not os.path.exists(path):
        return []
    
    try:
        with open(path, "rb") as f:
            decrypted = json.loads(fernet.decrypt(f.read()))
        return list(decrypted.keys())
    except Exception as e:
        logger.error(f"Could not load user IDs: {e}")
        return []
