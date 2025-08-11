#!/usr/bin/env python3
"""
🧪 Test notification system
"""

import asyncio
from datetime import datetime, timezone, timedelta
from core.notification_scheduler import NotificationTask, schedule_reminder

async def test_notification():
    """Test if notifications work"""
    
    # Create a test notification for 1 minute from now
    test_time = datetime.now(timezone.utc) + timedelta(minutes=1)
    
    print(f"⏰ Scheduling test notification for: {test_time}")
    
    success = await schedule_reminder(
        user_id="5948684459",  # Your user ID
        title="Test Notification",
        message="This is a test notification from your bot!",
        scheduled_time=test_time
    )
    
    print(f"✅ Notification scheduled: {success}")
    
    # Keep the script running for 2 minutes to see if it triggers
    print("⏳ Waiting 2 minutes to see if notification is sent...")
    await asyncio.sleep(120)
    
    print("🏁 Test completed")

if __name__ == "__main__":
    asyncio.run(test_notification())
