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
from typing import Dict, List, Optional, Any, Tuple, Set
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
        # In-memory precise timers for near-term notifications
        self._in_memory_timers: Dict[str, asyncio.Task] = {}
        # In-process lock to prevent duplicate sends (poller vs precise timer)
        self._sending_ids: Set[str] = set()
        
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
                    # No running loop yet; defer initialization until first async use
                    self.scheduler = None
                    logger.info("⏳ Notification scheduler will initialize after event loop starts")
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize scheduler: {e}")
                self.scheduler = None
        else:
            logger.warning("⚠️ Scheduler not available. Notifications will be processed manually.")

    async def run_background_poller(self, poll_interval_seconds: int = 15, grace_seconds: int = 2):
        """Run a lightweight background poller inside FastAPI's event loop.
        - Polls DB periodically for due notifications (<= now + grace)
        - Sends them via Telegram and marks as sent
        """
        logger.info(f"🛎️ Starting background poller (interval={poll_interval_seconds}s, grace={grace_seconds}s)")
        while True:
            try:
                now = datetime.now(timezone.utc)
                cutoff = now if grace_seconds <= 0 else (now + timedelta(seconds=grace_seconds))

                pending = await self._get_pending_notifications()
                # Filter by time window and optionally set precise timers
                ready: List[Dict] = []
                for n in pending:
                    try:
                        ts = n.get('scheduled_time')
                        if not ts:
                            continue
                        # Robust parse of ISO with or without Z
                        s = str(ts)
                        if s.endswith('Z'):
                            s = s.replace('Z', '+00:00')
                        scheduled_dt = datetime.fromisoformat(s)
                        if scheduled_dt <= cutoff:
                            ready.append(n)
                        else:
                            # Schedule precise near-term timer for better accuracy (<= 120s)
                            dt_seconds = (scheduled_dt - now).total_seconds()
                            if 0 < dt_seconds <= 120:
                                notif = NotificationTask(
                                    id=str(n.get('id')),
                                    user_id=str(n.get('user_id')),
                                    title=n.get('title', 'Reminder'),
                                    message=n.get('message', ''),
                                    notification_type=n.get('notification_type', 'reminder'),
                                    scheduled_time=scheduled_dt,
                                    recurring_pattern=n.get('recurring_pattern'),
                                    metadata=n.get('metadata') or {}
                                )
                                await self._ensure_precise_timer(notif, dt_seconds)
                    except Exception as e:
                        logger.warning(f"⚠️ Poller time parse error: {e}")

                if ready:
                    logger.info(f"📬 Poller sending {len(ready)} due notifications (now={now.isoformat()}, grace={grace_seconds}s)")
                else:
                    logger.debug("⌛ Poller found no due notifications in window")
                for n in ready:
                    try:
                        notif = NotificationTask(
                            id=str(n.get('id')),
                            user_id=str(n.get('user_id')),
                            title=n.get('title', 'Reminder'),
                            message=n.get('message', ''),
                            notification_type=n.get('notification_type', 'reminder'),
                            scheduled_time=datetime.fromisoformat(str(n.get('scheduled_time')).replace('Z', '+00:00')),
                            recurring_pattern=n.get('recurring_pattern'),
                            metadata=n.get('metadata') or {}
                        )
                        logger.info(f"📤 Poller attempting send for notification {notif.id} (user {notif.user_id})")
                        await self._send_notification(notif)
                    except Exception as e:
                        logger.error(f"❌ Poller failed sending notification {n.get('id')}: {e}")

            except Exception as loop_err:
                logger.error(f"❌ Background poller loop error: {loop_err}")
            finally:
                await asyncio.sleep(max(1, poll_interval_seconds))

    async def _ensure_precise_timer(self, notification: NotificationTask, seconds_until_fire: float):
        """Create an in-memory precise timer for near-term notifications (<= 120s)."""
        if notification.id in self._in_memory_timers:
            return
        async def _fire():
            try:
                await asyncio.sleep(max(0.0, seconds_until_fire))
                # Double-check not already sent in DB
                try:
                    from core.supabase_rest import supabase_rest
                    res = supabase_rest.table('notifications').select().eq('id', notification.id).execute()
                    if res and res.get('error') is None and res.get('data'):
                        row = res['data'][0]
                        if row.get('is_sent') is True:
                            return
                except Exception:
                    pass
                await self._send_notification(notification)
            finally:
                self._in_memory_timers.pop(notification.id, None)
        task = asyncio.create_task(_fire())
        self._in_memory_timers[notification.id] = task
    
    async def _ensure_scheduler_initialized(self):
        """Ensure scheduler is initialized (for async contexts)."""
        if not self.scheduler and SCHEDULER_AVAILABLE:
            try:
                # Ensure an event loop exists
                try:
                    asyncio.get_running_loop()
                except RuntimeError:
                    # Still no loop; do not force-create here. Defer init.
                    logger.info("⏳ Deferring scheduler init until loop is running")
                    return
                
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
            # Disabled: periodic pending processor to avoid early sends.
            # If re-enabled, ensure due-only guard inside the method.
            
            # Check morning/evening windows every 5 minutes in Asia/Kolkata timezone
            self.scheduler.add_job(
                self._generate_morning_briefings,
                CronTrigger(minute='*/5', timezone='Asia/Kolkata'),
                id='morning_briefings',
                max_instances=1
            )
            self.scheduler.add_job(
                self._generate_evening_summaries,
                CronTrigger(minute='*/5', timezone='Asia/Kolkata'),
                id='evening_summaries',
                max_instances=1
            )
            
            # Random memory resurfacing throughout the day (Asia/Kolkata clock)
            self.scheduler.add_job(
                self._resurface_random_memories,
                IntervalTrigger(hours=6, timezone='Asia/Kolkata'),  # Every 6 hours
                id='memory_resurfacing',
                max_instances=1
            )
            
            logger.info("📅 Periodic tasks scheduled")
            
        except Exception as e:
            logger.error(f"Error scheduling periodic tasks: {e}")
    
    async def schedule_notification(self, notification: NotificationTask) -> bool:
        """Schedule a notification."""
        # CRITICAL: Always save to database first for persistence
        logger.info(f"🔍 DEBUG: Attempting to save notification {notification.id} to database")
        db_saved = await self._save_notification_to_db(notification)
        if not db_saved:
            logger.error(f"❌ Failed to save notification {notification.id} to database - aborting")
            return False
        
        logger.info(f"✅ Successfully saved notification {notification.id} to database")
        
        # Ensure scheduler is initialized
        # Initialize scheduler only if needed; do not crash if loop not ready
        try:
            await self._ensure_scheduler_initialized()
        except Exception as e:
            logger.warning(f"⚠️ Scheduler init skipped (will rely on DB polling): {e}")
        
        # Do NOT add per-notification APScheduler date jobs to avoid duplicates.
        # Delivery is handled by the background poller (and precise in-memory timers below).
        logger.info("📝 Notification saved; delivery handled by poller/precise timers (no APScheduler date job)")

        # Optional: precise near-term timer for sub-minute accuracy
        try:
            now = datetime.now(timezone.utc)
            delta = (notification.scheduled_time - now).total_seconds()
            if 0 < delta <= 120:
                await self._ensure_precise_timer(notification, delta)
        except Exception as e:
            logger.warning(f"⚠️ Could not set precise timer: {e}")

        return True
    
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
            # In-process idempotency guard
            if notification.id in self._sending_ids:
                return
            self._sending_ids.add(notification.id)
            
            # Ensure not already sent in DB (race guard)
            try:
                from core.supabase_rest import supabase_rest
                check = supabase_rest.table('notifications').select('*').eq('id', notification.id).limit(1).execute()
                if check and check.get('error') is None and check.get('data'):
                    if check['data'][0].get('is_sent') is True:
                        return
            except Exception:
                pass

            # Final timing guard: if we woke up early, wait until exact due time
            try:
                now = datetime.now(timezone.utc)
                if notification.scheduled_time and now < notification.scheduled_time:
                    delay = (notification.scheduled_time - now).total_seconds()
                    if delay > 0:
                        await asyncio.sleep(delay)
            except Exception:
                pass

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
        finally:
            # Release in-process lock
            try:
                self._sending_ids.discard(notification.id)
            except Exception:
                pass
    
    async def _send_telegram_message(self, chat_id: str, text: str, parse_mode: str = None) -> bool:
        """Send a message to Telegram chat (avoiding circular import)."""
        try:
            import httpx
            import os
            
            # Accept both var names to avoid env mismatches
            telegram_token = os.getenv('TELEGRAM_BOT_TOKEN') or os.getenv('TELEGRAM_TOKEN')
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
                    data = response.json()
                    ok = bool(data.get('ok'))
                    if ok:
                        logger.info(f"📤 Telegram message sent successfully to {chat_id}")
                        return True
                    else:
                        logger.error(f"❌ Telegram API response not ok: {data}")
                        return False
                else:
                    logger.error(f"❌ Telegram API error: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Error sending Telegram message: {e}")
            return False
    
    async def _format_notification_message(self, notification: NotificationTask) -> str:
        """Format notification message based on type."""
        
        if notification.notification_type == 'reminder':
            # Render in user's local timezone and simplify title
            try:
                from core.user_prefs import get_user_timezone
                import pytz
                user_tz_name = get_user_timezone(notification.user_id)
                tz = pytz.timezone(user_tz_name)
                local_dt = notification.scheduled_time.astimezone(tz) if notification.scheduled_time.tzinfo else tz.localize(notification.scheduled_time)
                # Clean message: drop trailing "at HH:MM ..." patterns
                import re
                title = notification.message or "Reminder"
                title = re.sub(r"\s+at\s+\d{1,2}(:\d{2})?(\s?(am|pm|AM|PM))?\b.*$", "", title).strip()
                if not title:
                    title = "Reminder"
                time_str = local_dt.strftime('%b %d, %I:%M %p')
                tz_abbr = local_dt.tzname() or user_tz_name
                return f"⏰ Reminder: {title}\nTime: {time_str} {tz_abbr}"
            except Exception:
                return f"⏰ Reminder: {notification.message}"
        
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
            now = datetime.now(timezone.utc)
            
            if not pending:
                logger.info("📭 No pending notifications to process")
                return
            
            logger.info(f"📬 Processing {len(pending)} pending notifications")
            
            for notification_data in pending:
                try:
                    # Map only known fields to avoid unexpected kwargs like content_id
                    raw_dt = notification_data.get('scheduled_time')
                    try:
                        scheduled_dt = raw_dt if isinstance(raw_dt, datetime) else datetime.fromisoformat(str(raw_dt).replace('Z', '+00:00'))
                    except Exception:
                        scheduled_dt = now
                    # Guard: only send when due
                    if scheduled_dt > now:
                        continue

                    notification = NotificationTask(
                        id=str(notification_data.get('id')),
                        user_id=str(notification_data.get('user_id')),
                        title=notification_data.get('title', 'Reminder'),
                        message=notification_data.get('message', ''),
                        notification_type=notification_data.get('notification_type', 'reminder'),
                        scheduled_time=scheduled_dt,
                        recurring_pattern=notification_data.get('recurring_pattern'),
                        metadata=notification_data.get('metadata') or {}
                    )
                    logger.info(f"📤 Sending notification {notification.id} to user {notification.user_id}")
                    await self._send_notification(notification)
                except Exception as e:
                    logger.error(f"❌ Failed to process notification {notification_data.get('id', 'unknown')}: {e}")
                
        except Exception as e:
            logger.error(f"❌ Error processing pending notifications: {e}")
    
    async def _generate_morning_briefings(self):
        """Generate morning briefings for all active users."""
        try:
            import pytz
            tz = pytz.timezone('Asia/Kolkata')
            now_local = datetime.now(tz)
            current = now_local.strftime('%H:%M')
            logger.info(f"🌅 Morning brief check at {current} IST")
            users = await self._get_users_with_morning_briefings()
            for user_data in users:
                # For now all users use 08:00 IST
                if current != '08:00':
                    continue
                user_id = user_data['user_id']
                brief_message = await self._create_morning_brief(user_id, 'Asia/Kolkata')
                notification = NotificationTask(
                    id=f"morning_{user_id}_{datetime.now().strftime('%Y%m%d')}",
                    user_id=str(user_id),
                    title="Good Morning!",
                    message=brief_message,
                    notification_type='morning_brief',
                    scheduled_time=datetime.now(timezone.utc)
                )
                # Persist first for cross-process idempotency, ignore errors
                try:
                    await self._save_notification_to_db(notification)
                except Exception:
                    pass
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
            import pytz
            tz = pytz.timezone('Asia/Kolkata')
            now_local = datetime.now(tz)
            current = now_local.strftime('%H:%M')
            logger.info(f"🌙 Evening summary check at {current} IST")
            users = await self._get_users_with_evening_summaries()
            for user_data in users:
                # Fire at 23:00 IST
                if current != '23:00':
                    continue
                user_id = user_data['user_id']
                summary_message = await self._create_evening_summary(user_id)
                notification = NotificationTask(
                    id=f"evening_{user_id}_{datetime.now().strftime('%Y%m%d')}",
                    user_id=str(user_id),
                    title="Daily Summary",
                    message=summary_message,
                    notification_type='evening_summary',
                    scheduled_time=datetime.now(timezone.utc)
                )
                # Persist first for cross-process idempotency, ignore errors
                try:
                    await self._save_notification_to_db(notification)
                except Exception:
                    pass
                await self._send_notification(notification)
                
        except Exception as e:
            logger.error(f"Error generating evening summaries: {e}")
    
    async def _create_evening_summary(self, user_id: str) -> str:
        """Create daily summary of user's activity."""
        try:
            summary_parts = ["🌙 **Daily Summary**\n"]
            
            # Get today's activity
            today_activity = await self._get_today_activity(user_id)
            
            has_any = False
            if today_activity.get('saves', 0) > 0:
                summary_parts.append(f"📝 You saved {today_activity['saves']} items today")
                has_any = True
            
            if today_activity.get('completed_tasks', 0) > 0:
                summary_parts.append(f"✅ Completed {today_activity['completed_tasks']} tasks")
                has_any = True
            
            if today_activity.get('searches', 0) > 0:
                summary_parts.append(f"🔍 Performed {today_activity['searches']} searches")
                has_any = True
            
            # Add brief content highlights
            highlights = await self._get_content_highlights(user_id)
            if highlights:
                summary_parts.append(f"\n💡 **Today's Highlights**:\n{highlights}")
                has_any = True

            if not has_any:
                summary_parts.append("📭 No new activity today")
            
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
    
    # Database interaction methods
    async def _save_notification_to_db(self, notification: NotificationTask) -> bool:
        """Save notification to database for persistence."""
        try:
            from core.supabase_rest import supabase_rest
            from datetime import datetime, timezone
            
            # Debug: Check if supabase_rest is properly initialized
            logger.info(f"🔍 DEBUG: Supabase client ready: {supabase_rest.ready}")
            
            notification_data = {
                'id': notification.id,
                'user_id': notification.user_id,
                'title': notification.title,
                'message': notification.message,
                'notification_type': notification.notification_type,
                'scheduled_time': notification.scheduled_time.isoformat(),
                'is_sent': False,
                'is_active': True,
                'recurring_pattern': notification.recurring_pattern,
                'metadata': notification.metadata or {},
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            response = supabase_rest.table('notifications').insert(notification_data).execute()

            # Debug: Log the full response to see what's happening
            logger.info(f"🔍 DEBUG: Supabase response: {response}")

            # Our REST client returns { data: [...], error: None } on success
            if response and response.get('error') is None:
                logger.info(f"💾 Saved notification {notification.id} to database")
                return True
            else:
                error_msg = response.get('error', 'Unknown error') if response else 'Response is None'
                logger.error(f"❌ Failed to save notification to database: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error saving notification to database: {e}")
            return False
    
    async def _get_pending_notifications(self) -> List[Dict]:
        """Get pending notifications from database."""
        try:
            from core.supabase_rest import supabase_rest
            from datetime import datetime, timezone
            
            # Get all pending notifications (time filtering handled by poller)
            response = supabase_rest.table('notifications').select().eq('is_sent', False).eq('is_active', True).order('scheduled_time').limit(200).execute()
            
            if response and response.get('error') is None and response.get('data'):
                logger.info(f"🔍 Found {len(response['data'])} pending active notifications")
                return response['data']
            else:
                logger.debug("🔍 No pending notifications found in database")
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
                'is_sent': True,
                'sent_at': datetime.now(timezone.utc).isoformat()
            }).eq('id', notification_id).execute()
            
            if response and response.get('error') is None:
                logger.info(f"✅ Marked notification {notification_id} as sent")
            else:
                logger.error(f"❌ Failed to mark notification {notification_id} as sent")
                
        except Exception as e:
            logger.error(f"❌ Error marking notification as sent: {e}")
    
    async def _get_users_with_morning_briefings(self) -> List[Dict]:
        """Get users who want morning briefings (basic: all active users, default Asia/Kolkata)."""
        try:
            from core.supabase_rest import supabase_rest
            res = supabase_rest.table('users').select('*').eq('is_active', True).limit(500).execute()
            users = []
            if res and res.get('error') is None and res.get('data'):
                for row in res['data']:
                    users.append({
                        'user_id': str(row['user_id']),
                        'timezone': 'Asia/Kolkata',
                        'morning_brief_time': '08:00'
                    })
            return users
        except Exception as e:
            logger.error(f"get_users_with_morning_briefings failed: {e}")
            return []
    
    async def _get_users_with_evening_summaries(self) -> List[Dict]:
        """Get users who want evening summaries (basic: all active users)."""
        try:
            from core.supabase_rest import supabase_rest
            res = supabase_rest.table('users').select('*').eq('is_active', True).limit(500).execute()
            users = []
            if res and res.get('error') is None and res.get('data'):
                for row in res['data']:
                    users.append({'user_id': str(row['user_id'])})
            return users
        except Exception as e:
            logger.error(f"get_users_with_evening_summaries failed: {e}")
            return []
    
    async def _get_active_users(self) -> List[Dict]:
        """Get all active users (basic)."""
        try:
            from core.supabase_rest import supabase_rest
            res = supabase_rest.table('users').select('*').eq('is_active', True).limit(500).execute()
            if res and res.get('error') is None and res.get('data'):
                return [{'user_id': str(r['user_id'])} for r in res['data']]
            return []
        except Exception as e:
            logger.error(f"get_active_users failed: {e}")
            return []
    
    async def _get_task_summary(self, user_id: str) -> Optional[str]:
        """Get summary of user's tasks (basic counts)."""
        try:
            from core.supabase_rest import supabase_rest
            res = supabase_rest.table('content').select('*').eq('user_id', user_id).eq('content_type', 'task').execute()
            if res and res.get('error') is None and res.get('data') is not None:
                total = len(res['data'])
                if total:
                    return f"{total} tasks in your list"
            return None
        except Exception as e:
            logger.error(f"get_task_summary failed: {e}")
            return None
    
    async def _get_recent_content_summary(self, user_id: str) -> Optional[str]:
        """Get summary of recent content (last 5 items)."""
        try:
            from core.supabase_rest import supabase_rest
            res = supabase_rest.table('content').select('*').eq('user_id', user_id).order('created_at', desc=True).limit(5).execute()
            if res and res.get('error') is None and res.get('data'):
                titles = []
                for r in res['data']:
                    title = r.get('title') or (r.get('content') or '')[:30]
                    ctype = r.get('content_type') or 'item'
                    titles.append(f"{ctype}: {title}")
                return ", ".join(titles)
            return None
        except Exception as e:
            logger.error(f"get_recent_content_summary failed: {e}")
            return None
    
    async def _get_today_activity(self, user_id: str) -> Dict:
        """Get today's activity summary (basic: saves count)."""
        try:
            from core.supabase_rest import supabase_rest
            # Assuming content.created_at is ISO; filter client-side basic
            res = supabase_rest.table('content').select('*').eq('user_id', user_id).order('created_at', desc=True).limit(100).execute()
            saves = 0
            if res and res.get('error') is None and res.get('data'):
                from datetime import datetime
                today = datetime.utcnow().date()
                for r in res['data']:
                    ts = str(r.get('created_at') or '')
                    if ts:
                        try:
                            if ts.endswith('Z'):
                                ts = ts.replace('Z', '+00:00')
                            d = datetime.fromisoformat(ts).date()
                            if d == today:
                                saves += 1
                        except Exception:
                            pass
            return {'saves': saves, 'completed_tasks': 0, 'searches': 0}
        except Exception as e:
            logger.error(f"get_today_activity failed: {e}")
            return {'saves': 0, 'completed_tasks': 0, 'searches': 0}
    
    async def _get_content_highlights(self, user_id: str) -> Optional[str]:
        """Get content highlights for the day (basic: latest 3 titles)."""
        try:
            from core.supabase_rest import supabase_rest
            res = supabase_rest.table('content').select('*').eq('user_id', user_id).order('created_at', desc=True).limit(3).execute()
            if res and res.get('error') is None and res.get('data'):
                lines = []
                for r in res['data']:
                    title = r.get('title') or (r.get('content') or '')[:50]
                    lines.append(f"• {title}")
                return "\n".join(lines)
            return None
        except Exception as e:
            logger.error(f"get_content_highlights failed: {e}")
            return None
    
    async def _should_resurface_memory(self, user_id: str, frequency: str) -> bool:
        """Check if user should get memory resurfacing (basic rules).
        daily: 50% chance per run; weekly: 25%; monthly: 10%.
        """
        freq = (frequency or 'weekly').lower()
        if freq == 'daily':
            p = 0.5
        elif freq == 'weekly':
            p = 0.25
        elif freq == 'monthly':
            p = 0.1
        else:
            p = 0.2
        return random.random() < p
    
    async def _get_random_memory(self, user_id: str) -> Optional[Dict]:
        """Get a random older piece of content (basic heuristic)."""
        try:
            from core.supabase_rest import supabase_rest
            res = supabase_rest.table('content').select('*').eq('user_id', user_id).order('created_at', desc=True).limit(200).execute()
            if res and res.get('error') is None and res.get('data'):
                items = res['data']
                if len(items) == 0:
                    return None
                # Prefer items not in the latest 10 to avoid showing very fresh content
                pool = items[10:] if len(items) > 10 else items
                import random as _r
                return _r.choice(pool)
            return None
        except Exception as e:
            logger.error(f"get_random_memory failed: {e}")
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
    
    import uuid
    
    notification = NotificationTask(
        id=str(uuid.uuid4()),  # Generate proper UUID
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
    
    import uuid
    
    notification = NotificationTask(
        id=str(uuid.uuid4()),  # Generate proper UUID
        user_id=user_id,
        title=f"Task Due: {task_title}",
        message=f"Your task '{task_title}' is due now!",
        notification_type='task',
        scheduled_time=due_time
    )
    
    return await scheduler.schedule_notification(notification)
