from langchain_mcp_adapters.client import MultiServerMCPClient

from backend.agent.config import MCP_SERVER_URL


async def get_mcp_tools() -> list:
    client = MultiServerMCPClient(
        {
            "knowledge_base": {
                "url": MCP_SERVER_URL,
                "transport": "streamable_http",
            }
        }
    )
    return await client.get_tools()
