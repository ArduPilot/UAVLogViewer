from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_openai import ChatOpenAI

# custom imports
import json
import os
from uav_state import UAVGraph

with open("./config.json", "r") as fp:
    config = json.load(fp)
    TOGETHERAI_API_BASE = "https://api.together.xyz/v1"
    os.environ['OPENAI_API_BASE'] = TOGETHERAI_API_BASE
    os.environ['OPENAI_API_KEY'] = config['TOGETHER_API_KEY']


class Message(BaseModel):
    message: str

class ChatAgent:
    def __init__(self):
        #self.llm = OpenAI(temperature=0.5)

        self.llm = ChatOpenAI(
            model = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
            temperature = 0.3
        )
        
    def search_tool(self, query: str) -> str:
        return f"Searching for '{query}'..."

    def run(self, query: str) -> str:
        return self.agent.run(query)
    
    def get_llm(self):
        return self.llm


class ChatApp:
    def __init__(self):
        self.app = FastAPI()
        self.agent = ChatAgent()
        self.uav_graph = UAVGraph(llm = self.agent.get_llm())
        self.knowledge_base = {}
        self.knowledge_base_info = {}

        self.configure_cors()
        self.register_routes()
        

    def configure_cors(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def set_knowledgebase(self, knowledge_base_str):
        self.knowledge_base = json.loads(knowledge_base_str)
        print(self.knowledge_base.keys())
        with open('./flight-telemetry-details.json', 'r') as fp:
            self.knowledge_base_info = json.load(fp)

    def register_routes(self):
        @self.app.post("/chat")
        async def chat_endpoint(msg: Message):
            response = self.uav_graph.invoke(query = msg.message, raw_messages = self.knowledge_base)
            if response != "" or response != None:
                return { "response": response }
            return { "response": "I didn't understand your question! Can you elaborate on your query?"}

        @self.app.post("/chat-knowledge")
        async def establish_knowledgebase(msg: Message):
            try:
                #self.knowledge_base = json.loads(msg.message)
                self.set_knowledgebase(msg.message)
                return {"response": "knowledge base received", "status": 200}
            except json.JSONDecodeError:
                return {"response": "Invalid JSON format", "status": 400}


# Instantiate and expose the FastAPI app
chat_app = ChatApp()
app = chat_app.app
