"""Embed scraped chunks using BAAI/bge-small-en-v1.5.

Reads chunks.jsonl, filters out binary/garbled content,
generates 384-dim embeddings, and saves results in multiple formats.
"""

import argparse
import json
import string
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import numpy as np
from sentence_transformers import SentenceTransformer

ROOT_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
CHUNKS_PATH = PROCESSED_DIR / "chunks.jsonl"

MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384
# BGE recommends this prefix for retrieval tasks
INSTRUCTION_PREFIX = "Represent this sentence: "

# Output paths
OUT_JSONL = PROCESSED_DIR / "chunks_with_embeddings.jsonl"
OUT_NPY = PROCESSED_DIR / "embeddings.npy"
OUT_IDS = PROCESSED_DIR / "chunk_ids.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def is_valid_text(text: str, threshold: float = 0.10) -> bool:
    """Return True if the text is mostly printable/meaningful.

    Chunks from raw PDF binary data contain lots of replacement characters
    (\\ufffd) and non-printable bytes.  We skip any chunk where more than
    `threshold` fraction of characters are non-printable.
    """
    if not text or len(text.strip()) < 20:
        return False

    printable = set(string.printable)
    non_printable = sum(1 for ch in text if ch not in printable and ch != "\ufffd")
    replacement = text.count("\ufffd")
    bad_chars = non_printable + replacement
    ratio = bad_chars / len(text)
    return ratio < threshold


def load_chunks(path: Path) -> List[Dict]:
    """Load all chunks from JSONL."""
    chunks = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    return chunks


def filter_chunks(chunks: List[Dict]) -> List[Dict]:
    """Keep only chunks with meaningful text content."""
    valid = []
    for chunk in chunks:
        text = chunk.get("text", "")
        if is_valid_text(text):
            valid.append(chunk)
    return valid


def embed_texts(
    model: SentenceTransformer,
    texts: List[str],
    batch_size: int = 32,
    show_progress: bool = True,
) -> np.ndarray:
    """Generate embeddings with the BGE instruction prefix."""
    prefixed = [INSTRUCTION_PREFIX + t for t in texts]
    embeddings = model.encode(
        prefixed,
        batch_size=batch_size,
        show_progress_bar=show_progress,
        normalize_embeddings=True,
    )
    return embeddings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Embed chunks using bge-small-en-v1.5."
    )
    parser.add_argument(
        "--chunks",
        type=str,
        default=str(CHUNKS_PATH),
        help="Path to chunks.jsonl",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Encoding batch size (default: 32)",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="Device to run model on (default: auto-detect)",
    )
    args = parser.parse_args()

    chunks_path = Path(args.chunks)
    if not chunks_path.exists():
        print(f"ERROR: Chunks file not found: {chunks_path}")
        return 1

    # --- Load and filter ---
    print(f"Loading chunks from {chunks_path} ...")
    all_chunks = load_chunks(chunks_path)
    print(f"  Total chunks loaded: {len(all_chunks)}")

    valid_chunks = filter_chunks(all_chunks)
    skipped = len(all_chunks) - len(valid_chunks)
    print(f"  Valid text chunks:   {len(valid_chunks)}")
    print(f"  Skipped (binary):    {skipped}")

    if not valid_chunks:
        print("ERROR: No valid chunks to embed.")
        return 1

    # --- Load model ---
    print(f"\nLoading model {MODEL_NAME} ...")
    device = args.device
    model = SentenceTransformer(MODEL_NAME, device=device)
    print(f"  Device: {model.device}")

    # --- Embed ---
    texts = [c["text"] for c in valid_chunks]
    print(f"\nEmbedding {len(texts)} chunks (batch_size={args.batch_size}) ...")
    embeddings = embed_texts(model, texts, batch_size=args.batch_size)
    print(f"  Embedding shape: {embeddings.shape}")
    assert embeddings.shape == (len(texts), EMBEDDING_DIM), (
        f"Unexpected shape {embeddings.shape}, expected ({len(texts)}, {EMBEDDING_DIM})"
    )

    # --- Save JSONL with embeddings ---
    print(f"\nSaving {OUT_JSONL} ...")
    with OUT_JSONL.open("w", encoding="utf-8") as f:
        for chunk, emb in zip(valid_chunks, embeddings):
            row = dict(chunk)
            row["embedding"] = emb.tolist()
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # --- Save numpy array ---
    print(f"Saving {OUT_NPY} ...")
    np.save(str(OUT_NPY), embeddings)

    # --- Save chunk ID mapping ---
    chunk_ids = [c["chunk_id"] for c in valid_chunks]
    print(f"Saving {OUT_IDS} ...")
    OUT_IDS.write_text(
        json.dumps(chunk_ids, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # --- Summary ---
    print("\n" + "=" * 50)
    print("Embedding complete!")
    print(f"  Model:             {MODEL_NAME}")
    print(f"  Embedding dim:     {EMBEDDING_DIM}")
    print(f"  Total chunks:      {len(all_chunks)}")
    print(f"  Embedded chunks:   {len(valid_chunks)}")
    print(f"  Skipped chunks:    {skipped}")
    print(f"  Output JSONL:      {OUT_JSONL}")
    print(f"  Output NPY:        {OUT_NPY}")
    print(f"  Output IDs:        {OUT_IDS}")
    print("=" * 50)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
