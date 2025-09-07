from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
import uuid
import datetime

# ---------------------------
# In-memory session store
# ---------------------------
SESSION_STORE = {}

# ---------------------------
# Models
# ---------------------------
class StartSessionRequest(BaseModel):
    topic: str
    difficulty: str
    question_text: str | None = None
    simulate: bool = True


class TranscriptTurn(BaseModel):
    session_id: str
    turn_id: int
    agent: str
    role: str
    content: str
    timestamp: str


class SessionResponse(BaseModel):
    session_id: str
    transcript: list[TranscriptTurn]


# ---------------------------
# FastAPI App
# ---------------------------
app = FastAPI(title="AI Study Group API")

# Allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # loosen for dev
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static if `web/static/` exists
WEB_DIR = Path(__file__).resolve().parent.parent / "web" / "static"
if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


# ---------------------------
# Routes
# ---------------------------
@app.get("/")
def root():
    return {"msg": "AI Study Group backend is running."}


@app.post("/start_session", response_model=SessionResponse)
def start_session(req: StartSessionRequest):
    sid = str(uuid.uuid4())
    now = datetime.datetime.now().isoformat()

    transcript = []
    if req.simulate:
        # Generate a fake transcript
        transcript = [
            TranscriptTurn(
                session_id=sid,
                turn_id=1,
                agent="QuestionAgent",
                role="question",
                content=req.question_text or f"Auto question on {req.topic}",
                timestamp=now,
            ),
            TranscriptTurn(
                session_id=sid,
                turn_id=2,
                agent="PeerAgent",
                role="peer_attempt",
                content="Naive solution with wrong complexity claim. (wrong complexity)",
                timestamp=now,
            ),
            TranscriptTurn(
                session_id=sid,
                turn_id=3,
                agent="Learner",
                role="learner_input",
                content="I think that’s right, but I’m not sure.",
                timestamp=now,
            ),
            TranscriptTurn(
                session_id=sid,
                turn_id=4,
                agent="TeacherAgent",
                role="teacher_reply",
                content="Good start, but complexity is exponential O(2^n), not quadratic.",
                timestamp=now,
            ),
            TranscriptTurn(
                session_id=sid,
                turn_id=5,
                agent="SummaryAgent",
                role="summary",
                content="- **Question**: Write fib\n- **Peer**: naive attempt\n- **Correction**: complexity fixed\n- **Next Steps**: implement & test",
                timestamp=now,
            ),
        ]

    SESSION_STORE[sid] = transcript
    return SessionResponse(session_id=sid, transcript=transcript)


@app.get("/session/{sid}", response_model=SessionResponse)
def get_session(sid: str):
    if sid not in SESSION_STORE:
        raise HTTPException(status_code=404, detail="session not found")
    return SessionResponse(session_id=sid, transcript=SESSION_STORE[sid])


@app.post("/session/{sid}/step", response_model=SessionResponse)
def step_session(sid: str):
    if sid not in SESSION_STORE:
        raise HTTPException(status_code=404, detail="session not found")

    turns = SESSION_STORE[sid]
    new_turn_id = len(turns) + 1
    now = datetime.datetime.now().isoformat()

    turns.append(
        TranscriptTurn(
            session_id=sid,
            turn_id=new_turn_id,
            agent="TeacherAgent",
            role="teacher_reply",
            content="(Simulated) advancing session one step...",
            timestamp=now,
        )
    )
    SESSION_STORE[sid] = turns
    return SessionResponse(session_id=sid, transcript=turns)
