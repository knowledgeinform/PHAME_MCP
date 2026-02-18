import asyncio
from supervisor.supervisor_mcp import MCPBasedSupervisor


async def main():
    supervisor = MCPBasedSupervisor()

    while True:
        user = input("\nyou> ")
        if user.lower() in ["exit", "quit"]:
            break

        result = await supervisor.handle_request(user)

        print("\n--- FACTS ---")
        print(result["facts"])

        print("\n--- CAD CODE ---")
        print(result["cad_code"])


if __name__ == "__main__":
    asyncio.run(main())
