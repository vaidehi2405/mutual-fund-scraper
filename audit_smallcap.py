import requests

scheme = "Small Cap"
queries = [
    "What is the latest NAV of the Small Cap fund?",
    "What is the expense ratio for Small Cap fund?",
    "Who manages the Small Cap fund?",
    "What is the total AUM or Fund Size of the Small Cap fund?",
    "What is the risk category of the ICICI Small Cap fund?",
    "What benchmark does the Small Cap fund follow?",
    "Tell me about the 1-year, 3-year, and 5-year returns of the Small Cap fund."
]

print(f"--- COMPREHENSIVE AUDIT: {scheme} ---")
for query in queries:
    try:
        r = requests.post("http://localhost:8000/chat", json={"query": query})
        if r.status_code == 200:
            ans = r.json().get("text", "NO TEXT FOUND")
            status = "✅ PASS" if "not in my current sources" not in ans.lower() and "visit icicipruamc" not in ans.lower() else "❌ FAIL"
            print(f"QUERY: {query}")
            print(f"STATUS: {status}")
            print(f"ANSWER: {ans[:250]}...")
            print("-" * 30)
        else:
            print(f"QUERY: {query} | HTTP ERROR: {r.status_code}")
    except Exception as e:
        print(f"QUERY: {query} | EXCEPTION: {e}")
print("--- AUDIT COMPLETE ---")
