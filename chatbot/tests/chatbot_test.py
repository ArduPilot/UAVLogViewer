import sys
import os
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import ask_llm
from log_parser import parse_log

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
BATCH_SIZE = 2
QUESTIONS = [
    "What was the highest altitude reached during the flight?",
    "When did the GPS signal first get lost?",
    "What was the maximum battery temperature?",
    "How long was the total flight time?",
    "List all critical errors that happened mid-flight.",
    "When was the first instance of RC signal loss?",
    "Are there any anomalies in this flight?",
    "Was the GPS performance stable?",
    "Do you think this flight was safe?",
    "Can you explain what's wrong with the flight log?"
]

logs = sorted(f for f in os.listdir(LOG_DIR)
              if f.lower().endswith((".bin", ".tlog")))

for batch_idx in range(0, len(logs), BATCH_SIZE):
    batch = logs[batch_idx:batch_idx+BATCH_SIZE]
    md = os.path.join(os.path.dirname(__file__),
                      f"chatbot_test_batch_{batch_idx//BATCH_SIZE+1}.md")

    with open(md, "w", encoding="utf-8") as out:
        out.write(f"# Batch {batch_idx//BATCH_SIZE+1} Results\n\n")
        for lf in batch:
            out.write(f"## {lf}\n\n")
            tel = parse_log(os.path.join(LOG_DIR, lf))
            if "error" in tel:
                out.write(f"**Error:** {tel['error']}\n\n")
                continue

            for i, q in enumerate(QUESTIONS, 1):
                out.write(f"### Q{i}: {q}\n\n")
                try:
                    ans = ask_llm(q, [], tel)
                    out.write(ans.strip() + "\n\n")
                except Exception as e:
                    out.write(f"**Error:** {e}\n\n")
                time.sleep(2)
