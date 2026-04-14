import argparse
import csv
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
SOURCES_CSV = ROOT_DIR / "LIP2urls.csv"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

OFFICIAL_DOMAINS = {
    "sebi.gov.in",
    "www.sebi.gov.in",
    "icicipruamc.com",
    "www.icicipruamc.com",
    "groww.in",
    "www.groww.in",
}

CHUNK_SIZE = 850
CHUNK_OVERLAP = 120


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "na"


def read_sources(only_active: bool = True, source_file: Path = SOURCES_CSV) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    current_doc_type = ""
    with source_file.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        for line_no, line in enumerate(reader, start=1):
            if not line:
                continue
            first_col = (line[0] if len(line) > 0 else "").strip()
            second_col = (line[1] if len(line) > 1 else "").strip()

            if not first_col and not second_col:
                continue

            # Section header rows in LIP2urls.csv look like "SID,", "KIM,", etc.
            if first_col and not first_col.lower().startswith(("http://", "https://")):
                current_doc_type = first_col
                continue

            # URL rows contain URL in first column and optional scheme label in second.
            if not first_col.lower().startswith(("http://", "https://")):
                continue

            scheme = second_col or "NA"
            row = {
                "source_id": f"{slugify(current_doc_type)}_{slugify(scheme)}_{line_no}",
                "fund": scheme,
                "doc_type": current_doc_type or "Unknown",
                "url": first_col,
                "amc": "ICICI Prudential AMC",
                "scheme": scheme,
                "active": "true",
            }
            active = row.get("active", "true").strip().lower() == "true"
            if only_active and not active:
                continue
            rows.append(row)
    return rows


def clean_text(raw_html: str) -> str:
    soup = BeautifulSoup(raw_html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    if not text:
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: List[str] = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= chunk_size:
            current = (current + "\n\n" + para).strip()
            continue

        if current:
            chunks.append(current)

        if len(para) <= chunk_size:
            current = para
            continue

        start = 0
        while start < len(para):
            end = start + chunk_size
            piece = para[start:end]
            if piece:
                chunks.append(piece.strip())
            start = max(end - overlap, end)
        current = ""

    if current:
        chunks.append(current)

    return chunks


def hash_string(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def source_domain(url: str) -> str:
    return urlparse(url).netloc.lower()


def is_official(url: str) -> bool:
    return source_domain(url) in OFFICIAL_DOMAINS


def fetch_url(session: requests.Session, url: str, timeout: int) -> Dict[str, str]:
    response = session.get(url, timeout=timeout, allow_redirects=True)
    response.raise_for_status()
    return {
        "final_url": response.url,
        "status_code": str(response.status_code),
        "content_type": response.headers.get("Content-Type", ""),
        "text": response.text,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape configured MF sources and build chunked artifacts.")
    parser.add_argument("--timeout-seconds", type=int, default=30, help="HTTP timeout for each request.")
    parser.add_argument(
        "--source-file",
        type=str,
        default=str(SOURCES_CSV),
        help="Path to LIP2-style URL CSV file.",
    )
    parser.add_argument("--only-active", action="store_true", default=True, help="Use only active rows.")
    args = parser.parse_args()

    ensure_dirs()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_raw_dir = RAW_DIR / run_id
    run_raw_dir.mkdir(parents=True, exist_ok=True)

    sources = read_sources(only_active=args.only_active, source_file=Path(args.source_file))
    fetched_cache: Dict[str, Dict[str, str]] = {}
    source_snapshots: List[Dict[str, str]] = []
    chunks: List[Dict[str, str]] = []
    started_at = utc_now_iso()

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "mf-faq-rag-scraper/1.0 (+github-actions; facts-only-rag)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
    )

    for source in sources:
        url = source["url"].strip()
        source_id = source["source_id"].strip()
        fetched_at = utc_now_iso()

        if url in fetched_cache:
            result = fetched_cache[url]
            status = "success"
            error = ""
        else:
            try:
                result = fetch_url(session, url, timeout=args.timeout_seconds)
                fetched_cache[url] = result
                status = "success"
                error = ""
            except Exception as exc:  # noqa: BLE001
                result = {
                    "final_url": url,
                    "status_code": "",
                    "content_type": "",
                    "text": "",
                }
                status = "failed"
                error = str(exc)

        cleaned = clean_text(result["text"]) if status == "success" else ""
        content_hash = hash_string(cleaned) if cleaned else ""

        source_snapshot = {
            "run_id": run_id,
            "source_id": source_id,
            "fund": source.get("fund", ""),
            "doc_type": source.get("doc_type", ""),
            "url": url,
            "final_url": result["final_url"],
            "domain": source_domain(result["final_url"]),
            "official_domain_flag": is_official(result["final_url"]),
            "amc": source.get("amc", ""),
            "scheme": source.get("scheme", ""),
            "status": status,
            "status_code": result["status_code"],
            "content_type": result["content_type"],
            "content_hash": content_hash,
            "char_count": len(cleaned),
            "fetched_at": fetched_at,
            "last_checked_at": fetched_at,
            "error": error,
        }
        source_snapshots.append(source_snapshot)

        if status != "success" or not cleaned:
            continue

        raw_path = run_raw_dir / f"{source_id}.html"
        raw_path.write_text(result["text"], encoding="utf-8")

        text_path = run_raw_dir / f"{source_id}.txt"
        text_path.write_text(cleaned, encoding="utf-8")

        for idx, chunk in enumerate(chunk_text(cleaned), start=1):
            chunk_id = f"{source_id}:{idx}:{hash_string(chunk)[:12]}"
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "run_id": run_id,
                    "source_id": source_id,
                    "url": result["final_url"],
                    "domain": source_domain(result["final_url"]),
                    "fund": source.get("fund", ""),
                    "amc": source.get("amc", ""),
                    "scheme": source.get("scheme", ""),
                    "doc_type": source.get("doc_type", ""),
                    "section_title": "",
                    "published_or_effective_date": "",
                    "ingested_at": fetched_at,
                    "text": chunk,
                }
            )

    snapshots_path = PROCESSED_DIR / "sources_snapshot.jsonl"
    chunks_path = PROCESSED_DIR / "chunks.jsonl"
    run_report_path = PROCESSED_DIR / "scrape_run.json"

    with snapshots_path.open("w", encoding="utf-8") as f:
        for row in source_snapshots:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")

    with chunks_path.open("w", encoding="utf-8") as f:
        for row in chunks:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")

    run_report = {
        "run_id": run_id,
        "started_at": started_at,
        "ended_at": utc_now_iso(),
        "source_rows_total": len(sources),
        "unique_urls_total": len({s["url"] for s in sources}),
        "successful_sources": sum(1 for s in source_snapshots if s["status"] == "success"),
        "failed_sources": sum(1 for s in source_snapshots if s["status"] == "failed"),
        "chunks_generated": len(chunks),
        "outputs": {
            "raw_run_dir": str(run_raw_dir.relative_to(ROOT_DIR)),
            "sources_snapshot_jsonl": str(snapshots_path.relative_to(ROOT_DIR)),
            "chunks_jsonl": str(chunks_path.relative_to(ROOT_DIR)),
        },
    }
    run_report_path.write_text(json.dumps(run_report, indent=2, ensure_ascii=True), encoding="utf-8")

    print(json.dumps(run_report, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
