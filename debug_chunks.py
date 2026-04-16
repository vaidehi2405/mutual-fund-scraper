import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from dotenv import load_dotenv; load_dotenv()
from app.pipeline import get_collection, get_embedder
from app.classify import detect_scheme, detect_topic
from app.retriever import retrieve_chunks

q = "What is the expense ratio of ICICI Bluechip Fund?"
s = detect_scheme(q)
t = detect_topic(q)
chunks = retrieve_chunks(q, s, t, get_collection(), get_embedder())
for i, c in enumerate(chunks):
    print(f"=== CHUNK {i+1} ===")
    print("SCHEME:", c["scheme"])
    print("URL:", c["url"])
    print("TEXT (first 500 chars):")
    print(c["text"][:500])
    print()
