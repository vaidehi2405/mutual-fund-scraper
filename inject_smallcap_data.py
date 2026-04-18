import json
import os
from datetime import datetime, timezone
from pathlib import Path

# Data extracted by browser subagent
URL = "https://groww.in/mutual-funds/icici-prudential-smallcap-fund-direct-plan-growth"
MANAGERS_TEXT = """
ICICI Prudential Smallcap Fund Direct Plan Growth Fund Management Details:

Current Fund Managers:
1. Rajat Chandak: Fund Manager since Aug 2022.
2. Aatur Shah: Fund Manager since Apr 2025. Education: CA, CFA, B.Com. 10+ years at ICICI Prudential AMC.
3. Sakshat Goel: Fund Manager since Feb 2026. Education: PGDM (S.P. Jain), B.E. (P.E.S. Institute). Previously with Futures First.
4. Gaurav Jain: Fund Manager since Feb 2026. Education: B.Com, CA, CFA Level III, CS. Previously with Nippon AMC and Wipro Ltd.

This information is sourced from Groww.
"""

CHUNKS_PATH = Path("data/processed/chunks.jsonl")

def append_manual_chunk():
    if not CHUNKS_PATH.exists():
        print("Chunks file not found!")
        return

    # Create a unique-ish chunk for this new data
    manual_chunk = {
        "chunk_id": "manual_smallcap_fund_manager_01",
        "run_id": "manual_import_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "source_id": "manual_groww_smallcap",
        "url": URL,
        "domain": "groww.in",
        "fund": "small cap",
        "amc": "ICICI Prudential AMC",
        "scheme": "small cap",
        "doc_type": "Groww scheme specific data and FAQs",
        "section_title": "Fund Management",
        "published_or_effective_date": "2026-04-17",
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "text": MANAGERS_TEXT
    }

    with open(CHUNKS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(manual_chunk, ensure_ascii=True) + "\n")
    
    print("✅ Manual Small Cap chunk successfully appended to chunks.jsonl")

if __name__ == "__main__":
    append_manual_chunk()
