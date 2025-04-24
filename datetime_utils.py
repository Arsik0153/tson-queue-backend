from datetime import datetime, time, timedelta
from config import settings

# We'll use these functions consistently throughout the application
# to avoid timezone confusion

def parse_datetime(date_str: str) -> datetime:
    """
    Parse an ISO-format datetime string (assumed to be in local time) 
    into a naive datetime object.
    
    Example: "2025-04-29T11:00:00" -> datetime(2025, 4, 29, 11, 0, 0)
    """
    return datetime.fromisoformat(date_str)

def parse_date(date_str: str) -> datetime.date:
    """
    Parse a date string in YYYY-MM-DD format into a date object.
    """
    return datetime.strptime(date_str, "%Y-%m-%d").date()

def format_datetime(dt: datetime) -> str:
    """
    Format a naive datetime to ISO format for frontend.
    """
    return dt.isoformat()

def format_date(dt: datetime.date) -> str:
    """
    Format a date to YYYY-MM-DD for frontend.
    """
    return dt.strftime("%Y-%m-%d")

def get_working_slots_for_date(target_date: datetime.date) -> list[datetime]:
    """
    Get all possible working hour slots for a specific date.
    Returns list of naive datetime objects with 30-minute intervals.
    """
    slots = []
    start_hour = settings.WORKING_HOURS["start"]
    end_hour = settings.WORKING_HOURS["end"]
    
    current_slot = datetime.combine(target_date, time(start_hour, 0))
    end_time = datetime.combine(target_date, time(end_hour, 0))
    
    # Use 30-minute intervals
    interval_minutes = 30
    
    while current_slot < end_time:
        slots.append(current_slot)
        current_slot += timedelta(minutes=interval_minutes)
        
    return slots

def get_date_range_bounds(target_date: datetime.date) -> tuple[datetime, datetime]:
    """
    Get the start and end datetime bounds for a specific date.
    Returns tuple of (start, end) naive datetime objects.
    """
    start = datetime.combine(target_date, time(0, 0, 0))
    end = datetime.combine(target_date + timedelta(days=1), time(0, 0, 0))
    return start, end

def is_past_date(date_to_check: datetime.date) -> bool:
    """
    Check if a date is in the past compared to today.
    """
    return date_to_check < datetime.now().date()

def is_valid_working_hour(dt: datetime) -> bool:
    """
    Check if a datetime falls within working hours.
    """
    hour = dt.hour
    minute = dt.minute
    
    # Check if hour is within working hours
    if not (settings.WORKING_HOURS["start"] <= hour < settings.WORKING_HOURS["end"]):
        return False
    
    # Check if minute is either 00 or 30
    return minute in [0, 30] 