from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# custom imports
import json
import os
from uav_state import UAVGraph
from prompts.query_designer import get_message_classification_prompt, get_elaboration_prompt, get_task_clarification_prompt, get_task_sumarization_prompt
from utils.string_utils import extract_json_text_by_key

with open("./config.json", "r") as fp:
    config = json.load(fp)
    TOGETHERAI_API_BASE = "https://api.together.xyz/v1"
    os.environ['OPENAI_API_BASE'] = TOGETHERAI_API_BASE
    os.environ['OPENAI_API_KEY'] = config['TOGETHER_API_KEY']

FALLBACK_ERR_RESPONSE_UNABLE_HELP = "I'm sorry, I'm unable to answer your query."
SYSTEM_RESPONSE_GLAD = "Glad to be of help."

MODELS = [
    "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
    "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8"
]

class Message(BaseModel):
    message: str

class ChatAgent:
    def __init__(self):
        #self.llm = OpenAI(temperature=0.5)

        self.llm = ChatOpenAI(
            model = MODELS[0],
            temperature = 0.3
        )
        self.chat_history = []
        
    def get_llm(self):
        return self.llm
    
    def get_chat_history(self):
        return self.chat_history
    
    def get_task_summary(self):
        task_summarization_prompt = get_task_sumarization_prompt(chat_messages = self.chat_history)
        messages = [HumanMessage(content = task_summarization_prompt)]
        res = self.llm.invoke(messages)
        res_obj = extract_json_text_by_key(raw_text = res.content, target_key = "task_summary")
        return res_obj["task_summary"]
    
    def get_task_clarification(self, user_message):
        print('chat history length: ', len(self.chat_history))
        task_clarification_prompt = get_task_clarification_prompt(user_message = user_message, context_messages = self.chat_history[-1:])
        messages = [HumanMessage(content = task_clarification_prompt)]
        res = self.llm.invoke(messages)
        res_obj = extract_json_text_by_key(raw_text = res.content, target_key = "task_info")
        if res_obj["task_info"] == 'TASK_CLEAR':
            return 'TASK_CLEAR'
        else:
            self.chat_history.append({"role": "system", "message": res_obj["task_info"]})
            return res_obj["task_info"]

    def get_message_elaboration(self, user_message):
        chat_history = self.chat_history[-51:-1]
        query_elaboration_prompt = get_elaboration_prompt(query = user_message, chat_history = chat_history)
        messages = [HumanMessage(content = query_elaboration_prompt)]
        res = self.llm.invoke(messages)
        print('elaboration raw response: ', res.content)
        res_obj = extract_json_text_by_key(raw_text = res.content, target_key="answer")
        if res_obj != None and "answer" in res_obj and res_obj["answer"] != None:
            print("Elaboration response: ", res_obj['answer'])
            self.chat_history.append({"role": "system", "message": res_obj['answer']})
            return res_obj['answer']
        self.chat_history.append({"role": "system", "message": FALLBACK_ERR_RESPONSE_UNABLE_HELP})
        return FALLBACK_ERR_RESPONSE_UNABLE_HELP
    
    def classify_message(self, user_message: str) -> str:
        query_classification_prompt = get_message_classification_prompt(user_message = user_message, chat_history = self.chat_history[-20:])

        messages = [HumanMessage(content = query_classification_prompt)]
        res = self.llm.invoke(messages)
        self.chat_history.append({"role": "user", "message": user_message})
        print('classification res: ', res.content)
        res_obj = extract_json_text_by_key(raw_text = res.content, target_key = "task_class")
        if res_obj['task_class'] == 'elaboration':
            return "MESSAGE_ELABORATION"
        elif res_obj['task_class'] == 'new_task':
            self.chat_history = []
            return 'EXECUTE_NEW_TASK'
        elif res_obj['task_class'] == 'task_clarification':
            return 'TASK_CLARIFICATION'
        elif res_obj['task_class'] == 'redo_task':
            return 'REDO_TASK'
        return 'MESSAGE_ELABORATION'
    
    def reset_chat_history(self):
        self.chat_history = []

    def add_to_history(self, role, message):
        self.chat_history.append({ "role": role, "message": message })
        

class ChatApp:
    def __init__(self):
        self.app = FastAPI()
        self.agent = ChatAgent()
        self.uav_graph = UAVGraph(chat_agent = self.agent)
        self.knowledge_base = {}
        self.knowledge_base_info = {}
        self.current_message_status = "INIT"
        self.current_task_summary = ""
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
            res = self.agent.classify_message(user_message = msg.message)
            if self.current_message_status != "NEW_TASK_CLARIFICATION" and res == "EXECUTE_NEW_TASK":
                self.agent.reset_chat_history()
                self.current_task_summary = ''
            if res == 'EXECUTE_NEW_TASK' or res == 'TASK_CLARIFICATION':
                self.current_message_status = "NEW_TASK_CLARIFICATION"
                self.agent.add_to_history(role = "user", message = msg.message)
                res = self.agent.get_task_clarification(user_message = msg.message)
                if res == 'TASK_CLEAR':
                    self.current_task_summary = self.agent.get_task_summary()
                    print('\nFinal user task summary: ', self.current_task_summary)
                    response = self.uav_graph.invoke(query = self.current_task_summary, raw_messages = self.knowledge_base)
                    if response != "" or response != None:
                        self.current_message_status = "TASK_RESPONSE_COMPLETED"
                        self.agent.add_to_history(role = "system", message = response)
                        return { "response": response }
                    else:
                        return { "response": FALLBACK_ERR_RESPONSE_UNABLE_HELP }
                else:
                    return { "response": res }
            elif res == 'REDO_TASK':
                self.agent.add_to_history(role = "user", message = msg.message)
                self.current_message_status = 'REDO_TASK'
                response = self.uav_graph.invoke(query = self.current_task_summary, raw_messages = self.knowledge_base)
                if response != "" or response != None:
                    self.current_message_status = "TASK_RESPONSE_COMPLETED"
                    self.agent.add_to_history(role = "system", message = response)
                    return { "response": response }
                else:
                    return { "response": FALLBACK_ERR_RESPONSE_UNABLE_HELP }
            elif res == "MESSAGE_ELABORATION":
                self.agent.add_to_history(role = "user", message = msg.message)
                self.current_message_status = "MESSAGE_ELABORATION"
                res = self.agent.get_message_elaboration(user_message = msg.message)
                return { "response": res }
            else:
                return { "response": SYSTEM_RESPONSE_GLAD }
        
        @self.app.post("/chat-session-end")
        async def end_chat_session(msg: Message):
            self.agent.reset_chat_history()

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
