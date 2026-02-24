from .base_client import MCPToolClient


class LibrarianClient:

    def __init__(self, server_url: str):
        self.client = MCPToolClient(server_url)

    def query(self, question: str, top_k: int = 5):
        result = self.client.call(
            "librarian",
            {
                "question": question,
                "top_k": top_k
            }
        )
        return result["answer"]






# from .base_client import MCPToolClient

# LIBRARIAN_SERVER_PATH = "mcp_servers/librarian_server.py"

# class LibrarianClient:

#     def __init__(self):
#         self.client = MCPToolClient(LIBRARIAN_SERVER_PATH)

#     async def ask(self, question: str):
#         return await self.client.call(
#             "ask_librarian",
#             {"question": question}
#         )
