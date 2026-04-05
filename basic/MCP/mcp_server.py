from mcp.server.fastmcp import FastMCP

# 1. 初始化（host/port 在这里配）
mcp = FastMCP("demo-server", host="0.0.0.0", port=8000)

# 2. 注册 tools，实现handler：函数签名即 Schema，docstring 即 description
@mcp.tool()
def add(a: float, b: float) -> float:
    """两数相加"""
    return a + b

# 3. 启动：stdio/SSE
# mcp.run()          # 默认 stdio
mcp.run("sse")       # SSE 