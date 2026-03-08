"""Launch configuration loader for PersonaUI.

Reads config/launch_options.ini and provides a module-level `config` dict
that any module can import:

    from utils.launch_config import config
    if config['no_gui']:
        ...
"""

import os
import sys
import shutil
import configparser

_SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # src/
_CONFIG_DIR = os.path.join(_SRC_DIR, '..', 'config')
_INI_PATH = os.path.join(_CONFIG_DIR, 'launch_options.ini')
_DEFAULT_PATH = os.path.join(_CONFIG_DIR, 'default', 'launch_options.ini')


def _ensure_ini():
    """Copy default INI if user INI doesn't exist yet."""
    if not os.path.exists(_INI_PATH) and os.path.exists(_DEFAULT_PATH):
        shutil.copy2(_DEFAULT_PATH, _INI_PATH)


def _load():
    _ensure_ini()
    cp = configparser.ConfigParser()
    cp.read(_INI_PATH, encoding='utf-8')

    cfg = {
        # [app]
        'no_gui': cp.getboolean('app', 'no_gui', fallback=False),
        'dev_mode': cp.getboolean('app', 'dev_mode', fallback=False),
        'force_build': cp.getboolean('app', 'force_build', fallback=False),
        # [server]
        'port': cp.getint('server', 'port', fallback=5000),
        'host': cp.get('server', 'host', fallback='127.0.0.1').strip(),
        # [startup]
        'check_updates': cp.getboolean('startup', 'check_updates', fallback=True),
        'show_splash': cp.getboolean('startup', 'show_splash', fallback=True),
        'show_console': cp.getboolean('startup', 'show_console', fallback=False),
        # [dev]
        'vite_port': cp.getint('dev', 'vite_port', fallback=5173),
        'log_level': cp.get('dev', 'log_level', fallback='info').strip().upper(),
    }

    # CLI flags override INI values
    if '--no-gui' in sys.argv:
        cfg['no_gui'] = True
    if '--dev' in sys.argv:
        cfg['dev_mode'] = True
    if '--force-build' in sys.argv:
        cfg['force_build'] = True

    return cfg


config = _load()
