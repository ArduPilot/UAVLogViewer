# UAV Log Viewer

A web application for viewing and analyzing UAV flight logs with an AI-powered chatbot interface.

## Features

- Interactive 3D visualization of flight paths
- Real-time parameter monitoring
- AI-powered chatbot for data analysis
- SQL and statistical analysis capabilities
- Event logging and analysis

## Prerequisites

- Node.js (v14 or higher)
- Python 3.8 or higher
- npm or yarn package manager

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/UAVLogViewer.git
cd UAVLogViewer
```

2. Install backend dependencies:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
pip install -r requirements.txt
```

3. Install frontend dependencies:
```bash
cd ../frontend
npm install
```

## Running the Application

### Backend Server

1. Navigate to the backend directory:
```bash
cd backend
```

2. Activate the virtual environment (if not already activated):
```bash
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Start the backend server:
```bash
# For production:
python app.py

# For development with hot reloading:
uvicorn app:app --reload --host localhost --port 5000
```
The backend server will start running on `http://localhost:5000`

### Frontend Client

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Start the development server:
```bash
npm run dev
```
The frontend application will start running on `http://localhost:8080`

## Development

- Backend API documentation is available at `http://localhost:5000/api/docs`
- Frontend development server includes hot-reloading for instant feedback
- Backend server will automatically reload when changes are detected using uvicorn

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request




