# Interview Practice Agent

A small local service that runs an interview-practice agent (FastAPI backend) and a minimal frontend. The project is intended for practicing technical interview questions with an LLM-driven agent and collecting feedback at the end of a session.

**Key features**
- Lightweight FastAPI backend providing sessioned interview flows.
- Simple frontend (`frontend/index.html`) that can be used for manual testing or demos.
- Environment-configurable model selection and API key support via `.env`.

**Repository Structure**
- `app/` — Python application code (FastAPI endpoints, orchestrator, agent logic).
- `frontend/` — Minimal static frontend (single `index.html`).
- `requirements.txt` — Python dependencies.

Getting started
---------------

Prerequisites
- Python 3.11+ (recommended).
- Git (optional).

Installation (Windows / cmd.exe)
1. Create and activate a virtual environment:

	 ```cmd
	 python -m venv .venv
	 .\.venv\Scripts\activate
	 ```

2. Install dependencies:

	 ```cmd
	 pip install -r requirements.txt
	 ```

Configuration
-------------
Copy or create a `.env` file in the project root to configure model or API keys used by the agent. Example `.env`:

```
GROQ_API_KEY=your_api_key_here
MODEL_NAME=llama-3.1-8b-instant
```

The project reads `GROQ_API_KEY` and `MODEL_NAME` from environment variables (see `app/config.py`). If you use another model provider or key names, adjust `app/config.py` or add the appropriate environment variables.

Running the backend (development)
---------------------------------
From the project root (with your virtualenv active):

```cmd
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

This starts the FastAPI server on `http://127.0.0.1:8000`. You can open the automatic API docs at `http://127.0.0.1:8000/docs`.

Serving the frontend (optional)
------------------------------
To serve the `frontend/` folder locally (so the browser can load it via HTTP rather than `file://`):

```cmd
python -m http.server 5500 --directory frontend
```

Then open `http://127.0.0.1:5500` in your browser. Adjust ports as needed.

API Endpoints
-------------
The backend exposes a few endpoints for driving an interview session. All request/response bodies are JSON.

- `POST /start` — Start a new interview session.
	- Request body: `{ "role": "Software Engineer", "max_questions": 5 }`
	- Response: `{ "session_id": "...", "first_question": "..." }`

- `POST /answer` — Submit an answer to the current question.
	- Request body: `{ "session_id": "...", "answer": "..." }`
	- Response: `{ "next_message": "...", "finished": false }`

- `POST /feedback` — Request final feedback for a finished session.
	- Request body: `{ "session_id": "..." }`
	- Response: `{ "feedback": "..." }`

Quick examples
--------------
Using the Python `httpx` client (installed via `requirements.txt`):

```python
import httpx

BASE = "http://127.0.0.1:8000"

# Start a session
resp = httpx.post(f"{BASE}/start", json={"role": "Software Engineer", "max_questions": 3})
data = resp.json()
session_id = data["session_id"]
print("First question:", data["first_question"])

# Answer and progress
resp2 = httpx.post(f"{BASE}/answer", json={"session_id": session_id, "answer": "I would use a hash map..."})
print(resp2.json())

# When finished, fetch feedback
resp3 = httpx.post(f"{BASE}/feedback", json={"session_id": session_id})
print(resp3.json())
```

If you prefer `curl` on Windows `cmd.exe`, a typical `curl` command looks like this (PowerShell quoting or cmd escaping may differ):

```cmd
curl -X POST "http://127.0.0.1:8000/start" -H "Content-Type: application/json" -d "{\"role\": \"Software Engineer\", \"max_questions\": 5}"
```

Notes & Development
-------------------
- Sessions are stored in-memory in the current implementation (see `app/main.py`). They will be lost when the process stops. For production use, replace the session store with a database or cache.
- The LLM / agent pieces are implemented inside `app/interview_agent.py`. If you want to swap providers or models, check `app/config.py` and the agent implementation.
- Consider adding unit tests, CI, and a proper contribution guide if you plan to collaborate.

Contributing
------------
- Fork the repo, create a feature branch, and open a pull request. Please include tests for new behavior.

License
-------
This project does not include a license file. Add one (`LICENSE`) if you intend to share or open-source the code.

Contact
-------
If you want help improving the README or adding quick start scripts, ask here or open an issue in the repository.
