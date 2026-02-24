import requests


class MCPToolClient:

    def __init__(self, base_url: str, timeout: int = 60):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def call(self, tool_name: str, payload: dict):
        response = requests.post(
            f"{self.base_url}/mcp",
            json={
                "tool": tool_name,
                "payload": payload
            },
            timeout=self.timeout
        )

        if response.status_code != 200:
            raise RuntimeError(response.text)

        return response.json()["result"]




# from mcp import ClientSession, StdioServerParameters
# from mcp.client.stdio import stdio_client
# import asyncio


# class MCPToolClient:

#     def __init__(self, script_path: str):
#         self.script_path = script_path

#     async def call(self, tool_name: str, args: dict):
#         server_params = StdioServerParameters(
#             command="python",
#             args=[self.script_path],
#         )

#         async with stdio_client(server_params) as (read, write):
#             async with ClientSession(read, write) as session:
#                 await session.initialize()
#                 result = await session.call_tool(tool_name, args)
#                 return result.content[0].text
