# UAVLogViewer Chatbot Extension

This repository adds a Groq-powered, agentic chatbot backend to the UAVLogViewer project. It enables natural language queries against parsed MAVLink `.bin` (DataFlash) and `.tlog` (telemetry) log files.

## Features

* **Multi-format support:** Parses both `.bin` (ArduPlane DataFlash logs) and `.tlog` (MAVLink telemetry logs).
* **Agentic behavior:** Maintains context across turns and asks clarifying questions when data is missing or ambiguous.
* **Anomaly reasoning:** Provides flexible, model-driven anomaly detection hints (e.g., GPS drops, altitude spikes, battery overheating, RC loss).
* **Example queries:**

  * "What was the highest altitude reached during the flight?"
  * "When did the GPS signal first get lost?"
  * "What was the maximum battery temperature?"
  * "How long was the total flight time?"
  * "List all critical errors that happened mid-flight."
  * "Are there any anomalies in this flight?"

## Requirements

* Python 3.9 or higher
* A valid Groq API Key (sign up at [https://console.groq.com/](https://console.groq.com/))
* Sample `.bin` or `.tlog` files for testing (place in `chatbot/logs/`)

## Manual Setup Steps

1. **Clone the repository**

   ```bash
   git clone https://github.com/zhuhaiweiyan/UAVLogViewer.git
   cd UAVLogViewer/chatbot
   ```

2. **Create a virtual environment**

   ```bash
   python -m venv venv
   ```

3. **Activate the environment**

   * On **Linux/macOS/WSL/Git Bash**:

     ```bash
     source venv/bin/activate
     ```
   * On **Windows CMD**:

     ```cmd
     venv\Scripts\activate
     ```

4. **Install dependencies**

   ```bash
   pip install fastapi uvicorn python-dotenv pyserial pymavlink requests
   ```

5. **Configure environment variables**

   ```bash
   touch .env
   ```

   Edit `.env` and set:

   ```ini
   GROQ_API_KEY=your_api_key_here
   GROQ_MODEL=llama3-70b-8192
   ```

6. **Place log files**
   Copy your `.bin` and `.tlog` files into:

   ```bash
   chatbot/logs/
   ```

## Running the Chatbot Server

Start the FastAPI backend:

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 5000
```

The interactive documentation is available at `http://localhost:5000/docs`.

## Sample API Call

```bash
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"What was the highest altitude reached during the flight?","history":[]}'
```

## Batch Testing Logs

1. Ensure `.bin`/`.tlog` files are in `chatbot/logs/`.
2. Run the batch test script:

   ```bash
   python -m tests.chatbot_test
   ```
3. Review generated Markdown reports in `chatbot/tests/` (`chatbot_test_batch_1.md`, etc.).

## Cleanup

To remove generated artifacts and environment:

```bash
rm -rf venv
rm -rf chatbot/logs/*.md
```

---

Maintained by **Your Name** for the Arena Software Engineering Take-Home Challenge. For questions, contact [angeuswork@gmail.com](mailto:angeuswork@gmail.com).
