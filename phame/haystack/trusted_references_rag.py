from pathlib import Path
import os
import time
from argparse import ArgumentParser

from haystack import Pipeline, component

from haystack.utils import Secret

from haystack_integrations.document_stores.chroma import ChromaDocumentStore
from haystack_integrations.components.retrievers.chroma import ChromaEmbeddingRetriever

from haystack.components.converters import PyPDFToDocument
from haystack.components.preprocessors import DocumentCleaner, DocumentSplitter
from haystack.components.embedders import SentenceTransformersTextEmbedder, SentenceTransformersDocumentEmbedder
from haystack.components.embedders import OpenAIDocumentEmbedder, OpenAITextEmbedder

from haystack.components.writers import DocumentWriter
from haystack.components.builders import ChatPromptBuilder, AnswerBuilder
from haystack.components.joiners import AnswerJoiner
from haystack.components.generators.chat import OpenAIChatGenerator

from haystack.dataclasses import ChatMessage, GeneratedAnswer

from phame.llm.utils import _extract_workpsace_str


def get_embedding_model(embedding_model: str = None):
    if embedding_model is None:
        embedding_model = "sentence-transformers/all-MiniLM-L6-v2"

    if embedding_model.startswith("sentence-transformers/") or \
       embedding_model.startswith("intfloat/") or \
       embedding_model.startswith("BAAI/"):
        doc = SentenceTransformersDocumentEmbedder(model=embedding_model)
        text = SentenceTransformersTextEmbedder(model=embedding_model)
        return doc, text

    elif embedding_model.startswith("@opal") or \
         embedding_model.startswith("@openai-enterprise-pilot") or \
         embedding_model.startswith("@openai-phame-pg"):

        doc = OpenAIDocumentEmbedder(
            model=embedding_model,
            api_key=Secret.from_env_var(_extract_workpsace_str(embedding_model)),
            api_base_url=os.getenv("PORTKEY_BASE_URL"),
            batch_size=128
        )
        text = OpenAITextEmbedder(
            model=embedding_model,
            api_key=Secret.from_env_var(_extract_workpsace_str(embedding_model)),
            api_base_url=os.getenv("PORTKEY_BASE_URL")
        )
        return doc, text

    raise ValueError(f"Unsupported embedding model: {embedding_model}")

def make_chroma_document_store(persist_path: str | None = None) -> ChromaDocumentStore:
    # persist_path keeps your collection across runs (optional)
    return ChromaDocumentStore(persist_path=persist_path) if persist_path else ChromaDocumentStore()
    # Connection options (persist_path / host+port) are documented here. :contentReference[oaicite:2]{index=2}


def build_indexing_pipeline(document_store: ChromaDocumentStore, embedding_model: str) -> Pipeline:
    pdf_converter = PyPDFToDocument()
    cleaner = DocumentCleaner()
    splitter = DocumentSplitter(split_by="word", split_length=150, split_overlap=50)
    doc_embedder, _ = get_embedding_model(embedding_model)
    writer = DocumentWriter(document_store=document_store)

    # doc_embedder.warm_up()

    p = Pipeline()
    p.add_component("pdf_converter", pdf_converter)
    p.add_component("cleaner", cleaner)
    p.add_component("splitter", splitter)
    p.add_component("doc_embedder", doc_embedder)
    p.add_component("writer", writer)

    # p.connect("pdf_converter", "cleaner")
    # p.connect("cleaner", "splitter")
    # p.connect("splitter", "doc_embedder")
    # p.connect("doc_embedder.documents", "writer.documents")  # embedder outputs documents w/ embeddings
    
    # ✅ Explicit ports: everything passes a list of Documents via "documents"
    p.connect("pdf_converter.documents", "cleaner.documents")
    p.connect("cleaner.documents", "splitter.documents")
    p.connect("splitter.documents", "doc_embedder.documents")
    p.connect("doc_embedder.documents", "writer.documents")

    return p


def index_pdf_dir(pdf_root_dir: str, indexing_pipeline: Pipeline) -> int:
    pdf_paths = [str(p) for p in Path(pdf_root_dir).rglob("*.pdf") if p.is_file()]
    if not pdf_paths:
        raise FileNotFoundError(f"No PDFs found under: {pdf_root_dir}")

    out = indexing_pipeline.run({
        "pdf_converter": {"sources": pdf_paths},
        })

    # out = indexing_pipeline.run(
    #     {"pdf_converter": {"sources": pdf_paths[:1]}},
    #     include_outputs_from={"pdf_converter", "cleaner", "splitter", "doc_embedder"},
    # )

    # print("converter docs:", out["pdf_converter"]["documents"])
    # print("splitter docs:", out["splitter"]["documents"])

    # conv = PyPDFToDocument()
    # docs = conv.run(sources=[pdf_paths[0]])["documents"]
    # print(len(docs), docs[0].content[:200] if docs else "NO TEXT")


    return out["writer"]["documents_written"]




@component
class FirstAnswerText:
    @component.output_types(answer=str)
    def run(self, answers: list[GeneratedAnswer]):
        return {"answer": answers[0].data if answers else ""}

def build_rag_pipeline(document_store: ChromaDocumentStore, embedding_model: str, llm_model: str = "@openai-enterprise-pilot/o4-mini") -> Pipeline:

    # Get embedding model
    _, text_embedder = get_embedding_model(embedding_model)

    retriever = ChromaEmbeddingRetriever(document_store=document_store)  # key change :contentReference[oaicite:4]{index=4}

    template = [
        ChatMessage.from_user(
            """
Given the following information, answer the question.

Context:
{% for document in documents %}
{{ document.content }}
{% endfor %}

Question: {{ question }}
Answer:
""".strip()
        )
    ]
    prompt_builder = ChatPromptBuilder(template=template, required_variables="*")
    llm = OpenAIChatGenerator(
        model=llm_model,
        api_base_url=os.environ["PORTKEY_BASE_URL"],  # Portkey OpenAI-compatible URL
        api_key=Secret.from_env_var(_extract_workpsace_str(model_name=llm_model))
        )
    answer_builder = AnswerBuilder()
    # first_answer = AnswerJoiner(top_k=1)
    first_answer = FirstAnswerText()

    p = Pipeline()
    p.add_component("text_embedder", text_embedder)
    p.add_component("retriever", retriever)
    p.add_component("prompt_builder", prompt_builder)
    p.add_component("llm", llm)
    p.add_component("answer_builder", answer_builder)
    p.add_component("first_answer", first_answer)

    # same wiring pattern you had:
    p.connect("text_embedder.embedding", "retriever.query_embedding")  # ChromaEmbeddingRetriever expects query_embedding :contentReference[oaicite:5]{index=5}
    p.connect("retriever.documents", "prompt_builder.documents")
    p.connect("prompt_builder.prompt", "llm.messages")
    p.connect("llm.replies", "answer_builder.replies")
    p.connect("retriever.documents", "answer_builder.documents")
    p.connect("answer_builder.answers", "first_answer.answers")

    return p


if __name__ == "__main__":

    parser = ArgumentParser(description="trusted references rag. For embedding and querying trusted reference db.")
    parser.add_argument("-m", "--embedding_model", type=str, default="sentence-transformers/all-MiniLM-L6-v2",
                        help="Embedding model.")

    parser.add_argument("-d", "--dir", type=str, default=".",
                        help="directory of documents to embed.")

    parser.add_argument("-r", "--rebuild", action="store_true",
                        help="If the db should be rebuilt.")

    parser.add_argument("-p", "--persist", type=str, default="./chroma_db/trusted_refs",
                        help="Directory to save chroma db")

    parser.add_argument("-l", "--llm_model", type=str, default="@openai-enterprise-pilot/o4-mini",
                        help="LLM model for question answering.")

    args = parser.parse_args()

    EMBED_MODEL = args.embedding_model
    PDF_DIR = args.dir
    REBUILD_DB = args.rebuild
    CHROMA_PERSIST = args.persist
    LLM = args.llm_model

    print("\n===== RAG System Configuration =====")
    print(f"Embedding model : {EMBED_MODEL}")
    print(f"Document dir    : {PDF_DIR}")
    print(f"Persist path    : {CHROMA_PERSIST}")
    print(f"Rebuild DB      : {REBUILD_DB}")
    print(f"Question LLM    : {LLM}")
    print("=====================================\n")

    # generate db directory
    print("[1/3] Initializing document store...")
    document_store = make_chroma_document_store(persist_path=CHROMA_PERSIST)
    print("Document store ready\n")

    if REBUILD_DB:
        print("[2/3] Rebuilding vector database...")
        start = time.time()

        indexing = build_indexing_pipeline(document_store, EMBED_MODEL)
        written = index_pdf_dir(PDF_DIR, indexing)

        elapsed = time.time() - start
        print(f"Indexed {written} document chunks in {elapsed:.2f} seconds\n")
    else:
        print("[2/3] Skipping rebuild (using existing DB)\n")

    print("[3/3] Building RAG pipeline...")
    rag = build_rag_pipeline(document_store, EMBED_MODEL, llm_model=LLM)
    print("RAG pipeline ready\n")

    while True:
        question = input("\nWhat would you like to know? (type 'exit' to quit)\n> ").strip()

        if question.lower() in {"exit", "quit"}:
            print("Exiting.")
            break

        print("\nRunning retrieval + generation...")
        start = time.time()

        result = rag.run(
            {
                "text_embedder": {"text": question},   # must be string
                "prompt_builder": {"question": question},
                "answer_builder": {"query": question},
                "retriever": {"top_k": 5},
            }
        )

        elapsed = time.time() - start

        print("\n===== Answer =====")
        print(result["first_answer"]["answer"])
        print("==================")
        print(f"(Completed in {elapsed:.2f} seconds)")
