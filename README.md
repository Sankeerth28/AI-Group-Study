# AI Group Study

A small learning platform that simulates study sessions with a QuestionAgent, PeerAgent, TeacherAgent, and SummaryAgent. Includes a FastAPI backend and a Streamlit frontend demo.

## Features
- Deterministic simulated sessions for offline testing
- Pluggable real LLM client for live responses (if OPENAI_API_KEY is set)
- Robust scoring logic for identifying common mistakes (uses fuzzy/lemmatization)
- Streamlit UI demo to start sessions and view transcripts

## Repo layout
See project root for `api/` backend code, `streamlit_app.py` frontend, and `tests/` for unit tests.

## Quickstart (local, no Docker)

1. Activate your virtualenv:
   ```powershell
   .\venv\Scripts\activate    # Windows PowerShell
   source venv/bin/activate   # macOS / Linux
