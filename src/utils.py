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


# Phone number utilities
def sanitize_phone_number(phone: str) -> str:
    """
    Sanitize phone number by removing spaces, dashes, parentheses, and other formatting.
    Ensures number starts with + and country code.
    
    Args:
        phone: Raw phone number (e.g., "91 9876543210", "+91-987-654-3210", "(91) 9876543210")
        
    Returns:
        str: Sanitized phone number (e.g., "+919876543210")
    """
    if not phone:
        return ""
    
    # Convert to string and strip whitespace
    phone = str(phone).strip()
    
    if not phone:
        return ""
    
    # Remove common formatting characters
    phone = phone.replace(' ', '')   # Remove spaces
    phone = phone.replace('-', '')   # Remove dashes
    phone = phone.replace('(', '')   # Remove opening parentheses
    phone = phone.replace(')', '')   # Remove closing parentheses
    phone = phone.replace('.', '')   # Remove dots
    phone = phone.replace('_', '')   # Remove underscores
    
    # Handle 00 prefix (convert to +)
    if phone.startswith('00'):
        phone = '+' + phone[2:]
    
    # Ensure it starts with exactly one +
    # Remove multiple + symbols if present
    while phone.startswith('++'):
        phone = phone[1:]
    
    if not phone.startswith('+'):
        phone = '+' + phone
    
    # Remove any non-digit characters except the leading +
    # Keep only: +1234567890
    import re
    # Extract just the digits after the first character (skip the +)
    digits = re.sub(r'[^\d]', '', phone[1:])
    phone = '+' + digits
    
    return phone


def validate_phone_number(phone: str) -> tuple[bool, str]:
    """
    Validate phone number format.
    
    Args:
        phone: Phone number to validate
        
    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
    if not phone:
        return False, "Phone number is empty"
    
    # Sanitize first
    sanitized = sanitize_phone_number(phone)
    
    # Must start with +
    if not sanitized.startswith('+'):
        return False, "Phone number must start with +"
    
    # Must have 11-16 digits (including country code)
    # Format: +CC (1-3 digits) + Number (8-13 digits)
    digits_only = sanitized[1:]  # Remove +
    
    if len(digits_only) < 10:
        return False, f"Phone number too short ({len(digits_only)} digits, need at least 10)"
    
    if len(digits_only) > 15:
        return False, f"Phone number too long ({len(digits_only)} digits, max 15)"
    
    # Must contain only digits after +
    if not digits_only.isdigit():
        return False, "Phone number contains invalid characters"
    
    return True, ""


def format_phone_display(phone: str) -> str:
    """
    Format phone number for display (with spaces for readability).
    
    Args:
        phone: Sanitized phone number (e.g., "+919876543210")
        
    Returns:
        str: Formatted for display (e.g., "+91 98765 43210")
    """
    if not phone or len(phone) < 5:
        return phone
    
    # For Indian numbers (+91)
    if phone.startswith('+91') and len(phone) == 13:
        return f"{phone[:3]} {phone[3:8]} {phone[8:]}"
    
    # For US/Canada numbers (+1)
    if phone.startswith('+1') and len(phone) == 12:
        return f"{phone[:2]} ({phone[2:5]}) {phone[5:8]}-{phone[8:]}"
    
    # For UK numbers (+44)
    if phone.startswith('+44') and len(phone) >= 12:
        return f"{phone[:3]} {phone[3:7]} {phone[7:]}"
    
    # Default: just add space after country code
    if len(phone) > 4:
        return f"{phone[:3]} {phone[3:]}"
    
    return phone


# Name utilities
def extract_first_name(full_name: str) -> str:
    """
    Extract first name from full name for more natural greetings.
    
    Args:
        full_name: Full name (e.g., "Prathamesh Kumar", "DINESH BASKARAN SHANTHI")
        
    Returns:
        str: First name only (e.g., "Prathamesh", "Dinesh")
        
    Examples:
        "Prathamesh Kumar" → "Prathamesh"
        "DINESH BASKARAN SHANTHI" → "Dinesh"
        "john smith" → "John"
        "Priya" → "Priya"
    """
    if not full_name:
        return ""
    
    # Strip whitespace and split by spaces
    name_parts = str(full_name).strip().split()
    
    if not name_parts:
        return ""
    
    # Get first part (first name)
    first_name = name_parts[0]
    
    # Capitalize properly (handle all caps names like "DINESH")
    # If all caps, convert to title case
    if first_name.isupper() and len(first_name) > 1:
        first_name = first_name.capitalize()
    
    return first_name

