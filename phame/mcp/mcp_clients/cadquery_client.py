from .base_client import MCPToolClient

CADQUERY_SERVER_PATH = "mcp_servers/cadquery_server.py"

class CADQueryClient:

    def __init__(self):
        self.client = MCPToolClient(CADQUERY_SERVER_PATH)

    async def generate(self, prompt: str):
        return await self.client.call(
            "generate_cadquery_code",
            {"design_prompt": prompt}
        )
