import os
from pathlib import Path
from datetime import datetime, timezone
import chromadb

# Turn off huggingface warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"
if not os.environ.get("HF_HUB_DISABLE_SYMLINKS_WARNING"):
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

from sentence_transformers import SentenceTransformer

from app.classify import classify_query, detect_scheme, detect_topic
from app.retriever import retrieve_chunks
from app.generator import generate_answer
from app.validator import validate_response, REFUSAL_MESSAGE

ROOT_DIR = Path(__file__).resolve().parent.parent
VECTOR_STORE_DIR = ROOT_DIR / "data" / "vector_store"

# Global Singletons
_collection = None
_embedder = None

def get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
        _collection = client.get_or_create_collection(
            name="mf_chunks", 
            metadata={"hnsw:space": "cosine"}
        )
    return _collection

def get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer("BAAI/bge-small-en-v1.5")
    return _embedder

def get_refusal(last_updated: str = "") -> str:
    msg = REFUSAL_MESSAGE
    if last_updated:
        msg = f"{msg} | Last updated: {last_updated}"
    return msg

def run_pipeline(query: str) -> str:
    """
    Execute the full RAG pipeline for a given query.
    """
    # 1. Call classify_query(query)
    classification = classify_query(query)
    if classification == "ADVISORY":
        last_updated = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return get_refusal(last_updated)
        
    # 2. Call detect_scheme and detect_topic
    scheme = detect_scheme(query)
    topic = detect_topic(query)
    
    # Ensure dependencies are loaded
    collection = get_collection()
    embedder = get_embedder()
    
    # 3. Call retrieve_chunks
    chunks = retrieve_chunks(query, scheme, topic, collection, embedder)
    if not chunks:
        return "No matching information found. Please visit icicipruamc.com."
        
    # 4. Call generate_answer
    answer = generate_answer(query, chunks)
    
    if answer.startswith("API_ERROR"):
        return f"Whoops! I hit my AI provider's Rate Limits: {answer}"
        
    # 5. Call validate_response
    validated_answer = validate_response(answer)
    
    # 6. Return the validated answer
    return validated_answer

def main():
    test_queries = [
        "What is the expense ratio of ICICI Prudential Bluechip Fund?",
        "What is the lock-in period for the ELSS fund?",
        "Should I invest in the Flexicap Fund?"
    ]
    
    print("\nStarting Unified RAG Pipeline Test...\n")
    for q in test_queries:
        print("-" * 60)
        print(f"QUERY: {q}")
        try:
            response = run_pipeline(q)
            print(f"RESPONSE:\n{response}")
        except Exception as e:
            print(f"PIPELINE ERROR: {e}")
            
    print("-" * 60)

if __name__ == "__main__":
    main()
