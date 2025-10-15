"""
Utility functions for the Smart Presales application.

This module provides timezone handling and other common utilities.
"""

from datetime import datetime, timedelta
import pytz
from typing import Optional

# Indian Standard Time timezone
INDIA_TZ = pytz.timezone('Asia/Kolkata')


def get_ist_now() -> datetime:
    """
    Get current time in Indian Standard Time (IST).
    
    Returns:
        datetime: Current time with IST timezone
    """
    return datetime.now(INDIA_TZ)


def get_ist_timestamp() -> str:
    """
    Get current IST timestamp as ISO 8601 formatted string.
    
    Returns:
        str: ISO formatted timestamp with timezone (e.g., "2025-10-13T15:30:45.123456+05:30")
    """
    return get_ist_now().isoformat()


def parse_ist_timestamp(iso_string: str) -> Optional[datetime]:
    """
    Parse ISO timestamp string to IST datetime object.
    
    Args:
        iso_string: ISO formatted timestamp string
        
    Returns:
        datetime: Datetime object in IST timezone, or None if parsing fails
    """
    try:
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        
        # If no timezone info, assume UTC
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        
        # Convert to IST
        return dt.astimezone(INDIA_TZ)
    except (ValueError, AttributeError) as e:
        print(f"Error parsing timestamp '{iso_string}': {e}")
        return None


def format_ist_datetime(dt: datetime, format_str: str = "%d %b %Y, %I:%M %p IST") -> str:
    """
    Format datetime object to readable IST string.
    
    Args:
        dt: Datetime object to format
        format_str: strftime format string (default: "13 Oct 2025, 03:30 PM IST")
        
    Returns:
        str: Formatted datetime string
    """
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    
    ist_dt = dt.astimezone(INDIA_TZ)
    return ist_dt.strftime(format_str)


def get_ist_date() -> str:
    """
    Get current date in IST (YYYY-MM-DD format).
    
    Returns:
        str: Current date in IST
    """
    return get_ist_now().strftime("%Y-%m-%d")


def add_hours_ist(hours: int) -> datetime:
    """
    Get IST datetime N hours from now.
    
    Args:
        hours: Number of hours to add (can be negative)
        
    Returns:
        datetime: Future/past datetime in IST
    """
    return get_ist_now() + timedelta(hours=hours)


def add_hours_ist_timestamp(hours: int) -> str:
    """
    Get IST timestamp N hours from now.
    
    Args:
        hours: Number of hours to add (can be negative)
        
    Returns:
        str: ISO formatted timestamp
    """
    return add_hours_ist(hours).isoformat()


def is_ist_business_hours() -> bool:
    """
    Check if current IST time is within business hours (9 AM - 9 PM).
    
    Returns:
        bool: True if within business hours
    """
    now = get_ist_now()
    return 9 <= now.hour < 21


def get_next_business_hour_ist() -> datetime:
    """
    Get next business hour in IST (9 AM if outside business hours).
    
    Returns:
        datetime: Next business hour datetime
    """
    now = get_ist_now()
    
    # If before 9 AM, return today at 9 AM
    if now.hour < 9:
        return now.replace(hour=9, minute=0, second=0, microsecond=0)
    
    # If after 9 PM, return tomorrow at 9 AM
    if now.hour >= 21:
        tomorrow = now + timedelta(days=1)
        return tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
    
    # Otherwise, return current time (we're in business hours)
    return now


# Backward compatibility: Keep datetime.now() interface but with IST
def now_ist() -> datetime:
    """Alias for get_ist_now() for backward compatibility."""
    return get_ist_now()


def timestamp_ist() -> str:
    """Alias for get_ist_timestamp() for backward compatibility."""
    return get_ist_timestamp()

