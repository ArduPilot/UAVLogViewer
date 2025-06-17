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
import logging

logger = logging.getLogger(__name__)


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
            recent_user_msgs = [
                m["content"]
                for m in self.session_store.get_history(self.session_id)[-5:]
                if m["role"] == "user"
            ]
            combined_query = "\n".join(recent_user_msgs[-1:] + [message])
            logger.info(f"combined_query: {combined_query}")

            raw_types = infer_message_types_llm(combined_query, frozenset(self.tdata.by_type.keys()))
            logger.info(f"raw_types: {raw_types}")
            msg_types = refine_types_with_llm(message, list(raw_types))
            logger.info(f"msg_types: {msg_types}")
            self.session_store.set_last_msg_types(self.session_id, list(msg_types))

        ctx = build_context(self.tdata, msg_types) if msg_types else "No relevant telemetry data found."

        # ---------- System Prompt ----------
        system_prompt = (
            "You are **Falcon-AI**, a UAV telemetry anomaly detection expert trained to identify unusual patterns in ArduPilot flight logs.\n\n"

            "### Objective\n"
            "Review flight telemetry (e.g., GPS, IMU, barometer, battery, RC input) and flag potential anomalies — such as sensor failures, erratic control behavior, or abnormal flight dynamics.\n\n"

            "### Formatting Instructions\n"
            "• Use <b>bold text</b> to highlight critical findings or key metrics.\n"
            "• Use <i>italics</i> for emphasis where needed.\n"
            "• Use <br> for line breaks when you need to separate sections clearly.\n"
            "• Use <ul><li>bullet points</li><li>for lists</li></ul> when appropriate.\n"
            "• Always close HTML tags properly.\n\n"
            "• Respond strictly using HTML formatting. Do not use Markdown or plain text. All bold must use <b>, italics with <i>, and new lines with <br>\n"

            "### Reasoning Strategy\n"
            "• Use flexible, data-driven reasoning rather than rigid thresholds.\n"
            "• Look for sudden changes, flatlines, out-of-range values, or sensor disagreement.\n"
            "• Interpret behavior in context — distinguish minor fluctuations from concerning trends.\n"

            "### Communication Style\n"
            "• Be concise, clear, and structured.\n"
            "• Start with a <b>one-sentence summary</b> of the key finding (or lack thereof).\n"
            "• Cite telemetry field names, values, and precise UTC timestamps to justify observations.\n"
            "• Never invent values. Only discuss what's present in the data.\n"
            "• If uncertain, ask for more data rather than speculating.\n\n"

            "### What Not to Do\n"
            "✘ Do not enforce fixed rules like 'altitude must not drop more than 10 meters/sec.'\n"
            "✘ Do not output long explanations or summaries unless asked.\n"
        )

        # ---------- Analysis Prompt ----------
        analysis_prompt = (
            "### Your internal scratchpad (not visible to the user)\n"
            "1. Parse available telemetry rows: extract key metrics (e.g., GPS status, altitude, attitude, RC input, battery).\n"
            "2. Identify patterns that may signal anomalies:\n"
            "   • Sudden changes or spikes\n"
            "   • Unexpected sensor flatlines or dropouts\n"
            "   • Contradictions across related sensors (e.g., baro vs GPS alt)\n"
            "   • Unusual mode switches or erratic inputs\n"
            "3. Consider the *potential significance* of these observations.\n"
            "4. Draft a concise explanation or request a time slice for deeper review.\n"
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
