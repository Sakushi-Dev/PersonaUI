"""
User Profile Routes - Benutzerprofil-Verwaltung
"""
from flask import Blueprint, request
import os
import uuid
import json

from utils.logger import log
from utils.settings_manager import load_section, save_section, get_section_defaults
from routes.helpers import success_response, error_response, handle_route_error

user_profile_bp = Blueprint('user_profile', __name__)

DEFAULT_PROFILE = get_section_defaults('profile')


def _load_profile():
    """Lädt das User-Profil aus settings.json (profile-Sektion)"""
    return load_section('profile')


def _save_profile(profile):
    """Speichert das User-Profil in settings.json (profile-Sektion)"""
    return save_section('profile', profile)


def get_user_profile_data():
    """Öffentliche Funktion zum Laden des User-Profils (für andere Module)"""
    return _load_profile()


@user_profile_bp.route('/api/user-profile', methods=['GET'])
@handle_route_error('get_user_profile')
def get_user_profile():
    """Gibt das User-Profil zurück"""
    profile = _load_profile()
    return success_response(profile=profile)


@user_profile_bp.route('/api/user-profile', methods=['PUT'])
@handle_route_error('update_user_profile')
def update_user_profile():
    """Aktualisiert das User-Profil"""
    data = request.get_json()
    if not data:
        return error_response('Keine Daten')

    current = _load_profile()
    
    # Nur erlaubte Felder aktualisieren
    allowed_keys = {'userName', 'userAvatar', 'userAvatarType', 'userGender', 'userInterestedIn', 'userInfo', 'personaLanguage'}
    for key in allowed_keys:
        if key in data:
            current[key] = data[key]
    
    # Validierung: user_gender
    valid_genders = {'Male', 'Female', 'Other'}
    if current.get('userGender') and current['userGender'] not in valid_genders:
        current['userGender'] = None
    
    # Validierung: userInterestedIn (Liste von Geschlechtern)
    if isinstance(current.get('userInterestedIn'), list):
        current['userInterestedIn'] = [g for g in current['userInterestedIn'] if g in valid_genders]
    else:
        current['userInterestedIn'] = []
    
    # Validierung: userInfo max 500 Zeichen
    if current.get('userInfo') and len(current['userInfo']) > 500:
        current['userInfo'] = current['userInfo'][:500]
    
    # Validierung: userName max 30 Zeichen, nicht leer
    if current.get('userName'):
        current['userName'] = current['userName'].strip()[:30]
    if not current.get('userName'):
        current['userName'] = 'User'
    
    # Validierung: personaLanguage – muss ein nicht-leerer String sein
    if not current.get('personaLanguage') or not isinstance(current['personaLanguage'], str):
        current['personaLanguage'] = 'english'
    else:
        current['personaLanguage'] = current['personaLanguage'].strip().lower()
    
    if _save_profile(current):
        # PromptEngine-Cache invalidieren (user_profile-Werte wie language sind gecached)
        try:
            from utils.provider import get_prompt_engine
            engine = get_prompt_engine()
            if engine:
                engine.invalidate_cache()
        except Exception:
            pass
        return success_response(profile=current)
    else:
        return error_response('Speichern fehlgeschlagen', 500)


@user_profile_bp.route('/api/user-profile/avatar/upload', methods=['POST'])
@handle_route_error('upload_user_avatar')
def upload_user_avatar():
    """Lädt ein User-Avatar-Bild hoch (mit Crop-Verarbeitung)"""
    if 'file' not in request.files:
        return error_response('Keine Datei hochgeladen')
    
    file = request.files['file']
    
    if file.filename == '':
        return error_response('Keine Datei ausgewählt')
    
    # Validiere Dateityp
    allowed_extensions = {'.png', '.jpg', '.jpeg', '.webp'}
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        return error_response('Nur PNG, JPG, JPEG und WebP Dateien sind erlaubt')
    
    # Validiere Dateigröße (max 10MB)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > 10 * 1024 * 1024:
        return error_response('Datei zu groß (max. 10MB)')
    
    # Crop-Daten
    crop_data_str = request.form.get('crop_data')
    
    try:
        from PIL import Image
        img = Image.open(file)
        
        # Wenn Crop-Daten vorhanden
        if crop_data_str:
            crop_data = json.loads(crop_data_str)
            cx = int(crop_data.get('x', 0))
            cy = int(crop_data.get('y', 0))
            csize = int(crop_data.get('size', min(img.size)))
            img = img.crop((cx, cy, cx + csize, cy + csize))
        else:
            # Center-Crop zu 1:1
            w, h = img.size
            min_dim = min(w, h)
            left = (w - min_dim) // 2
            top = (h - min_dim) // 2
            img = img.crop((left, top, left + min_dim, top + min_dim))
        
        # Resize auf 1024x1024
        img = img.resize((1024, 1024), Image.LANCZOS)
        
        # Convert to RGB
        if img.mode in ('RGBA', 'P', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if 'A' in img.mode else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Speichere Datei
        base_dir = os.path.dirname(os.path.dirname(__file__))
        custom_images_dir = os.path.join(base_dir, 'static', 'images', 'custom')
        os.makedirs(custom_images_dir, exist_ok=True)
        
        unique_filename = f"user_{uuid.uuid4().hex[:8]}.jpeg"
        filepath = os.path.join(custom_images_dir, unique_filename)
        
        img.save(filepath, 'JPEG', quality=90)
        
        # Profil aktualisieren
        profile = _load_profile()
        profile['user_avatar'] = unique_filename
        profile['user_avatar_type'] = 'custom'
        _save_profile(profile)
        
        return success_response(filename=unique_filename, avatar_type='custom')
        
    except Exception as e:
        from utils.logger import log
        log.error("Fehler beim User-Avatar-Upload: %s", e)
        return error_response(f'Fehler beim Verarbeiten des Bildes: {str(e)}')
