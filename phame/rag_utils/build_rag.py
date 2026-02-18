"""
This python file is meant for building a RAG database using Chroma. It does so with these steps:
1) load PDFs
2) chucking texts
3) embedding texts with chosen model (OPAL)
4) upsert into a persistent Chroma collection
"""


from __future__ import annotations
import argparse, os, json, uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Tuple, Dict, Any

import yaml
from tqdm import tqdm
from pypdf import PdfReader
import numpy as np
from sentence_transformers import SentenceTransformer

import chromadb
from chromadb.config import Settings

from phame.rag_utils.globals import DEFAULTS_RAG

from portkey_ai import Portkey


# Types
@dataclass
class Chunk:
    id: str
    source: str
    page: int
    start: int
    end: int
    text: str


# I/O

def load_config(path: str | None) -> Dict[str, Any]:
    """
    Loads config. Default config is in globals.py
    :param path: config path (yaml file)
    :return: config dictionary
    """
    cfg = DEFAULTS_RAG.copy()
    if path:
        with open(path, "r", encoding="utf-8") as f:
            user = yaml.safe_load(f) or {}
        for k, v in user.items():
            if isinstance(v, dict) and k in cfg: cfg[k].update(v)
            else: cfg[k] = v
    return cfg

def list_pdfs(root: str='.') -> List[Path]:
    """
    Helper function for listing out pdfs in a directory.
    :param root: directotry root
    :return: list of pdf locations on disk
    """
    return [Path(p) for p in Path(root).rglob('*.pdf')]

def read_pdf_pages(pdf_path: Path) -> List[str]:
    """
    this function translates a pdf into text. The return is a list of each page of the PDF in text.
    :param pdf_path: PDF location on disk
    :return: list of pages as strings
    """
    r = PdfReader(str(pdf_path))
    out = []
    for p in r.pages:
        try:
            out.append(p.extract_text() or "")
        except Exception:
            out.append("")
    return out

# Chunking

def sliding_chunks(text: str, size: int, overlap: int) -> List[Tuple[int,int,str]]:
    """
    This function slides a window over text and chunks the text into size with overlaps.
    :param text: Text for chunking
    :param size: Size of chunk
    :param overlap: size of overlap between chunks (i.e. the end of one chunk starts another)
    :return: list of chunks
    """
    if not text:
        return []

    if overlap >= size:
        raise ValueError("overlap must be < chunk_size")

    n, start, chunks = len(text), 0, []
    while start < n:
        end = min(start + size, n)
        t = text[start:end].strip()
        if t:
            chunks.append((start, end, t))
        if end == n:
            break
        start = end - overlap
    return chunks

def chunk_pdf(pdf_path: Path, chunk_size: int, overlap: int) -> List[Chunk]:
    """
    This function takes a list of page texts, and chunks each one and returns a list of Chunk classes.
    :param pdf_path: dir to all pdfs
    :param chunk_size: size for chunk
    :param overlap: size of overlap between chunks (i.e. the end of one chunk starts another)
    :return: list of Chunks
    """
    out: List[Chunk] = []
    pdfs_pages = read_pdf_pages(pdf_path)
    for page_i, page_txt in enumerate(pdfs_pages, start=1):
        for s, e, txt in sliding_chunks(page_txt, chunk_size, overlap):
            out.append(Chunk(
                id=str(uuid.uuid4()),
                source=str(pdf_path.resolve()),
                page=page_i, start=s, end=e, text=txt
            ))
    return out


# Embedding

def embed_texts_sentence_transformer(
        model: SentenceTransformer,
        texts: List[str],
        batch_size: int,
        normalize: bool = False
) -> np.ndarray:
    """
    This function is for embedding text using a SentenceTransformer model
    :param model: Sentence Transformer model for embedding
    :param texts: list of texts
    :param batch_size: number of texts to embed at once
    :param normalize: bool for normalizing resulting embeddings
    :return: list of vectors
    """
    vecs = model.encode(texts, batch_size=batch_size, convert_to_numpy=True,
                        normalize_embeddings=normalize, show_progress_bar=True)
    return vecs.astype("float32")


def embed_texts_portkey(
        client: Portkey,
        model: str = 'text-embedding-3-small',
        texts: List[str] = [],
        batch_size: int = 64,
        normalize: bool = False
) -> np.ndarray:
    """
    This function is for embedding text using a portkey client tied to an ai model
    :param client: portkey client
    :param model: model name
    :param texts: list of texts
    :param normalize: bool for normalizing resulting embeddings
    :return: list of vectors
    """
    vecs = []
    n = len(texts)
    for start in tqdm(range(0, n, batch_size)):
        end = min(start + batch_size, n)
        response = client.embeddings.create(
            model = model,
            input=texts[start: end],
            encoding_format="float"
        )
        vecs += [d.embedding for d in response.data]
    vecs = np.array(vecs, dtype="float32")

    if normalize:
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        vecs = vecs / norms

    return vecs

def ensure_parent(p: str | Path):
    """
    helper function for generating save path if not extant
    :param p:
    :return:
    """
    Path(p).parent.mkdir(parents=True, exist_ok=True)

def upload_embeddings_to_db(chunks, texts, vecs, persist_dir: str, collection: str, recreate: bool):
    client = chromadb.PersistentClient(path=persist_dir)
    if recreate and any(col.name == collection for col in client.list_collections()):
        client.delete_collection(collection)

    col = client.get_or_create_collection(
        name=collection,
        # we pass embeddings manually; no embedding function needed here
        metadata={"hnsw:space": "cosine"}  # cosine distance for normalized embeddings
    )

    print("Upserting to Chroma…")
    B = 2048
    ids = [c.id for c in chunks]
    metadatas = [asdict(c) for c in chunks]
    documents = texts
    # upsert in batches
    for i in tqdm(range(0, len(chunks), B), desc="Upserts"):
        col.upsert(
            ids=ids[i:i + B],
            embeddings=vecs[i:i + B].tolist(),
            documents=documents[i:i + B],
            metadatas=metadatas[i:i + B],
        )

def create_db_metadata(meta_path: str, model_path: str, emb_model:str, chunks: List):

    # Persist convenience files
    ensure_parent(meta_path)
    with open(meta_path, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")
    ensure_parent(model_path)
    Path(model_path).write_text(emb_model, encoding="utf-8")

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
        config["outputs"]["model_name_path"] = args.persist_dir + "/outputs/index/model_name.txt"

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




    # get list of pdfs
    pdfs = list_pdfs(raw_dir)

    if not pdfs:
        raise SystemExit(f"No PDFs found under: {raw_dir}")

    print(f"Found {len(pdfs)} PDFs. Chunking…")

    # chunk
    chunks: List[Chunk] = []
    for p in tqdm(pdfs, desc="PDFs"):
        chunks.extend(chunk_pdf(p, chunk_size, overlap))

    if not chunks:
        raise SystemExit("No chunks extracted.")

    print(f"Embedding {len(chunks)} chunks with {emb_model}…")

    # embed texts
    texts = [c.text for c in chunks]
    if emb_source.lower().startswith("portkey"):
        api_key = os.environ['PORTKEY_API_KEY']
        base_url = os.environ['PORTKEY_BASE_URL']
        client = Portkey(
            base_url = base_url,
            api_key = api_key,
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