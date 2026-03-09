"""
Cortex Package — Unified persona memory system.

Contains:
- File I/O (CortexService), directory management, templates
- Update scheduling (tier_checker, tier_tracker, CortexUpdateService)

Re-exports all public symbols for backward compatibility.
"""

# ─── Constants ───────────────────────────────────────────────────────────────
from .constants import CORTEX_FILES, MAX_CORTEX_FILE_SIZE, BASE_DIR, DATA_DIR

# ─── Templates (loaded from .md files on disk) ──────────────────────────────
from .templates_loader import get_templates, get_template, reload_templates

TEMPLATES = get_templates()

MEMORY_TEMPLATE = get_template('memory.md')
SOUL_TEMPLATE = get_template('soul.md')
RELATIONSHIP_TEMPLATE = get_template('relationship.md')
BONDING_TEMPLATE = get_template('bonding.md')
GROWTH_TEMPLATE = get_template('growth.md')

# ─── Directory Functions ─────────────────────────────────────────────────────
from .directories import (
    get_cortex_dir,
    ensure_cortex_dir,
    create_cortex_dir,
    delete_cortex_dir,
    ensure_cortex_dirs,
)

# ─── Service Class ───────────────────────────────────────────────────────────
from .service import CortexService

# ─── Tier System (update scheduling) ────────────────────────────────────────
from .tier_tracker import (
    get_cycle_base, set_cycle_base, reset_session,
    get_progress
)
from .tier_checker import check_and_trigger_cortex_update
from .update_service import CortexUpdateService

__all__ = [
    # Constants
    'CORTEX_FILES', 'MAX_CORTEX_FILE_SIZE', 'BASE_DIR', 'DATA_DIR',
    # Templates
    'TEMPLATES', 'get_templates', 'get_template', 'reload_templates',
    'MEMORY_TEMPLATE', 'SOUL_TEMPLATE', 'RELATIONSHIP_TEMPLATE',
    'BONDING_TEMPLATE', 'GROWTH_TEMPLATE',
    # Directories
    'get_cortex_dir', 'ensure_cortex_dir', 'create_cortex_dir',
    'delete_cortex_dir', 'ensure_cortex_dirs',
    # Service
    'CortexService',
    # Tier system
    'get_cycle_base', 'set_cycle_base', 'reset_session',
    'get_progress', 'check_and_trigger_cortex_update',
    'CortexUpdateService',
]
