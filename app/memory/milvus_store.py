from pymilvus import MilvusClient

# For local MVP development, Milvus Lite is built strictly into the client
# meaning it runs locally on a file just like SQLite without needing Docker!
milvus_client = MilvusClient("./data/milvus_demo.db")

def add_texts_to_milvus(tenant_id: str, project_id: str, texts: list[str], vectors: list[list[float]]):
    # Data is isolated via separate collections based on tenant+project 
    collection_name = f"bible_{tenant_id}_{project_id}"
    
    # Create schema if collection doesn't exist
    if not milvus_client.has_collection(collection_name):
        milvus_client.create_collection(
            collection_name=collection_name,
            dimension=len(vectors[0])  # E.g. 1536 for OpenAI
        )
        
    data = [
        {"id": i, "vector": vectors[i], "text": texts[i], "source": "user_upload"}
        for i in range(len(texts))
    ]
    
    milvus_client.insert(collection_name=collection_name, data=data)

def search_milvus_bible(tenant_id: str, project_id: str, query_vector: list[float], limit: int = 2) -> list[str]:
    # Prevent retrieving data from another tenant/project
    collection_name = f"bible_{tenant_id}_{project_id}"
    
    if not milvus_client.has_collection(collection_name):
        return []
        
    # Search the vector database
    search_res = milvus_client.search(
        collection_name=collection_name,
        data=[query_vector],
        limit=limit,
        output_fields=["text", "source"]
    )
    
    results = []
    # parse Milvus search returns (usually a nested list of hits)
    for hits in search_res:
        for hit in hits:
            results.append(hit["entity"]["text"])
            
    return results
