from __future__ import annotations
from typing import Optional
import os

from langchain_openai import ChatOpenAI
from langchain.memory import ConversationSummaryBufferMemory

from agents.agents import Agent
from core.session_store import SessionStore
from service.llm_router import infer_message_types_llm, refine_types_with_llm
from service.summariser import build_context
from models.telemetry_data import TelemetryData
import logging

logger = logging.getLogger(__name__)

class TelemetryAnalysisAgent(Agent):
    """One-per-session conversational assistant."""

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
        """Process a user message and return the response.
        
        Args:
            message: The user's input message
            
        Returns:
            str: The agent's response
        """
        # Default fallback
        msg_types = set()

        if self.session_store:
            # Collect message type inference context
            recent_user_msgs = [
                m["content"]
                for m in self.session_store.get_history(self.session_id)[-5:]
                if m["role"] == "user"
            ]
            combined_query = "\n".join(recent_user_msgs[-2:] + [message])
            logger.info(f"combined_query: {combined_query}")

            # Use history + current message to infer types
            raw_types = infer_message_types_llm(combined_query, frozenset(self.tdata.by_type.keys()))
            logger.info(f"raw_types: {raw_types}")
            msg_types = refine_types_with_llm(message, list(raw_types))  # use only current msg here for refining
            logger.info(f"msg_types: {msg_types}")
            self.session_store.set_last_msg_types(self.session_id, list(msg_types))

    
        # Build context from message types
        ctx = build_context(self.tdata, msg_types) if msg_types else "No relevant telemetry data found."
        
        # ---------- 1. System prompt (core persona + conversational guardrails) ----------
        system_prompt = (
            # ---------- Persona ----------
            "You are <b>Falcon-AI</b>, an expert UAV flight data analyst specializing in ArduPilot telemetry logs (.bin). "
            "You assist UAV engineers and pilots in answering specific questions about their flight logs by referencing telemetry data. "
            "You do not speculate or hypothesize beyond what's shown in the data.\n\n"

            # ---------- Formatting Instructions ----------
            "### Formatting Guidelines\n"
            "• Use <b>bold text</b> to highlight key metrics or important findings.\n"
            "• Use <i>italics</i> for emphasis where appropriate.\n"
            "• Use <br> for line breaks when you need to separate sections clearly.\n"
            "• Use <ul><li>bullet points</li><li>for lists</li></ul> when presenting multiple items.\n"
            "• Always close HTML tags properly.\n\n"

            # ---------- Tone & Style ----------
            "### Style Guidelines\n"
            "• Clear, direct, and conversational — act like a skilled co-pilot, not a textbook.\n"
            "• Use concise language: respond in 1–2 short paragraphs (≤ 200 words).\n"
            "• Prefer plain language ('Altitude dropped sharply') over jargon.\n"
            "• Use first-person <i>sparingly</i>. Favor direct descriptions: 'The max altitude was...'\n"
            "• Always include relevant units (e.g., m/s, m, degrees) and precise UTC timestamps.\n\n"

            "### When to Ask for Clarification\n"
            "• If the question lacks specific field names or contextual clues, do NOT make assumptions.\n"
            "• If you are unsure what the user is referring to — based on the current query and prior messages — ask for clarification.\n"
            "• Your goal is to avoid misinterpretation by prompting the user to narrow down or specify their request.\n\n"

            # ---------- Capabilities ----------
            "### What You Can Do\n"
            "• Reference telemetry data rows provided in context.\n"
            "• Cite exact field names and values to support the answer.\n"
            "• Use ArduPilot message definitions (https://ardupilot.org/plane/docs/logmessages.html) to interpret field names.\n"
            "• Do not speculate or invent data. Only report what's shown.\n\n"

            # ---------- Response Format ----------
            "### Response Structure\n"
            "1. <b>Answer first</b> (1–2 clear sentences).<br>"
            "2. <b>Brief justification</b> with key values and timestamps.<br>"
            "3. If the question is ambiguous, ask the user for clarification instead of answering directly.<br>"
            "4. Keep it focused and actionable."
            "5. Respond strictly using HTML formatting. Do not use Markdown or plain text. All bold must use <b>, italics with <i>, and new lines with <br>\n"
        )

        # ---------- 2. Internal analysis prompt (chain-of-thought, not shown to user) ----------
        analysis_prompt = (
            "### Your analysis scratchpad (not visible to user)\n"
            "1. Review telemetry rows in context — extract relevant fields, values, and UTC timestamps.\n"
            "2. Match these to the user’s question — identify what’s directly answerable.\n"
            "3. Structure a concise answer or follow-up request based strictly on observed data.\n"
        )

        # ---------- 3.  Build message list for Chat-Completion ---------------
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": analysis_prompt},
        ]

        memory_vars = self.memory.load_memory_variables({})
        summary_msgs = memory_vars.get("chat_history", [])
        messages.extend(summary_msgs)

        ctx_chunks = self.split_context_into_chunks(ctx, max_tokens=40000)

        partial_answers = []
        for chunk in ctx_chunks:
            partial_msg = [
                {"role": "system", "content": system_prompt},
                {"role": "system", "content": analysis_prompt},
                *summary_msgs,  # if memory is light
                {"role": "user", "content": f"### Context\n{chunk}\n\n### Question\n{message}"}
            ]
            partial_resp = self.llm.invoke(partial_msg)
            partial_answers.append(partial_resp.content)


        # Final aggregation step
        combined = "\n---\n".join(partial_answers)
        summary_prompt = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Original question: {message}\n\n Here are partial analyses from multiple telemetry slices:\n\n{combined}\n\nPlease merge and summarize the key insights, as if answering the original question."}
        ]
        final_resp = self.llm.invoke(summary_prompt)

        # save turn to session store
        self.memory.save_context({"input": message}, {"output": final_resp.content})

        if self.session_store:
            self.session_store.add_message(self.session_id, "user", message)
            self.session_store.add_message(self.session_id, "assistant", final_resp.content)

        return final_resp.content
