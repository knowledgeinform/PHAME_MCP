import asyncio
from mcp_clients.librarian_client import LibrarianClient
from mcp_clients.cadquery_client import CADQueryClient


class MCPBasedSupervisor:

    def __init__(self):
        self.librarian = LibrarianClient()
        self.cadquery = CADQueryClient()

    async def handle_request(self, user_prompt: str):

        print("Step 1: Consulting Librarian")
        facts = await self.librarian.ask(user_prompt)

        print("Step 2: Generating CAD")
        cad_code = await self.cadquery.generate(
            f"{user_prompt}\n\nRelevant facts:\n{facts}"
        )

        return {
            "facts": facts,
            "cad_code": cad_code
        }
