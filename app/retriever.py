def retrieve_chunks(
    query: str, 
    scheme: str, 
    topic: str, 
    collection, 
    embedder
) -> list[dict]:
    """
    Retrieve top 3 similar chunks for a given query from ChromaDB.

    Args:
        query (str): The user's search query.
        scheme (str): The exact scheme name to filter by. If "all", no scheme filtering is applied.
        topic (str): The identified topic for the query (passed through to the response).
        collection: The initialized chromadb Collection instance.
        embedder: The embedding model instance (must have an .encode() method) used to vectorize the query.

    Returns:
        list[dict]: A list of up to 3 dictionaries containing the retrieved chunk details:
            - text: The document content
            - url: Source URL from metadata
            - scheme: Scheme from metadata
            - topic: Topic (from metadata or fallback to provided topic)
            - scraped_at: Ingestion timestamp from metadata
    """
    # 1. Embed the query using the embedder passed in
    query_embedding = embedder.encode(query)
    
    # Convert numpy array to list for ChromaDB if necessary
    if hasattr(query_embedding, "tolist"):
        query_embedding = query_embedding.tolist()

    # 2. Filter ChromaDB where metadata scheme == scheme (unless "all")
    where_filter = None
    if scheme and scheme.lower() != "all":
        # Handle variations and always include "NA" for global FAQs
        scheme_variations = ["NA"]
        if scheme == "large_cap":
            scheme_variations.extend(["largecap", "Largecap", "large cap"])
        elif scheme == "flexicap":
            scheme_variations.extend(["flexicap", "flexi cap"])
        elif scheme == "elss":
            scheme_variations.extend(["elss", "ELSS"])
        elif scheme == "midcap":
            scheme_variations.extend(["Midcap", "MidCap", "mid cap", "midcap"])
        elif scheme == "small_cap":
            scheme_variations.extend(["small cap", "smallcap"])
        else:
            scheme_variations.append(scheme)
            
        where_filter = {"scheme": {"$in": scheme_variations}}

    # 3. Query ChromaDB for top 10 most similar chunks
    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=10,
            where=where_filter
        )
    except Exception as e:
        print(f"Error querying ChromaDB: {e}")
        return []

    # Handle cases where nothing was found
    if not results or not results.get("documents") or not results["documents"][0]:
        return []
        
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]

    # 4 & 5. Return a list of up to 3 dicts containing requested data mapping
    retrieved = []
    for doc, meta in zip(documents, metadatas):
        retrieved.append({
            "text": doc,
            "url": meta.get("url", ""),
            "scheme": meta.get("scheme", ""),
            # Use metadata topic if exists, otherwise fallback to the query's detected topic
            "topic": meta.get("topic", topic), 
            # ingested_at is the metadata key in build_vector_store for the timestamp
            "scraped_at": meta.get("ingested_at", "")
        })

    return retrieved
