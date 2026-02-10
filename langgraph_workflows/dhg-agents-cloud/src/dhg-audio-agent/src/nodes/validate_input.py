"""
Node 1: validate_input

Verify audio file exists, is a supported format, and is readable.
Per Build Spec Section 3.3 Node 1.
"""

import os
import logging
from pathlib import Path

from ..state import AudioAgentState

logger = logging.getLogger(__name__)

# Supported audio formats
SUPPORTED_FORMATS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".wma", ".aac"}


async def validate_input(state: AudioAgentState) -> dict:
    """
    Validate the input audio file.
    
    Checks:
        1. File exists at audio_path
        2. File size > 0 bytes
        3. Extension is supported
        4. File is readable (can open and read first 1KB)
    
    Returns:
        dict with 'error' key if validation fails, empty dict otherwise
    """
    audio_path = state.get("audio_path", "")
    
    if not audio_path:
        logger.error("No audio_path provided")
        return {"error": "No audio_path provided in request"}
    
    path = Path(audio_path)
    
    # Check 1: File exists
    if not path.exists():
        logger.error(f"Audio file not found: {audio_path}")
        return {"error": f"Audio file not found: {audio_path}"}
    
    # Check 2: File size > 0
    file_size = path.stat().st_size
    if file_size == 0:
        logger.error(f"Audio file is empty: {audio_path}")
        return {"error": f"Audio file is empty (0 bytes): {audio_path}"}
    
    # Check 3: Supported format
    extension = path.suffix.lower()
    if extension not in SUPPORTED_FORMATS:
        logger.error(f"Unsupported audio format: {extension}")
        return {
            "error": f"Unsupported audio format: {extension}. "
                     f"Supported: {', '.join(sorted(SUPPORTED_FORMATS))}"
        }
    
    # Check 4: File is readable
    try:
        with open(path, "rb") as f:
            _ = f.read(1024)  # Read first 1KB
    except PermissionError:
        logger.error(f"Permission denied reading: {audio_path}")
        return {"error": f"Permission denied reading audio file: {audio_path}"}
    except IOError as e:
        logger.error(f"IO error reading file: {e}")
        return {"error": f"Cannot read audio file: {e}"}
    
    logger.info(f"Validated audio file: {audio_path} ({file_size:,} bytes, {extension})")
    return {}
