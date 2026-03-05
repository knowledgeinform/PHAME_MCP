from mcp.server.fastmcp import FastMCP
from phame.agents.design_agents import build_cadquery_macro_agent

cadquery_agent = build_cadquery_macro_agent(model_name="@opal/Qwen/Qwen3-30B-A3B-Thinking-2507-FP8")

server = FastMCP("PHAME CADQuery MCP Server")


@server.tool()
async def generate_cadquery_code(design_prompt: str) -> str:
    result = cadquery_agent.run_sync(design_prompt)
    return result.output


if __name__ == "__main__":
    server.run()
