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
            last_intent = self.session_store.get_intent(self.session_id)
            print("last_intent", last_intent)

            # Collect message type inference context
            recent_user_msgs = [
                m["content"]
                for m in self.session_store.get_history(self.session_id)[-5:]
                if m["role"] == "user"
            ]
            combined_query = "\n".join(recent_user_msgs[-2:] + [message])
            print("combined_query", combined_query)

            # Use history + current message to infer types
            raw_types = infer_message_types_llm(combined_query, frozenset(self.tdata.by_type.keys()))
            print("raw_types", raw_types)
            msg_types = refine_types_with_llm(message, list(raw_types))  # use only current msg here for refining
            print("msg_types", msg_types)
            self.session_store.set_last_msg_types(self.session_id, list(msg_types))

    
        # Build context from message types
        ctx = build_context(self.tdata, msg_types) if msg_types else "No relevant telemetry data found."
        
        # ---------- 1.  System prompt (core persona + guard-rails) ----------
        system_prompt = (
            # ---------- Persona ----------
            "You are **Falcon-AI**, an aviation data scientist and certified ArduPilot "
            "log analyst.  You chat with UAV pilots and engineers to help them "
            "understand flight-log telemetry (.bin) and diagnose potential issues.\n\n"

            # ---------- Conversational Style ----------
            "### Tone & Voice\n"
            "• Friendly and conversational — think helpful co-pilot, not dry textbook.\n"
            "• Use first-person (“I”) sparingly; prefer direct answers (“The max altitude was…”).\n"
            "• Keep paragraphs short (1-3 sentences) so they render nicely in the chat bubble.\n\n"

            # ---------- Capabilities ----------
            "### What you can do\n"
            "• Parse numeric ranges, trends, and outliers in the provided context.\n"
            "• Cross-reference ArduPilot message definitions "
            "(https://ardupilot.org/plane/docs/logmessages.html) to explain field names.\n"
            "• Perform *reasoned* analysis — not rigid rule checks — and clearly state "
            "uncertainties.\n"
            "• If you require a specific range of telemetry rows that are too large to include directly, call the `slice_context_tool` with the `msg_type` and `time_window` (in UTC timestamp format) to retrieve a summarized slice.\n\n"


            # ---------- Output Guidelines ----------
            "### How to reply\n"
            "1. **Answer first** (1-2 sentences), then **brief justification** with key numbers & timestamps.\n"
            "2. If context seems insufficient, ask a *clarifying follow-up* (e.g., "
            "“Could you share the GPS rows for that time window?”).\n"
            "3. Never invent values that aren’t present; cite only what you see.\n"
            "4. Use UTC timestamps exactly as they appear in the log.\n"
            "5. Aim for ≤ 200 words unless the user explicitly requests more detail.\n"
        )


        # ---------- 2.  “Scratchpad” instructions for chain-of-thought ----------
        analysis_prompt = (
            "### Your analysis scratchpad\n"
            "1. Summarise relevant rows, fields, & units.\n"
            "2. Identify patterns / anomalies (spikes, drops, zeroes, mode changes).\n"
            "3. Formulate the answer or follow-up question.\n"
            "(The scratchpad is *not* shown to the user.)\n"
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
