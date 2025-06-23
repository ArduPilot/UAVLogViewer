import os
from groq import Groq
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

def get_groq_client():
    """
    Initializes and returns the Groq client using the API key from environment variables.
    Handles potential errors during initialization.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        logger.error("GROQ_API_KEY not found in environment variables. Please set it in your .env file.")
        raise ValueError("GROQ_API_KEY is not set.")
    
    try:
        client = Groq(api_key=api_key)
        # A simple check to see if the client is functional without making a full API call
        logger.info("Groq client appears to be configured correctly.")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Groq client: {e}")
        raise

# Example of how to instantiate the client.
if __name__ == '__main__':
    try:
        client = get_groq_client()
        print("Groq client initialized successfully.")
    except ValueError as e:
        print(e)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
