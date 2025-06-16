from __future__ import annotations
from typing import Optional, Dict, Any
import os

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain.memory import ConversationSummaryBufferMemory
from langchain.agents import Tool
from functools import partial

from agents.agents import Agent
from core.session_store import SessionStore
from service.llm_router import infer_message_types_llm, refine_types_with_llm
from service.summariser import build_context
from models.telemetry_data import TelemetryData


class AnomalyAgent(Agent):
    """Agent specialized in detecting and analyzing anomalies in UAV telemetry data."""

    def __init__(self, tdata: TelemetryData, session_id: str, session_store: Optional[SessionStore] = None):
        self.tdata = tdata
        self.session_id = session_id
        self.session_store = session_store
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        self.memory = ConversationSummaryBufferMemory(
            llm=self.llm,
            max_token_limit=40000,
            return_messages=True
        )

    def chat(self, message: str) -> str:
        """Process a user message about potential anomalies and return the response.

        Args:
            message: The user's input message about potential anomalies

        Returns:
            str: The agent's response to the message
        """
        msg_types = set()

        if self.session_store:
            last_intent = self.session_store.get_intent(self.session_id)
            print("last_intent", last_intent)

            recent_user_msgs = [
                m["content"]
                for m in self.session_store.get_history(self.session_id)[-5:]
                if m["role"] == "user"
            ]
            combined_query = "\n".join(recent_user_msgs[-2:] + [message])
            print("combined_query", combined_query)

            raw_types = infer_message_types_llm(combined_query, frozenset(self.tdata.by_type.keys()))
            print("raw_types", raw_types)
            msg_types = refine_types_with_llm(message, list(raw_types))
            print("msg_types", msg_types)
            self.session_store.set_last_msg_types(self.session_id, list(msg_types))

        ctx = build_context(self.tdata, msg_types) if msg_types else "No relevant telemetry data found."

        # ---------- System Prompt ----------
        system_prompt = (
            "You are a UAV telemetry anomaly expert.\n\n"
            "Analyze telemetry data logs to detect potential anomalies, sensor failures, or behavioral irregularities.\n\n"
            "You MUST reason through the provided data, identify abnormal trends, and explain findings clearly with timestamps.\n"
            "Respond clearly and concisely, citing numerical evidence, timestamp ranges, and implications.\n"
            "If unsure, ask for more context. Never make up values not in context.\n"
        )

        # ---------- Analysis Prompt ----------
        analysis_prompt = (
            "### Your internal scratchpad\n"
            "1. Summarize the available telemetry metrics.\n"
            "2. Identify potential anomalies (e.g., sensor dropouts, spikes, inconsistent states).\n"
            "3. Suggest potential causes and implications.\n"
            "4. Prepare final explanation or ask for more data.\n"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": analysis_prompt},
        ]

        memory_vars = self.memory.load_memory_variables({})
        summary_msgs = memory_vars.get("chat_history", [])
        messages.extend(summary_msgs)

        ctx_chunks = self.split_context_into_chunks(ctx, max_tokens=50000)

        partial_answers = []
        for chunk in ctx_chunks:
            partial_msg = [
                {"role": "system", "content": system_prompt},
                {"role": "system", "content": analysis_prompt},
                *summary_msgs,
                {"role": "user", "content": f"### Context\n{chunk}\n\n### Question\n{message}"}
            ]
            partial_resp = self.llm.invoke(partial_msg)
            partial_answers.append(partial_resp.content)

        combined = "\n---\n".join(partial_answers)
        summary_prompt = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Original question: {message}\n\nPartial analyses from telemetry slices:\n\n{combined}\n\nPlease merge and summarize the key insights as a final answer."}
        ]
        final_resp = self.llm.invoke(summary_prompt)

        self.memory.save_context({"input": message}, {"output": final_resp.content})

        if self.session_store:
            self.session_store.add_message(self.session_id, "user", message)
            self.session_store.add_message(self.session_id, "assistant", final_resp.content)

        return final_resp.content
