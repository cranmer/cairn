"""MCP server subpackage. Optional — requires the ``mcp`` extra.

A single ``cairn mcp`` server serves multiple cairns (per ADR-0010), with
each tool accepting a ``cairn`` parameter naming the target. The server
imports ``mcp.server.fastmcp`` only when actually used, so the base
package works without the MCP SDK installed.
"""
