"""
Node 5: tag_topics

Extract main topics from transcript using Ollama LLM.
Returns structured topic labels with confidence scores.
Per Build Spec Section 3.3 Node 5.
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional

from ..state import AudioAgentState
from ..ollama_client import call_ollama, OllamaError

logger = logging.getLogger(__name__)

# Load prompt template
PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "tag_topics.txt"
SYSTEM_PROMPT = PROMPT_FILE.read_text().strip() if PROMPT_FILE.exists() else (
    'You are a content categorization expert. Analyze the following transcript and identify '
    'the 3-8 main topics discussed. Return ONLY a valid JSON array of objects, each with '
    "'label' (string, 2-5 words) and 'confidence' (float 0.0-1.0). "
    'Example: [{"label": "Budget Planning", "confidence": 0.92}, {"label": "Q3 Revenue", "confidence": 0.87}]. '
    'Output valid JSON only, no explanation.'
)

STRICT_JSON_PROMPT = (
    "Your previous response was not valid JSON. Please respond with ONLY a JSON array, "
    "no other text. Format: [{\"label\": \"Topic Name\", \"confidence\": 0.85}]"
)


def extract_json_array(text: str) -> Optional[list]:
    """Try to extract JSON array from text response."""
    text = text.strip()
    
    # Try direct parse first
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass
    
    # Try to find JSON array in text
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass
    
    return None


def validate_topics(topics: list) -> list[dict]:
    """Validate and clean topic list."""
    valid_topics = []
    
    for t in topics:
        if not isinstance(t, dict):
            continue
        
        label = t.get("label", "")
        confidence = t.get("confidence", 0.5)
        
        # Validate label
        if not label or not isinstance(label, str):
            continue
        label = label.strip()
        if len(label) < 2:
            continue
        
        # Validate confidence
        try:
            confidence = float(confidence)
            confidence = min(1.0, max(0.0, confidence))
        except (TypeError, ValueError):
            confidence = 0.5
        
        valid_topics.append({
            "label": label,
            "confidence": confidence,
        })
    
    return valid_topics


def fallback_keyword_extraction(text: str) -> list[dict]:
    """
    Simple fallback topic extraction using keyword frequency.
    Used when LLM fails to return valid JSON.
    """
    import re
    from collections import Counter
    
    # Remove common words
    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "must", "shall", "can", "need", "dare",
        "and", "but", "or", "nor", "for", "yet", "so", "as", "at", "by",
        "to", "from", "in", "out", "on", "off", "over", "under", "again",
        "then", "once", "here", "there", "when", "where", "why", "how",
        "all", "each", "every", "both", "few", "more", "most", "other",
        "some", "such", "no", "not", "only", "own", "same", "than", "too",
        "very", "just", "also", "now", "this", "that", "these", "those",
        "i", "me", "my", "we", "our", "you", "your", "he", "him", "his",
        "she", "her", "it", "its", "they", "them", "their", "what", "which",
        "who", "whom", "whose", "if", "because", "about", "into", "through",
        "during", "before", "after", "above", "below", "between", "with",
    }
    
    # Extract words (3+ chars)
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    words = [w for w in words if w not in stopwords]
    
    # Count frequencies
    counter = Counter(words)
    
    # Get top topics
    topics = []
    for word, count in counter.most_common(5):
        # Capitalize
        label = word.capitalize()
        # Rough confidence based on frequency
        confidence = min(1.0, count / 20)
        topics.append({"label": label, "confidence": round(confidence, 2)})
    
    return topics


async def tag_topics(state: AudioAgentState) -> dict:
    """
    Extract main topics from transcript using Ollama.
    
    Returns structured topic labels with confidence scores.
    Falls back to keyword extraction if JSON parsing fails.
    
    Returns:
        dict with 'topics' key (list of {label, confidence})
    """
    # Skip if error already set
    if state.get("error"):
        return {}
    
    # Use translation if available, otherwise use transcript
    text_to_analyze = state.get("translation") or state.get("transcript_text", "")
    
    if not text_to_analyze:
        logger.warning("No text to analyze for topics")
        return {"topics": []}
    
    logger.info(f"Extracting topics from {len(text_to_analyze)} chars")
    
    try:
        # First attempt
        response = await call_ollama(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=text_to_analyze,
            max_tokens=300,
            temperature=0.3,
        )
        
        topics = extract_json_array(response)
        
        # Retry with stricter prompt if parsing failed
        if topics is None:
            logger.warning("First topic extraction returned invalid JSON, retrying...")
            response = await call_ollama(
                system_prompt=STRICT_JSON_PROMPT,
                user_prompt=f"Text to categorize:\n\n{text_to_analyze[:2000]}",
                max_tokens=300,
                temperature=0.2,
            )
            topics = extract_json_array(response)
        
        # Fallback to keyword extraction
        if topics is None:
            logger.warning("JSON parsing failed, using keyword fallback")
            topics = fallback_keyword_extraction(text_to_analyze)
        else:
            topics = validate_topics(topics)
        
        logger.info(f"Extracted {len(topics)} topics")
        return {"topics": topics}
        
    except OllamaError as e:
        logger.error(f"Topic extraction failed: {e}")
        # Use fallback rather than failing completely
        topics = fallback_keyword_extraction(text_to_analyze)
        return {"topics": topics}
    except Exception as e:
        logger.error(f"Topic extraction error: {e}")
        topics = fallback_keyword_extraction(text_to_analyze)
        return {"topics": topics}
