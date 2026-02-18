"""
Query a local Chroma RAG collection using the same embedding model.
"""

from __future__ import annotations
import argparse
from pathlib import Path
from typing import Dict, Any, List

import yaml
import numpy as np
from sentence_transformers import SentenceTransformer

import chromadb
from chromadb.config import Settings

from phame.rag_utils.globals import DEFAULTS_RAG

from portkey_ai import Portkey
from phame.rag_utils.build_rag import load_config


TENANT = "default_tenant"
DATABASE = "default_database"

def embed_query_sentence_transformer(
        model: SentenceTransformer,
        query: str = '',
) -> np.ndarray:
    """
    This function is for embedding queries using a SentenceTransformer model
    :param model: Sentence Transformer model for embedding
    :param texts: list of texts
    :param batch_size: number of texts to embed at once
    :param normalize: bool for normalizing resulting embeddings
    :return: list of vectors
    """
    vec = model.encode(query, convert_to_numpy=True, show_progress_bar=True)
    return vec.astype("float32")


def embed_query_portkey(
        client: Portkey,
        model: str = 'text-embedding-3-small',
        query: str = '',
) -> np.ndarray:
    """
    This function is for embedding queries using a portkey client tied to an ai model
    :param client: portkey client
    :param model: model name
    :param query: list of texts
    :return: embeddings
    """

    response = client.embeddings.create(
        model = model,
        input=query[start: end],
        encoding_format="float"
    )
    vec = response.data.d.embedding

    return vec


def find_k_similar_docs(q_vec: numpy.ndarray, persist_dir: str, collection: str, top_k: int=5):

    print(f"Connecting to Chroma (dir={persist_dir}) collection={collection}")
    client =  chromadb.PersistentClient(path=persist_dir, tenant=TENANT, database=DATABASE)
    col = client.get_collection(name=collection)

    res = col.query(
        query_embeddings=[q_vec],
        n_results=top_k,
        #where=make_where(),
        include=["documents", "metadatas", "distances"]
    )
    return res

def run_query(query: str, config: Dict):
    emb_source = config['embedding']['source']
    emb_model = config['embedding']['model']
    persist_dir = config['chroma']['persist_dir']
    collection = config['chroma']['collection']
    top_k = config['retrieval']['top_k']

    # embed query
    api_key = None
    base_url = None
    if emb_source.lower().startswith("portkey"):
        api_key = os.environ.get('PORTKEY_API_KEY')
        base_url = os.environ.get('PORTKEY_BASE_URL')

        if not api_key or not base_url:
            raise ValueError("Missing or empty PORTKEY_API_KEY or PORTKEY_BASE_URL environment variable.")

        client = Portkey(
            base_url = base_url,
            api_key = api_key,
        )
        q_vec = embed_query_portkey(client, emb_model, query)

    else:
        # default to sentence transformer
        model = SentenceTransformer(emb_model)
        q_vec = embed_query_sentence_transformer(model, query)

    # get matches
    res = find_k_similar_docs(q_vec, persist_dir, collection, top_k)

    return res



def main():
    pass

if __name__ == "__main__":
    main()
