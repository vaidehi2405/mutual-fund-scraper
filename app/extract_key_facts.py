import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple


ROOT_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
CHUNKS_PATH = PROCESSED_DIR / "chunks.jsonl"
OUT_JSON_PATH = PROCESSED_DIR / "key_facts.json"
OUT_MD_PATH = PROCESSED_DIR / "key_facts.md"


FIELD_PATTERNS = {
    # Groww often puts the % on the line after the label; allow whitespace/newlines between.
    "expense_ratio": [
        r"(expense\s*ratio\s+[\n\r]*\s*\d+(?:\.\d+)?\s*%)",
        r"(total\s*expense\s*ratio\s+[\n\r]*\s*\d+(?:\.\d+)?\s*%)",
        r"(expense\s*ratio[^\d]{0,40}\d+(?:\.\d+)?\s*%)",
        r"(total\s*expense\s*ratio[^\d]{0,40}\d+(?:\.\d+)?\s*%)",
    ],
    "nav": [
        r"(latest\s*nav\s*as\s*of[^\n]+is\s*(?:rs\.?\s*)?(?:\u20b9)?\s*[\d,.]+)",
        r"(NAV:\s*[^\n]+[\n\r]+\s*(?:rs\.?\s*)?(?:\u20b9)?\s*[\d,.]+)",
        r"(NAV\s+as\s*of[^\n]+(?:rs\.?\s*)?(?:\u20b9)\s*[\d,.]+)",
    ],
    "exit_load": [
        r"(exit\s*load[^.\n]{0,220}?(?:\d+(?:\.\d+)?\s*%|nil|none|not applicable))",
        r"(exit\s*load[^.\n]{0,220})",
    ],
    "minimum_sip": [
        r"(minimum\s*sip[^.\n]{0,140}?(?:rs\.?|inr|₹)\s*\d+[,\d]*)",
        r"(minimum\s*sip[^.\n]{0,180})",
        r"(sip[^.\n]{0,100}minimum[^.\n]{0,100})",
    ],
    "lock_in_elss": [
        r"(lock[-\s]*in[^.\n]{0,180}?(?:3\s*years?|three\s*years?))",
        r"(elss[^.\n]{0,140}(?:3\s*years?|three\s*years?))",
        r"(lock[-\s]*in[^.\n]{0,220})",
    ],
    "riskometer": [
        r"(riskometer[^.\n]{0,200})",
        r"(very\s*high|high|moderately\s*high|moderate|low)\s*risk",
        r"(risk\s*level[^.\n]{0,160})",
    ],
    "benchmark": [
        r"(benchmark(?:\s*index)?[^.\n]{0,220})",
    ],
    "statement_download": [
        r"(download[^.\n]{0,140}(?:statement|capital\s*gains|account\s*statement)[^.\n]{0,160})",
        r"((?:capital\s*gains|account\s*statement)[^.\n]{0,100}download[^.\n]{0,120})",
        r"((?:statement|capital\s*gains)[^.\n]{0,140}(?:mail|email|portal|online))",
    ],
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_snippet(snippet: str) -> str:
    snippet = re.sub(r"\s+", " ", snippet).strip()
    return snippet[:260]


def normalize_scheme(raw_scheme: str) -> str:
    value = raw_scheme.strip().lower()
    value = re.sub(r"[^a-z0-9]+", " ", value).strip()

    aliases = {
        "small cap": "Small Cap",
        "smallcap": "Small Cap",
        "mid cap": "Midcap",
        "midcap": "Midcap",
        "large cap": "Large Cap",
        "largecap": "Large Cap",
        "flexi cap": "Flexicap",
        "flexicap": "Flexicap",
        "elss": "ELSS",
        "na": "NA",
    }
    return aliases.get(value, raw_scheme.strip() or "NA")


def empty_result() -> Dict[str, Dict[str, str]]:
    return {
        key: {"value": "", "source_url": "", "source_id": "", "scheme": "", "matched_text": "", "score": 0}
        for key in FIELD_PATTERNS
    }


def is_expense_ratio_glossary_snippet(snippet: str) -> bool:
    """Skip 'Understand terms' definitions (no numeric ratio)."""
    lower = snippet.lower()
    return "fee payable" in lower or "managing your mutual fund" in lower or "total percentage" in lower


def score_match(field: str, snippet: str, row: Dict[str, str]) -> int:
    score = 0
    text = snippet.lower()
    doc_type = (row.get("doc_type", "") or "").lower()
    url = (row.get("url", "") or "").lower()

    # Content quality signals
    if re.search(r"\d+(?:\.\d+)?\s*%", text):
        score += 3
    if re.search(r"(₹|rs\.?|inr)\s*\d", text):
        score += 3
    if len(text) > 25:
        score += 1

    # Field-specific keyword confidence
    keyword_bonus: Dict[str, Tuple[str, ...]] = {
        "expense_ratio": ("expense ratio", "total expense ratio"),
        "nav": ("nav", "latest nav"),
        "exit_load": ("exit load",),
        "minimum_sip": ("minimum sip", "sip"),
        "lock_in_elss": ("lock-in", "lock in", "elss", "3 year", "three year"),
        "riskometer": ("riskometer", "risk level", "high risk", "moderate risk"),
        "benchmark": ("benchmark", "benchmark index"),
        "statement_download": ("download", "statement", "capital gains", "account statement"),
    }
    for kw in keyword_bonus.get(field, ()):
        if kw in text:
            score += 2

    # Prefer authoritative doc types for numeric/static facts
    if field in {"expense_ratio", "nav", "exit_load", "minimum_sip", "benchmark", "riskometer"}:
        if any(x in doc_type for x in ("factsheet", "sid", "kim")):
            score += 2
    if field in {"expense_ratio", "nav"} and "groww" in url:
        score += 3
    if field == "statement_download":
        if "faq" in doc_type or "groww" in doc_type or "help-center" in url:
            score += 2

    return score


def extract_from_chunks() -> Dict[str, Dict[str, Dict[str, str]]]:
    per_scheme: Dict[str, Dict[str, Dict[str, str]]] = {}
    compiled = {k: [re.compile(p, re.IGNORECASE) for p in pats] for k, pats in FIELD_PATTERNS.items()}

    with CHUNKS_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            text = row.get("text", "")
            scheme = normalize_scheme(row.get("scheme", "NA") or "NA")

            if scheme not in per_scheme:
                per_scheme[scheme] = empty_result()

            for field, patterns in compiled.items():
                for pattern in patterns:
                    for m in pattern.finditer(text):
                        snippet = normalize_snippet(m.group(0))
                        if field == "expense_ratio" and is_expense_ratio_glossary_snippet(snippet):
                            continue
                        if field == "expense_ratio" and not re.search(r"\d+(?:\.\d+)?\s*%", snippet):
                            continue
                        candidate_score = score_match(field, snippet, row)
                        current_score = int(per_scheme[scheme][field].get("score", 0))
                        if candidate_score < current_score:
                            continue
                        per_scheme[scheme][field] = {
                            "value": snippet,
                            "source_url": row.get("url", ""),
                            "source_id": row.get("source_id", ""),
                            "scheme": scheme,
                            "matched_text": snippet,
                            "score": candidate_score,
                        }

    return per_scheme


FIELD_ORDER = [
    "expense_ratio",
    "nav",
    "exit_load",
    "minimum_sip",
    "lock_in_elss",
    "riskometer",
    "benchmark",
    "statement_download",
]


def to_markdown(payload: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# Extracted Key Facts")
    lines.append("")
    lines.append(f"Generated at: `{payload['generated_at']}`")
    lines.append(f"Source file: `{payload['source_file']}`")
    lines.append("")

    for scheme, fields in payload["facts_by_scheme"].items():
        lines.append(f"## Scheme: {scheme}")
        lines.append("")
        ordered_names = [n for n in FIELD_ORDER if n in fields] + [
            n for n in fields if n not in FIELD_ORDER
        ]
        for field_name in ordered_names:
            info = fields[field_name]
            value = info.get("value", "")
            url = info.get("source_url", "")
            if value:
                lines.append(f"- **{field_name}**: {value}")
                lines.append(f"  - Source: {url}")
            else:
                lines.append(f"- **{field_name}**: Not found")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    if not CHUNKS_PATH.exists():
        raise FileNotFoundError(f"Missing chunks file: {CHUNKS_PATH}")

    facts = extract_from_chunks()
    payload = {
        "generated_at": utc_now_iso(),
        "source_file": str(CHUNKS_PATH.relative_to(ROOT_DIR)),
        "tracked_fields": list(FIELD_PATTERNS.keys()),
        "facts_by_scheme": facts,
    }

    OUT_JSON_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    OUT_MD_PATH.write_text(to_markdown(payload), encoding="utf-8")
    print(f"Wrote: {OUT_JSON_PATH}")
    print(f"Wrote: {OUT_MD_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
