"""
Last Encounter – Determines the {{last_encounter}} placeholder value.

Logic:
1. First encounter:  No other session exists AND no previous user interaction
   → "This is your first encounter with the user"
2. New session:      Other sessions exist, current session has 0 user messages
   → "Your last conversation with the user was [time ago]"
3. Active session:   Current session has user messages
   → "The user last wrote [time ago]"
"""

from datetime import datetime, timezone
from typing import Optional
from .logger import log
from .sql_loader import sql
from .database.connection import get_db_connection


def humanize_time_delta(seconds: float) -> str:
    """
    Converts a time delta in seconds to a human-readable English string.

    Thresholds:
      0–45s    → "a few seconds ago"
      46–90s   → "about a minute ago"
      91s–45m  → "X minutes ago"
      46–90m   → "about an hour ago"
      91m–22h  → "X hours ago"
      22–36h   → "about a day ago"
      37h–25d  → "X days ago"
      26–45d   → "about a month ago"
      46d–10.5mo → "X months ago"
      10.5–18mo  → "about a year ago"
      >18mo    → "X years ago"
    """
    if seconds < 0:
        seconds = 0

    minutes = seconds / 60
    hours = seconds / 3600
    days = seconds / 86400
    months = days / 30.44  # average month length
    years = days / 365.25

    if seconds <= 45:
        return "a few seconds ago"
    elif seconds <= 90:
        return "about a minute ago"
    elif minutes <= 45:
        return f"{int(round(minutes))} minutes ago"
    elif minutes <= 90:
        return "about an hour ago"
    elif hours <= 22:
        return f"{int(round(hours))} hours ago"
    elif hours <= 36:
        return "about a day ago"
    elif days <= 25:
        return f"{int(round(days))} days ago"
    elif days <= 45:
        return "about a month ago"
    elif months <= 10.5:
        return f"{int(round(months))} months ago"
    elif months <= 18:
        return "about a year ago"
    else:
        return f"{int(round(years))} years ago"


def _parse_timestamp(ts_str: str) -> Optional[datetime]:
    """Parses a SQLite DATETIME string into a timezone-aware UTC datetime."""
    if not ts_str:
        return None
    try:
        # SQLite CURRENT_TIMESTAMP format: "YYYY-MM-DD HH:MM:SS"
        dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        try:
            # Fallback: ISO format with T separator
            dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, TypeError):
            log.warning("Could not parse timestamp: %s", ts_str)
            return None


def compute_last_encounter(session_id: Optional[int], persona_id: str = 'default') -> str:
    """
    Computes the {{last_encounter}} placeholder value.

    Args:
        session_id: Current session ID (None → latest session)
        persona_id: Persona ID (determines which DB to query)

    Returns:
        Human-readable encounter string, e.g.:
        - "This is your first encounter with the user"
        - "Your last conversation with the user was about 2 hours ago"
        - "The user last wrote 5 minutes ago"
    """
    try:
        conn = get_db_connection(persona_id)
        cursor = conn.cursor()

        # If no session_id, get the latest
        if session_id is None:
            cursor.execute(sql('chat.get_latest_session_id'))
            result = cursor.fetchone()
            if result:
                session_id = result[0]
            else:
                conn.close()
                return "This is your first encounter with the user"

        # 1. How many sessions exist?
        cursor.execute(sql('chat.get_session_count'))
        session_count = cursor.fetchone()[0]

        # 2. How many user messages in the current session?
        cursor.execute(sql('chat.get_user_message_count_in_session'), (session_id,))
        user_msg_count = cursor.fetchone()[0]

        now = datetime.now(timezone.utc)

        if user_msg_count > 0:
            # Case 3: Active session – show when user last wrote
            cursor.execute(sql('chat.get_last_user_message_timestamp'), (session_id,))
            row = cursor.fetchone()
            conn.close()

            if row and row[0]:
                last_ts = _parse_timestamp(row[0])
                if last_ts:
                    delta_seconds = (now - last_ts).total_seconds()
                    return f"The user last wrote {humanize_time_delta(delta_seconds)}"

            return "The user last wrote a few seconds ago"

        # No user messages in current session yet
        if session_count <= 1:
            # Case 1: Only one session (this one), no user messages → first encounter
            conn.close()
            return "This is your first encounter with the user"

        # Case 2: Other sessions exist → find last interaction from previous sessions
        cursor.execute(sql('chat.get_last_user_message_other_sessions'), (session_id,))
        row = cursor.fetchone()
        conn.close()

        if row and row[0]:
            last_ts = _parse_timestamp(row[0])
            if last_ts:
                delta_seconds = (now - last_ts).total_seconds()
                return f"Your last conversation with the user was {humanize_time_delta(delta_seconds)}"

        # Other sessions exist but no user messages found in them → still first encounter
        return "This is your first encounter with the user"

    except Exception as e:
        log.warning("compute_last_encounter failed: %s", e)
        return ""
