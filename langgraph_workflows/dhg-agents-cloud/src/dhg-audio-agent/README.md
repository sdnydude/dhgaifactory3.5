# DHG Audio Analysis Agent

Self-hosted audio transcription, translation, summarization, and topic tagging.

**Zero external paid APIs** — everything runs on DHG-owned hardware.

## Features

- **Transcription**: faster-whisper (Whisper large-v3)
- **Speaker Diarization**: pyannote-audio 3.1
- **Translation**: Local LLM via Ollama
- **Summarization**: 3-5 sentence executive summary
- **Topic Tagging**: Structured topic extraction with confidence scores

## Prerequisites

- Docker & Docker Compose
- NVIDIA GPU with CUDA support
- NVIDIA Container Toolkit
- ~10 GB VRAM (for Whisper + Ollama)

## Quick Start

### 1. Clone and Configure

```bash
cd dhg-audio-agent
cp .env.example .env
# Edit .env and add your HF_TOKEN (free HuggingFace token for pyannote)
```

### 2. Build and Start

```bash
make build
make up
make pull-model   # Download LLM model into Ollama
```

### 3. Verify Health

```bash
make health
# Or: curl http://localhost:8100/health
```

### 4. Analyze Audio

```bash
# Async (returns job_id for polling)
curl -X POST http://localhost:8100/analyze \
  -H "Content-Type: application/json" \
  -d '{"audio_path": "/data/audio/sample.wav", "diarize": true}'

# Poll for result
curl http://localhost:8100/jobs/{job_id}
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/analyze` | Submit audio for async analysis |
| GET | `/jobs/{id}` | Get job status and results |
| GET | `/health` | Health check for all services |
| POST | `/analyze/sync` | Synchronous analysis (short audio only) |
| GET | `/models` | List available models |
| GET | `/metrics` | Prometheus metrics |

## Output Format

```json
{
  "transcription": {
    "text": "Full transcript...",
    "segments": [{"start": 0.0, "end": 3.2, "text": "Hello", "speaker": "Speaker_1"}],
    "language": "en",
    "confidence": 0.94
  },
  "translation": null,
  "summary": "Executive summary of the content...",
  "topics": [{"label": "Topic Name", "confidence": 0.92}],
  "metadata": {
    "duration_seconds": 120.5,
    "processing_time_seconds": 45.2,
    "model_versions": {...}
  }
}
```

## Development

```bash
# Local development (requires Python 3.11 + GPU)
pip install -r requirements.txt
make dev

# Run tests
make test

# View logs
make logs
```

## Architecture

```
Audio File → validate_input → transcribe → [translate?] → summarize → tag_topics → Result
                                   ↓
                            (if not English)
```

## Environment Variables

See `.env.example` for all configuration options.

Key settings:
- `HF_TOKEN`: HuggingFace token for pyannote (free, required for diarization)
- `OLLAMA_MODEL`: LLM model for summarization/translation
- `WHISPER_MODEL_SIZE`: Whisper model size (default: large-v3)

## License

Confidential — Digital Harmony Group Internal
