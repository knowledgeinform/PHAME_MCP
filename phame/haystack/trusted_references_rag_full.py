from pathlib import Path

from haystack import Pipeline, component
from haystack.components.converters import PyPDFToDocument
from haystack.components.preprocessors import DocumentCleaner, DocumentSplitter
from haystack.components.embedders import SentenceTransformersDocumentEmbedder
from haystack.components.writers import DocumentWriter
from haystack_integrations.document_stores.chroma import ChromaDocumentStore
from haystack.utils import Secret
from haystack.components.embedders import OpenAIDocumentEmbedder, OpenAITextEmbedder
from haystack.components.embedders import SentenceTransformersTextEmbedder
from haystack.components.builders import ChatPromptBuilder, AnswerBuilder
from haystack.components.joiners import AnswerJoiner
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.dataclasses import ChatMessage, GeneratedAnswer

from haystack_integrations.components.retrievers.chroma import ChromaEmbeddingRetriever
import os

def make_chroma_document_store(persist_path: str | None = None) -> ChromaDocumentStore:
    # persist_path keeps your collection across runs (optional)
    return ChromaDocumentStore(persist_path=persist_path) if persist_path else ChromaDocumentStore()
    # Connection options (persist_path / host+port) are documented here. :contentReference[oaicite:2]{index=2}


def build_indexing_pipeline(document_store: ChromaDocumentStore, embedding_model: str) -> Pipeline:
    pdf_converter = PyPDFToDocument()
    cleaner = DocumentCleaner()
    splitter = DocumentSplitter(split_by="word", split_length=150, split_overlap=50)
    doc_embedder = SentenceTransformersDocumentEmbedder(model=embedding_model)    
    # doc_embedder = OpenAIDocumentEmbedder(
    #     api_key=Secret.from_env_var("PORTKEY_API_KEY"),
    #     api_base_url=os.environ["PORTKEY_BASE_URL"],
    #     model=embedding_model,  # or whatever your Portkey config routes to
    # )
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
        "pdf_converter": {"sources": pdf_paths}
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

def build_rag_pipeline(document_store: ChromaDocumentStore, embedding_model: str, llm_model: str = "openai/gpt-oss-120b") -> Pipeline:
    text_embedder = SentenceTransformersTextEmbedder(model=embedding_model)
    # text_embedder = OpenAITextEmbedder(
    #     api_base_url=os.environ["PORTKEY_BASE_URL"],  # Portkey OpenAI-compatible URL
    #     api_key=Secret.from_env_var("PORTKEY_API_KEY"),
    #     model=embedding_model,
    # )
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
        api_key=Secret.from_env_var("PORTKEY_API_KEY")
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

    
    EMBED_MODEL = "intfloat/e5-large-v2"
    # EMBED_MODEL = "openai/clip-vit-large-patch14"
    
    
    # PDF_DIR = "/home/amundrj1/phame/input_data/pdfs_subset"
    PDF_DIR = r"C:\Users\amundrj1\Documents\phame\input_data\pdfs"
    REBUILD_DB = True
    CHROMA_PERSIST = "./chroma_db/trusted_ref"  # optional; omit for in-memory

    document_store = make_chroma_document_store(persist_path=CHROMA_PERSIST)
    
    if REBUILD_DB is True:
        indexing = build_indexing_pipeline(document_store, EMBED_MODEL)
        written = index_pdf_dir(PDF_DIR, indexing)
        print("Indexed PDFs chunks:", written)

    rag = build_rag_pipeline(document_store, EMBED_MODEL)

    question = "What is this collection about?"
    result = rag.run(
        {
            "text_embedder": {"text": question},
            "prompt_builder": {"question": question},
            "answer_builder": {"query": question},
            "retriever": {"top_k": 5},
        }
    )
    print(result["first_answer"]["answer"])
