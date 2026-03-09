"""
Constants for the Cortex system.
"""

import os

MAX_CORTEX_FILE_SIZE = 8000  # Max chars per cortex file (~2000 tokens)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATA_DIR = os.path.join(BASE_DIR, 'data')

CORTEX_FILES = ['memory.md', 'soul.md', 'relationship.md', 'bonding.md', 'growth.md']
