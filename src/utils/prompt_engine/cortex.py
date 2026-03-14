"""
CortexMixin — Cortex tool definitions and virtual file access.
"""

from typing import Dict, Any, List

from ..logger import log


_FALLBACK_CORTEX_TOOLS = [
    {
        "name": "read_file",
        "description": "Reads the current content of one of your Cortex files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "enum": ["memory.md", "soul.md", "relationship.md"],
                    "description": "Name of the Cortex file to read"
                }
            },
            "required": ["filename"]
        }
    },
    {
        "name": "write_file",
        "description": "Writes new content to one of your Cortex files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "enum": ["memory.md", "soul.md", "relationship.md"],
                    "description": "Name of the Cortex file to write"
                },
                "content": {
                    "type": "string",
                    "description": "The new complete file content (Markdown format)."
                }
            },
            "required": ["filename", "content"]
        }
    }
]


class CortexMixin:
    """Provides cortex tool definitions and virtual cortex file reading."""

    def get_cortex_tools(self) -> List[Dict[str, Any]]:
        """Returns cortex tool definitions from internal/cortex_update_tools.json."""
        tool_data = self.read_internal_json('cortex_update_tools')
        if not tool_data:
            return _FALLBACK_CORTEX_TOOLS

        read_desc = tool_data.get('read_file', {})
        write_desc = tool_data.get('write_file', {})

        return [
            {
                "name": "read_file",
                "description": read_desc.get('tool_description',
                    "Reads the current content of one of your Cortex files."),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "enum": ["memory.md", "soul.md", "relationship.md"],
                            "description": read_desc.get('filename_description',
                                "Name of the Cortex file to read")
                        }
                    },
                    "required": ["filename"]
                }
            },
            {
                "name": "write_file",
                "description": write_desc.get('tool_description',
                    "Writes new content to one of your Cortex files."),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "enum": ["memory.md", "soul.md", "relationship.md"],
                            "description": write_desc.get('filename_description',
                                "Name of the Cortex file to write")
                        },
                        "content": {
                            "type": "string",
                            "description": write_desc.get('content_description',
                                "The new complete file content (Markdown format).")
                        }
                    },
                    "required": ["filename", "content"]
                }
            }
        ]

    @staticmethod
    def _get_cortex_virtual_files() -> List[Dict[str, str]]:
        """Returns cortex files as virtual file entries if cortex is enabled."""
        try:
            from utils.settings_manager import get_value
            if not get_value('cortex', 'enabled', True):
                return []
        except Exception:
            pass

        return [
            {'filename': 'cortex_memory.md', 'description': 'Your memories about the user and shared experiences'},
            {'filename': 'cortex_soul.md', 'description': 'Your identity, values, growth, and inner reflections'},
            {'filename': 'cortex_relationship.md', 'description': 'Your relationship with the user'},
        ]

    def _read_cortex_file(self, virtual_name: str, placeholders: dict) -> str:
        """Reads a cortex file from the active persona's cortex directory."""
        cortex_name_map = {
            'cortex_memory.md': 'memory.md',
            'cortex_soul.md': 'soul.md',
            'cortex_relationship.md': 'relationship.md',
        }
        real_name = cortex_name_map.get(virtual_name)
        if not real_name:
            return "Unknown cortex file"

        try:
            from ..provider import get_cortex_service
            from ..config import get_active_persona_id
            persona_id = get_active_persona_id()
            cortex_service = get_cortex_service()
            content = cortex_service.read_file(persona_id, real_name)
            if content:
                return content
            return f"(empty — no {real_name} entries yet)"
        except Exception as e:
            log.warning("Cortex file %s read failed: %s", virtual_name, e)
            return f"(cortex not available: {e})"
