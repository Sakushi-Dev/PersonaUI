"""
Prompt Engine Package – Strukturiertes JSON-basiertes Prompt-System.

Ersetzt das alte .txt-basierte System mit:
- JSON-Dateien pro Domain (chat, prefill, afterthought, summary, spec_autofill)
- Prompt-Manifest mit Metadata und Reihenfolge
- Placeholder-Registry mit 3-Phasen-Resolution (static → computed → runtime)
- Varianten-System (default/experimental)

Usage:
    from utils.prompt_engine import PromptEngine
    engine = PromptEngine()
    system_prompt = engine.build_system_prompt(variant='default', runtime_vars={...})
"""

from .engine import PromptEngine

__all__ = ['PromptEngine']
