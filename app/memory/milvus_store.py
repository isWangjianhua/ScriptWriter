from pymilvus import MilvusClient, DataType

# For local MVP development, Milvus Lite is built strictly into the client
# meaning it runs locally on a file just like SQLite without needing Docker!
milvus_client = MilvusClient("./data/milvus_demo.db")

GLOBAL_COLLECTION_NAME = "global_script_vectors"

def _ensure_collection_exists(dimension: int):
    # Create schema if global collection doesn't exist
    if not milvus_client.has_collection(GLOBAL_COLLECTION_NAME):
        # We need a proper schema to support scalar filtering on user_id and project_id
        schema = MilvusClient.create_schema(
            auto_id=True,
            enable_dynamic_field=True,
        )
        schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True, auto_id=True)
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=dimension)
        schema.add_field(field_name="user_id", datatype=DataType.VARCHAR, max_length=255)
        schema.add_field(field_name="project_id", datatype=DataType.VARCHAR, max_length=255)
        schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=65535)
        schema.add_field(field_name="source", datatype=DataType.VARCHAR, max_length=255)
        
        index_params = milvus_client.prepare_index_params()
        index_params.add_index(field_name="vector", metric_type="COSINE", index_type="FLAT")
        index_params.add_index(field_name="user_id", index_type="Trie")
        index_params.add_index(field_name="project_id", index_type="Trie")
        
        milvus_client.create_collection(
            collection_name=GLOBAL_COLLECTION_NAME,
            schema=schema,
            index_params=index_params
        )

def add_texts_to_milvus(user_id: str, project_id: str, texts: list[str], vectors: list[list[float]]):
    if not texts:
        return
        
    # Ensure global table is ready
    _ensure_collection_exists(dimension=len(vectors[0]))
        
    # Data is isolated logically via fields (Metadata), NOT via separate tables
    data = [
        {
            "vector": vectors[i], 
            "text": texts[i], 
            "user_id": user_id,
            "project_id": project_id,
            "source": "user_upload"
        }
        for i in range(len(texts))
    ]
    
    milvus_client.insert(collection_name=GLOBAL_COLLECTION_NAME, data=data)

def search_milvus_bible(user_id: str, project_id: str, query_vector: list[float], limit: int = 2) -> list[str]:
    if not milvus_client.has_collection(GLOBAL_COLLECTION_NAME):
        return []
        
    # Search the vector database using scalar filtering for strict isolation
    # This prevents retrieving data from another user/project on the database engine level
    filter_expr = f'user_id == "{user_id}" and project_id == "{project_id}"'
    
    search_res = milvus_client.search(
        collection_name=GLOBAL_COLLECTION_NAME,
        data=[query_vector],
        limit=limit,
        filter=filter_expr,
        output_fields=["text", "source"]
    )
    
    results = []
    # parse Milvus search returns (usually a nested list of hits)
    for hits in search_res:
        for hit in hits:
            results.append(hit["entity"]["text"])
            
    return results
