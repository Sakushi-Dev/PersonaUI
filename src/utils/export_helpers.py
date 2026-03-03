"""
Export Helpers - Chat-Export-Formatierung

Handles:
- TXT format: [YYYY-MM-DD HH:MM] Sender: Message
- JSON format: Array of objects with timestamp, role, content
- Filename generation for downloads
"""

import json
from datetime import datetime
from typing import List, Dict


def format_messages_as_txt(messages: List[Dict]) -> str:
    """
    Formats messages as plain text with timestamps.
    
    Format: [YYYY-MM-DD HH:MM] Sender: Message
    
    Args:
        messages: List of message dicts from database
        
    Returns:
        Formatted text string
    """
    if not messages:
        return ""
    
    lines = []
    for msg in messages:
        # Parse timestamp from ISO string to datetime
        timestamp_str = msg.get('timestamp', '')
        try:
            # Parse ISO format timestamp (e.g., "2024-03-03T20:30:15")
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            formatted_time = timestamp.strftime('%Y-%m-%d %H:%M')
        except (ValueError, AttributeError):
            formatted_time = "Unknown"
        
        # Determine sender
        if msg.get('is_user', False):
            sender = "User"
        else:
            sender = msg.get('character_name', 'Assistant')
        
        # Format message
        content = msg.get('message', '')
        lines.append(f"[{formatted_time}] {sender}: {content}")
    
    return '\n'.join(lines)


def format_messages_as_json(messages: List[Dict]) -> str:
    """
    Formats messages as JSON array.
    
    Format: [{"timestamp": "ISO", "role": "user|assistant", "content": "text"}]
    
    Args:
        messages: List of message dicts from database
        
    Returns:
        JSON string
    """
    if not messages:
        return "[]"
    
    formatted_messages = []
    for msg in messages:
        formatted_msg = {
            "timestamp": msg.get('timestamp', ''),
            "role": "user" if msg.get('is_user', False) else "assistant",
            "content": msg.get('message', '')
        }
        formatted_messages.append(formatted_msg)
    
    return json.dumps(formatted_messages, ensure_ascii=False, indent=2)


def make_export_filename(session_id: int, format_ext: str) -> str:
    """
    Generates filename for chat export.
    
    Format: chat_export_{session_id}_{YYYY-MM-DD}.{ext}
    
    Args:
        session_id: Session ID
        format_ext: File extension (txt or json)
        
    Returns:
        Filename string
    """
    date_str = datetime.now().strftime('%Y-%m-%d')
    return f"chat_export_{session_id}_{date_str}.{format_ext}"
