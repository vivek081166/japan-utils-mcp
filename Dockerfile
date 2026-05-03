# Dockerfile for japan-utils-mcp
#
# Runs the MCP server over stdio. Used by Glama and other MCP registries
# to introspect the server (initialize → tools/list). Not the recommended
# install path for end users — use `uvx japan-utils-mcp` directly.

FROM python:3.13-slim

# Install the MCP server from PyPI
RUN pip install --no-cache-dir japan-utils-mcp

# MCP servers communicate over stdio; the entrypoint runs forever waiting
# for JSON-RPC messages on stdin and writes responses to stdout.
ENTRYPOINT ["japan-utils-mcp"]
