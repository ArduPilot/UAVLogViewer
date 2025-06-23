# UAV Log Viewer & Flight Assistant

This is a forked and enhanced version of the UAVLogViewer, featuring a new backend and an AI-powered Flight Assistant chatbot to analyze MAVLink flight logs.

# Demo

**[▶️ Click here to watch a demo of the UAV Log Viewer & Flight Assistant](https://drive.google.com/file/d/1gLB6g5n798Gemc8GFtRH6WYCD2jv7hz-/view?usp=sharing)**

---

## Features

*   **Interactive 3D Flight Path Visualization:** View flight paths in Cesium 3D.
*   **Comprehensive Log Plotting:** Analyze various telemetry data points with interactive plots.
*   **AI Flight Assistant:** An agentic chatbot powered by the Groq API to answer questions about your flight logs, detect anomalies, and provide detailed analysis.

## How to Run (Production Mode)

These instructions will guide you through running the production-ready version of the application.

### Prerequisites

*   [Node.js and npm](https://nodejs.org/en/) (v16.x or later recommended)
*   [Python](https://www.python.org/downloads/) (v3.8 or later recommended)
*   [Git](https://git-scm.com/downloads/)
*   A Groq API Key (get one for free at [groq.com](https://groq.com/))

---

### Step 1: Clone the Repository

Clone your forked repository to your local machine:

```bash
git clone https://github.com/YOUR_USERNAME/UAVLogViewer.git
cd UAVLogViewer
```
*(Replace `YOUR_USERNAME` with your GitHub username)*

---

### Step 2: Set Up and Run the Backend Server

The backend is a Python server powered by FastAPI.

1.  **Navigate to the backend directory:**
    ```bash
    cd python-backend
    ```

2.  **Create and activate a Python virtual environment:**
    *   **macOS/Linux:**
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```
    *   **Windows:**
        ```bash
        python -m venv venv
        .\venv\Scripts\activate
        ```

3.  **Install the required Python packages:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Create an environment file for your API key:**
    Create a new file named `.env` in the `python-backend` directory and add your Groq API key to it:
    ```
    GROQ_API_KEY=your_actual_groq_api_key_here
    ```

5.  **Start the backend server:**
    ```bash
    python api_v2.py
    ```
    The backend server will start running on `http://127.0.0.1:8001`. Keep this terminal window open.

---

### Step 3: Build and Run the Frontend Application

The frontend is a Vue.js application. We will create a production build and serve it.

1.  **Open a new terminal window.**

2.  **Navigate to the project's root directory:**
    ```bash
    cd /path/to/your/UAVLogViewer
    ```

3.  **Install the Node.js dependencies:**
    ```bash
    npm install
    ```

4.  **Create the production build:**
    This command bundles the frontend application into a `dist` directory.
    ```bash
    npm run build
    ```
    *You may see warnings about asset sizes, which is normal for this project and can be ignored.*

5.  **Serve the production build:**
    We will use `npx serve` to serve the static files from the `dist` directory.
    ```bash
    npx serve -s dist
    ```
    This will start a server on `http://localhost:3000` (or another available port).

---

### Step 4: Access the Application

You can now open your web browser and navigate to:

**http://localhost:3000**

You should see the UAV Log Viewer interface. You can now upload a `.bin` or `.tlog` file and use the AI Flight Assistant.

---

## Alternative: Development Mode

If you prefer to run in development mode with hot reloading:

1.  **Start the backend server** (as described in Step 2 above)
2.  **In a new terminal, run:**
    ```bash
    npm run dev
    ```
3.  **Access the application at:** `http://localhost:8080`

---

## Usage

1.  **Upload a Flight Log:** Click the upload button and select a `.bin` or `.tlog` file from your UAV.
2.  **View 3D Flight Path:** The application will display your flight path in an interactive 3D environment.
3.  **Ask the AI Assistant:** Use the chat interface to ask questions about your flight data, such as:
    *   "What was the highest altitude reached during the flight?"
    *   "When did the GPS signal first get lost?"
    *   "What was the maximum battery temperature?"
    *   "How long was the total flight time?"
    *   "List all critical errors that happened mid-flight."
    *   "Are there any anomalies in this flight?"

The AI assistant will provide detailed, agentic responses with explanations of how it calculated each answer.

---

## Troubleshooting

*   **Backend Connection Issues:** Ensure the Python backend is running on port 8001 before accessing the frontend.
*   **API Key Issues:** Verify your Groq API key is correctly set in the `.env` file.
*   **Port Conflicts:** If port 3000 is in use, `npx serve` will automatically use the next available port.
*   **Build Errors:** Make sure all Node.js dependencies are installed with `npm install`.

---

## Technical Details

*   **Backend:** FastAPI with Python 3.8+
*   **Frontend:** Vue.js 2.x with Webpack
*   **AI:** Groq API (compound-beta model)
*   **3D Visualization:** Cesium.js
*   **MAVLink Parsing:** pymavlink library
