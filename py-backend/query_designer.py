from prompts.task_designer import get_query_classification_prompt
from langchain_core.messages import HumanMessage

class QueryDesigner:

    def __init__(self, chat_agent):
        self.chat_agent = chat_agent
        self.messages = []

    def classify_query(self, query):

        prompt = get_query_classification_prompt(query = query)
        res = self.chat_agent.run(prompt)
        print('classification res: ', res)

    def summarize_query(self, query):
        self.messages.append({
            "user": query
        })
