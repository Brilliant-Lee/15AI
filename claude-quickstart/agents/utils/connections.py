"""MCP 服务器连接管理模块。"""

# ── 两种连接方式简介 ──────────────────────────────────────────────
#
# Stdio（标准输入输出）
#   Agent 在本机启动一个子进程（如 python calculator_mcp.py），
#   通过 stdin 发数据、从 stdout 收结果。
#   就像父进程和子进程之间"对话"，数据走管道，不走网络。
#   适合：本地工具、开发调试
#
#   Agent进程 ──stdin──→ calculator_mcp.py子进程
#            ←─stdout── 返回结果
#
# SSE（Server-Sent Events，服务器推送事件）
#   Agent 连接一个已经部署好的远程 HTTP 服务。
#   基于 HTTP 长连接，服务端可以主动向客户端推送数据。
#   适合：远程工具服务、多个 Agent 共用同一个 MCP 服务
#
#   Agent进程 ──HTTP请求──→ 远程MCP服务器
#            ←─HTTP响应──  返回结果
#
# ──────────────────────────────────────────────────────────────────

from abc import ABC, abstractmethod
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client

from ..tools.mcp_tool import MCPTool


class MCPConnection(ABC):
    """MCP 连接抽象基类，定义连接/断开/调用工具的通用接口。"""

    def __init__(self):
        self.session = None       # MCP 会话对象，建立后才能收发消息
        self._rw_ctx = None       # 底层读写通道上下文（stdio管道 或 HTTP连接）
        self._session_ctx = None  # MCP 协议层会话上下文

    @abstractmethod
    async def _create_rw_context(self):
        """子类实现：创建具体的读写通道（stdio 或 SSE）。"""

    async def __aenter__(self):
        """建立连接：打开通道 → 创建 MCP 会话 → 握手初始化。"""
        self._rw_ctx = await self._create_rw_context()
        read_write = await self._rw_ctx.__aenter__()
        read, write = read_write                        # 拿到读/写两个流
        self._session_ctx = ClientSession(read, write)  # 用流创建 MCP 会话
        self.session = await self._session_ctx.__aenter__()
        await self.session.initialize()                 # MCP 握手，协商能力
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """断开连接：关闭会话 → 关闭底层通道，无论是否报错都会执行。"""
        try:
            if self._session_ctx:
                await self._session_ctx.__aexit__(exc_type, exc_val, exc_tb)
            if self._rw_ctx:
                await self._rw_ctx.__aexit__(exc_type, exc_val, exc_tb)
        except Exception as e:
            print(f"Error during cleanup: {e}")
        finally:
            # 清空引用，防止残留状态
            self.session = None
            self._session_ctx = None
            self._rw_ctx = None

    async def list_tools(self) -> Any:
        """向 MCP 服务器查询它暴露了哪些工具。"""
        response = await self.session.list_tools()
        return response.tools

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> Any:
        """调用 MCP 服务器上的指定工具，参数由 Agent 传入。"""
        return await self.session.call_tool(tool_name, arguments=arguments)


class MCPConnectionStdio(MCPConnection):
    """Stdio 连接：在本机启动子进程，通过 stdin/stdout 管道通信。

    使用场景：calculator_mcp.py 这类本地 Python 脚本
    配置示例：{"type": "stdio", "command": "python", "args": ["calculator_mcp.py"]}
    """

    def __init__(
        self, command: str, args: list[str] = [], env: dict[str, str] = None
    ):
        super().__init__()
        self.command = command  # 启动子进程的命令，如 "python"
        self.args = args        # 命令参数，如 ["calculator_mcp.py"]
        self.env = env          # 传给子进程的环境变量（可选）

    async def _create_rw_context(self):
        # stdio_client 会 subprocess 启动子进程，返回 (stdin, stdout) 管道
        return stdio_client(
            StdioServerParameters(
                command=self.command, args=self.args, env=self.env
            )
        )


class MCPConnectionSSE(MCPConnection):
    """SSE 连接：通过 HTTP 长连接访问远程 MCP 服务器。

    使用场景：已部署的远程 MCP 服务，多个 Agent 共用
    配置示例：{"type": "sse", "url": "https://my-mcp-server.com/mcp"}
    """

    def __init__(self, url: str, headers: dict[str, str] = None):
        super().__init__()
        self.url = url              # 远程 MCP 服务地址
        self.headers = headers or {}  # HTTP 请求头，如鉴权 token

    async def _create_rw_context(self):
        # sse_client 建立 HTTP 长连接，返回读写流
        return sse_client(url=self.url, headers=self.headers)


def create_mcp_connection(config: dict[str, Any]) -> MCPConnection:
    """工厂函数：根据配置字典的 type 字段，创建对应的连接对象。"""
    conn_type = config.get("type", "stdio").lower()

    if conn_type == "stdio":
        if not config.get("command"):
            raise ValueError("Command is required for STDIO connections")
        return MCPConnectionStdio(
            command=config["command"],
            args=config.get("args"),
            env=config.get("env"),
        )

    elif conn_type == "sse":
        if not config.get("url"):
            raise ValueError("URL is required for SSE connections")
        return MCPConnectionSSE(
            url=config["url"], headers=config.get("headers")
        )

    else:
        raise ValueError(f"Unsupported connection type: {conn_type}")


async def setup_mcp_connections(
    mcp_servers: list[dict[str, Any]] | None,
    stack: AsyncExitStack,
) -> list[MCPTool]:
    """批量建立所有 MCP 连接，将每个工具包装成 MCPTool 返回给 Agent。

    stack 负责统一管理连接生命周期，Agent 退出时自动断开所有连接。
    """
    if not mcp_servers:
        return []

    mcp_tools = []

    for config in mcp_servers:
        try:
            connection = create_mcp_connection(config)
            # 将连接托管给 stack，退出 async with 时自动调用 __aexit__
            await stack.enter_async_context(connection)
            # 查询这个服务器有哪些工具
            tool_definitions = await connection.list_tools()

            # 每个工具定义包装成 MCPTool，持有 connection 引用用于后续调用
            for tool_info in tool_definitions:
                mcp_tools.append(
                    MCPTool(
                        name=tool_info.name,
                        description=tool_info.description
                        or f"MCP tool: {tool_info.name}",
                        input_schema=tool_info.inputSchema,
                        connection=connection,
                    )
                )

        except Exception as e:
            print(f"Error setting up MCP server {config}: {e}")

    print(
        f"Loaded {len(mcp_tools)} MCP tools from {len(mcp_servers)} servers."
    )
    return mcp_tools
