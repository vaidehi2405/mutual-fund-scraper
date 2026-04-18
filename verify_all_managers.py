import requests

funds = ["Large Cap", "Midcap", "Small Cap", "Flexicap", "ELSS"]

print("--- FINAL VERIFICATION OF FUND MANAGERS ---")
for fund in funds:
    query = f"Who is the fund manager for {fund} fund?"
    try:
        r = requests.post("http://localhost:8000/chat", json={"query": query})
        if r.status_code == 200:
            ans = r.json().get("text", "NO TEXT FOUND")
            print(f"FUND: {fund:10} | ANSWER: {ans[:150]}...")
        else:
            print(f"FUND: {fund:10} | ERROR: Status {r.status_code}")
    except Exception as e:
        print(f"FUND: {fund:10} | EXCEPTION: {e}")
print("-" * 50)
