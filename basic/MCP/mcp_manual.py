from mcp import ClientSession
from mcp.client.sse import sse_client
import asyncio

async def main():
    async with sse_client("http://localhost:8000/sse") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 列出 tools
            tools = await session.list_tools()
            for t in tools.tools:
                print(f"tool: {t.name} — {t.description}")

            # 调用 tool
            result = await session.call_tool("add", {"a": 3, "b": 5})
            print(f"add(3, 5) = {result.content[0].text}")

asyncio.run(main())
