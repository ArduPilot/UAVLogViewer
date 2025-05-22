from collections import defaultdict

class SessionManager:
    def __init__(self):
        self.sessions = defaultdict(dict)
    
    def init_session(self, session_id):
        self.sessions[session_id] = {
            "history": [],
            "current_data": None
        }
    
    def update_history(self, session_id, role, content):
        self.sessions[session_id]["history"].append({
            "role": role,
            "content": content
        })