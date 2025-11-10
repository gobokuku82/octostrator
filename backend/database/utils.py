"""
Database Utility Functions

Common helpers for CRUD operations across all agents.
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime


def parse_json_field(value: Optional[str]) -> Optional[Dict]:
    """Parse JSON string from database to Python dict

    Args:
        value: JSON string from database Text column

    Returns:
        Parsed dict or None if empty/invalid

    Example:
        >>> parse_json_field('{"key": "value"}')
        {"key": "value"}
        >>> parse_json_field(None)
        None
    """
    if not value:
        return None

    try:
        result = json.loads(value)
        return result if isinstance(result, dict) else None
    except (json.JSONDecodeError, TypeError):
        return None


def serialize_json_field(value: Optional[Dict]) -> Optional[str]:
    """Serialize Python dict to JSON string for database

    Args:
        value: Python dict to serialize

    Returns:
        JSON string or None if empty

    Example:
        >>> serialize_json_field({"key": "value"})
        '{"key": "value"}'
        >>> serialize_json_field(None)
        None
    """
    if not value:
        return None

    return json.dumps(value, ensure_ascii=False)


def parse_json_list(value: Optional[str]) -> Optional[List]:
    """Parse JSON array string from database to Python list

    Args:
        value: JSON array string from database Text column

    Returns:
        Parsed list or None if empty/invalid

    Example:
        >>> parse_json_list('[1, 2, 3]')
        [1, 2, 3]
        >>> parse_json_list('["a", "b"]')
        ["a", "b"]
        >>> parse_json_list(None)
        None
    """
    if not value:
        return None

    try:
        result = json.loads(value)
        return result if isinstance(result, list) else None
    except (json.JSONDecodeError, TypeError):
        return None


def serialize_json_list(value: Optional[List]) -> Optional[str]:
    """Serialize Python list to JSON array string for database

    Args:
        value: Python list to serialize

    Returns:
        JSON array string or None if empty

    Example:
        >>> serialize_json_list([1, 2, 3])
        '[1, 2, 3]'
        >>> serialize_json_list(None)
        None
    """
    if not value:
        return None

    return json.dumps(value, ensure_ascii=False)


def datetime_to_str(dt: Optional[datetime]) -> Optional[str]:
    """Convert datetime to ISO format string

    Args:
        dt: Python datetime object

    Returns:
        ISO format string or None

    Example:
        >>> datetime_to_str(datetime(2025, 11, 7, 10, 30))
        '2025-11-07T10:30:00'
    """
    if not dt:
        return None

    return dt.isoformat()


def parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse ISO format string to datetime

    Args:
        value: ISO format datetime string

    Returns:
        Python datetime object or None

    Example:
        >>> parse_datetime('2025-11-07T10:30:00')
        datetime(2025, 11, 7, 10, 30)
    """
    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def safe_get_int(data: Dict[str, Any], key: str, default: int = 0) -> int:
    """Safely get integer value from dict

    Args:
        data: Source dictionary
        key: Key to retrieve
        default: Default value if not found or invalid

    Returns:
        Integer value or default
    """
    value = data.get(key)
    if value is None:
        return default

    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_get_float(data: Dict[str, Any], key: str, default: float = 0.0) -> float:
    """Safely get float value from dict

    Args:
        data: Source dictionary
        key: Key to retrieve
        default: Default value if not found or invalid

    Returns:
        Float value or default
    """
    value = data.get(key)
    if value is None:
        return default

    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_get_str(data: Dict[str, Any], key: str, default: str = "") -> str:
    """Safely get string value from dict

    Args:
        data: Source dictionary
        key: Key to retrieve
        default: Default value if not found

    Returns:
        String value or default
    """
    value = data.get(key)
    if value is None:
        return default

    return str(value)
