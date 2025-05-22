# config/settings.py
from pathlib import Path
import yaml
from dotenv import load_dotenv
import os

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Load settings from YAML
config_path = Path(__file__).parent / 'settings.yaml'
with open(config_path, 'r') as file:
    settings = yaml.safe_load(file)

# Extract specific settings for easier access
class Config:
    class Chatbot:
        MAX_HISTORY = settings['chatbot']['max_history']
        TIMEOUT = settings['chatbot']['timeout']
        class LLM:
            MODEL = settings['chatbot']['llm']['model']
            TEMPERATURE = settings['chatbot']['llm']['temperature']
            API_KEY = settings['chatbot']['llm']['api_key']  # Add this line

    class UAV:
        SUPPORTED_FIELDS = settings['uav']['supported_fields']

# Make settings accessible as module attributes
chatbot = Config.Chatbot()
uav = Config.UAV()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Optional, not used with Gemini