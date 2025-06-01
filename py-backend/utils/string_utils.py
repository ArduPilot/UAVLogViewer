import re
import json
import ast

def extract_array_from_response(response_str, target_key):

    """
    Extract a JSON array from a string response given a target key.

    This function searches for the given target_key in the response string,
    and if found, extracts the corresponding JSON array value. The array
    value is expected to be enclosed in [] and contain at least one string
    element, e.g., "[\"first\", \"second\", ...]".

    Args:
        response_str (str): The string response to search.
        target_key (str): The key to search for.

    Returns:
        list: The extracted array, or None if not found.
    """

    
    # check for presence of the target key in the string, followed by [] and "" inside [] in the string    
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
    Extract a JSON object from a raw text string containing a specific key.

    This function searches for a JSON object within the given raw text
    that contains the specified target key, and returns the first matching
    JSON object found. The JSON object is expected to have the key-value
    pair in the format: { "target_key": "some_value" }.

    Parameters:
        raw_text (str): The raw text potentially containing JSON objects.
        target_key (str): The key to search for in the JSON object.

    Returns:
        dict: The first JSON object containing the target key, or None if
              no such object is found or if there is a JSON decoding error.
    """

    # Clean string from code block markers like ```json ... ```
    raw_text = re.sub(r"^```json\s*|\s*```$", "", raw_text.strip(), flags=re.IGNORECASE)
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
    Extract and filter a list of JSON objects by top-level key and required keys.

    This function processes a JSON-formatted string, locating a specified top-level
    key whose value is expected to be a list of JSON objects. It then filters this
    list to include only objects that contain all specified required keys.

    Parameters:
        text (str): The raw string potentially containing the JSON data.
        top_level_key (str): The top-level key within the JSON data whose value is a list of objects.
        required_keys (list): A list of keys that each object within the top-level list must contain.

    Returns:
        list: A list of dictionaries from the JSON array that contain all required keys.
              Returns an empty list if the conditions are not met or if parsing fails.
    """

    # Clean string from code block markers like ```json ... ```
    text = re.sub(r"^```json\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)

    try:
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
