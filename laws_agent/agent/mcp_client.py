from langchain_mcp_adapters.client import MultiServerMCPClient

from laws_agent.agent.config import MCP_SERVER_URL


async def get_mcp_tools() -> list:
    client = MultiServerMCPClient(
        {
            "laws_kb": {
                "url": MCP_SERVER_URL,
                "transport": "streamable_http",
            }
        }
    )
    return await client.get_tools()
