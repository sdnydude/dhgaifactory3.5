"""
Node 4: summarize

Generate executive summary of transcript using Ollama LLM.
Per Build Spec Section 3.3 Node 4.
"""

import logging
from pathlib import Path

from ..state import AudioAgentState
from ..ollama_client import call_ollama, OllamaError

logger = logging.getLogger(__name__)

# Load prompt template
PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "summarize.txt"
SYSTEM_PROMPT = PROMPT_FILE.read_text().strip() if PROMPT_FILE.exists() else (
    "You are an expert content analyst. Summarize the following transcript in 3-5 concise "
    "sentences. Focus on: key topics discussed, decisions made, action items mentioned, "
    "and any conclusions reached. Be factual — only include information explicitly stated "
    "in the transcript. Do not add interpretation."
)


async def summarize(state: AudioAgentState) -> dict:
    """
    Generate executive summary of the transcript.
    
    Uses translation if available, otherwise uses original transcript.
    
    Returns:
        dict with 'summary' key or 'error' if failed
    """
    # Skip if error already set
    if state.get("error"):
        return {}
    
    # Use translation if available, otherwise use transcript
    text_to_summarize = state.get("translation") or state.get("transcript_text", "")
    
    if not text_to_summarize:
        logger.warning("No text to summarize")
        return {"summary": "No content available for summarization."}
    
    logger.info(f"Generating summary for {len(text_to_summarize)} chars")
    
    try:
        summary = await call_ollama(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=text_to_summarize,
            max_tokens=500,
            temperature=0.3,
        )
        
        summary = summary.strip()
        logger.info(f"Summary generated: {len(summary)} chars")
        
        return {"summary": summary}
        
    except OllamaError as e:
        logger.error(f"Summarization failed: {e}")
        return {"error": f"Summarization failed: {e.message}"}
    except Exception as e:
        logger.error(f"Summarization error: {e}")
        return {"error": f"Summarization failed: {e}"}
