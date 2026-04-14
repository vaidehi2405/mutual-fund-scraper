import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
CHUNKS_PATH = PROCESSED_DIR / "chunks.jsonl"
OUT_PATH = PROCESSED_DIR / "fund_faq_data.json"

FUND_KEYS = {
    "icici-prudential-large-cap-fund-direct-growth": {"large cap", "largecap"},
    "icici-prudential-flexicap-fund-direct-growth": {"flexicap", "flexi cap"},
    "icici-prudential-midcap-fund-direct-growth": {"midcap", "mid cap"},
    "icici-prudential-smallcap-fund-direct-growth": {"small cap", "smallcap"},
    "icici-prudential-elss-tax-saver-direct-plan-growth": {"elss", "elss tax saver"},
}

SOURCE_ALLOWED = ("icicipruamc.com", "sebi.gov.in", "groww.in")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_scheme(scheme: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", scheme.lower()).strip()


def infer_fund_key(scheme: str, url: str) -> Optional[str]:
    s = normalize_scheme(scheme)
    u = url.lower()
    for key, aliases in FUND_KEYS.items():
        if any(alias in s for alias in aliases) or key in u:
            return key
    if "smallcap" in u:
        return "icici-prudential-smallcap-fund-direct-growth"
    return None


def best_match(chunks: List[Dict[str, str]], patterns: List[str], required: Optional[str] = None) -> Tuple[str, str]:
    compiled = [re.compile(p, re.IGNORECASE) for p in patterns]
    best_val = "N/A"
    best_url = ""
    best_score = -1
    for row in chunks:
        text = row["text"]
        for pattern in compiled:
            for match in pattern.finditer(text):
                snippet = normalize_text(match.group(0))
                if required and required.lower() not in snippet.lower():
                    continue
                score = 0
                if len(snippet) > 12:
                    score += 1
                if re.search(r"\d", snippet):
                    score += 1
                if "groww.in" in row["url"]:
                    score += 2
                if any(t in row.get("doc_type", "").lower() for t in ("factsheet", "kim", "sid")):
                    score += 1
                if score > best_score:
                    best_score = score
                    best_val = snippet
                    best_url = row["url"]
    if best_val == "N/A":
        return best_val, ""
    return best_val, best_url


def extract_returns(chunks: List[Dict[str, str]]) -> Dict[str, str]:
    returns = {"1y": "N/A", "3y": "N/A", "5y": "N/A"}
    for row in chunks:
        text = row["text"]
        for horizon, key in (("1\s*year|1y", "1y"), ("3\s*year|3y", "3y"), ("5\s*year|5y", "5y")):
            if returns[key] != "N/A":
                continue
            m = re.search(rf"(?:{horizon})[^\d%]{{0,30}}(\d+(?:\.\d+)?\s*%)", text, re.IGNORECASE)
            if m:
                returns[key] = m.group(1)
    return returns


def extract_top_holdings(chunks: List[Dict[str, str]]) -> List[str]:
    found: List[str] = []
    pattern = re.compile(r"([A-Za-z][A-Za-z0-9& .,'()-]{2,60})\s+(\d+(?:\.\d+)?%)")
    for row in chunks:
        text = row["text"]
        if "holding" not in text.lower():
            continue
        for name, weight in pattern.findall(text):
            line = f"{normalize_text(name)} - {weight}"
            if line.lower().startswith(("top holdings", "holding")):
                continue
            if line not in found:
                found.append(line)
            if len(found) >= 10:
                return found
    return found


def extract_sector_alloc(chunks: List[Dict[str, str]]) -> Dict[str, str]:
    alloc: Dict[str, str] = {}
    pattern = re.compile(r"([A-Za-z][A-Za-z &/-]{2,40})\s+(\d+(?:\.\d+)?%)")
    for row in chunks:
        text = row["text"]
        if "sector" not in text.lower():
            continue
        for sector, pct in pattern.findall(text):
            sector_name = normalize_text(sector)
            if sector_name.lower() in {"sector", "sector allocation", "allocation"}:
                continue
            if sector_name not in alloc:
                alloc[sector_name] = pct
            if len(alloc) >= 10:
                return alloc
    return alloc


def format_with_source(value: str, source_url: str) -> str:
    if value == "N/A" or not source_url:
        return value
    return f"{value} (Source: {source_url})"


def extract_faqs(chunks: List[Dict[str, str]]) -> List[str]:
    faqs: List[str] = []
    question_pattern = re.compile(r"([^.!?\n]{8,140}\?)")
    for row in chunks:
        if not ("groww.in" in row["url"] or "kim" in row.get("doc_type", "").lower()):
            continue
        for q in question_pattern.findall(row["text"]):
            nq = normalize_text(q)
            low = nq.lower()
            if not any(k in low for k in ("sip", "redemption", "elss", "tax")):
                continue
            if nq not in faqs:
                faqs.append(nq)
            if len(faqs) >= 10:
                return faqs
    return faqs


def load_chunks(path: Path) -> Dict[str, List[Dict[str, str]]]:
    grouped: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            url = row.get("url", "")
            if not any(domain in url for domain in SOURCE_ALLOWED):
                continue
            key = infer_fund_key(row.get("scheme", ""), url)
            if not key:
                continue
            grouped[key].append(row)
    return grouped


def build_fund_payload(rows: List[Dict[str, str]], fund_key: str) -> Dict[str, object]:
    nav, nav_url = best_match(rows, [r"latest\s*nav[^\n.]{0,120}", r"nav\s*as\s*of[^\n.]{0,120}"])
    aum, aum_url = best_match(rows, [r"aum[^\n]{0,60}(?:cr|crore)", r"assets\s*under\s*management[^\n]{0,80}"])
    expense, expense_url = best_match(rows, [r"expense\s*ratio[^\n]{0,60}\d+(?:\.\d+)?\s*%"])
    objective, objective_url = best_match(rows, [r"investment\s*objective[^\n]{0,240}", r"objective[^\n]{0,220}"], "objective")
    riskometer, risk_url = best_match(rows, [r"riskometer[^\n]{0,120}", r"(low|moderate|high|very\s*high)\s*risk"])
    benchmark, bench_url = best_match(rows, [r"benchmark[^\n]{0,180}"])
    manager, manager_url = best_match(rows, [r"fund\s*manager[^\n]{0,140}", r"managed\s*by[^\n]{0,120}"])
    launch, launch_url = best_match(rows, [r"(launch|inception)\s*date[^\n]{0,80}"])
    exit_load, exit_url = best_match(rows, [r"exit\s*load[^\n]{0,200}"])
    min_lump, lump_url = best_match(rows, [r"minimum\s*lumpsum[^\n]{0,120}", r"minimum\s*investment[^\n]{0,120}"])
    min_sip, sip_url = best_match(rows, [r"minimum\s*sip[^\n]{0,120}", r"sip[^\n]{0,80}minimum[^\n]{0,80}"])

    returns = extract_returns(rows)
    top_holdings = extract_top_holdings(rows)
    sector_alloc = extract_sector_alloc(rows)

    tax_note = "N/A"
    if "elss" in fund_key:
        tax_note = "ELSS has a 3-year lock-in; eligible for deduction under Section 80C up to applicable limits."
    else:
        tval, turl = best_match(rows, [r"tax[^\n]{0,220}", r"capital\s*gains[^\n]{0,220}"])
        tax_note = format_with_source(tval, turl) if tval != "N/A" else "N/A"

    return {
        "live_metrics": {
            "nav": format_with_source(nav, nav_url),
            "aum_cr": format_with_source(aum, aum_url),
            "returns": returns,
            "expense_ratio": format_with_source(expense, expense_url),
        },
        "scheme_info": {
            "objective": format_with_source(objective, objective_url),
            "riskometer": format_with_source(riskometer, risk_url),
            "benchmark": format_with_source(benchmark, bench_url),
            "fund_manager": format_with_source(manager, manager_url),
            "launch_date": format_with_source(launch, launch_url),
        },
        "fees_loads": {
            "exit_load": format_with_source(exit_load, exit_url),
            "min_lumpsum": format_with_source(min_lump, lump_url),
            "min_sip": format_with_source(min_sip, sip_url),
        },
        "portfolio": {
            "top_holdings": top_holdings if top_holdings else ["N/A"],
            "sector_alloc": sector_alloc,
        },
        "tax_notes": tax_note,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build FAQ chatbot JSON from scraped chunks.")
    parser.add_argument("--chunks", type=str, default=str(CHUNKS_PATH), help="Path to chunks.jsonl")
    parser.add_argument("--out", type=str, default=str(OUT_PATH), help="Output JSON path")
    args = parser.parse_args()

    chunks_by_fund = load_chunks(Path(args.chunks))

    payload = {
        "funds": {},
        "faqs": [],
    }

    all_chunks: List[Dict[str, str]] = []
    for fund_key in FUND_KEYS:
        rows = chunks_by_fund.get(fund_key, [])
        all_chunks.extend(rows)
        payload["funds"][fund_key] = build_fund_payload(rows, fund_key)

    payload["faqs"] = extract_faqs(all_chunks)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
