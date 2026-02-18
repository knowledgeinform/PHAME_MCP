DEFAULTS_RAG = {
    "data": {"raw_dir": "data/raw"},
    "chunking": {"chunk_size": 1200, "overlap": 200},
    "embedding": {
        "source": "sentence-transformers",
        "model": "sentence-transformers/all-MiniLM-L6-v2",
        "batch_size": 64,
        "normalize": False
    },
    "chroma": {
        "persist_dir": "outputs/chroma",
        "collection": "rag_chunks",
        "recreate": False
    },
    "outputs": {
        "metadata_path": "outputs/metadata/metadata.jsonl",
        "model_name_path": "outputs/index/model_name.txt"
    },
    "retrieval": {"top_k": 5,
                  "llm": "Qwen/Qwen3-30B-A3B-Thinking-2507-FP8"}
}


