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


# Wochentag-Maps für verschiedene Sprachen
_WEEKDAYS = {
    'german': {0: "Montag", 1: "Dienstag", 2: "Mittwoch", 3: "Donnerstag", 4: "Freitag", 5: "Samstag", 6: "Sonntag"},
    'english': {0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"},
    'french': {0: "Lundi", 1: "Mardi", 2: "Mercredi", 3: "Jeudi", 4: "Vendredi", 5: "Samedi", 6: "Dimanche"},
    'spanish': {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"},
    'italian': {0: "Lunedì", 1: "Martedì", 2: "Mercoledì", 3: "Giovedì", 4: "Venerdì", 5: "Sabato", 6: "Domenica"},
    'portuguese': {0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira", 3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo"},
    'russian': {0: "Понедельник", 1: "Вторник", 2: "Среда", 3: "Четверг", 4: "Пятница", 5: "Суббота", 6: "Воскресенье"},
    'japanese': {0: "月曜日", 1: "火曜日", 2: "水曜日", 3: "木曜日", 4: "金曜日", 5: "土曜日", 6: "日曜日"},
    'chinese': {0: "星期一", 1: "星期二", 2: "星期三", 3: "星期四", 4: "星期五", 5: "星期六", 6: "星期日"},
    'korean': {0: "월요일", 1: "화요일", 2: "수요일", 3: "목요일", 4: "금요일", 5: "토요일", 6: "일요일"},
}


def _get_persona_language() -> str:
    """Lädt die Persona-Sprache aus dem User-Profil."""
    try:
        from routes.user_profile import get_user_profile_data
        profile = get_user_profile_data()
        return (profile.get('persona_language') or 'english').lower()
    except Exception:
        return 'english'


def get_weekday(date: datetime = None, language: str = None) -> str:
    """
    Gibt den Wochentag in der konfigurierten Persona-Sprache zurück.

    Args:
        date: Datum (Standard: heute)
        language: Sprache (Standard: aus User-Profil)

    Returns:
        Wochentag in der jeweiligen Sprache
    """
    if date is None:
        date = datetime.now()
    if language is None:
        language = _get_persona_language()

    weekdays = _WEEKDAYS.get(language, _WEEKDAYS['english'])
    return weekdays[date.weekday()]


# Legacy-Alias für Abwärtskompatibilität
def get_german_weekday(date: datetime = None) -> str:
    """Legacy: Gibt den Wochentag zurück (jetzt sprachabhängig)."""
    return get_weekday(date)


def get_time_context(ip_address: Optional[str] = None) -> Dict[str, str]:
    """
    Erstellt einen vollständigen Zeit-Kontext mit Datum, Uhrzeit und Wochentag.

    Args:
        ip_address: IP-Adresse des Users (optional, wird nicht mehr verwendet)

    Returns:
        Dictionary mit allen Zeit-Informationen
    """
    now = datetime.now()

    return {
        'current_date': now.strftime('%d.%m.%Y'),
        'current_time': now.strftime('%H:%M'),
        'current_weekday': get_weekday(now)
    }
