from pathlib import Path
import os
import time
from argparse import ArgumentParser
import pandas as pd
import yaml

from phame.haystack.trusted_references_rag import get_embedding_model, make_chroma_document_store

from haystack import Pipeline, component, Document

from haystack.utils import Secret

from haystack_integrations.document_stores.chroma import ChromaDocumentStore
from haystack_integrations.components.retrievers.chroma import ChromaEmbeddingRetriever

from haystack.components.preprocessors import DocumentCleaner
from haystack.components.embedders import SentenceTransformersTextEmbedder, SentenceTransformersDocumentEmbedder
from haystack.components.embedders import OpenAIDocumentEmbedder, OpenAITextEmbedder

from haystack.components.writers import DocumentWriter
from haystack.components.builders import ChatPromptBuilder, AnswerBuilder
from haystack.components.joiners import AnswerJoiner
from haystack.components.generators.chat import OpenAIChatGenerator

from haystack.dataclasses import ChatMessage, GeneratedAnswer


def build_indexing_pipeline(document_store: ChromaDocumentStore, embedding_model: str) -> Pipeline:
    cleaner = DocumentCleaner()
    doc_embedder, _ = get_embedding_model(embedding_model)
    writer = DocumentWriter(document_store=document_store)

    p = Pipeline()
    p.add_component("cleaner", cleaner)
    p.add_component("doc_embedder", doc_embedder)
    p.add_component("writer", writer)

    p.connect("cleaner.documents", "doc_embedder.documents")
    p.connect("doc_embedder.documents", "writer.documents")

    return p



def index_cad_query(csv_file: str, indexing_pipeline: Pipeline) -> int:

    csv = pd.read_csv(csv_file)
    docs = []
    for irow, row in csv.iterrows():
        # getting text
        text = row['description']

        # getting code
        file_name = row['file_name']
        with open(file_name, "r", encoding="utf-8") as fp:
            code = fp.read()

        doc = Document(content=text, meta={'file_name': file_name, "cad_code":code})
        docs.append(doc)

    out = indexing_pipeline.run({
        "cleaner": {"documents": docs},
        })

    return out["writer"]["documents_written"]


def build_query_pipeline(document_store: ChromaDocumentStore, embedding_model: str="sentence-transformers/all-MiniLM-L6-v2") -> Pipeline:

    # Get embedding model
    _, text_embedder = get_embedding_model(embedding_model)

    retriever = ChromaEmbeddingRetriever(document_store=document_store)  # key change :contentReference[oaicite:4]{index=4}

    p = Pipeline()
    p.add_component("text_embedder", text_embedder)
    p.add_component("retriever", retriever)

    # same wiring pattern you had:
    p.connect("text_embedder.embedding", "retriever.query_embedding")  # ChromaEmbeddingRetriever expects query_embedding :contentReference[oaicite:5]{index=5}

    return p


if __name__ == "__main__":

    parser = ArgumentParser(description="trusted references rag. For embedding and querying trusted reference db.")
    parser.add_argument("-m", "--model", type=str, default="sentence-transformers/all-MiniLM-L6-v2",
                        help="Embedding model.")

    parser.add_argument("-c", "--csv", type=str, default=".",
                        help="csv file of cadquery descriptions")

    parser.add_argument("-r", "--rebuild", action="store_true",
                        help="If the db should be rebuilt.")

    parser.add_argument("-p", "--persist", type=str, default="./chroma_db/trusted_refs",
                        help="Directory to save chroma db")


    args = parser.parse_args()

    EMBED_MODEL = args.model
    CSV_LOC = args.csv
    REBUILD_DB = args.rebuild
    CHROMA_PERSIST = args.persist

    print("\n===== RAG System Configuration =====")
    print(f"Embedding model : {EMBED_MODEL}")
    print(f"CSV File        : {CSV_LOC}")
    print(f"Persist path    : {CHROMA_PERSIST}")
    print(f"Rebuild DB      : {REBUILD_DB}")
    print("=====================================\n")

    # generate db directory
    print("[1/3] Initializing document store...")
    document_store = make_chroma_document_store(persist_path=CHROMA_PERSIST)
    print("Document store ready\n")

    if REBUILD_DB:
        print("[2/3] Rebuilding vector database...")
        start = time.time()

        indexing = build_indexing_pipeline(document_store, EMBED_MODEL)
        written = index_cad_query(CSV_LOC, indexing)

        # writting metadata
        metadata = {"embedding_model": EMBED_MODEL, "csv_file": CSV_LOC}
        with open(CHROMA_PERSIST + "metadata.yaml", "w") as fp:
            yaml.dump(metadata, fp)

        elapsed = time.time() - start
        print(f"Indexed {written} document chunks in {elapsed:.2f} seconds\n")
    else:
        # check if existing db embedding matches requested
        with open(CHROMA_PERSIST + "metadata.yaml") as fp:
            metadata = yaml.safe_load(fp)

        chroma_embedding = metadata['embedding_model']
        assert chroma_embedding == EMBED_MODEL, f"\nEmbedding model {EMBED_MODEL} does not match the embedding of the chroma db in {CHROMA_PERSIST} which is {chroma_embedding}\n"

        print("[2/3] Skipping rebuild (using existing DB)\n")

    print("[3/3] Building RAG pipeline...")
    rag = build_query_pipeline(document_store, EMBED_MODEL)
    print("RAG pipeline ready\n")

    while True:
        question = input("\nWhat examples do you need? (type 'exit' to quit)\n> ").strip()

        if question.lower() in {"exit", "quit"}:
            print("Exiting.")
            break

        print("\nRunning retrieval + generation...")
        start = time.time()

        result = rag.run(
            {
                "text_embedder": {"text": question},   # must be string
                "retriever": {"top_k": 5},
            }
        )

        elapsed = time.time() - start

        print("\n===== Answer =====")
        print(result["retriever"]["documents"])
        print("==================")
        print(f"(Completed in {elapsed:.2f} seconds)")
