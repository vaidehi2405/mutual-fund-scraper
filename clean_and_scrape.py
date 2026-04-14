iimport requests
from bs4 import BeautifulSoup
import re
import json
import os

URLS = [
    "https://groww.in/mutual-funds/icici-prudential-large-cap-fund-direct-growth",
    "https://groww.in/mutual-funds/icici-prudential-flexicap-fund-direct-growth",
    "https://groww.in/mutual-funds/icici-prudential-midcap-fund-direct-growth",
    "https://groww.in/mutual-funds/icici-prudential-smallcap-fund-direct-plan-growth",
    "https://groww.in/mutual-funds/icici-prudential-elss-tax-saver-direct-plan-growth"
]

def extract_float(pattern, text):
    match = re.search(pattern, text)
    return float(match.group(1).replace(",", "")) if match else None

def scrape_fund(url):
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")
    text = soup.get_text(" ", strip=True)

    data = {}

    # Fund name
    title = soup.title.string if soup.title else ""
    data["fund_name"] = title.split("-")[0].strip()

    # Expense ratio
    data["expense_ratio"] = extract_float(r"Expense ratio\s*([\d.]+)%", text)

    # NAV
    data["nav"] = extract_float(r"NAV.*?₹\s*([\d,\.]+)", text)

    # Returns
    data["returns_1y"] = extract_float(r"1 year.*?([\d.]+)%", text)
    data["returns_3y"] = extract_float(r"3 years.*?([\d.]+)%", text)
    data["returns_5y"] = extract_float(r"5 years.*?([\d.]+)%", text)

    # AUM
    data["aum_cr"] = extract_float(r"Fund size.*?₹\s*([\d,\.]+)", text)

    # Risk
    risk_match = re.search(r"(Very High|High|Moderate) Risk", text)
    data["risk"] = risk_match.group(1) if risk_match else None

    # SIP
    sip = extract_float(r"Min\. SIP.*?₹\s*([\d,]+)", text)
    data["min_sip"] = int(sip) if sip else None

    return data

def main():
    os.makedirs("data/processed", exist_ok=True)

    results = []

    for url in URLS:
        try:
            results.append(scrape_fund(url))
        except Exception as e:
            print(f"Error scraping {url}: {e}")

    with open("data/processed/clean_data.json", "w") as f:
        json.dump(results, f, indent=2)

    print("✅ Clean JSON generated!")

if __name__ == "__main__":
    main()
