"""
Avatar Routes - Avatar-Verwaltung und Upload
"""
from flask import Blueprint, request
import os
import uuid
import json

from utils.config import save_avatar_config
from utils.logger import log
from routes.helpers import success_response, error_response, handle_route_error

avatar_bp = Blueprint('avatar', __name__)

# ── Pfad-Hilfsfunktionen ──

def _avatar_dirs():
    """Gibt (base_dir, avatar_dir, costum_dir) zurück."""
    base_dir = os.path.dirname(os.path.dirname(__file__))
    frontend_public = os.path.normpath(os.path.join(base_dir, '..', 'frontend', 'public'))
    avatar_dir = os.path.join(frontend_public, 'avatar')
    costum_dir = os.path.join(avatar_dir, 'costum')
    return avatar_dir, costum_dir


def _rebuild_avatar_index():
    """Scannt avatar/ und avatar/costum/ und schreibt index.json."""
    avatar_dir, costum_dir = _avatar_dirs()
    os.makedirs(costum_dir, exist_ok=True)

    ext = ('.jpg', '.jpeg', '.png', '.webp')
    avatars = []

    if os.path.exists(avatar_dir):
        for f in sorted(os.listdir(avatar_dir)):
            if f.lower().endswith(ext) and os.path.isfile(os.path.join(avatar_dir, f)):
                avatars.append({'filename': f, 'type': 'standard'})

    if os.path.exists(costum_dir):
        for f in sorted(os.listdir(costum_dir)):
            if f.lower().endswith(ext):
                avatars.append({'filename': f, 'type': 'custom'})

    index_path = os.path.join(avatar_dir, 'index.json')
    with open(index_path, 'w', encoding='utf-8') as fh:
        json.dump({'avatars': avatars}, fh, ensure_ascii=False, indent=2)

    return avatars


@avatar_bp.route('/api/get_available_avatars', methods=['GET'])
@handle_route_error('get_available_avatars')
def get_available_avatars():
    """Rebuilds index.json and returns avatar list (Fallback für Backend-Clients)."""
    avatars = _rebuild_avatar_index()
    return success_response(avatars=avatars)


@avatar_bp.route('/api/save_avatar', methods=['POST'])
@handle_route_error('save_avatar')
def save_avatar():
    """Speichert die Avatar-Auswahl (kein Crop mehr nötig, da alle 1:1)"""
    data = request.get_json()
    avatar_filename = data.get('avatar')
    avatar_type = data.get('avatar_type', 'standard')
    target = data.get('target', 'persona')  # 'persona' oder 'user'
    
    if not avatar_filename:
        return error_response('Kein Avatar ausgewählt')
    
    avatar_data = {
        'avatar': avatar_filename,
        'avatar_type': avatar_type
    }
    
    if target == 'user':
        # User-Profil Avatar speichern
        from routes.user_profile import _load_profile, _save_profile
        profile = _load_profile()
        profile['user_avatar'] = avatar_filename
        profile['user_avatar_type'] = avatar_type
        success = _save_profile(profile)
    else:
        # Persona Avatar speichern
        success = save_avatar_config(avatar_data)
    
    if success:
        return success_response()
    else:
        return error_response('Fehler beim Speichern', 500)


@avatar_bp.route('/api/upload_avatar', methods=['POST'])
@handle_route_error('upload_avatar')
def upload_avatar():
    """
    Lädt ein Custom-Avatar-Bild hoch.
    Erwartet: file + crop_data (JSON) mit x, y, size für den Zuschnitt.
    Speichert als 1024x1024 JPEG in frontend/public/avatar/costum/
    """
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
        return error_response('Datei zu groß (max 10MB)')
    
    # Crop-Daten aus dem Request
    crop_data_str = request.form.get('crop_data')
    
    try:
        from PIL import Image
        img = Image.open(file)
        
        # Wenn Crop-Daten vorhanden, schneide zu
        if crop_data_str:
            crop_data = json.loads(crop_data_str)
            cx = int(crop_data.get('x', 0))
            cy = int(crop_data.get('y', 0))
            csize = int(crop_data.get('size', min(img.size)))
            
            # Crop anwenden
            img = img.crop((cx, cy, cx + csize, cy + csize))
        else:
            # Fallback: Center-Crop zu 1:1
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
        
        # Erstelle costum Verzeichnis
        base_dir = os.path.dirname(os.path.dirname(__file__))
        frontend_public = os.path.join(base_dir, '..', 'frontend', 'public')
        custom_images_dir = os.path.join(frontend_public, 'avatar', 'costum')
        os.makedirs(custom_images_dir, exist_ok=True)
        
        # Generiere eindeutigen Dateinamen
        unique_filename = f"custom_{uuid.uuid4().hex[:12]}.jpeg"
        file_path = os.path.join(custom_images_dir, unique_filename)
        
        # Speichere als JPEG
        img.save(file_path, 'JPEG', quality=90)

        # index.json aktualisieren
        _rebuild_avatar_index()

        return success_response(filename=unique_filename)
        
    except Exception as e:
        log.error("Fehler beim Verarbeiten des Avatar-Uploads: %s", e)
        return error_response(f'Fehler beim Verarbeiten des Bildes: {str(e)}')


@avatar_bp.route('/api/delete_avatar/<filename>', methods=['DELETE'])
@handle_route_error('delete_avatar')
def delete_avatar(filename):
    """Löscht ein Custom-Avatar-Bild"""
    base_dir = os.path.dirname(os.path.dirname(__file__))
    frontend_public = os.path.join(base_dir, '..', 'frontend', 'public')
    custom_images_dir = os.path.join(frontend_public, 'avatar', 'costum')
    file_path = os.path.join(custom_images_dir, filename)
    
    # Sicherheitsprüfung
    if not os.path.abspath(file_path).startswith(os.path.abspath(custom_images_dir)):
        return error_response('Ungültiger Dateipfad')
    
    if not os.path.exists(file_path):
        return error_response('Datei nicht gefunden', 404)

    os.remove(file_path)
    _rebuild_avatar_index()

    return success_response()


@avatar_bp.route('/api/delete_custom_avatar', methods=['POST'])
@handle_route_error('delete_custom_avatar')
def delete_custom_avatar():
    """Löscht ein Custom-Avatar-Bild (POST-Version)"""
    data = request.get_json()
    filename = data.get('filename')
    
    if not filename:
        return error_response('Kein Dateiname angegeben')
    
    base_dir = os.path.dirname(os.path.dirname(__file__))
    frontend_public = os.path.join(base_dir, '..', 'frontend', 'public')
    custom_images_dir = os.path.join(frontend_public, 'avatar', 'costum')
    file_path = os.path.join(custom_images_dir, filename)
    
    if not os.path.abspath(file_path).startswith(os.path.abspath(custom_images_dir)):
        return error_response('Ungültiger Dateipfad')
    
    if not os.path.exists(file_path):
        return error_response('Datei nicht gefunden', 404)

    os.remove(file_path)
    _rebuild_avatar_index()

    return success_response()


@avatar_bp.route('/api/save_user_avatar', methods=['POST'])
@handle_route_error('save_user_avatar')
def save_user_avatar():
    """Speichert die Avatar-Auswahl für das User-Profil."""
    data = request.get_json()
    avatar_filename = data.get('avatar')
    avatar_type = data.get('avatar_type', 'standard')

    if not avatar_filename:
        return error_response('Kein Avatar ausgewählt')

    from routes.user_profile import _load_profile, _save_profile
    profile = _load_profile()
    profile['user_avatar'] = avatar_filename
    profile['user_avatar_type'] = avatar_type
    success = _save_profile(profile)

    if success:
        return success_response()
    else:
        return error_response('Fehler beim Speichern', 500)
