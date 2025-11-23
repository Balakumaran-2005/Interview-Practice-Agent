# app/main.py
from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uuid

from .interview_agent import (
    InterviewState,
    orchestrator_step,
    feedback_agent,
)

app = FastAPI(title="Interview Practice Agent API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # you can restrict later to ["http://localhost:5500"] etc.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session storage (for demo)
# session_id -> {"state": InterviewState, "history": [...]}
SESSIONS: Dict[str, Dict[str, Any]] = {}


# ---------- Pydantic Models ----------

class StartRequest(BaseModel):
    role: str = "Software Engineer"
    max_questions: int = 5


class StartResponse(BaseModel):
    session_id: str
    first_question: str


class AnswerRequest(BaseModel):
    session_id: str
    answer: str


class AnswerResponse(BaseModel):
    next_message: Optional[str]
    finished: bool


class FeedbackRequest(BaseModel):
    session_id: str


class FeedbackResponse(BaseModel):
    feedback: str


# ---------- Helper ----------

def get_session(session_id: str) -> Dict[str, Any]:
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
    return SESSIONS[session_id]


# ---------- Endpoints ----------

@app.post("/start", response_model=StartResponse)
def start_interview(req: StartRequest):
    """
    Initialize a new interview session.
    Returns a session_id and the first question.
    """
    # Create session_id
    session_id = str(uuid.uuid4())

    # Create state & history
    state = InterviewState(role=req.role, max_questions=req.max_questions)
    history: List[Dict[str, str]] = []

    # First orchestrator step (no user answer yet)
    state, history, bot_msg, finished = orchestrator_step(
        state=state,
        history=history,
        user_answer=None
    )

    # Store in memory
    SESSIONS[session_id] = {
        "state": state,
        "history": history,
        "finished": finished,
    }

    if bot_msg is None:
        raise HTTPException(status_code=500, detail="Failed to generate first question")

    return StartResponse(session_id=session_id, first_question=bot_msg)


@app.post("/answer", response_model=AnswerResponse)
def answer(req: AnswerRequest):
    """
    Send an answer for the current question and get:
    - next question OR follow-up
    - finished flag (True when interview is over)
    """
    session_data = get_session(req.session_id)
    state: InterviewState = session_data["state"]
    history: List[Dict[str, str]] = session_data["history"]
    finished: bool = session_data.get("finished", False)

    if finished:
        # Already finished, no more questions
        return AnswerResponse(next_message=None, finished=True)

    # Run orchestrator step with user's answer
    state, history, bot_msg, finished = orchestrator_step(
        state=state,
        history=history,
        user_answer=req.answer
    )

    # Update session
    session_data["state"] = state
    session_data["history"] = history
    session_data["finished"] = finished
    SESSIONS[req.session_id] = session_data

    return AnswerResponse(
        next_message=bot_msg,   # could be None if interview ended
        finished=finished
    )


@app.post("/feedback", response_model=FeedbackResponse)
def get_feedback(req: FeedbackRequest):
    """
    Generate and return final feedback for the given session.
    Can be called after finished == True.
    """
    session_data = get_session(req.session_id)
    state: InterviewState = session_data["state"]

    feedback = feedback_agent(state)

    # (Optional) delete session after feedback
    # del SESSIONS[req.session_id]

    return FeedbackResponse(feedback=feedback)


@app.get("/")
def root():
    return {"message": "Interview Practice Agent API is running"}
