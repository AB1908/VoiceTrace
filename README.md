# Obsidian Voice Assistant (Local-first)

Pipeline:
1. Transcribe audio with local `faster-whisper`
2. Clean transcript with local OpenAI-compatible LLM (LM Studio)
3. Generate task breakdown (local LLM or Claude routing)
4. Append Obsidian-formatted entry to `capture.md`
5. Archive processed audio and write JSONL logs

## Features included
- Claude routing for complex notes
- No Groq fallback
- Optional anonymization before Claude calls
- Task breakdown generation
- Obsidian-specific markdown output

## Project files
- `config.py` configuration and vault paths
- `transcription.py` local Whisper transcription
- `anonymization.py` privacy helpers
- `llm.py` cleanup + task routing
- `process_audio.py` end-to-end pipeline
- `watch.py` folder watcher
- `manual.py` manual trigger
- `metrics_report.py` run summary from metrics logs

## Setup
1. Create virtualenv and install dependencies:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Configure environment:
```bash
cp .env.example .env
# edit .env
```

LM Studio defaults:
- `LOCAL_LLM_API_BASE=http://192.168.1.95:1234/v1`
- `LOCAL_LLM_MODEL=meta-llama-3-8b-instruct`
- `LOCAL_LLM_READ_TIMEOUT_SEC=120` (increase if model is slow)
- `LOCAL_LLM_RETRIES=2` (automatic retry for transient failures)

3. Validate quickly:
```bash
python -c "from config import Config; Config.validate(); print('Config OK')"
```

## Run
Watch mode:
```bash
python watch.py
```

Manual mode:
```bash
python manual.py --all
python manual.py /path/to/audio.m4a
python manual.py --raw-only --all
python manual.py --raw-only /path/to/audio.m4a
python manual.py --clean-only --all
python manual.py --clean-only /path/to/audio.m4a
```

Metrics summary:
```bash
python metrics_report.py
```

## Obsidian folder expectations
Inside your vault:
- `audio/` incoming recordings
- `audio/processed/` archived recordings
- `capture.md` appended processing output
- `raw/` immediate Whisper outputs saved before cleanup
- `sessions/<session-id>/` per-run artifacts and metadata
- `logs/*.jsonl` process events
- `logs/metrics.jsonl` machine-readable run metrics
