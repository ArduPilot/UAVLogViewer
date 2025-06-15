from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import uuid
from dotenv import load_dotenv
from agent_orchestrator import AgentOrchestrator

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Initialize agent orchestrator
orchestrator = AgentOrchestrator()

@app.route('/', methods=['GET'])
def index():
    return jsonify({'message': 'Server is running'}), 200


@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message')
        session_id = data.get('sessionId')
        flight_data = data.get('flightData')  # Get flight data from frontend
        
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400
            
        # Generate new session ID if none provided
        if not session_id:
            session_id = str(uuid.uuid4())
            
        response = orchestrator.process_message(user_message, session_id, flight_data)
        # Include session ID in response
        response['sessionId'] = session_id
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000) 