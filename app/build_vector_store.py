"""Build a ChromaDB vector store from embedded chunks.

Reads chunks_with_embeddings.jsonl and inserts them into a persistent
ChromaDB collection with metadata for filtered retrieval.
"""

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import chromadb

ROOT_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
CHUNKS_PATH = PROCESSED_DIR / "chunks_with_embeddings.jsonl"
VECTOR_STORE_DIR = ROOT_DIR / "data" / "vector_store"

COLLECTION_NAME = "mf_chunks"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_embedded_chunks(path: Path) -> List[Dict]:
    """Load chunks that already have embeddings."""
    chunks = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    return chunks


def sanitize_metadata(chunk: Dict) -> Dict[str, str]:
    """Extract and clean metadata fields for ChromaDB.

    ChromaDB metadata values must be str, int, float, or bool.
    """
    return {
        "source_id": str(chunk.get("source_id", "")),
        "url": str(chunk.get("url", "")),
        "domain": str(chunk.get("domain", "")),
        "fund": str(chunk.get("fund", "")),
        "amc": str(chunk.get("amc", "")),
        "scheme": str(chunk.get("scheme", "")),
        "doc_type": str(chunk.get("doc_type", "")),
        "section_title": str(chunk.get("section_title", "")),
        "ingested_at": str(chunk.get("ingested_at", "")),
        "run_id": str(chunk.get("run_id", "")),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build ChromaDB vector store from embedded chunks."
    )
    parser.add_argument(
        "--chunks",
        type=str,
        default=str(CHUNKS_PATH),
        help="Path to chunks_with_embeddings.jsonl",
    )
    parser.add_argument(
        "--store-dir",
        type=str,
        default=str(VECTOR_STORE_DIR),
        help="Directory for persistent ChromaDB storage",
    )
    parser.add_argument(
        "--collection",
        type=str,
        default=COLLECTION_NAME,
        help="ChromaDB collection name",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        default=False,
        help="Delete existing vector store before building",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for ChromaDB upserts",
    )
    args = parser.parse_args()

    chunks_path = Path(args.chunks)
    store_dir = Path(args.store_dir)

    if not chunks_path.exists():
        print(f"ERROR: Embedded chunks not found: {chunks_path}")
        print("Run embed_chunks.py first.")
        return 1

    # --- Load chunks ---
    print(f"Loading embedded chunks from {chunks_path} ...")
    chunks = load_embedded_chunks(chunks_path)
    print(f"  Loaded {len(chunks)} chunks with embeddings")

    if not chunks:
        print("ERROR: No chunks to index.")
        return 1

    # --- Reset if requested ---
    if args.reset and store_dir.exists():
        print(f"  Resetting vector store at {store_dir} ...")
        shutil.rmtree(store_dir)

    # --- Initialize ChromaDB ---
    store_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nInitializing ChromaDB at {store_dir} ...")
    client = chromadb.PersistentClient(path=str(store_dir))

    # Get or create collection (cosine similarity for normalized embeddings)
    collection = client.get_or_create_collection(
        name=args.collection,
        metadata={"hnsw:space": "cosine"},
    )
    print(f"  Collection: {args.collection}")
    print(f"  Existing docs: {collection.count()}")

    # --- Prepare data ---
    ids = []
    documents = []
    embeddings = []
    metadatas = []

    for chunk in chunks:
        chunk_id = chunk["chunk_id"]
        ids.append(chunk_id)
        documents.append(chunk["text"])
        embeddings.append(chunk["embedding"])
        metadatas.append(sanitize_metadata(chunk))

    # --- Upsert in batches ---
    total = len(ids)
    batch_size = args.batch_size
    print(f"\nUpserting {total} chunks (batch_size={batch_size}) ...")

    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        collection.upsert(
            ids=ids[start:end],
            documents=documents[start:end],
            embeddings=embeddings[start:end],
            metadatas=metadatas[start:end],
        )
        print(f"  Batch {start // batch_size + 1}: chunks {start + 1}-{end}")

    # --- Verify ---
    final_count = collection.count()
    print(f"\n{'=' * 50}")
    print("Vector store built!")
    print(f"  Store path:       {store_dir}")
    print(f"  Collection:       {args.collection}")
    print(f"  Documents stored: {final_count}")
    print(f"  Metadata fields:  {list(metadatas[0].keys())}")

    # Quick sanity check: query with the first chunk's embedding
    test_result = collection.query(
        query_embeddings=[embeddings[0]],
        n_results=3,
    )
    print(f"\n  Sanity check — top 3 results for first chunk:")
    for i, (doc_id, dist) in enumerate(
        zip(test_result["ids"][0], test_result["distances"][0])
    ):
        meta = test_result["metadatas"][0][i]
        print(f"    {i + 1}. {doc_id[:40]:<40s}  dist={dist:.4f}  scheme={meta.get('scheme', '')}")

    print("=" * 50)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
