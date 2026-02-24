import os
from phame.agents.design_agents import build_cadquery_macro_agent


class CadQueryService:
    """
    Server-side CadQuery agent service using macro agent.
    """

    def __init__(self):
        api_key = os.environ["PORTKEY_API_KEY"]
        base_url = os.environ["PORTKEY_BASE_URL"]

        self.cadquery_agent = build_cadquery_macro_agent(
            model_name="Qwen/Qwen3-30B-A3B-Thinking-2507-FP8",
            api_key=api_key,
            base_url=base_url,
        )

    def generate(self, design_prompt: str) -> dict:
        result = self.cadquery_agent.run_sync(design_prompt)

        return {
            "cad_output": result.output
        }








# from mcp.server.fastmcp import FastMCP
# from phame.agents.design_agents import build_cadquery_macro_agent
# import os

# api_key = os.environ["PORTKEY_API_KEY"]
# base_url = os.environ["PORTKEY_BASE_URL"]

# cadquery_agent = build_cadquery_macro_agent(
#     model_name="Qwen/Qwen3-30B-A3B-Thinking-2507-FP8",
#     api_key=api_key,
#     base_url=base_url,
# )

# server = FastMCP("PHAME CADQuery MCP Server")


# @server.tool()
# async def generate_cadquery_code(design_prompt: str) -> str:
#     result = cadquery_agent.run_sync(design_prompt)
#     return result.output


# if __name__ == "__main__":
#     server.run()
