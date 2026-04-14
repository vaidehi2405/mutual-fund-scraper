import requests
from bs4 import BeautifulSoup
import re
import json

URLS = [
    "https://groww.in/mutual-funds/icici-prudential-indo-asia-equity-fund-direct-growth"
]

# ---------- CLEANING FUNCTIONS ----------

def extract_percentage(text):
    match = re.search(r"([\d.]+)%", text)
    return float(match.group(1)) if match else None

def extract_rupees(text):
    match = re.search(r"₹\s?([\d,\.]+)", text)
    return float(match.group(1).replace(",", "")) if match else None

def extract_number(text):
    match = re.search(r"([\d.]+)", text)
    return float(match.group(1)) if match else None

def clean_risk(text):
    if "Very High" in text:
        return "Very High"
    elif "High" in text:
        return "High"
    elif "Moderate" in text:
        return "Moderate"
    return None

# ---------- SCRAPER ----------

def scrape_fund(url):
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")

    text = soup.get_text(" ", strip=True)

    data = {}

    # Fund name
    title = soup.title.string if soup.title else ""
    data["fund_name"] = title.replace(" - NAV, Mutual Fund Performance & Portfolio", "").strip()

    # Expense Ratio
    exp_match = re.search(r"Expense ratio\s*([\d.]+)%", text)
    data["expense_ratio"] = float(exp_match.group(1)) if exp_match else None

    # NAV
    nav_match = re.search(r"NAV.*?₹\s?([\d,\.]+)", text)
    data["nav"] = float(nav_match.group(1).replace(",", "")) if nav_match else None

    # Returns (from table)
    returns = {}

    r1 = re.search(r"1 year.*?\+?([\d.]+)%", text)
    r3 = re.search(r"3 years.*?\+?([\d.]+)%", text)
    r5 = re.search(r"5 years.*?\+?([\d.]+)%", text)

    returns["1y"] = float(r1.group(1)) if r1 else None
    returns["3y"] = float(r3.group(1)) if r3 else None
    returns["5y"] = float(r5.group(1)) if r5 else None

    data["returns"] = returns

    # AUM (Fund size)
    aum_match = re.search(r"Fund size.*?₹\s?([\d,\.]+)", text)
    data["aum_cr"] = float(aum_match.group(1).replace(",", "")) if aum_match else None

    # Risk
    risk_match = re.search(r"(Very High|High|Moderate) Risk", text)
    data["risk"] = risk_match.group(1) if risk_match else None

    # SIP
    sip_match = re.search(r"Min\. SIP.*?₹\s?([\d,]+)", text)
    data["min_sip"] = int(sip_match.group(1).replace(",", "")) if sip_match else None

    # Exit Load
    exit_match = re.search(r"Exit load.*?\d+%.*?year", text)
    data["exit_load"] = exit_match.group(0) if exit_match else None

    return data


# ---------- RUN ----------

all_data = [scrape_fund(url) for url in URLS]

with open("clean_data.json", "w") as f:
    json.dump(all_data, f, indent=2)

print("✅ Clean data saved!")
