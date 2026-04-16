"""
Comprehensive test: all in-scope topics × all 5 funds.
Tests the full pipeline end-to-end and reports PASS/FAIL for each.
"""
import os, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from dotenv import load_dotenv; load_dotenv()

from app.classify import detect_scheme, detect_topic
from app.retriever import retrieve_chunks
from app.pipeline import get_collection, get_embedder, run_pipeline

# ── Step 1: Verify detect_scheme mapping ──
print("=" * 70)
print("STEP 1: SCHEME DETECTION MAPPING")
print("=" * 70)
scheme_tests = {
    "bluechip fund": "large_cap",
    "large cap fund": "large_cap",
    "largecap fund": "large_cap",
    "flexicap fund": "flexicap",
    "flexi cap fund": "flexicap",
    "midcap fund": "midcap",
    "mid cap fund": "midcap",
    "smallcap fund": "small_cap",
    "small cap fund": "small_cap",
    "ELSS fund": "elss",
    "tax saver fund": "elss",
}

for query, expected in scheme_tests.items():
    result = detect_scheme(query)
    status = "PASS" if result == expected else f"FAIL (got '{result}', expected '{expected}')"
    print(f"  '{query}' → {result}  [{status}]")

# ── Step 2: Verify chunk retrieval per scheme ──
print("\n" + "=" * 70)
print("STEP 2: CHUNK RETRIEVAL PER SCHEME (no LLM call)")
print("=" * 70)
collection = get_collection()
embedder = get_embedder()

funds = {
    "bluechip": "large_cap",
    "flexicap": "flexicap",
    "midcap": "midcap",
    "small cap": "small_cap",
    "ELSS": "elss",
}
topics_queries = [
    ("expense ratio", "What is the expense ratio of the {fund} fund?"),
    ("exit load", "What is the exit load of the {fund} fund?"),
    ("minimum sip", "What is the minimum sip for the {fund} fund?"),
    ("lock-in period", "What is the lock-in period of the {fund} fund?"),
    ("nav", "What is the nav of the {fund} fund?"),
    ("riskometer", "What is the riskometer of the {fund} fund?"),
]

retrieval_results = {}
for fund_name, scheme_id in funds.items():
    retrieval_results[fund_name] = {}
    print(f"\n  FUND: {fund_name} (scheme={scheme_id})")
    for topic_label, query_template in topics_queries:
        q = query_template.format(fund=fund_name)
        topic = detect_topic(q)
        chunks = retrieve_chunks(q, scheme_id, topic, collection, embedder)
        n = len(chunks)
        status = "PASS" if n > 0 else "FAIL (0 chunks)"
        retrieval_results[fund_name][topic_label] = n
        preview = chunks[0]["text"][:80] + "..." if n > 0 else "N/A"
        print(f"    [{topic_label}] chunks={n} [{status}]  preview: {preview}")

# ── Step 3: Full pipeline (with LLM) for one query per fund ──
print("\n" + "=" * 70)
print("STEP 3: FULL PIPELINE TEST (with LLM — one query per fund)")
print("=" * 70)

pipeline_queries = [
    "What is the expense ratio of ICICI Prudential Bluechip Fund?",
    "What is the exit load of the flexicap fund?",
    "What is the nav of the midcap fund?",
    "What is the minimum sip for the small cap fund?",
    "What is the lock-in period for the ELSS fund?",
]

for q in pipeline_queries:
    print(f"\n  QUERY: {q}")
    print(f"    scheme={detect_scheme(q)}, topic={detect_topic(q)}")
    try:
        ans = run_pipeline(q)
        has_url = "http" in ans
        is_error = "API_ERROR" in ans or "Whoops" in ans
        is_empty = "No matching" in ans
        if is_error:
            status = "FAIL (API error)"
        elif is_empty:
            status = "FAIL (no chunks matched)"
        elif has_url:
            status = "PASS"
        else:
            status = "PARTIAL (answer but no URL)"
        print(f"    [{status}]")
        print(f"    ANSWER: {ans[:200]}")
    except Exception as e:
        print(f"    [FAIL] Exception: {e}")
    time.sleep(3)  # avoid rate limits

# ── Summary ──
print("\n" + "=" * 70)
print("RETRIEVAL SUMMARY MATRIX")
print("=" * 70)

header = f"{'Fund':<15}" + "".join(f"{t:<18}" for t, _ in topics_queries)
print(header)
print("-" * len(header))
for fund_name in funds:
    row = f"{fund_name:<15}"
    for topic_label, _ in topics_queries:
        n = retrieval_results[fund_name][topic_label]
        mark = f"{n} chunks" if n > 0 else "FAIL"
        row += f"{mark:<18}"
    print(row)
