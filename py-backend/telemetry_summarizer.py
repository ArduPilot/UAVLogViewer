from google import genai
import json

# custom imports
from prompts.query_designer import get_telemetry_summarization_prompt
from utils.string_utils import extract_json_object_array_by_keys

class TelemetrySummarizer:

    def __init__(self):
        with open("config.json", "r") as fp:
            cfg = json.load(fp)
        self.client = genai.Client(api_key=cfg["GOOGLE_API_KEY"])

    def summarize_telemetry(self, telemetry_data, data_info):
        telemetry_summarization_prompt = get_telemetry_summarization_prompt(telemetry_data=telemetry_data, data_info=data_info)
        response = self.client.models.generate_content(
            model = "gemini-2.0-flash",
            contents = telemetry_summarization_prompt
        )
        print('gemini response: ', response.text)
        response_obj = extract_json_object_array_by_keys(text=response.text, top_level_key="data_summary", required_keys=['description', 'implication', 'timestamp', 'changes_observed'])
        return response_obj

