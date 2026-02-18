from .base_client import MCPToolClient

LIBRARIAN_SERVER_PATH = "mcp_servers/librarian_server.py"

class LibrarianClient:

    def __init__(self):
        self.client = MCPToolClient(LIBRARIAN_SERVER_PATH)

    async def ask(self, question: str):
        return await self.client.call(
            "ask_librarian",
            {"question": question}
        )
