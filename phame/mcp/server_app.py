# phame/mcp/server_app.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from mcp.server.fastmcp import FastMCP
from phame.mcp.servers.librarian_server import LibrarianService
from phame.mcp.servers.cadquery_server import CadQueryService

# --------------------------------------------------
# Configuration
# --------------------------------------------------

# CHROMA_PATH = "/db/chroma_db/trusted_refs_subset" #change to "trusted_refs" when finished 

# # EMBED_MODEL = "@opal/Qwen/Qwen3-Embedding-8B"
# EMBED_MODEL = "intfloat/e5-large-v2"
CHROMA_PATH = "/db/chroma_db/trusted_refs_sentence-transformers-all-MiniLM-L6-v2"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


LLM_MODEL = "@opal/openai/gpt-oss-120b"
# --------------------------------------------------
# MCP Server Instance
# --------------------------------------------------

app = FastAPI(title="PHAME MCP Server")
mcp_server = FastMCP("PHAME Librarian MCP Server")

# --------------------------------------------------
# Instantiate Services Separately
# --------------------------------------------------

librarian_service = LibrarianService(
    chroma_path=CHROMA_PATH,
    embed_model=EMBED_MODEL,
    llm_model=LLM_MODEL
)

cadquery_service = CadQueryService()

# --------------------------------------------------
# Register Tools
# --------------------------------------------------

@mcp_server.tool("librarian")
def librarian_tool(rag_query: str, top_k: int = 5):
    return librarian_service.query(rag_query, top_k)


@mcp_server.tool("cadquery")
def generate_cadquery_code(design_prompt: str) -> dict:
    return cadquery_service.generate(design_prompt)

# --------------------------------------------------
# MCP Request Schema
# --------------------------------------------------

class MCPRequest(BaseModel):
    tool: str
    payload: dict


# --------------------------------------------------
# MCP Endpoint
# --------------------------------------------------

@app.post("/mcp")
async def mcp_endpoint(request: MCPRequest):
    try:
        result = await mcp_server.call_tool(
            request.tool,
            request.payload
        )
        return {
            "status": "ok",
            "result": result
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.get("/tools")
async def list_tools():
    tools = await mcp_server.list_tools()
    return {
        "tools": tools
    }


@app.get("/health")
def health():
    return {"status": "ok"}
