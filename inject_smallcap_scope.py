import json
import os
from datetime import datetime, timezone
from pathlib import Path

# Scraped Facts from Browser Subagent
URL = "https://groww.in/mutual-funds/icici-prudential-smallcap-fund-direct-plan-growth"
PROCESSED_DIR = Path("data/processed")
CHUNKS_PATH = PROCESSED_DIR / "chunks.jsonl"

SMALLCAP_FACTS = """
ICICI Prudential Smallcap Fund Direct Plan Growth Factsheet Summary (as of 16-17 Apr 2026):

1. Latest NAV: ₹94.31 (as of 16 Apr 2026)
2. Expense Ratio: 0.81%
3. Fund Size (AUM): ₹7,538.12 Crores
4. Risk Category: Very High Risk
5. Benchmark: Nifty Smallcap 250 TRI
6. Minimum Investment: 
   - Lumpsum: ₹5,000
   - SIP: ₹100
7. Returns:
   - 1 Year: +7.60%
   - 3 Year (Annualized): +17.0%
   - 5 Year (Annualized): +19.6%
8. Exit Load: 1% if redeemed within 1 year.
9. Fund Category: Equity - Small Cap

This data is sourced directly from Groww.
"""

def inject_full_smallcap_data():
    if not CHUNKS_PATH.exists():
        print("Chunks file not found!")
        return

    # Create a unique-ish chunk for this new data scope
    new_chunk = {
        "chunk_id": "manual_smallcap_full_scope_01",
        "run_id": "manual_recovery_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "source_id": "manual_groww_smallcap_full",
        "url": URL,
        "domain": "groww.in",
        "fund": "small cap",
        "amc": "ICICI Prudential AMC",
        "scheme": "small cap",
        "doc_type": "Groww scheme specific data and FAQs",
        "section_title": "Scheme Summary & Key Facts",
        "published_or_effective_date": "2026-04-17",
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "text": SMALLCAP_FACTS
    }

    with open(CHUNKS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(new_chunk, ensure_ascii=True) + "\n")
    
    print("Added comprehensive Small Cap facts to chunks.jsonl")

if __name__ == "__main__":
    inject_full_smallcap_data()
