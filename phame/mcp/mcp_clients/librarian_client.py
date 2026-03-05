"""
python phame/mcp/mcp_clients/librarian_client.py \
  --host phame-justdance \
  --port 8001 \
  --question "What is bending stress?" \
  --top-k 3
"""

import requests
import json
import argparse
import sys


class LibrarianClient:
    def __init__(self, host: str, port: int, timeout: int = 300):
        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout

    def health(self):
        response = requests.get(
            f"{self.base_url}/health",
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def query(self, rag_query: str, top_k: int = 5):
        response = requests.post(
            f"{self.base_url}/mcp",
            json={
                "tool": "librarian",
                "payload": {
                    "rag_query": rag_query,
                    "top_k": top_k
                }
            },
            timeout=self.timeout
        )

        response.raise_for_status()
        data = response.json()

        if data["status"] != "ok":
            raise RuntimeError(f"MCP error: {data}")

        result = data["result"]

        # Unwrap FastMCP response format
        if isinstance(result, list) and len(result) > 0:
            text_payload = result[0]["text"]
            return json.loads(text_payload)

        return result


def parse_args():
    parser = argparse.ArgumentParser(
        description="Query remote MCP Librarian service"
    )

    parser.add_argument(
        "--host",
        required=True,
        help="Hostname or IP of MCP server (e.g. phame-justdance)"
    )

    parser.add_argument(
        "--port",
        type=int,
        required=True,
        help="Port number of MCP server (e.g. 8001)"
    )

    parser.add_argument(
        "--question",
        required=True,
        help="Question to send to librarian tool"
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of retrieved documents (default: 5)"
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="HTTP timeout in seconds (default: 60)"
    )

    return parser.parse_args()


def main():
    args = parse_args()

    client = LibrarianClient(
        host=args.host,
        port=args.port,
        timeout=args.timeout
    )

    try:
        print("Checking server health...")
        print(client.health())

        print("\nQuerying librarian...\n")
        result = client.query(args.question, args.top_k)

        print("Answer:\n")
        print(result["answer"])

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

# import requests
# import json
# import sys


# class LibrarianClient:
#     def __init__(self, host="phame-justdance", port=8001, timeout=60):
#         self.base_url = f"http://{host}:{port}"
#         self.timeout = timeout

#     def health(self):
#         response = requests.get(
#             f"{self.base_url}/health",
#             timeout=self.timeout
#         )
#         response.raise_for_status()
#         return response.json()

#     def query(self, rag_query: str, top_k: int = 5):
#         response = requests.post(
#             f"{self.base_url}/mcp",
#             json={
#                 "tool": "librarian",
#                 "payload": {
#                     "rag_query": rag_query,
#                     "top_k": top_k
#                 }
#             },
#             timeout=self.timeout
#         )

#         response.raise_for_status()
#         data = response.json()

#         if data["status"] != "ok":
#             raise RuntimeError(f"MCP error: {data}")

#         result = data["result"]

#         # Unwrap FastMCP message format
#         if isinstance(result, list) and len(result) > 0:
#             text_payload = result[0]["text"]
#             return json.loads(text_payload)

#         return result


# def main():
#     if len(sys.argv) < 2:
#         print("Usage:")
#         print("  python librarian_client.py \"your question here\"")
#         sys.exit(1)

#     question = sys.argv[1]

#     client = LibrarianClient()

#     print("Checking server health...")
#     print(client.health())

#     print("\nQuerying librarian...\n")

#     result = client.query(question)

#     print("Answer:\n")
#     print(result["answer"])


# if __name__ == "__main__":
#     main()





# from .base_client import MCPToolClient


# class LibrarianClient:

#     def __init__(self, server_url: str):
#         self.client = MCPToolClient(server_url)

#     def query(self, question: str, top_k: int = 5):
#         result = self.client.call(
#             "librarian",
#             {
#                 "question": question,
#                 "top_k": top_k
#             }
#         )
#         return result["answer"]






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
