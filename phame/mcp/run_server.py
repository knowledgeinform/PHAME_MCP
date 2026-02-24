

import argparse
import uvicorn
import os


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--persist", type=str, default=None)

    args = parser.parse_args()

    if args.persist:
        os.environ["CHROMA_PERSIST"] = args.persist

    uvicorn.run(
        "phame.mcp.server_app:app",
        host=args.host,
        port=args.port,
        reload=False
    )


if __name__ == "__main__":
    main()


# # Librarian Server A
# python run_server.py --port 8001 --persist ./trusted_ref_A

# # Librarian Server B
# python run_server.py --port 8002 --persist ./trusted_ref_B
