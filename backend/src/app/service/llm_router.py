"""
LLM-based router: given a natural-language question, return a *set* of
MAVLink message types (strings) that the analysis layer should include
in the context.  Uses OpenAI function-calling for structured output.
"""

from functools import lru_cache
from typing import FrozenSet, Set
import os

from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, request_timeout=8, openai_api_key=os.getenv("OPENAI_API_KEY"))

def make_func_spec(supported_types: Set[str]) -> dict:
    return {
        "name": "select_log_types",
        "description": (
            "Pick the smallest set of MAVLink log message types that contain "
            "enough information to answer the user's question."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "message_types": {
                    "type": "array",
                    "items": {"type": "string", "enum": sorted(supported_types)},
                    "description": "Distinct MAVLink message types to consult."
                }
            },
            "required": ["message_types"],
        },
    }

SYSTEM = SystemMessage(
    content=(
        "You are Falcon-Router, an expert in ArduPilot flight log telemetry. "
        "Your job is to select the *smallest* set of MAVLink message types "
        "required to answer a user's question based on available data.\n\n"
        "Use the function tool only to return the message types — no commentary.\n\n"
        "Reference this documentation for message definitions:\n"
        "▸ https://ardupilot.org/plane/docs/logmessages.html\n\n"
        "Only include message types that are likely relevant — prefer precision over recall."
    )
)

REFINER_SYSTEM = SystemMessage(
    content=(
        "You are a MAVLink log message filter. Your job is to refine a set of message types "
        "suggested by another AI, removing any that are irrelevant, redundant, or noisy.\n\n"
        "Do not introduce new message types. You must only select from the provided list.\n\n"
        "You may refer to the ArduPilot log message definitions at:\n"
        "→ https://ardupilot.org/plane/docs/logmessages.html\n"
        "This link is to help you understand the meaning of fields — not to invent message types "
        "not present in the input list.\n\n"
        "Return the **minimal set** of message types most likely to help answer the user’s question."
    )
)

@lru_cache(maxsize=256)
def infer_message_types_llm(question: str, types: FrozenSet[str]) -> Set[str]:
    user = HumanMessage(content=question)

    resp = _llm(messages=[SYSTEM, user], functions=[make_func_spec(types)])

    if resp.additional_kwargs.get("function_call"):
        import json
        payload = json.loads(resp.additional_kwargs["function_call"]["arguments"])
        selected = set(payload.get("message_types", [])) & types
        return selected or {"ERR"}
    # Fallback if model doesn’t call the function
    return {"ERR"}


def refine_types_with_llm(question: str, raw_types: list[str]) -> set[str]:
    user = HumanMessage(content=(
        f"Original question: {question}\n\n"
        f"Candidate types: {', '.join(sorted(raw_types))}\n\n"
        "Return the refined list of message types that are *most relevant* and *minimally sufficient* "
        "to answer the question. Respond ONLY with a comma-separated list (no commentary)."
    ))
    resp = _llm(messages=[REFINER_SYSTEM, user])
    if resp.content:
        return set(t.strip() for t in resp.content.split(",") if t.strip())
    return set(raw_types)