"""
DHG Audio Analysis Agent — LangGraph Pipeline

StateGraph definition wiring all nodes with conditional edge for translation.
Per Build Spec Section 3.1 and 3.4.
"""

import logging
from langgraph.graph import StateGraph, END

from .state import AudioAgentState
from .nodes.validate_input import validate_input
from .nodes.transcribe import transcribe
from .nodes.translate import translate
from .nodes.summarize import summarize
from .nodes.tag_topics import tag_topics

logger = logging.getLogger(__name__)


def should_translate(state: AudioAgentState) -> str:
    """
    Routing function: decide whether to translate.
    
    Per Build Spec Section 3.4:
    - Returns 'translate' if effective language != 'en'
    - Returns 'summarize' if english (skip translation)
    """
    # If there's an error, go to END
    if state.get("error"):
        return END
    
    # Determine effective language
    effective_lang = state.get("language_id") or state.get("detected_language", "en")
    
    # Check if English
    if effective_lang.lower().startswith("en"):
        logger.info(f"Language is English ({effective_lang}) — skipping translation")
        return "summarize"
    
    logger.info(f"Language is {effective_lang} — routing to translation")
    return "translate"


def should_continue(state: AudioAgentState) -> str:
    """Check if we should continue or stop due to error."""
    if state.get("error"):
        return END
    return "continue"


def build_audio_graph() -> StateGraph:
    """
    Build the audio analysis LangGraph pipeline.
    
    Flow:
        START → validate_input → transcribe → [should_translate?]
                                                  ↓ YES → translate → summarize
                                                  ↓ NO  → summarize (direct)
            summarize → tag_topics → END
    
    Returns:
        Compiled StateGraph
    """
    # Create graph with state schema
    graph = StateGraph(AudioAgentState)
    
    # Add all nodes
    graph.add_node("validate_input", validate_input)
    graph.add_node("transcribe", transcribe)
    graph.add_node("translate", translate)
    graph.add_node("summarize", summarize)
    graph.add_node("tag_topics", tag_topics)
    
    # Set entry point
    graph.set_entry_point("validate_input")
    
    # Wire nodes: validate → transcribe
    graph.add_conditional_edges(
        "validate_input",
        should_continue,
        {
            "continue": "transcribe",
            END: END,
        }
    )
    
    # Conditional edge after transcribe: translate or skip to summarize
    graph.add_conditional_edges(
        "transcribe",
        should_translate,
        {
            "translate": "translate",
            "summarize": "summarize",
            END: END,
        }
    )
    
    # translate → summarize
    graph.add_conditional_edges(
        "translate",
        should_continue,
        {
            "continue": "summarize",
            END: END,
        }
    )
    
    # summarize → tag_topics
    graph.add_conditional_edges(
        "summarize",
        should_continue,
        {
            "continue": "tag_topics",
            END: END,
        }
    )
    
    # tag_topics → END
    graph.add_edge("tag_topics", END)
    
    # Compile and return
    return graph.compile()


# Pre-built graph instance
audio_graph = build_audio_graph()


async def run_audio_pipeline(
    audio_path: str,
    language_id: str = None,
    diarize: bool = True,
    num_speakers: int = None,
) -> AudioAgentState:
    """
    Run the full audio analysis pipeline.
    
    Args:
        audio_path: Path to audio file
        language_id: ISO language code (auto-detect if None)
        diarize: Whether to identify speakers
        num_speakers: Hint for number of speakers
    
    Returns:
        Final state with all results
    """
    initial_state: AudioAgentState = {
        "audio_path": audio_path,
        "language_id": language_id,
        "diarize": diarize,
        "num_speakers": num_speakers,
    }
    
    logger.info(f"Starting audio pipeline: {audio_path}")
    
    result = await audio_graph.ainvoke(initial_state)
    
    if result.get("error"):
        logger.error(f"Pipeline failed: {result['error']}")
    else:
        logger.info("Pipeline completed successfully")
    
    return result
