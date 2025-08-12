#!/usr/bin/env python3
"""
⏰ Advanced Notification Scheduler for MySecondMind

This module provides intelligent notification scheduling:
- Time-based reminders and tasks
- Daily memory resurfacing
- Morning briefings with weather
- Random content sharing for knowledge retention
- Smart notification timing based on user preferences
"""

import os
import json
import logging
import asyncio
import random
from datetime import datetime, timezone, timedelta, time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# Check for scheduling dependencies
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.date import DateTrigger
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False
    logger.warning("APScheduler not available. Notification scheduling disabled.")

@dataclass
class NotificationTask:
    """Notification task data structure."""
    id: str
    user_id: str
    title: str
    message: str
    notification_type: str  # reminder, task, morning_brief, memory_resurface
    scheduled_time: datetime
    recurring_pattern: Optional[str] = None
    metadata: Dict = None
    is_active: bool = True
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class NotificationScheduler:
    """Advanced notification scheduler with multiple notification types."""
    
    def __init__(self):
        self.scheduler = None
        self.active_jobs = {}  # job_id -> job info
        self.weather_api_key = os.getenv('WEATHER_API_KEY')
        
        # Initialize scheduler if available
        if SCHEDULER_AVAILABLE:
            try:
                # Check if we're in an async context
                try:
                    loop = asyncio.get_running_loop()
                    # We're in an async context, defer scheduler initialization
                    self.scheduler = None
                    logger.info("✅ Notification scheduler will be initialized on first use (async context)")
                except RuntimeError:
                    # No running loop, safe to initialize now
                    self.scheduler = AsyncIOScheduler()
                    self.scheduler.start()
                    logger.info("✅ Notification scheduler initialized")
                    
                    # Schedule periodic tasks
                    self._schedule_periodic_tasks()
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize scheduler: {e}")
                self.scheduler = None
        else:
            logger.warning("⚠️ Scheduler not available. Notifications will be processed manually.")
    
    async def _ensure_scheduler_initialized(self):
        """Ensure scheduler is initialized (for async contexts)."""
        if not self.scheduler and SCHEDULER_AVAILABLE:
            try:
                self.scheduler = AsyncIOScheduler()
                self.scheduler.start()
                logger.info("✅ Notification scheduler initialized (deferred)")
                
                # Schedule periodic tasks
                self._schedule_periodic_tasks()
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize deferred scheduler: {e}")
                self.scheduler = None
    
    def _schedule_periodic_tasks(self):
        """Schedule recurring system tasks."""
        if not self.scheduler:
            return
        
        try:
            # Check for pending notifications every minute
            self.scheduler.add_job(
                self._process_pending_notifications,
                IntervalTrigger(minutes=1),
                id='process_notifications',
                max_instances=1
            )
            
            # Generate morning briefings at 8 AM daily
            self.scheduler.add_job(
                self._generate_morning_briefings,
                CronTrigger(hour=8, minute=0),
                id='morning_briefings',
                max_instances=1
            )
            
            # Generate evening summaries at 8 PM daily
            self.scheduler.add_job(
                self._generate_evening_summaries,
                CronTrigger(hour=20, minute=0),
                id='evening_summaries',
                max_instances=1
            )
            
            # Random memory resurfacing throughout the day
            self.scheduler.add_job(
                self._resurface_random_memories,
                IntervalTrigger(hours=6),  # Every 6 hours
                id='memory_resurfacing',
                max_instances=1
            )
            
            logger.info("📅 Periodic tasks scheduled")
            
        except Exception as e:
            logger.error(f"Error scheduling periodic tasks: {e}")
    
    async def schedule_notification(self, notification: NotificationTask) -> bool:
        """Schedule a notification."""
        # Ensure scheduler is initialized
        await self._ensure_scheduler_initialized()
        
        if not self.scheduler:
            return await self._manual_schedule(notification)
        
        try:
            job_id = f"notification_{notification.id}"
            
            # Create trigger based on notification type
            if notification.recurring_pattern:
                trigger = self._create_recurring_trigger(notification.scheduled_time, notification.recurring_pattern)
            else:
                trigger = DateTrigger(run_date=notification.scheduled_time)
            
            # Schedule the job
            self.scheduler.add_job(
                self._send_notification,
                trigger,
                args=[notification],
                id=job_id,
                max_instances=1,
                replace_existing=True
            )
            
            # Store job info
            self.active_jobs[job_id] = {
                'notification_id': notification.id,
                'user_id': notification.user_id,
                'type': notification.notification_type,
                'scheduled_time': notification.scheduled_time
            }
            
            logger.info(f"📅 Scheduled {notification.notification_type} for user {notification.user_id} at {notification.scheduled_time}")
            return True
            
        except Exception as e:
            logger.error(f"Error scheduling notification: {e}")
            return False
    
    def _create_recurring_trigger(self, base_time: datetime, pattern: str):
        """Create recurring trigger based on pattern."""
        if pattern == 'daily':
            return CronTrigger(hour=base_time.hour, minute=base_time.minute)
        elif pattern == 'weekly':
            return CronTrigger(day_of_week=base_time.weekday(), hour=base_time.hour, minute=base_time.minute)
        elif pattern == 'monthly':
            return CronTrigger(day=base_time.day, hour=base_time.hour, minute=base_time.minute)
        elif pattern.startswith('every_'):
            # Handle patterns like "every_2_hours", "every_3_days"
            parts = pattern.split('_')
            if len(parts) >= 3:
                interval = int(parts[1])
                unit = parts[2]
                
                if unit == 'minutes':
                    return IntervalTrigger(minutes=interval)
                elif unit == 'hours':
                    return IntervalTrigger(hours=interval)
                elif unit == 'days':
                    return IntervalTrigger(days=interval)
        
        # Default to one-time trigger
        return DateTrigger(run_date=base_time)
    
    async def _send_notification(self, notification: NotificationTask):
        """Send a notification to the user."""
        try:
            # Format the notification message
            formatted_message = await self._format_notification_message(notification)
            
            # Send via Telegram directly (avoid circular import)
            success = await self._send_telegram_message(notification.user_id, formatted_message)
            
            if success:
                logger.info(f"✅ Sent {notification.notification_type} to user {notification.user_id}")
                
                # Mark as sent in database
                await self._mark_notification_sent(notification.id)
                
                # Handle recurring notifications
                if not notification.recurring_pattern:
                    # Remove one-time notifications from active jobs
                    job_id = f"notification_{notification.id}"
                    if job_id in self.active_jobs:
                        del self.active_jobs[job_id]
            else:
                logger.error(f"❌ Failed to send notification to user {notification.user_id}")
                
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
    
    async def _send_telegram_message(self, chat_id: str, text: str, parse_mode: str = None) -> bool:
        """Send a message to Telegram chat (avoiding circular import)."""
        try:
            import httpx
            import os
            
            telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
            if not telegram_token:
                logger.error("❌ TELEGRAM_BOT_TOKEN not found")
                return False
            
            api_url = f"https://api.telegram.org/bot{telegram_token}"
            
            async with httpx.AsyncClient() as client:
                payload = {
                    "chat_id": chat_id,
                    "text": text
                }
                if parse_mode:
                    payload["parse_mode"] = parse_mode
                    
                response = await client.post(f"{api_url}/sendMessage", json=payload)
                
                if response.status_code == 200:
                    logger.info(f"📤 Telegram message sent successfully to {chat_id}")
                    return True
                else:
                    logger.error(f"❌ Telegram API error: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Error sending Telegram message: {e}")
            return False
    
    async def _format_notification_message(self, notification: NotificationTask) -> str:
        """Format notification message based on type."""
        
        if notification.notification_type == 'reminder':
            return f"⏰ **Reminder**\n\n{notification.message}\n\n_Set for {notification.scheduled_time.strftime('%I:%M %p')}_"
        
        elif notification.notification_type == 'task':
            return f"📋 **Task Due**\n\n{notification.message}\n\n_Use /complete to mark as done_"
        
        elif notification.notification_type == 'morning_brief':
            return notification.message  # Already formatted
        
        elif notification.notification_type == 'memory_resurface':
            return f"🧠 **Memory from your Second Brain**\n\n{notification.message}\n\n_Originally saved on {notification.metadata.get('original_date', 'unknown date')}_"
        
        else:
            return f"🔔 **Notification**\n\n{notification.message}"
    
    async def _process_pending_notifications(self):
        """Process notifications that should be sent (backup for manual mode)."""
        try:
            logger.info("🔍 Checking for pending notifications...")
            
            # Get pending notifications from database
            pending = await self._get_pending_notifications()
            
            if not pending:
                logger.info("📭 No pending notifications to process")
                return
            
            logger.info(f"📬 Processing {len(pending)} pending notifications")
            
            for notification_data in pending:
                try:
                    notification = NotificationTask(**notification_data)
                    logger.info(f"📤 Sending notification {notification.id} to user {notification.user_id}")
                    await self._send_notification(notification)
                except Exception as e:
                    logger.error(f"❌ Failed to process notification {notification_data.get('id', 'unknown')}: {e}")
                
        except Exception as e:
            logger.error(f"❌ Error processing pending notifications: {e}")
    
    async def _generate_morning_briefings(self):
        """Generate morning briefings for all active users."""
        try:
            logger.info("🌅 Generating morning briefings...")
            
            # Get all users who want morning briefings
            users = await self._get_users_with_morning_briefings()
            
            for user_data in users:
                user_id = user_data['user_id']
                timezone = user_data.get('timezone', 'UTC')
                brief_time = user_data.get('morning_brief_time', '08:00')
                
                # Generate personalized morning brief
                brief_message = await self._create_morning_brief(user_id, timezone)
                
                # Create notification
                notification = NotificationTask(
                    id=f"morning_{user_id}_{datetime.now().strftime('%Y%m%d')}",
                    user_id=str(user_id),
                    title="Good Morning!",
                    message=brief_message,
                    notification_type='morning_brief',
                    scheduled_time=datetime.now(timezone=timezone.utc)
                )
                
                await self._send_notification(notification)
                
        except Exception as e:
            logger.error(f"Error generating morning briefings: {e}")
    
    async def _create_morning_brief(self, user_id: str, user_timezone: str) -> str:
        """Create personalized morning briefing."""
        try:
            brief_parts = ["🌅 **Good Morning!**\n"]
            
            # Add weather if API key is available
            weather_info = await self._get_weather_info(user_timezone)
            if weather_info:
                brief_parts.append(f"🌤️ **Weather**: {weather_info}\n")
            
            # Add task summary
            task_summary = await self._get_task_summary(user_id)
            if task_summary:
                brief_parts.append(f"📋 **Today's Tasks**: {task_summary}\n")
            
            # Add recent content summary
            content_summary = await self._get_recent_content_summary(user_id)
            if content_summary:
                brief_parts.append(f"📚 **Recent Saves**: {content_summary}\n")
            
            # Add motivational message
            motivational_messages = [
                "💪 You've got this! Make today count!",
                "🎯 Focus on what matters most today!",
                "✨ Every small step counts towards your goals!",
                "🚀 Ready to tackle today's challenges!",
                "🌟 Make today better than yesterday!"
            ]
            brief_parts.append(random.choice(motivational_messages))
            
            return "\n".join(brief_parts)
            
        except Exception as e:
            logger.error(f"Error creating morning brief: {e}")
            return "🌅 Good Morning! Hope you have a great day ahead!"
    
    async def _get_weather_info(self, timezone: str) -> Optional[str]:
        """Get weather information (if API key is available)."""
        if not self.weather_api_key:
            return None
        
        try:
            # This would integrate with a weather API like OpenWeatherMap
            # For now, return a placeholder
            return "Sunny, 22°C (Perfect day to be productive!)"
        except Exception as e:
            logger.error(f"Error getting weather: {e}")
            return None
    
    async def _generate_evening_summaries(self):
        """Generate evening summaries for all active users."""
        try:
            logger.info("🌙 Generating evening summaries...")
            
            # Get all users who want evening summaries
            users = await self._get_users_with_evening_summaries()
            
            for user_data in users:
                user_id = user_data['user_id']
                
                # Generate daily summary
                summary_message = await self._create_evening_summary(user_id)
                
                # Create notification
                notification = NotificationTask(
                    id=f"evening_{user_id}_{datetime.now().strftime('%Y%m%d')}",
                    user_id=str(user_id),
                    title="Daily Summary",
                    message=summary_message,
                    notification_type='evening_summary',
                    scheduled_time=datetime.now(timezone.utc)
                )
                
                await self._send_notification(notification)
                
        except Exception as e:
            logger.error(f"Error generating evening summaries: {e}")
    
    async def _create_evening_summary(self, user_id: str) -> str:
        """Create daily summary of user's activity."""
        try:
            summary_parts = ["🌙 **Daily Summary**\n"]
            
            # Get today's activity
            today_activity = await self._get_today_activity(user_id)
            
            if today_activity.get('saves', 0) > 0:
                summary_parts.append(f"📝 You saved {today_activity['saves']} items today")
            
            if today_activity.get('completed_tasks', 0) > 0:
                summary_parts.append(f"✅ Completed {today_activity['completed_tasks']} tasks")
            
            if today_activity.get('searches', 0) > 0:
                summary_parts.append(f"🔍 Performed {today_activity['searches']} searches")
            
            # Add brief content highlights
            highlights = await self._get_content_highlights(user_id)
            if highlights:
                summary_parts.append(f"\n💡 **Today's Highlights**:\n{highlights}")
            
            summary_parts.append("\n🎯 Ready for tomorrow? Set some goals for a productive day ahead!")
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            logger.error(f"Error creating evening summary: {e}")
            return "🌙 Hope you had a productive day! Rest well for tomorrow."
    
    async def _resurface_random_memories(self):
        """Resurface random memories for knowledge retention."""
        try:
            logger.info("🧠 Resurfacing random memories...")
            
            # Get all active users
            users = await self._get_active_users()
            
            for user_data in users:
                user_id = user_data['user_id']
                frequency = user_data.get('memory_resurface_frequency', 'weekly')
                
                # Check if user should get memory resurfacing today
                if await self._should_resurface_memory(user_id, frequency):
                    # Get a random piece of old content
                    memory_content = await self._get_random_memory(user_id)
                    
                    if memory_content:
                        # Create resurfacing notification
                        notification = NotificationTask(
                            id=f"memory_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M')}",
                            user_id=str(user_id),
                            title="Memory from your Second Brain",
                            message=await self._format_memory_resurface(memory_content),
                            notification_type='memory_resurface',
                            scheduled_time=datetime.now(timezone.utc),
                            metadata={'original_date': memory_content.get('created_at')}
                        )
                        
                        await self._send_notification(notification)
                
        except Exception as e:
            logger.error(f"Error resurfacing memories: {e}")
    
    async def _format_memory_resurface(self, content: Dict) -> str:
        """Format memory resurfacing message."""
        content_type = content.get('content_type', 'item')
        title = content.get('title', 'Untitled')
        snippet = content.get('content', '')[:200]
        
        emoji_map = {
            'note': '📝',
            'task': '📋',
            'link': '🔗',
            'reminder': '⏰'
        }
        
        emoji = emoji_map.get(content_type, '📄')
        
        message = f"{emoji} **{title}**\n\n{snippet}"
        
        if len(snippet) >= 200:
            message += "..."
        
        message += f"\n\n_This {content_type} might be worth revisiting!_"
        
        return message
    
    # Database interaction methods (to be implemented)
    async def _get_pending_notifications(self) -> List[Dict]:
        """Get pending notifications from database."""
        try:
            from core.supabase_rest import supabase_rest
            from datetime import datetime, timezone
            
            # Get current time in UTC
            now = datetime.now(timezone.utc)
            
            # Query for notifications that should be sent now
            response = supabase_rest.table('notifications').select().eq('status', 'pending').execute()
            
            if response.get('success') and response.get('data'):
                logger.info(f"🔍 Found {len(response['data'])} pending notifications")
                return response['data']
            else:
                logger.debug("🔍 No pending notifications found")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error getting pending notifications: {e}")
            return []
    
    async def _mark_notification_sent(self, notification_id: str):
        """Mark notification as sent in database."""
        try:
            from core.supabase_rest import supabase_rest
            from datetime import datetime, timezone
            
            # Update notification status to 'sent'
            response = supabase_rest.table('notifications').update({
                'status': 'sent',
                'sent_at': datetime.now(timezone.utc).isoformat()
            }).eq('id', notification_id).execute()
            
            if response.get('success'):
                logger.info(f"✅ Marked notification {notification_id} as sent")
            else:
                logger.error(f"❌ Failed to mark notification {notification_id} as sent")
                
        except Exception as e:
            logger.error(f"❌ Error marking notification as sent: {e}")
    
    async def _get_users_with_morning_briefings(self) -> List[Dict]:
        """Get users who want morning briefings."""
        # This would query user preferences
        return []
    
    async def _get_users_with_evening_summaries(self) -> List[Dict]:
        """Get users who want evening summaries."""
        # This would query user preferences
        return []
    
    async def _get_active_users(self) -> List[Dict]:
        """Get all active users."""
        # This would query the users table
        return []
    
    async def _get_task_summary(self, user_id: str) -> Optional[str]:
        """Get summary of user's tasks."""
        # This would query user's tasks
        return None
    
    async def _get_recent_content_summary(self, user_id: str) -> Optional[str]:
        """Get summary of recent content."""
        # This would query recent user content
        return None
    
    async def _get_today_activity(self, user_id: str) -> Dict:
        """Get today's activity summary."""
        # This would query usage analytics
        return {'saves': 0, 'completed_tasks': 0, 'searches': 0}
    
    async def _get_content_highlights(self, user_id: str) -> Optional[str]:
        """Get content highlights for the day."""
        # This would analyze today's content
        return None
    
    async def _should_resurface_memory(self, user_id: str, frequency: str) -> bool:
        """Check if user should get memory resurfacing."""
        # This would check resurfacing log and frequency
        return random.random() < 0.3  # 30% chance for demo
    
    async def _get_random_memory(self, user_id: str) -> Optional[Dict]:
        """Get a random old piece of content."""
        # This would query old content with spaced repetition logic
        return None
    
    async def _manual_schedule(self, notification: NotificationTask) -> bool:
        """Manual scheduling when APScheduler is not available."""
        # Store in database for manual processing
        logger.info(f"📝 Manually scheduled {notification.notification_type} for user {notification.user_id}")
        return True
    
    def cancel_notification(self, notification_id: str) -> bool:
        """Cancel a scheduled notification."""
        if not self.scheduler:
            return True  # In manual mode, just mark as cancelled in DB
        
        try:
            job_id = f"notification_{notification_id}"
            if job_id in self.active_jobs:
                self.scheduler.remove_job(job_id)
                del self.active_jobs[job_id]
                logger.info(f"❌ Cancelled notification {notification_id}")
                return True
        except Exception as e:
            logger.error(f"Error cancelling notification: {e}")
        
        return False
    
    def get_scheduled_notifications(self, user_id: str) -> List[Dict]:
        """Get user's scheduled notifications."""
        user_jobs = []
        for job_id, job_info in self.active_jobs.items():
            if job_info['user_id'] == user_id:
                user_jobs.append({
                    'id': job_info['notification_id'],
                    'type': job_info['type'],
                    'scheduled_time': job_info['scheduled_time']
                })
        return user_jobs

# Global notification scheduler
notification_scheduler = None

def get_notification_scheduler() -> NotificationScheduler:
    """Get global notification scheduler instance."""
    global notification_scheduler
    if notification_scheduler is None:
        notification_scheduler = NotificationScheduler()
    return notification_scheduler

async def schedule_reminder(user_id: str, title: str, message: str, scheduled_time: datetime, recurring: Optional[str] = None) -> bool:
    """Schedule a reminder notification."""
    scheduler = get_notification_scheduler()
    
    notification = NotificationTask(
        id=f"reminder_{user_id}_{int(scheduled_time.timestamp())}",
        user_id=user_id,
        title=title,
        message=message,
        notification_type='reminder',
        scheduled_time=scheduled_time,
        recurring_pattern=recurring
    )
    
    return await scheduler.schedule_notification(notification)

async def schedule_task_reminder(user_id: str, task_title: str, due_time: datetime) -> bool:
    """Schedule a task due reminder."""
    scheduler = get_notification_scheduler()
    
    notification = NotificationTask(
        id=f"task_{user_id}_{int(due_time.timestamp())}",
        user_id=user_id,
        title=f"Task Due: {task_title}",
        message=f"Your task '{task_title}' is due now!",
        notification_type='task',
        scheduled_time=due_time
    )
    
    return await scheduler.schedule_notification(notification)
