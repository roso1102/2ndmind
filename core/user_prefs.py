#!/usr/bin/env python3
"""
🛠️ User Preferences (Timezone)

Simple helpers to get/set a user's timezone in Supabase. Falls back to Asia/Kolkata.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_TZ = "Asia/Kolkata"

def _validate_timezone(tz_name: str) -> bool:
    try:
        import pytz
        _ = pytz.timezone(tz_name)
        return True
    except Exception:
        return False

def get_user_timezone(user_id: str) -> str:
    """Fetch user's timezone from Supabase; return default if missing/invalid."""
    try:
        from core.supabase_rest import supabase_rest
        res = supabase_rest.table('user_preferences').select('*').eq('user_id', user_id).limit(1).execute()
        if res and res.get('error') is None and res.get('data'):
            tz = res['data'][0].get('timezone')
            if tz and _validate_timezone(tz):
                return tz
    except Exception as e:
        logger.warning(f"get_user_timezone failed: {e}")
    return DEFAULT_TZ

def set_user_timezone(user_id: str, tz_name: str) -> bool:
    """Upsert user's timezone. Returns True on success."""
    if not _validate_timezone(tz_name):
        return False
    try:
        from core.supabase_rest import supabase_rest
        # Check if exists
        existing = supabase_rest.table('user_preferences').select('*').eq('user_id', user_id).limit(1).execute()
        if existing and existing.get('error') is None and existing.get('data'):
            # Update
            upd = supabase_rest.table('user_preferences').update({'timezone': tz_name}).eq('user_id', user_id).execute()
            return upd and upd.get('error') is None
        else:
            # Insert
            ins = supabase_rest.table('user_preferences').insert({'user_id': user_id, 'timezone': tz_name}).execute()
            return ins and ins.get('error') is None
    except Exception as e:
        logger.error(f"set_user_timezone failed: {e}")
        return False


