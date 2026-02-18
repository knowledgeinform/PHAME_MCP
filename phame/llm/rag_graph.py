#!/usr/bin/env python3
import os
import time
import logging
import argparse
from pathlib import Path
from typing import TypedDict, List, Optional, Dict, Any

import yaml

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from langchain_openai import ChatOpenAI
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document

# -------------------------
# Logging
# -------------------------
logging.basicConfig(
    level=logging.DEBUG,  # change to INFO/WARNING to reduce output
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("rag-graph")

# -------------------------
# YAML helpers
# -------------------------
def load_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def get_embedding_cfg(cfg: Dict[str, Any]) -> Dict[str, Any]:
    emb = (cfg or {}).get("embedding", {}) or {}
    return {
        "source": emb.get("source", "portkey"),
        "model": emb.get("model", "@opal/sean/openai/clip-vit-large-patch14"),
        "batch_size": int(emb.get("batch_size", 256) or 256),
        "normalize": bool(emb.get("normalize", False)),
        "base_url": emb.get("base_url"),
        "api_key": emb.get("api_key"),
    }

def get_chat_cfg(cfg: Dict[str, Any]) -> Dict[str, Any]:
    chat = (cfg or {}).get("chat", {}) or {}
    return {
        "model": chat.get("model", "@opal/Qwen/Qwen3-0.6B"),
        "temperature": float(chat.get("temperature", 0.3)),
        "base_url": chat.get("base_url"),
        "api_key": chat.get("api_key"),
    }

# -------------------------
# Resolve config precedence
# CLI > config.yml > environment
# -------------------------
def resolve(value_cli, value_cfg, env_name, default=None):
    if value_cli is not None:
        return value_cli
    if value_cfg:
        return value_cfg
    return os.getenv(env_name, default)

# -------------------------
# Builders
# -------------------------
def build_embeddings(
    emb_cfg: Dict[str, Any],
    api_key: str,
    base_url: Optional[str],
) -> OpenAIEmbeddings:
    logger.info(
        f"🔧 Embeddings: model={emb_cfg['model']!r}, normalize={emb_cfg['normalize']}, "
        f"batch_size={emb_cfg['batch_size']}, base_url={base_url!r}"
    )
    return OpenAIEmbeddings(
        model=emb_cfg["model"],
        api_key=api_key,
        base_url=base_url,
        batch_size=emb_cfg["batch_size"],
        normalize=emb_cfg["normalize"],
    )

def read_model_name(default_path: str, override: Optional[str]) -> str:
    if override:
        return override
    p = Path(default_path)
    if p.exists():
        return p.read_text(encoding="utf-8").strip()
    return "@opal/Qwen/Qwen3-0.6B"

# -------------------------
# Prompt
# -------------------------
PROMPT = ChatPromptTemplate.from_template(
    """You are a helpful assistant. Use ONLY the provided context to answer the question.
If the answer isn't in the context, say you don't know.

Context:
{context}

Question:
{question}
"""
)

def format_docs(docs: List[Document]) -> str:
    return "\n\n".join(
        f"[{i+1}] {d.page_content}" + (f"\nMETA: {d.metadata}" if d.metadata else "")
        for i, d in enumerate(docs)
    )

# -------------------------
# State & Nodes
# -------------------------
class RAGState(TypedDict):
    question: str
    context: List[Document]
    citations: List[Dict[str, Any]]  # <-- we’ll keep (id/meta/score) here
    answer: str

def make_nodes(retriever, llm, k: int):
    def retrieve_node(state: RAGState) -> dict:
        """Retrieve with scores + timing; stash citations."""
        query = state["question"]
        logger.info(f"🔍 Retrieving docs for query: {query!r}")

        t0 = time.time()
        results = retriever.vectorstore.similarity_search_with_score(query, k=k)
        dt = (time.time() - t0) * 1000
        docs = [doc for doc, _ in results]

        citations = []
        logger.debug(f"Retrieved {len(results)} documents in {dt:.1f} ms:")
        for i, (doc, score) in enumerate(results):
            meta = doc.metadata or {}
            preview = (doc.page_content or "").replace("\n", " ")[:200]
            try:
                s = float(score)
            except Exception:
                s = score
            logger.debug(f"  • Doc {i+1}: score={s:.4f}" if isinstance(s, float) else f"  • Doc {i+1}: score={s}")
            logger.debug(f"    Metadata: {meta}")
            logger.debug(f"    Preview: {preview}...")
            citations.append({
                "rank": i + 1,
                "score": s,
                "metadata": meta,
                "preview": preview,
            })

        return {"context": docs, "citations": citations}

    def generate_node(state: RAGState) -> dict:
        """Generate answer; keep citations in state; track latency."""
        ctx = format_docs(state["context"])
        messages = PROMPT.format_messages(context=ctx, question=state["question"])

        logger.info(f"🧠 Generating answer for query: {state['question']!r}")
        t0 = time.time()
        ai_msg = llm.invoke(messages)
        dt = (time.time() - t0) * 1000
        logger.debug(f"LLM latency: {dt:.1f} ms")
        logger.debug(f"LLM raw response: {ai_msg}")
        return {"answer": ai_msg.content}

    return retrieve_node, generate_node

# -------------------------
# Main
# -------------------------
def main():
    parser = argparse.ArgumentParser(description="LangGraph + Chroma RAG with separate chat/embedding configs.")
    parser.add_argument("--config", required=True, help="Path to YAML config.")
    parser.add_argument("--persist-dir", default="outputs/chroma")
    parser.add_argument("--collection", default="rag_chunks")
    parser.add_argument("--k", type=int, default=4)

    # Chat overrides / fallbacks
    parser.add_argument("--chat-model", default=None)
    parser.add_argument("--chat-base-url", default=None)
    parser.add_argument("--chat-api-key", default=None)
    parser.add_argument("--chat-temperature", type=float, default=None)

    # Embedding overrides / fallbacks
    parser.add_argument("--embed-base-url", default=None)
    parser.add_argument("--embed-api-key", default=None)

    # Misc
    parser.add_argument("--model-file", default="outputs/index/model_name.txt", help="Fallback for chat model if not set.")
    parser.add_argument("--question", default="What does the metadata describe in this corpus?")
    parser.add_argument("--thread-id", default="yaml-demo")

    args = parser.parse_args()

    cfg = load_yaml(args.config)
    emb_cfg = get_embedding_cfg(cfg)
    chat_cfg = get_chat_cfg(cfg)

    # Resolve API keys and base URLs with precedence
    embed_api_key = resolve(args.embed_api_key, emb_cfg.get("api_key"), "OPENAI_API_KEY")
    embed_base_url = resolve(args.embed_base_url, emb_cfg.get("base_url"), "OPENAI_BASE_URL")

    chat_api_key = resolve(args.chat_api_key, chat_cfg.get("api_key"), "OPENAI_API_KEY")
    chat_base_url = resolve(args.chat_base_url, chat_cfg.get("base_url"), "OPENAI_BASE_URL")

    if not embed_api_key:
        raise SystemExit("Missing embeddings API key: provide --embed-api-key, config.embedding.api_key, or OPENAI_API_KEY.")
    if not chat_api_key:
        raise SystemExit("Missing chat API key: provide --chat-api-key, config.chat.api_key, or OPENAI_API_KEY.")

    # Build embeddings + vector store/retriever
    embeddings = build_embeddings(emb_cfg, api_key=embed_api_key, base_url=embed_base_url)
    vectorstore = Chroma(
        persist_directory=args.persist_dir,
        collection_name=args.collection,
        embedding_function=embeddings,
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": args.k})

    # Chat model (model name: CLI > config.yml > file)
    chat_model_name = resolve(args.chat_model, chat_cfg.get("model"), None) or read_model_name(args.model_file, None)
    chat_temperature = resolve(args.chat_temperature, chat_cfg.get("temperature"), None, default=0.3)
    logger.info(f"🧩 Chat model: {chat_model_name!r} (temp={chat_temperature}, base_url={chat_base_url!r})")

    llm = ChatOpenAI(
        model=chat_model_name,
        api_key=chat_api_key,
        base_url=chat_base_url,
        temperature=float(chat_temperature),
    )

    # Build graph
    retrieve_node, generate_node = make_nodes(retriever, llm, k=args.k)
    graph = StateGraph(RAGState)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)

    checkpointer = MemorySaver()
    app = graph.compile(checkpointer=checkpointer)

    logger.info("🚀 Starting LangGraph RAG pipeline")
    out = app.invoke(
        {"question": args.question, "context": [], "citations": [], "answer": ""},
        config={"configurable": {"thread_id": args.thread_id}},
    )
    logger.info("✅ Pipeline complete")

    # Print answer + citations
    print("\n--- FINAL ANSWER ---\n", out["answer"])
    if out.get("citations"):
        print("\n--- CITATIONS (rank, score, metadata) ---")
        for c in out["citations"]:
            score = f"{c['score']:.4f}" if isinstance(c["score"], float) else str(c["score"])
            print(f"[{c['rank']}] score={score} meta={c['metadata']}")

if __name__ == "__main__":
    main()
