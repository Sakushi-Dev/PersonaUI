"""
User Profile Routes - Benutzerprofil-Verwaltung
"""
from flask import Blueprint, request
import os
import uuid
import json

from utils.logger import log
from routes.helpers import success_response, error_response, handle_route_error

user_profile_bp = Blueprint('user_profile', __name__)

PROFILE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'settings', 'user_profile.json')

DEFAULT_PROFILE = {
    "user_name": "User",
    "user_avatar": None,
    "user_avatar_type": None,
    "user_type": None,
    "user_type_description": None,
    "user_gender": None,
    "user_interested_in": [],
    "user_info": ""
}


def _load_profile():
    """Lädt das User-Profil aus JSON-Datei"""
    try:
        if os.path.exists(PROFILE_FILE):
            with open(PROFILE_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
            # Merge mit Defaults
            merged = {**DEFAULT_PROFILE, **saved}
            return merged
        return dict(DEFAULT_PROFILE)
    except Exception as e:
        log.error("Fehler beim Laden des User-Profils: %s", e)
        return dict(DEFAULT_PROFILE)


def _save_profile(profile):
    """Speichert das User-Profil in JSON-Datei"""
    try:
        os.makedirs(os.path.dirname(PROFILE_FILE), exist_ok=True)
        with open(PROFILE_FILE, 'w', encoding='utf-8') as f:
            json.dump(profile, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        log.error("Fehler beim Speichern des User-Profils: %s", e)
        return False


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
    allowed_keys = {'user_name', 'user_avatar', 'user_avatar_type', 'user_type', 'user_type_description', 'user_gender', 'user_interested_in', 'user_info'}
    for key in allowed_keys:
        if key in data:
            current[key] = data[key]
    
    # Validierung: user_gender
    valid_genders = {'Männlich', 'Weiblich', 'Divers'}
    if current.get('user_gender') and current['user_gender'] not in valid_genders:
        current['user_gender'] = None
    
    # Validierung: user_interested_in (Liste von Geschlechtern)
    if isinstance(current.get('user_interested_in'), list):
        current['user_interested_in'] = [g for g in current['user_interested_in'] if g in valid_genders]
    else:
        current['user_interested_in'] = []
    
    # Validierung: user_info max 500 Zeichen
    if current.get('user_info') and len(current['user_info']) > 500:
        current['user_info'] = current['user_info'][:500]
    
    # Validierung: user_name max 30 Zeichen, nicht leer
    if current.get('user_name'):
        current['user_name'] = current['user_name'].strip()[:30]
    if not current.get('user_name'):
        current['user_name'] = 'User'
    
    if _save_profile(current):
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
