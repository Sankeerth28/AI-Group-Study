# api/models.py
from pydantic import BaseModel
from typing import List, Any, Optional

class StartSessionRequest(BaseModel):
    topic: str = "strings"
    difficulty: str = "easy"
    question_text: Optional[str] = None

class StartSessionResponse(BaseModel):
    session_id: str
    status: str

class TranscriptTurn(BaseModel):
    agent: str
    content: str
    role: Optional[str] = None
    turn_id: Optional[int] = None

class StepResponse(BaseModel):
    session_id: str
    ready: bool
    transcript: List[TranscriptTurn] = []

class TranscriptResponse(BaseModel):
    session_id: str
    transcript: List[TranscriptTurn] = []
