"""End-to-end test for the embedding + vector store pipeline.

Tests:
1. Vector store loads and has expected doc count
2. Semantic queries return relevant chunks
3. Metadata filtering works
4. Embedding model produces correct dimensions
"""

import json
import sys
from pathlib import Path

import chromadb
import numpy as np
from sentence_transformers import SentenceTransformer

ROOT_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
VECTOR_STORE_DIR = ROOT_DIR / "data" / "vector_store"

MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384
COLLECTION_NAME = "mf_chunks"
INSTRUCTION_PREFIX = "Represent this sentence: "

PASS = "PASS"
FAIL = "FAIL"
results = []


def log(test_name: str, passed: bool, detail: str = ""):
    status = PASS if passed else FAIL
    results.append(passed)
    msg = f"  {status} {test_name}"
    if detail:
        msg += f" — {detail}"
    print(msg)


def main() -> int:
    print("=" * 60)
    print("VECTOR STORE PIPELINE TEST")
    print("=" * 60)

    # ── Test 1: Output files exist ──
    print("\n[1] Output files exist")
    for name in ["chunks_with_embeddings.jsonl", "embeddings.npy", "chunk_ids.json"]:
        path = PROCESSED_DIR / name
        log(name, path.exists(), f"{path.stat().st_size:,} bytes" if path.exists() else "MISSING")

    log("vector_store/", VECTOR_STORE_DIR.exists())

    # ── Test 2: Embedding dimensions ──
    print("\n[2] Embedding dimensions")
    emb_array = np.load(str(PROCESSED_DIR / "embeddings.npy"))
    log(
        f"embeddings.npy shape",
        emb_array.shape[1] == EMBEDDING_DIM,
        f"shape={emb_array.shape}",
    )

    chunk_ids = json.loads((PROCESSED_DIR / "chunk_ids.json").read_text(encoding="utf-8"))
    log(
        "chunk_ids count matches embeddings",
        len(chunk_ids) == emb_array.shape[0],
        f"ids={len(chunk_ids)}, embeddings={emb_array.shape[0]}",
    )

    # ── Test 3: ChromaDB collection ──
    print("\n[3] ChromaDB collection")
    client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
    collection = client.get_collection(name=COLLECTION_NAME)
    doc_count = collection.count()
    log("Collection exists", True, f"name={COLLECTION_NAME}")
    log("Doc count matches", doc_count == len(chunk_ids), f"stored={doc_count}, expected={len(chunk_ids)}")

    # ── Test 4: Load embedding model ──
    print("\n[4] Embedding model")
    model = SentenceTransformer(MODEL_NAME)
    test_emb = model.encode([INSTRUCTION_PREFIX + "test"], normalize_embeddings=True)
    log("Model loads", True, f"device={model.device}")
    log("Output dim correct", test_emb.shape[1] == EMBEDDING_DIM, f"dim={test_emb.shape[1]}")

    # ── Test 5: Semantic queries ──
    print("\n[5] Semantic queries")
    test_queries = [
        {
            "query": "What is the expense ratio of ICICI Prudential Large Cap Fund?",
            "expect_keywords": ["expense ratio", "large cap"],
            "expect_scheme": None,
        },
        {
            "query": "What is the exit load for ICICI Prudential Flexicap Fund?",
            "expect_keywords": ["exit load"],
            "expect_scheme": None,
        },
        {
            "query": "ELSS lock-in period",
            "expect_keywords": ["elss", "lock"],
            "expect_scheme": None,
        },
        {
            "query": "minimum SIP amount",
            "expect_keywords": ["sip", "minimum"],
            "expect_scheme": None,
        },
    ]

    for tq in test_queries:
        query_emb = model.encode(
            [INSTRUCTION_PREFIX + tq["query"]],
            normalize_embeddings=True,
        ).tolist()

        result = collection.query(query_embeddings=query_emb, n_results=3)
        top_doc = result["documents"][0][0].lower() if result["documents"][0] else ""
        top_id = result["ids"][0][0] if result["ids"][0] else ""
        top_dist = result["distances"][0][0] if result["distances"][0] else -1
        top_meta = result["metadatas"][0][0] if result["metadatas"][0] else {}

        # Check if at least one keyword appears in top result
        kw_found = any(kw in top_doc for kw in tq["expect_keywords"])
        log(
            f'Query: "{tq["query"][:50]}"',
            kw_found,
            f'dist={top_dist:.4f}, scheme={top_meta.get("scheme","")}, id={top_id[:35]}',
        )

    # ── Test 6: Metadata filtering ──
    print("\n[6] Metadata filtering")
    query_emb = model.encode(
        [INSTRUCTION_PREFIX + "expense ratio"],
        normalize_embeddings=True,
    ).tolist()

    # Query with scheme filter
    schemes_to_test = ["flexicap", "small cap", "elss"]
    for scheme in schemes_to_test:
        filtered = collection.query(
            query_embeddings=query_emb,
            n_results=3,
            where={"scheme": scheme},
        )
        if filtered["ids"][0]:
            all_match = all(
                m.get("scheme", "").lower() == scheme.lower()
                for m in filtered["metadatas"][0]
            )
            log(
                f'Filter scheme="{scheme}"',
                all_match,
                f"returned={len(filtered['ids'][0])} docs, all_match={all_match}",
            )
        else:
            log(f'Filter scheme="{scheme}"', False, "no results returned")

    # ── Test 7: No binary garbage in store ──
    print("\n[7] Data quality")
    sample = collection.get(limit=50, include=["documents"])
    binary_count = 0
    for doc in sample["documents"]:
        if "\ufffd" in doc and doc.count("\ufffd") > len(doc) * 0.1:
            binary_count += 1
    log("No binary garbage in store", binary_count == 0, f"binary_chunks_found={binary_count}")

    # Check all docs have reasonable length
    short_count = sum(1 for doc in sample["documents"] if len(doc.strip()) < 20)
    log("No trivially short docs", short_count == 0, f"short_docs={short_count}")

    # ── Summary ──
    passed = sum(results)
    total = len(results)
    print(f"\n{'=' * 60}")
    print(f"RESULTS: {passed}/{total} tests passed")
    if passed == total:
        print("All tests passed! Pipeline is working correctly.")
    else:
        print(f"{total - passed} test(s) FAILED.")
    print("=" * 60)

    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
