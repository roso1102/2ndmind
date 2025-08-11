#!/usr/bin/env python3
"""
⏰ Advanced Time Parsing for MySecondMind

This module provides intelligent time parsing capabilities:
- Natural language time expressions ("tomorrow at 3pm", "in 2 hours")
- Timezone awareness
- Recurring pattern detection
- Smart time suggestions and validation
"""

import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Tuple, Union
from dateutil import parser as dateutil_parser
from dateutil.relativedelta import relativedelta
import parsedatetime

logger = logging.getLogger(__name__)

class TimeParser:
    """Advanced time parsing with natural language support."""
    
    def __init__(self):
        # Initialize parsedatetime calendar
        self.cal = parsedatetime.Calendar()
        
        # Common time patterns
        self.time_patterns = {
            'relative_simple': [
                r'in (\d+) (minute|minutes|min|mins|hour|hours|hr|hrs|day|days)',
                r'(\d+) (minute|minutes|min|mins|hour|hours|hr|hrs|day|days) from now'
            ],
            'relative_words': [
                r'(tomorrow|today|yesterday)',
                r'(next|this) (monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
                r'(next|this) (week|month|year)',
                r'(morning|afternoon|evening|night)',
            ],
            'specific_time': [
                r'at (\d{1,2}):?(\d{2})?\s*(am|pm|AM|PM)?',
                r'(\d{1,2})\s*(am|pm|AM|PM)',
            ],
            'recurring': [
                r'every (day|week|month|year)',
                r'every (monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
                r'(daily|weekly|monthly|yearly)',
                r'every (\d+) (days|weeks|months|years)'
            ]
        }
        
        # Time zone mappings (basic)
        self.timezone_mapping = {
            'EST': 'US/Eastern',
            'PST': 'US/Pacific',
            'CST': 'US/Central',
            'MST': 'US/Mountain',
            'UTC': 'UTC',
            'GMT': 'UTC'
        }
    
    async def parse_time_expression(self, time_str: str, user_timezone: str = 'UTC', reference_time: Optional[datetime] = None) -> Optional[Dict]:
        """
        Parse natural language time expression.
        
        Returns:
            Dict with parsed time information or None if parsing failed
        """
        if not time_str or not time_str.strip():
            return None
        
        time_str = time_str.strip().lower()
        reference_time = reference_time or datetime.now(timezone.utc)
        
        try:
            # Method 1: Try parsedatetime first (best for natural language)
            result = self._parse_with_parsedatetime(time_str, reference_time)
            if result:
                return result
            
            # Method 2: Try custom pattern matching
            result = self._parse_with_patterns(time_str, reference_time)
            if result:
                return result
            
            # Method 3: Try dateutil as fallback
            result = self._parse_with_dateutil(time_str, reference_time)
            if result:
                return result
            
            logger.warning(f"Could not parse time expression: {time_str}")
            return None
            
        except Exception as e:
            logger.error(f"Time parsing error: {e}")
            return None
    
    def _parse_with_parsedatetime(self, time_str: str, reference_time: datetime) -> Optional[Dict]:
        """Parse using parsedatetime library."""
        try:
            # Parse the time expression
            time_struct, parse_status = self.cal.parse(time_str, reference_time.timetuple())
            
            if parse_status == 0:  # No date/time found
                return None
            
            # Convert to datetime
            parsed_dt = datetime(*time_struct[:6])
            
            # Add timezone info (assume UTC for now)
            if parsed_dt.tzinfo is None:
                parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
            
            # Check if it's in the past (and adjust if it's meant to be future)
            if parsed_dt <= reference_time:
                # For relative times like "3pm", assume next occurrence
                if any(word in time_str for word in ['am', 'pm', 'morning', 'afternoon', 'evening']):
                    parsed_dt += timedelta(days=1)
            
            # Detect recurring pattern
            recurring_pattern = self._detect_recurring_pattern(time_str)
            
            return {
                'datetime': parsed_dt,
                'original_expression': time_str,
                'confidence': 0.9 if parse_status >= 2 else 0.7,
                'recurring_pattern': recurring_pattern,
                'is_relative': self._is_relative_expression(time_str),
                'parsed_components': {
                    'date_found': parse_status in [1, 3],
                    'time_found': parse_status in [2, 3]
                }
            }
            
        except Exception as e:
            logger.debug(f"Parsedatetime failed for '{time_str}': {e}")
            return None
    
    def _parse_with_patterns(self, time_str: str, reference_time: datetime) -> Optional[Dict]:
        """Parse using custom regex patterns."""
        try:
            # Handle relative simple patterns
            for pattern in self.time_patterns['relative_simple']:
                match = re.search(pattern, time_str)
                if match:
                    number = int(match.group(1))
                    unit = match.group(2).lower()
                    
                    # Convert to timedelta
                    if unit.startswith('min'):
                        delta = timedelta(minutes=number)
                    elif unit.startswith('hour') or unit.startswith('hr'):
                        delta = timedelta(hours=number)
                    elif unit.startswith('day'):
                        delta = timedelta(days=number)
                    else:
                        continue
                    
                    parsed_dt = reference_time + delta
                    
                    return {
                        'datetime': parsed_dt,
                        'original_expression': time_str,
                        'confidence': 0.95,
                        'recurring_pattern': None,
                        'is_relative': True,
                        'parsed_components': {
                            'relative_delta': delta,
                            'unit': unit,
                            'number': number
                        }
                    }
            
            # Handle specific time patterns
            time_match = None
            for pattern in self.time_patterns['specific_time']:
                time_match = re.search(pattern, time_str)
                if time_match:
                    break
            
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2) or 0)
                period = time_match.group(3) if len(time_match.groups()) >= 3 else None
                
                # Convert 12-hour to 24-hour
                if period:
                    period = period.lower()
                    if period == 'pm' and hour != 12:
                        hour += 12
                    elif period == 'am' and hour == 12:
                        hour = 0
                
                # Create datetime for today at specified time
                parsed_dt = reference_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # If time has passed today, assume tomorrow
                if parsed_dt <= reference_time:
                    parsed_dt += timedelta(days=1)
                
                return {
                    'datetime': parsed_dt,
                    'original_expression': time_str,
                    'confidence': 0.85,
                    'recurring_pattern': None,
                    'is_relative': False,
                    'parsed_components': {
                        'hour': hour,
                        'minute': minute,
                        'period': period
                    }
                }
            
            return None
            
        except Exception as e:
            logger.debug(f"Pattern matching failed for '{time_str}': {e}")
            return None
    
    def _parse_with_dateutil(self, time_str: str, reference_time: datetime) -> Optional[Dict]:
        """Parse using dateutil as fallback."""
        try:
            # Try to parse with dateutil
            parsed_dt = dateutil_parser.parse(time_str, default=reference_time, fuzzy=True)
            
            # Add timezone if missing
            if parsed_dt.tzinfo is None:
                parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
            
            return {
                'datetime': parsed_dt,
                'original_expression': time_str,
                'confidence': 0.6,  # Lower confidence for dateutil fallback
                'recurring_pattern': None,
                'is_relative': False,
                'parsed_components': {
                    'fallback_parser': 'dateutil'
                }
            }
            
        except Exception as e:
            logger.debug(f"Dateutil parsing failed for '{time_str}': {e}")
            return None
    
    def _detect_recurring_pattern(self, time_str: str) -> Optional[str]:
        """Detect if the time expression indicates a recurring pattern."""
        time_str_lower = time_str.lower()
        
        # Check for recurring patterns
        for pattern in self.time_patterns['recurring']:
            if re.search(pattern, time_str_lower):
                match = re.search(pattern, time_str_lower)
                if match:
                    return match.group(0)
        
        # Common recurring words
        recurring_words = {
            'daily': 'daily',
            'every day': 'daily',
            'weekly': 'weekly',
            'every week': 'weekly',
            'monthly': 'monthly',
            'every month': 'monthly',
            'yearly': 'yearly',
            'every year': 'yearly'
        }
        
        for phrase, pattern in recurring_words.items():
            if phrase in time_str_lower:
                return pattern
        
        return None
    
    def _is_relative_expression(self, time_str: str) -> bool:
        """Check if the expression is relative to current time."""
        relative_indicators = [
            'in ', 'from now', 'later', 'tomorrow', 'yesterday',
            'next ', 'this ', 'after', 'before'
        ]
        
        time_str_lower = time_str.lower()
        return any(indicator in time_str_lower for indicator in relative_indicators)
    
    def suggest_time_formats(self, partial_input: str = "") -> List[str]:
        """Suggest valid time format examples."""
        suggestions = [
            "tomorrow at 3pm",
            "in 2 hours", 
            "next Monday morning",
            "today at 5:30pm",
            "in 30 minutes",
            "next week",
            "Friday at 2pm",
            "tomorrow morning",
            "in 1 hour",
            "every day at 9am",
            "weekly on Monday",
            "monthly on the 1st"
        ]
        
        if partial_input:
            # Filter suggestions based on partial input
            partial_lower = partial_input.lower()
            filtered = [s for s in suggestions if partial_lower in s.lower()]
            return filtered[:5] if filtered else suggestions[:5]
        
        return suggestions[:8]
    
    def validate_time(self, parsed_result: Dict, min_advance_minutes: int = 1) -> Tuple[bool, Optional[str]]:
        """Validate parsed time result."""
        if not parsed_result or 'datetime' not in parsed_result:
            return False, "No valid time found"
        
        parsed_dt = parsed_result['datetime']
        now = datetime.now(timezone.utc)
        
        # Check if time is too far in the past
        if parsed_dt < now - timedelta(minutes=1):
            return False, "Time is in the past"
        
        # Check if time is too soon
        if parsed_dt < now + timedelta(minutes=min_advance_minutes):
            return False, f"Time must be at least {min_advance_minutes} minute(s) in the future"
        
        # Check if time is too far in the future (2 years)
        if parsed_dt > now + timedelta(days=730):
            return False, "Time is too far in the future (max 2 years)"
        
        return True, None
    
    def format_parsed_time(self, parsed_result: Dict, user_timezone: str = 'UTC') -> str:
        """Format parsed time for user display."""
        if not parsed_result or 'datetime' not in parsed_result:
            return "Invalid time"
        
        dt = parsed_result['datetime']
        
        # Format based on how far in the future it is
        now = datetime.now(timezone.utc)
        delta = dt - now
        
        if delta.days == 0:
            # Today
            return f"today at {dt.strftime('%I:%M %p')}"
        elif delta.days == 1:
            # Tomorrow
            return f"tomorrow at {dt.strftime('%I:%M %p')}"
        elif delta.days < 7:
            # This week
            return f"{dt.strftime('%A')} at {dt.strftime('%I:%M %p')}"
        else:
            # Further out
            return dt.strftime('%B %d, %Y at %I:%M %p')

# Global time parser instance
time_parser = TimeParser()

async def parse_time_expression(time_str: str, user_timezone: str = 'UTC') -> Optional[Dict]:
    """Main entry point for time parsing."""
    return await time_parser.parse_time_expression(time_str, user_timezone)

def suggest_time_formats(partial_input: str = "") -> List[str]:
    """Get time format suggestions."""
    return time_parser.suggest_time_formats(partial_input)

def validate_parsed_time(parsed_result: Dict) -> Tuple[bool, Optional[str]]:
    """Validate parsed time."""
    return time_parser.validate_time(parsed_result)
