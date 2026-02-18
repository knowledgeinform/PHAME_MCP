from __future__ import annotations

from phame.rag_utils.build_rag import embed_texts_portkey, embed_texts_sentence_transformer
from phame.rag_utils.build_rag import load_config, upload_embeddings_to_db, create_db_metadata


import argparse, os, json, uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Tuple, Dict, Any
import pandas as pd
import yaml
from tqdm import tqdm
from pypdf import PdfReader
import numpy as np
from sentence_transformers import SentenceTransformer

import chromadb
from chromadb.config import Settings

from globals import DEFAULTS_RAG

from portkey_ai import Portkey



@dataclass
class Part_Chunk:
    id: str
    abstract_description: str
    beginner_description: str
    intermediate_description: str
    expert_description: str
    nli_data: str
    cad_query_code: str


def chunk_part() -> List[Part_Chunk]:
    """
    This function takes a list of page texts, and chunks each one and returns a list of Chunk classes.
    :param pdf_path: dir to all pdfs
    :param chunk_size: size for chunk
    :param overlap: size of overlap between chunks (i.e. the end of one chunk starts another)
    :return: list of Chunks
    """

    text2cad = pd.read_csv('text2cad_v1.1.csv')

    text2cad.loc[
        text2cad['beginner'].apply(lambda x: type(x) != str), 'beginner'
    ] = text2cad[text2cad['beginner'].apply(lambda x: type(x) != str)]['abstract']

    out: List[Part_Chunk] = []
    random_sample = text2cad.sample(100000)
    for irow, row in random_sample.iterrows():
        id = str(row['uid'])
        code_file_name = f'CQ/{id}.py'
        with open(code_file_name) as fp:
            code = fp.readlines()

        out.append(Part_Chunk(
            id=id,
            abstract_description = row['abstract'],
            beginner_description = row['beginner'],
            intermediate_description = row['intermediate'],
            expert_description = row['expert'],
            nli_data = row['nli_data'],
            cad_query_code = "".join(code)
        ))

    return out


def main():
    ap = argparse.ArgumentParser(description="Build Chroma RAG collection from PDFs.")
    ap.add_argument("--config", type=str, default=None)
    ap.add_argument("--pdf_dir", type=str, default=None)
    ap.add_argument("--persist_dir", type=str, default=None)
    ap.add_argument("--collection", type=str, default=None)
    ap.add_argument("--recreate", action="store_true")
    args = ap.parse_args()

    # load in configs
    config = load_config(args.config)
    if args.pdf_dir:
        config["data"]["raw_dir"] = args.pdf_dir

    if args.persist_dir:
        config["chroma"]["persist_dir"] = args.persist_dir
        config["outputs"]["metadata_path"] = args.persist_dir + "/metadata/metadata.jsonl"
        config["outputs"]["model_name_path"] = args.persist_dir +  "/outputs/index/model_name.txt"

    if args.collection:
        config["chroma"]["collection"] = args.collection

    if args.recreate:
        config["chroma"]["recreate"] = True

    # pull out vars
    raw_dir = config["data"]["raw_dir"]
    chunk_size = config["chunking"]["chunk_size"]
    overlap = config["chunking"]["overlap"]

    emb_source = config["embedding"]["source"]
    emb_model = config["embedding"]["model"]
    batch_size = config["embedding"]["batch_size"]
    normalize = config["embedding"]["normalize"]

    persist_dir = config["chroma"]["persist_dir"]
    collection = config["chroma"]["collection"]
    recreate = config["chroma"]["recreate"]

    meta_path = config["outputs"]["metadata_path"]
    model_path = config["outputs"]["model_name_path"]

    #
    api_key = None
    base_url = None
    if emb_source.lower().startswith("portkey"):
        api_key = os.environ.get('PORTKEY_API_KEY')
        base_url = os.environ.get('PORTKEY_BASE_URL')

        if not api_key or not base_url:
            raise ValueError("Missing or empty PORTKEY_API_KEY or PORTKEY_BASE_URL environment variable.")

    # chunk
    chunks = chunk_part()

    if not chunks:
        raise SystemExit("No chunks extracted.")

    print(f"Embedding {len(chunks)} chunks with {emb_model}…")

    # embed texts
    texts = [c.beginner_description for c in chunks]
    if emb_source.lower().startswith("portkey"):
        api_key = os.environ['PORTKEY_API_KEY']
        base_url = os.environ['PORTKEY_BASE_URL']
        client = Portkey(
            base_url=base_url,
            api_key=api_key,
        )
        vecs = embed_texts_portkey(client, emb_model, texts, batch_size, normalize)

    else:
        # default to sentence transformer
        model = SentenceTransformer(emb_model)
        vecs = embed_texts_sentence_transformer(model, texts, batch_size, normalize)

    # generate Chroma vector db
    print(f"Connecting to Chroma (persist_dir={persist_dir})…")
    upload_embeddings_to_db(chunks, texts, vecs, persist_dir, collection, recreate)

    # saving metadata
    create_db_metadata(meta_path, model_path, emb_model, chunks)

    # Save to disk
    print("Done.")
    print(f"  Chroma dir:  {persist_dir}")
    print(f"  Collection:  {collection}")
    print(f"  Metadata:    {meta_path}")
    print(f"  Model file:  {model_path}")


if __name__ == "__main__":
    main()