"""
Node 3: translate

Translate transcript to English using Ollama LLM.
Only executes if source language is not English.
Per Build Spec Section 3.3 Node 3.
"""

import logging
from pathlib import Path

from ..state import AudioAgentState
from ..ollama_client import call_ollama, OllamaError

logger = logging.getLogger(__name__)

# Load prompt template
PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "translate.txt"
SYSTEM_PROMPT_TEMPLATE = PROMPT_FILE.read_text().strip() if PROMPT_FILE.exists() else (
    "You are a professional translator. Translate the following text from {source_language} "
    "to English. Preserve all meaning, technical terms, speaker labels, and formatting. "
    "Output ONLY the translated text, nothing else."
)


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return len(text) // 4


def chunk_text(text: str, max_tokens: int = 4000) -> list[str]:
    """Split text into chunks that fit within token limit."""
    if estimate_tokens(text) <= max_tokens:
        return [text]
    
    # Split by paragraphs (double newlines) or sentences
    paragraphs = text.split("\n\n")
    
    chunks = []
    current_chunk = []
    current_tokens = 0
    
    for para in paragraphs:
        para_tokens = estimate_tokens(para)
        
        if current_tokens + para_tokens > max_tokens and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = [para]
            current_tokens = para_tokens
        else:
            current_chunk.append(para)
            current_tokens += para_tokens
    
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
    
    return chunks


async def translate(state: AudioAgentState) -> dict:
    """
    Translate transcript to English using Ollama.
    
    Only runs if the effective language is not English.
    Uses the translation prompt template.
    
    Returns:
        dict with 'translation' key or 'error' if failed
    """
    # Skip if error already set
    if state.get("error"):
        return {}
    
    transcript_text = state.get("transcript_text", "")
    if not transcript_text:
        return {"translation": None}
    
    # Determine effective language
    effective_language = state.get("language_id") or state.get("detected_language", "en")
    
    # Skip translation if already English
    if effective_language.lower().startswith("en"):
        logger.info("Source is English — skipping translation")
        return {"translation": None}
    
    logger.info(f"Translating from {effective_language} to English")
    
    try:
        # Build system prompt
        system_prompt = SYSTEM_PROMPT_TEMPLATE.replace("{source_language}", effective_language)
        
        # Chunk if necessary
        chunks = chunk_text(transcript_text)
        translated_chunks = []
        
        for i, chunk in enumerate(chunks):
            logger.info(f"Translating chunk {i+1}/{len(chunks)}")
            translation = await call_ollama(
                system_prompt=system_prompt,
                user_prompt=chunk,
                max_tokens=len(chunk) * 2,  # Allow for expansion
                temperature=0.3,
            )
            translated_chunks.append(translation.strip())
        
        full_translation = "\n\n".join(translated_chunks)
        logger.info(f"Translation complete: {len(full_translation)} chars")
        
        return {"translation": full_translation}
        
    except OllamaError as e:
        logger.error(f"Translation failed: {e}")
        return {"error": f"Translation failed: {e.message}"}
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return {"error": f"Translation failed: {e}"}
