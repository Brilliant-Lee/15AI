"""基于 Claude API 和工具的 Agent 实现。"""

import asyncio
import os
from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import Any

from anthropic import Anthropic

from .tools.base import Tool
from .utils.connections import setup_mcp_connections
from .utils.history_util import MessageHistory
from .utils.tool_util import execute_tools


@dataclass
class ModelConfig:
    """Claude 模型参数配置。"""

    # 可用模型列表：
    # - claude-sonnet-4-20250514（默认，性能与速度均衡）
    # - claude-opus-4-20250514（最强能力）
    # - claude-haiku-4-5-20251001（最快速度）
    # - claude-3-5-sonnet-20240620
    # - claude-3-haiku-20240307
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096       # 单次响应最大 token 数
    temperature: float = 1.0    # 采样温度，越高越随机
    context_window_tokens: int = 180000  # 上下文窗口大小，用于控制历史裁剪


class Agent:
    """基于 Claude 的 Agent，支持工具调用能力。"""

    def __init__(
        self,
        name: str,
        system: str,
        tools: list[Tool] | None = None,
        mcp_servers: list[dict[str, Any]] | None = None,
        config: ModelConfig | None = None,
        verbose: bool = False,
        client: Anthropic | None = None,
        message_params: dict[str, Any] | None = None,
    ):
        """初始化 Agent。

        参数：
            name: Agent 名称，用于日志标识
            system: 系统提示词
            tools: Agent 可使用的工具列表
            mcp_servers: MCP 服务器配置列表
            config: 模型配置，未传入时使用默认值
            verbose: 是否开启详细日志
            client: Anthropic 客户端实例
            message_params: 传递给 client.messages.create() 的额外参数，
                           同名键会覆盖 config 中的配置。
        """
        self.name = name
        self.system = system
        self.verbose = verbose
        self.tools = list(tools or [])          # 拷贝工具列表，避免共享引用
        self.config = config or ModelConfig()   # 未传入配置时使用默认值
        self.mcp_servers = mcp_servers or []
        self.message_params = message_params or {}
        # 未传入 client 时从环境变量读取 API Key 自动创建
        self.client = client or Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY", "")
        )
        # 初始化消息历史管理器，负责上下文裁剪与格式转换
        self.history = MessageHistory(
            model=self.config.model,
            system=self.system,
            context_window_tokens=self.config.context_window_tokens,
            client=self.client,
        )

        if self.verbose:
            print(f"\n[{self.name}] Agent initialized")

    def _prepare_message_params(self) -> dict[str, Any]:
        """构造 client.messages.create() 的调用参数。

        返回以 config 为基础的参数字典，message_params 中的同名键会覆盖默认值。
        """
        return {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "system": self.system,
            "messages": self.history.format_for_api(),   # 将历史记录格式化为 API 所需结构
            "tools": [tool.to_dict() for tool in self.tools],  # 将工具对象序列化为字典
            **self.message_params,  # 用户自定义参数会覆盖上方同名键
        }

    async def _agent_loop(self, user_input: str) -> list[dict[str, Any]]:
        """处理用户输入，循环执行工具调用直到模型给出最终回答。"""
        if self.verbose:
            print(f"\n[{self.name}] Received: {user_input}")
        # 将用户消息写入历史
        await self.history.add_message("user", user_input, None)

        # 构建工具名称 -> 工具对象的映射，便于后续按名称查找
        tool_dict = {tool.name: tool for tool in self.tools}

        # 核心循环：持续调用模型直到没有工具调用为止（ReAct 模式）
        while True:
            # 若历史超出上下文窗口则自动裁剪
            self.history.truncate()
            params = self._prepare_message_params()

            # 合并请求头：默认 beta 头可被 message_params 中的 extra_headers 覆盖
            default_headers = {"anthropic-beta": "code-execution-2025-05-22"}
            if "extra_headers" in params:
                # 从 params 中取出 extra_headers，与默认头合并（自定义头优先）
                custom_headers = params.pop("extra_headers")
                merged_headers = {**default_headers, **custom_headers}
            else:
                merged_headers = default_headers

            # 调用 Claude API
            response = self.client.messages.create(
                **params,
                extra_headers=merged_headers
            )
            # 筛选出本轮所有工具调用块
            tool_calls = [
                block for block in response.content if block.type == "tool_use"
            ]

            if self.verbose:
                for block in response.content:
                    if block.type == "text":
                        print(f"\n[{self.name}] Output: {block.text}")
                    elif block.type == "tool_use":
                        params_str = ", ".join(
                            [f"{k}={v}" for k, v in block.input.items()]
                        )
                        print(
                            f"\n[{self.name}] Tool call: "
                            f"{block.name}({params_str})"
                        )

            # 将模型响应（含工具调用）写入历史，记录 token 用量
            await self.history.add_message(
                "assistant", response.content, response.usage
            )

            if tool_calls:
                # 并发执行所有工具，收集结果后作为 user 消息写回历史
                tool_results = await execute_tools(
                    tool_calls,
                    tool_dict,
                )
                if self.verbose:
                    for block in tool_results:
                        print(
                            f"\n[{self.name}] Tool result: "
                            f"{block.get('content')}"
                        )
                await self.history.add_message("user", tool_results)
            else:
                # 无工具调用，模型给出最终回答，退出循环并返回响应
                return response

    async def run_async(self, user_input: str) -> list[dict[str, Any]]:
        """异步运行 Agent，支持 MCP 工具。"""
        # AsyncExitStack 统一管理多个 MCP 连接的生命周期
        async with AsyncExitStack() as stack:
            original_tools = list(self.tools)  # 保存原始工具列表以便还原

            try:
                # 建立 MCP 连接并将其工具追加到当前工具列表
                mcp_tools = await setup_mcp_connections(
                    self.mcp_servers, stack
                )
                self.tools.extend(mcp_tools)
                return await self._agent_loop(user_input)
            finally:
                # 无论成功与否，都恢复原始工具列表，避免状态污染
                self.tools = original_tools

    def run(self, user_input: str) -> list[dict[str, Any]]:
        """同步运行 Agent。"""
        # 为不支持 async/await 的调用方提供同步入口
        return asyncio.run(self.run_async(user_input))
