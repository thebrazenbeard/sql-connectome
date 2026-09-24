from __future__ import annotations

import os

from .runtime import RuntimeConfigurationError, configure_database_environment


def main() -> None:
    process = os.getenv("SQL_CONNECTOME_PROCESS", "rest").strip().lower()
    configure_database_environment()

    if process == "rest":
        import uvicorn

        host = os.getenv("HOST", "0.0.0.0")
        port = int(os.getenv("PORT", "8080"))
        uvicorn.run("sql_connectome.app:app", host=host, port=port)
        return

    if process == "mcp":
        port = os.getenv("PORT")
        os.environ.setdefault("SQL_CONNECTOME_MCP_HOST", "0.0.0.0")
        if port:
            os.environ["SQL_CONNECTOME_MCP_PORT"] = port

        from .mcp_server import main as run_mcp

        run_mcp()
        return

    raise RuntimeConfigurationError(f"PROCESS_UNSUPPORTED:{process}")


if __name__ == "__main__":
    main()
