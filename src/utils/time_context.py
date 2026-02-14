"""
Zeit-Kontext für den Prompt

Dieses Modul ermittelt:
- Aktuelles Datum, Uhrzeit und Wochentag
"""

from datetime import datetime
from typing import Dict, Optional
import locale

# Setze deutsches Locale für Wochentage
try:
    locale.setlocale(locale.LC_TIME, 'de_DE.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'German')
    except:
        pass  # Fallback auf System-Standard


def get_german_weekday(date: datetime = None) -> str:
    """
    Gibt den deutschen Wochentag zurück
    
    Args:
        date: Datum (Standard: heute)
        
    Returns:
        Deutscher Wochentag (z.B. "Montag")
    """
    if date is None:
        date = datetime.now()
    
    weekdays = {
        0: "Montag",
        1: "Dienstag",
        2: "Mittwoch",
        3: "Donnerstag",
        4: "Freitag",
        5: "Samstag",
        6: "Sonntag"
    }
    
    return weekdays[date.weekday()]


def get_time_context(ip_address: Optional[str] = None) -> Dict[str, str]:
    """
    Erstellt einen vollständigen Zeit-Kontext mit Datum, Uhrzeit und Wochentag
    
    Args:
        ip_address: IP-Adresse des Users (optional, wird nicht mehr verwendet)
        
    Returns:
        Dictionary mit allen Zeit-Informationen
    """
    now = datetime.now()
    
    return {
        'current_date': now.strftime('%d.%m.%Y'),
        'current_time': now.strftime('%H:%M'),
        'current_weekday': get_german_weekday(now)
    }
