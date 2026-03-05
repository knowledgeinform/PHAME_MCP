#!/bin/sh

# python trusted_references_rag.py --embedding_model "@opal/openai/clip-vit-large-patch14" -d /db/pdfs_subset --rebuild -p /db/chroma_db/trusted_refs_subset_clip --llm_model @opal/openai/gpt-oss-120b
# python trusted_references_rag.py --embedding_model "@opal/Qwen/Qwen3-Embedding-8B" -d /db/pdfs_subset --rebuild -p /db/chroma_db/trusted_refs_subset --llm_model @opal/openai/gpt-oss-120b 

# python trusted_references_rag.py --embedding_model "@opal/Qwen/Qwen3-Embedding-8B" -d /home/amundrj1/phame/input_data/pdfs --rebuild -p /home/amundrj1/phame/home/amundrj1/phame/chroma_db/trusted_refs_qwen3_embeddings_8B --llm_model @opal/openai/gpt-oss-120b 


python trusted_references_rag.py --embedding_model "sentence-transformers/all-MiniLM-L6-v2" --rebuild -p /db/chroma_db/trusted_refs_subset_sentence-transformers-all-MiniLM-L6-v2 --llm_model @openai-enterprise-pilot/o3 -d @openai-enterprise-pilot/o3

