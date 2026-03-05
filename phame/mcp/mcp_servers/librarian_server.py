from mcp.server.fastmcp import FastMCP
from phame.agents.librarian import librarian_agent, LibrarianDeps
from phame.haystack.trusted_references_rag import (
    make_chroma_document_store,
    build_rag_pipeline,
)

import os

# -----------------------------------------
# RAG Setup 
# -----------------------------------------

# CHROMA_PERSIST = "./chroma_db/trusted_ref_subset"
# EMBED_MODEL = "intfloat/e5-large-v2"
CHROMA_PERSIST = "/db/chroma_db/trusted_refs_sentence-transformers-all-MiniLM-L6-v2"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


document_store = make_chroma_document_store(persist_path=CHROMA_PERSIST)
textbook_rag = build_rag_pipeline(document_store, EMBED_MODEL)

deps = LibrarianDeps(textbook_rag=textbook_rag)

# -----------------------------------------
# MCP Server
# -----------------------------------------

server = FastMCP("PHAME Librarian MCP Server")


@server.tool()
async def ask_librarian(question: str) -> str:
    result = librarian_agent.run_sync(
        question,
        deps=deps,
    )
    return result.output


if __name__ == "__main__":
    server.run()
