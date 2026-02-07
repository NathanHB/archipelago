import os

from fastmcp import FastMCP
from fastmcp.server.middleware.error_handling import (
    ErrorHandlingMiddleware,
    RetryMiddleware,
)
from middleware.logging import LoggingMiddleware
from tools.get_directory_tree import get_directory_tree
from tools.get_file_metadata import get_file_metadata
from tools.list_files import list_files
from tools.read_image_file import read_image_file
from tools.read_text_file import read_text_file
from tools.search_files import search_files

mcp = FastMCP("filesystem-server")
mcp.add_middleware(ErrorHandlingMiddleware(include_traceback=True))
mcp.add_middleware(RetryMiddleware())
mcp.add_middleware(LoggingMiddleware())

mcp.tool(list_files)
mcp.tool(read_image_file)
mcp.tool(read_text_file)
mcp.tool(search_files)
mcp.tool(get_file_metadata)
mcp.tool(get_directory_tree)

if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "http").lower()
    if transport == "http":
        port = int(os.getenv("MCP_PORT", "5000"))
        mcp.run(transport="http", host="0.0.0.0", port=port)
    else:
        mcp.run(transport="stdio")
