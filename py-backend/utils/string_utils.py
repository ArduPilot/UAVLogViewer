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

def extract_json_object_array_by_keys(text, top_level_key, required_keys):
    """
    Extract a JSON object from the text that contains a specific top-level key
    whose value is a list of JSON objects. Then filter this list to only include
    objects that contain all required second-level keys.
    
    Parameters:
        text (str): The raw string potentially containing JSON.
        top_level_key (str): The expected top-level key whose value is a list of dicts.
        required_keys (list): Keys required in each dict inside the list at top_level_key.
    
    Returns:
        list: A filtered list of dicts under the given top-level key.
    """
    # Clean string from code block markers like ```json ... ```
    text = re.sub(r"^```json\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)

    try:
        # Parse JSON string
        data = json.loads(text)
        
        # Check for the presence of the top-level key and ensure it's a list
        if isinstance(data, dict) and top_level_key in data and isinstance(data[top_level_key], list):
            filtered = [
                item for item in data[top_level_key]
                if isinstance(item, dict) and all(k in item for k in required_keys)
            ]
            return filtered
    except json.JSONDecodeError:
        print("Error parsing JSON array from string")
    
    return []

