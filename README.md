# **AI Interview Practice Agent — README**

A multi-agent AI interview simulation system with camera-based proctoring, voice input, adaptive questioning, and automated feedback.
Built using **FastAPI (backend)** + **Vanilla JS/HTML/CSS (frontend)** + **Groq LLMs (Interview, Follow-Up, Feedback Agents)**.

---

## 🚀 **Features**

* 🎤 **Voice-based interview** (speech-to-text + TTS)
* 🎥 **Camera verification** (face detection, multiple-face warning)
* 🧠 **Agentic Interview Flow**

	* Introduction → follow-ups → role-specific technical questions
* ⏳ **Silence Detection Agent** (automatically re-engages user)
* 📝 **Automated feedback** (communication, confidence, technical score)
* 🔄 **Adaptive follow-ups** (no repetition, depth-focused)
* 📦 **Fully local web UI + FastAPI backend**

---

# 🛠️ **Setup Instructions**

### **1. Clone the Repository**

```bash
git clone https://github.com/Balakumaran-2005/Interview-Practice-Agent
cd Interview-Practice-Agent
```

### **2. Create a Virtual Environment**

```bash
python -m venv venv
source venv/bin/activate    # Linux/Mac
venv\Scripts\activate       # Windows
```

### **3. Install Backend Requirements**

```bash
pip install -r requirements.txt
```

### **4. Add `.env` File**

Create `.env` in project root:

```
GROQ_API_KEY=your_key_here
MODEL_NAME=llama3-70b-versatile
```

### **5. Start Backend Server**

```bash
uvicorn app.main:app --reload
```

This starts the FastAPI backend at:

**[http://localhost:8000](http://localhost:8000)**

### **6. Run the Frontend**

Just open **index.html** in your browser (Chrome recommended).

> If Chrome blocks mic/camera for local files, use a static server:

```bash
python -m http.server 5500
```

---

# 🧠 **Agent Architecture**

## **1. Interviewer Agent**

* Starts every interview with **“Introduce yourself”** (mandatory).
* Extracts signals from introduction → asks relevant follow-ups.
* Moves into deeper role-based questions (system design, technical, behavioral).
* Avoids repetition, maintains context via history.

**Purpose:**
To simulate a *real interviewer* who adapts based on candidate background.

---

## **2. Follow-up Agent**

* Evaluates:

	* relevance of answer
	* completeness
	* depth and clarity
* Generates follow-up ONLY IF:

	* answer is vague, shallow, or off-topic
	* deeper probing is meaningful
* Avoids duplicates using full question history.

**Purpose:**
To create *human-like adaptive probing* rather than linear question flow.

---

## **3. Silence Recovery Agent**

Triggers when:

* User stays silent too long
* User gives hesitation tokens (“umm”, “...”, “idk”, etc.)
* User sounds confused

Provides:

* gentle re-engagement
* offers question repeating
* never pressures user
* prevents awkward long pauses

**Purpose:**
To mimic real interviewer behavior during silence and improve UX.

---

## **4. Feedback Agent**

Uses all Q&A pairs to generate:

* Summary
* Strengths
* Areas to improve
* Practice tips
* 0–10 ratings (Communication, Tech, Confidence)

**Purpose:**
To give structured, consistent evaluation like HR/Tech panel feedback.

---

# 🧩 **Design Decisions & Reasoning**

### **1. Multi-Agent Instead of One Agent**

One LLM prompt becomes confusing quickly.
Splitting roles enables:

* clearer responsibilities
* reduced hallucinations
* predictable interview flow
* human-like interaction logic

### **2. Strict Interview Script**

You enforced:

* Always start with **introduce yourself**
* Follow-ups anchored to intro
* No repeated questions
	→ This ensures consistency & a realistic structured interview.

### **3. Silence/Hesitation Logic**

Real interviews include:

* pauses
* candidate confusion
* request to repeat questions

So we built:

* hesitation counter
* escalating prompts
* supportive repeat function

This mimics real HR behavior and handles many edge cases.

### **4. Orchestrator Pattern**

All agents plug into a single function:

```
orchestrator_step()
```

This ensures:

* deterministic flow
* isolation of agent logic
* simple session storage
* easier debugging

### **5. Local Web UI + FastAPI**

* avoids framework complexity
* lightweight
* portable
* easy to deploy anywhere
* perfect for hackathons & demos

---

# 🏗️ **Backend Architecture (FastAPI)**

```
/app
 ├── main.py                # FastAPI server & endpoints
 ├── interview_agent.py     # All agents + orchestrator
 ├── config.py              # API keys / Model names
 ├── ...
```

### **Key Components**

* `/start` → initializes session + first question
* `/answer` → runs orchestrator + follow-ups
* `/feedback` → generates final report
* In-memory session store (can be replaced with Redis/DB)

### **Why FastAPI?**

* Async
* Very fast
* Auto-generated API docs
* Works perfectly with JS frontend

---

# 🎨 **Frontend Architecture (HTML/JS)**

### **Components**

* **Camera Module**

	* Uses `face-api.js`
	* Detects single face
	* Warns if none/multiple faces
	* Prevents cheating / improves realism

* **Voice Module**

	* Browser SpeechRecognition API
	* Handles pauses automatically
	* Speech synthesis for interviewer voice

* **UI Components**

	* Chat interface
	* Editable transcript box
	* Feedback panel

### **Why Vanilla JS?**

* Faster to load
* No frontend build steps
* Works offline
* Highly customizable

---

# 📌 **Future Improvements**

* Add scoring model
* Store logs in a DB
* Add coding interview mode
* WebRTC-based interview recording
