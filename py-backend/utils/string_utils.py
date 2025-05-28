import re
import json
import ast

def extract_array_from_response(response_str, target_key):
    """
    Extracts a list of strings from a JSON-like structure in LLM output
    where the given key maps to a string array.

    Returns a list of strings, or None if not found or not valid.
    """
    # Regex to find: "key": [ "value1", "value2", ... ]
    pattern = rf'"{re.escape(target_key)}"\s*:\s*\[(?:\s*"[^"]*"\s*,?\s*)+\]'
    #another_pattern = rf'"{re.escape(target_key)}"\s*:\s*\[(.*?)\]'

    match = re.search(pattern, response_str, re.DOTALL)
    if match:
        json_fragment = "{" + match.group(0) + "}"
        try:
            parsed = json.loads(json_fragment)
            return parsed[target_key]
        except json.JSONDecodeError:
            return None
    return None

def extract_json_text_by_key(raw_text, target_key):
    """
    Searches raw text for a JSON object that contains a specific key
    and returns it as a Python dictionary. Returns None if not found.
    """
    # Match any JSON object containing the key: { "target_key": "some_value" }
    pattern = rf'\{{[^{{}}]*"{re.escape(target_key)}"\s*:\s*"[^"{{}}]*"[^{{}}]*\}}'

    match = re.search(pattern, raw_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None
