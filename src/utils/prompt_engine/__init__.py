"""
Prompt Engine Package – File-basiertes Prompt-System mit Tool-Support.

Prompts als Markdown-Dateien in 3 Kategorien:
- core/     → Immer inline im System-Prompt
- files/    → Per read_file Tool für die API verfügbar
- internal/ → Nur intern (Afterthought, Cortex, Autofill)

Usage:
    from utils.prompt_engine import PromptEngine
    engine = PromptEngine()
    system_prompt = engine.build_core_system_prompt(variant='default', runtime_vars={...})
"""

from .engine import PromptEngine

__all__ = ['PromptEngine']
