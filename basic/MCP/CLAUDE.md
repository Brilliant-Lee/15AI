# MCP 示例代码

三个角色，缺一不可：

```
mcp_server.py  →  暴露工具（add）
mcp_manual.py  →  直连 server，验证工具可用（无 LLM，调试用）
mcp_llm.py    →  Claude + MCP 完整链路（LLM 决策 → 调工具 → 返回）
```

## 启动顺序

```bash
# 1. 先起 server
python mcp_server.py

# 2. 再跑 host（或 client）
python mcp_llm.py
```

## 关键设计

| | server | client / host |
|---|---|---|
| 连接端点 | GET `/sse` | `sse_client("http://localhost:8000/sse")` |
| 消息端点 | POST `/messages/` | SDK 自动处理 |
| transport | `mcp.run("sse")` 改 `mcp.run()` 切 stdio | 对应换 `stdio_client` |

## FastMCP 5 步 → 3 行

① 初始化 `FastMCP()`  
② 定义工具 + ③ 实现 handler → `@mcp.tool() def add(...)`  
④ 注册 transport + ⑤ 启动 → `mcp.run("sse")`
