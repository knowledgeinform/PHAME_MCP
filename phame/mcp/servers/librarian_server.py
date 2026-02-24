import os
from haystack_integrations.document_stores.chroma import ChromaDocumentStore
from phame.haystack.trusted_references_rag import build_rag_pipeline


class LibrarianService:

    def __init__(
        self,
        chroma_path: str,
        embed_model: str,
        llm_model: str,
    ):
        self.document_store = ChromaDocumentStore(
            persist_path=chroma_path
        )

        self.rag = build_rag_pipeline(
            self.document_store,
            embed_model,
            llm_model
        )

    def query(self, question: str, top_k: int = 5):
        result = self.rag.run({
            "text_embedder": {"text": question},
            "prompt_builder": {"question": question},
            "answer_builder": {"query": question},
            "retriever": {"top_k": top_k}
        })

        return {
            "answer": result["first_answer"]["answer"]
        }







# from mcp.server.fastmcp import FastMCP
# from phame.agents.librarian import librarian_agent, LibrarianDeps
# from phame.haystack.trusted_references_rag import (
#     make_chroma_document_store,
#     build_rag_pipeline,
# )

# import os

# # -----------------------------------------
# # RAG Setup 
# # -----------------------------------------

# CHROMA_PERSIST = "./chroma_db/trusted_ref_subset"
# EMBED_MODEL = "intfloat/e5-large-v2"

# document_store = make_chroma_document_store(persist_path=CHROMA_PERSIST)
# textbook_rag = build_rag_pipeline(document_store, EMBED_MODEL)

# deps = LibrarianDeps(textbook_rag=textbook_rag)

# # -----------------------------------------
# # MCP Server
# # -----------------------------------------

# server = FastMCP("PHAME Librarian MCP Server")


# @server.tool()
# async def ask_librarian(question: str) -> str:
#     result = librarian_agent.run_sync(
#         question,
#         deps=deps,
#     )
#     return result.output


# if __name__ == "__main__":
#     server.run()
