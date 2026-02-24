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

CHROMA_PATH = "./chroma_db/trusted_ref_subset"

EMBED_MODEL = "intfloat/e5-large-v2"

LLM_MODEL = "openai/gpt-oss-120b"
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
def librarian_tool(question: str, top_k: int = 5):
    return librarian_service.query(question, top_k)


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
def mcp_endpoint(request: MCPRequest):
    try:
        result = mcp_server.execute(
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
def list_tools():
    return {
        "tools": mcp_server.list_tools()
    }


@app.get("/health")
def health():
    return {"status": "ok"}
