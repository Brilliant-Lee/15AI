"""
Host = 协调者：从 MCP Server 拿工具列表 → 喂给 Claude → 执行工具调用 → 循环直到结束
"""
import os, asyncio, anthropic
from mcp import ClientSession
from mcp.client.sse import sse_client

async def run(query: str):
    client = anthropic.Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
        base_url=os.environ.get("ANTHROPIC_BASE_URL"),
    )

    async with sse_client("http://localhost:8000/sse") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. 把 MCP tools 转成 Claude API 格式
            tools = [
                {"name": t.name, "description": t.description, "input_schema": t.inputSchema}
                for t in (await session.list_tools()).tools
            ]

            messages = [{"role": "user", "content": query}]

            # 2. Agentic loop
            while True:
                resp = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=1024,
                    tools=tools,
                    messages=messages,
                )
                messages.append({"role": "assistant", "content": resp.content})

                if resp.stop_reason != "tool_use":
                    print(next(b.text for b in resp.content if hasattr(b, "text")))
                    break

                # 3. 执行工具，结果塞回 messages
                results = []
                for b in resp.content:
                    if b.type == "tool_use":
                        out = await session.call_tool(b.name, b.input)
                        results.append({"type": "tool_result", "tool_use_id": b.id,
                                        "content": out.content[0].text})
                messages.append({"role": "user", "content": results})

asyncio.run(run("帮我算一下 12 加 88 等于多少"))
