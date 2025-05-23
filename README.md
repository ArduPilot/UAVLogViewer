
# ✈️ Aero: UAV Log Viewer - Agentic Chatbot Extension

This project extends the [ArduPilot UAVLogViewer](https://github.com/ArduPilot/UAVLogViewer) with an **agentic chatbot backend** powered by Python (FastAPI) and a Large Language Model (LLM). The chatbot allows users to upload MAVLink `.bin` flight logs and ask natural language questions about the telemetry data, including flight summaries and potential anomalies.

---

## 📦 New Backend Module: `Chatbotbackend`

This extension introduces a new backend module, located at the root of the forked repository:

```
Chatbotbackend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── models.py
│   └── Services/
│       ├── __init__.py
│       ├── mavlink_parser.py
│       └── llm_service.py
├── uploads/
├── .env               # (Create manually)
└── requirements.txt
```

---

## 🗂️ Key Files Overview

| File/Folder | Purpose |
|-------------|---------|
| `app/main.py` | FastAPI app with routes `/upload_log/` and `/chat/` |
| `app/models.py` | Pydantic models for data validation |
| `Services/mavlink_parser.py` | Parses MAVLink `.bin` logs via `pymavlink` |
| `Services/llm_service.py` | Handles LLM communication using Langchain |
| `.env` | API keys for LLMs (e.g., Gemini, Anthropic) – *you must create this* |
| `requirements.txt` | All Python package dependencies |

---

## ⚙️ Backend Prerequisites

- Python 3.7+
- pip
- Google Gemini or other LLM API access and key

---

## 🚀 Backend Setup Instructions

1. **Navigate to the Backend Directory**
```bash
cd path/to/your_fork/Chatbotbackend
```

2. **Create the `.env` File**
Create a `.env` file with your API keys:
```env
GEMINI_API_KEY="YOUR_ACTUAL_GEMINI_API_KEY"
ANTHROPIC_API_KEY="YOUR_ACTUAL_ANTHROPIC_KEY"
```
> ⚠️ Be sure to `.gitignore` this file!

3. **Set Up Virtual Environment**
```bash
python -m venv venv
# Activate:
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

4. **Install Dependencies**
```bash
pip install -r requirements.txt
```

5. **Verify Package Structure**
Ensure the following exist:
```
app/__init__.py
app/Services/__init__.py
```

6. **Run the Backend**
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

> FastAPI will now be live at: http://localhost:8000 or http://0.0.0.0:8000

---

## 🧪 API Endpoints

- `POST /upload_log/`  
   → Accepts `.bin` file, parses it, returns `fileId`, summary, and status.

- `POST /chat/`  
   → Accepts `fileId`, `message`, and history. Returns conversation with LLM-generated response.

---

## 💬 Frontend Integration Notes

Integrates with Vue-based frontend (`Chatbot.vue`):

- Users can:
  - Upload `.bin` logs
  - Interact with chatbot using Aero button
  - View real-time responses based on log telemetry

Ensure the backend is running **before** launching the frontend:
```bash
# In root project directory:
npm install
npm run dev
```

---
---

## 🧩 Frontend Troubleshooting Instructions

If you encounter issues during frontend setup or while running the development server, follow these steps:

### 1. Clean Up Node Modules and Cache

If `npm install` fails or gives warnings/errors:
```bash
del package-lock.json
npm cache clean --force
npm install
```

### 2. Fix Missing `JsDataflashParser/parser.js` File

If you see errors like:
```
Field 'browser' doesn't contain a valid alias configuration
...JsDataflashParser\parser doesn't exist
```

➡️ Follow these steps:

1. Navigate to:
```
UAVLogViewer/src/tools/parsers/JsDataflashParser/
```

2. Download the missing `parser.js` file from:
   - [https://github.com/Williangalvani/JsDataflashParser](https://github.com/Williangalvani/JsDataflashParser)

3. Place it inside:
```
UAVLogViewer/src/tools/parsers/JsDataflashParser/parser.js
```

4. Then re-run the frontend:
```bash
npm run dev
```

---

## 🛠️ Built With

- Python, FastAPI, Langchain, Uvicorn
- Pymavlink, dotenv, Werkzeug
- Google Gemini, Anthropic Claude (optional)
- Vue.js, Bootstrap-Vue (frontend)

## 🏆 Related Project: Donna – 3D Virtual Assistant for Purdue Fort Wayne

**Donna** is an award-winning AI-powered virtual assistant built for **Purdue Fort Wayne**. It features:

- 🔹 Natural conversation with **OpenAI GPT** & **Gemini Flash 2.0**
- 🔹 Semantic search via **RAG + Pinecone**
- 🔹 Task automation through **Microsoft Graph**
- 🔹 Real-time voice & lip-sync via **Deepgram**, **Google TTS**, **Rhubarb**
- 🔹 **Indoor campus navigation**, reminders, and accessibility tools

> 🏅 **Winner of the 2025 Diversity, Equity, and Inclusion (DEI) Research Award** at the Purdue Fort Wayne Research Symposium

**🧪 Try it live**:  
[https://donnafrontend-759125479426.us-east4.run.app/](https://donnafrontend-759125479426.us-east4.run.app/)


