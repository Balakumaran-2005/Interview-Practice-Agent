# app/interview_agent.py

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import re
import time

from groq import Groq
from .config import GROQ_API_KEY, MODEL_NAME

# --- Check key ---
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is missing in .env file")

# --- Groq client ---
client = Groq(api_key=GROQ_API_KEY)

# ============================================================
#                     STATE DEFINITION
# ============================================================

@dataclass
class InterviewState:
    role: str
    max_questions: int = 5           # main questions (excluding follow-ups)
    main_questions_asked: int = 0
    qa_pairs: List[Dict[str, str]] = field(default_factory=list)  # [{question, answer}]
    # You can extend later: scores, timestamps, etc.


# ============================================================
#                     COMMON LLM HELPER
# ============================================================

def chat_with_groq(messages, temperature=0.7) -> str:
    """Generic helper to call Groq chat completion."""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()


# ============================================================
#                TIMEOUT / SILENCE AGENT
# ============================================================

TIMEOUT_SYSTEM_PROMPT = """
You are a Silence Recovery Agent.

You detect when the candidate:
- does not answer for a while,
- gives an empty or unhelpful answer,
- is confused or stuck,
- hesitates or goes silent.

Your job:
- Politely re-engage them.
- Ask if they need the question repeated.
- Offer help like: hints, clarification, or a simpler phrasing.
- Keep responses short, friendly, and supportive.
- NEVER pressure the candidate.
- Example responses:
  - "Are you still there? Take your time — would you like me to repeat the question?"
  - "I didn't catch that. Would you like me to repeat or give a hint?"
  - "No worries, take a moment. Should I repeat the question?"
Return a single short sentence or question suitable to be spoken aloud.
"""

def timeout_agent() -> str:
    messages = [
        {"role": "system", "content": TIMEOUT_SYSTEM_PROMPT},
        {"role": "user", "content": "The candidate has been silent or unresponsive. Provide a friendly one-line prompt to re-engage them."}
    ]
    try:
        return chat_with_groq(messages, temperature=0.7)
    except Exception:
        # Fallback friendly message if LLM fails
        return "Are you still there? Take your time — would you like me to repeat the question?"


# ============================================================
#                     AGENT 1: INTERVIEWER
# ============================================================

INTERVIEWER_SYSTEM_PROMPT = """
You are an Interviewer Agent for the role: {role}.

INTERVIEW FLOW (STRICT):

1. FIRST QUESTION — ALWAYS:
   "Can you introduce yourself?"

   Do NOT use any other opening question.
   Do NOT randomize.
   This must be the very first question of every interview.

2. AFTER INTRODUCTION:
   Based on the candidate’s introduction, ask relevant follow-up questions about:
   - Their skills
   - Their education background
   - Their experience (internships, projects)
   - Technologies they mentioned
   - Strengths relevant to the role

   Ask 1–3 follow-ups depending on how detailed their introduction is.
   Do NOT be repetitive.

3. MAIN INTERVIEW — ONLY AFTER INTRODUCTION FOLLOW-UPS:
   Transition naturally into deeper questions such as:
   - Role-specific technical skills
   - Projects related to the role
   - System design (if Software Engineer)
   - Problem-solving and coding practices
   - Behavioral questions (STAR)
   - Scenario questions

4. RULES:
   - Ask only ONE question at a time.
   - Do NOT repeat any previous question.
   - Do NOT paraphrase the same question in different words.
   - Do NOT ask introduction again after the first time.
   - Keep questions relevant to the candidate’s background.
   - Make questions aligned with the role: {role}.
"""

def interviewer_agent(state: InterviewState, history: List[Dict[str, str]]) -> str:
    """Returns the next MAIN interview question."""
    system_prompt = INTERVIEWER_SYSTEM_PROMPT.format(role=state.role)
    messages = [{"role": "system", "content": system_prompt}] + history
    question = chat_with_groq(messages, temperature=0.7)
    return question


# ============================================================
#                     AGENT 2: FOLLOW-UP
# ============================================================

FOLLOWUP_SYSTEM_PROMPT = """
You are a Follow-up Agent for a job interview.

You receive:
- The last main question.
- The candidate’s answer.
- A list of ALL previous questions asked (main + follow-ups).

Your job:
- Decide if a NEW follow-up is needed to probe deeper.
- If needed, generate ONE specific follow-up question.

IMPORTANT RULES:

1. DEPTH:
   - If the answer is incomplete, vague, or off-topic → ask a follow-up.
   - You may ask multiple follow-ups (1 at a time).

2. NO REPETITION:
   - DO NOT repeat or rephrase any previous question.
   - Compare your new question against all previous questions; 
     if it is similar → DO NOT ask it.
   - If ANY similar question exists → output EXACTLY: NONE

3. EDGE-CASE HANDLING:
   - If the answer is irrelevant or does not address the question, 
     ask a clarifying follow-up, BUT still follow the no-duplicate rule.

4. USER REFUSAL:
   - If user clearly says: “I don’t know”, “move on”, “skip”, “no experience”, 
     “next question”, or refuses → output EXACTLY: NONE

5. OUTPUT FORMAT:
   - If NO follow-up is needed → reply EXACTLY: NONE
   - If a follow-up is needed → output ONLY the follow-up question
     (no explanation, no comments)
"""

def followup_agent(last_question: str, last_answer: str, previous_questions: List[str]) -> str:
    """
    Returns either:
    - "NONE"  -> no follow-up
    - "<some question>" -> a follow-up question to ask
    """
    user_content = f"""
Main Question: {last_question}
Candidate Answer: {last_answer}

All Previous Questions:
{previous_questions}
Decide if a follow-up question is needed."""
    messages = [
        {"role": "system", "content": FOLLOWUP_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
    reply = chat_with_groq(messages, temperature=0.4)
    return reply.strip()


# ============================================================
#                     AGENT 3: FEEDBACK
# ============================================================

FEEDBACK_SYSTEM_PROMPT = """
You are an Expert Interviewer in the role.

You are given:
- The role.
- A list of interview questions and the candidate's answers.

Your job:
Provide feedback in EXACTLY this structured format:

1. Overall Summary (3–5 lines)

2. Strengths
- point 1
- point 2
- point 3

3. Areas to Improve
- point 1
- point 2
- point 3

4. Suggestions & Practice Tips
- point 1
- point 2
- point 3

5. Ratings (0–10)
- Communication: x/10
- Technical / Role Knowledge: x/10
- Confidence: x/10
- Domain Expertise: x/10

Feedback should be in organizd manner.
"""

def feedback_agent(state: InterviewState) -> str:
    """Generate structured feedback using all Q&A from state."""
    qa_text_lines = []
    for i, qa in enumerate(state.qa_pairs, start=1):
        q = qa.get("question", "")
        a = qa.get("answer", "")
        qa_text_lines.append(f"Q{i}: {q}\nA{i}: {a}\n")
    qa_text = "\n".join(qa_text_lines)

    user_content = f"Role: {state.role}\n\nHere are the questions and answers:\n\n{qa_text}\n\nNow provide feedback as per the format."

    messages = [
        {"role": "system", "content": FEEDBACK_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
    feedback = chat_with_groq(messages, temperature=0.3)
    return feedback.strip()


# ============================================================
#                 ORCHESTRATOR (CONTROLLER)
# ============================================================

def orchestrator_step(
    state: InterviewState,
    history: List[Dict[str, str]],
    user_answer: Optional[str]
) -> Tuple[InterviewState, List[Dict[str, str]], Optional[str], bool]:
    """
    One step of the Orchestrator Agent.

    Inputs:
      - state: InterviewState (mutable)
      - history: full chat history (system not included)
      - user_answer:
          - None -> means: need to ask the FIRST question
          - str -> the candidate's last answer

    Returns:
      (updated_state, updated_history, next_message, is_finished)

      - next_message: what the bot should say next (question or feedback-intro)
      - is_finished: True when interview is over (ready for feedback)
    """

    # 1) If this is the first step: ask first main question
    if user_answer is None and state.main_questions_asked == 0:
        # Ask first question via Interviewer Agent
        history.append({"role": "user", "content": "Start the interview and ask the first question."})
        question = interviewer_agent(state, history)
        history.append({"role": "assistant", "content": question})

        state.main_questions_asked += 1
        state.qa_pairs.append({"question": question, "answer": ""})

        return state, history, question, False

    # 2) Otherwise, we just received an answer from user
    if user_answer is not None:
        # Save the answer to the last question
        state.qa_pairs[-1]["answer"] = user_answer
        history.append({"role": "user", "content": user_answer})

        # 2.1) Ask Follow-up Agent if needed
        last_q = state.qa_pairs[-1]["question"]
        all_questions = [qa["question"] for qa in state.qa_pairs if qa["question"]]
        followup = followup_agent(last_q, user_answer, all_questions)

        if followup != "NONE":
            # Ask follow-up (does NOT count as a main question)
            history.append({"role": "assistant", "content": followup})
            # Add follow-up as a separate QA pair if you want to track it separately
            state.qa_pairs.append({"question": followup, "answer": ""})
            return state, history, followup, False

        # 2.2) If no follow-up, decide whether to continue with next main question
        if state.main_questions_asked >= state.max_questions:
            # Interview is finished, time for feedback
            return state, history, None, True

        # 2.3) Ask next main question
        question = interviewer_agent(state, history)
        history.append({"role": "assistant", "content": question})

        state.main_questions_asked += 1
        state.qa_pairs.append({"question": question, "answer": ""})

        return state, history, question, False

    # Fail-safe (should not reach here)
    return state, history, None, True


# ============================================================
#                 MAIN CONSOLE INTERVIEW FLOW (stable silence)
# ============================================================

# Silence / filler detection settings
# These counters are per question, reset when a new question is presented
MAX_HESITATION_COUNT = 3  # 1st hesitation -> friendly prompt; 2nd -> repeat question; 3rd -> skip
HESITATION_PHRASES = {
    "", " ", "...", ".", "..",
    "uh", "uhh", "um", "umm", "hmm", "huh", "mm",
    "idk", "i don't know", "i dont know", "dont know", "no idea",
    "no", "nah", "nope", "skip", "next", "none"
}
# allow short positive confirmations to pass (not hesitations)
POSITIVE_SHORTS = {"yes", "y", "ok", "okay", "sure", "fine", "good"}

# helper to detect hesitation / unhelpful answer
def is_hesitation(answer: Optional[str]) -> bool:
    if answer is None:
        return True
    text = answer.strip().lower()
    if text == "":
        return True
    # normalize repeating punctuation / gibberish like "fff" as hesitation if extremely short
    if text in HESITATION_PHRASES:
        return True
    # single letter that's not a meaningful affirmative
    if len(text) == 1 and text not in {"y", "n"}:
        return True
    # short tokens (<=2 chars) that are not positive confirmations
    if len(text) <= 2 and text not in POSITIVE_SHORTS:
        return True
    # if text is largely non-alphabetic and short, treat as hesitation
    if len(text) <= 4 and re.fullmatch(r'[^a-zA-Z0-9\s]+', text):
        return True
    return False

def supportive_repeat_text(original_question: str) -> str:
    """
    Style B — Supportive Repeat:
    "No problem, let me repeat the question so you can answer comfortably: <question>"
    """
    return f"No problem, let me repeat the question so you can answer comfortably:\n{original_question}"

def run_console_interview(role: str = "Software Engineer", max_questions: int = 5):
    state = InterviewState(role=role, max_questions=max_questions)
    history: List[Dict[str, str]] = []

    print(f"\n🚀 Starting multi-agent mock interview for role: {role}")
    print("(Type 'exit' anytime to stop)\n")

    # First orchestrator call -> first question
    state, history, bot_msg, finished = orchestrator_step(state, history, user_answer=None)
    if bot_msg:
        print(f"Interviewer: {bot_msg}\n")

    # Main loop
    while not finished:
        # For the current question, maintain a hesitation counter
        hesitation_count = 0
        captured_answer: Optional[str] = None

        # The "current question" is the last assistant message in state.qa_pairs
        # (safe because we append question when asked)
        if state.qa_pairs:
            current_question = state.qa_pairs[-1]["question"]
        else:
            current_question = None

        # Loop until we obtain a usable answer or decide to skip
        while True:
            user_input = input("You: ")

            # handle explicit exit
            if user_input.strip().lower() in ["exit", "quit", "stop"]:
                print("\n✅ Ending interview early as requested.\n")
                finished = True
                break

            # quick accept for affirmative short replies (treat as answer)
            if user_input.strip().lower() in POSITIVE_SHORTS:
                captured_answer = user_input.strip()
                break

            # detect hesitation / silence
            if is_hesitation(user_input):
                hesitation_count += 1

                if hesitation_count == 1:
                    # 1st hesitation -> friendly LLM prompt via timeout_agent
                    reengage_msg = timeout_agent()
                    print(f"\nInterviewer: {reengage_msg}\n")
                    # continue loop to allow user to respond
                    continue

                elif hesitation_count == 2:
                    # 2nd hesitation -> supportive repeat (Style B)
                    # Repeat the exact question (helpful, not accusatory)
                    repeat_msg = supportive_repeat_text(current_question or "Can you elaborate?")
                    print(f"\nInterviewer: {repeat_msg}\n")
                    # Also append to history as assistant content (so LLM history includes the repeat)
                    history.append({"role": "assistant", "content": repeat_msg})
                    # continue to wait for answer
                    continue

                else:  # hesitation_count >= 3
                    # 3rd hesitation -> soft skip: record skip and move on
                    skip_msg = "No worries, let's move to the next question."
                    print(f"\nInterviewer: {skip_msg}\n")
                    # record a skip answer for analytics / feedback
                    captured_answer = "No response / skipped"
                    break

            else:
                # Non-hesitation input: accept as captured answer
                captured_answer = user_input.strip()
                break

        # if finished was set (user typed exit)
        if finished:
            break

        # Now pass the captured_answer to the orchestrator
        state, history, bot_msg, finished = orchestrator_step(state, history, user_answer=captured_answer)

        # Print whatever the orchestrator returns (follow-up or next question)
        if bot_msg:
            print(f"\nInterviewer: {bot_msg}\n")

    # Feedback phase
    print("\n📝 Generating feedback......\n")
    feedback = feedback_agent(state)
    print("📣 FEEDBACK:\n")
    print(feedback) 

if __name__ == "__main__":
    run_console_interview(role="Software Engineer", max_questions=5)
