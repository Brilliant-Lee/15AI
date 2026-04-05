"""
Claude SDK 客户端配置模块
=========================

提供创建和配置 Claude Agent SDK 客户端的函数，
包含多层安全防护（沙箱隔离、权限限制、命令白名单）。
"""

import json
import os
from pathlib import Path

from claude_code_sdk import ClaudeCodeOptions, ClaudeSDKClient
from claude_code_sdk.types import HookMatcher

from security import bash_security_hook


# Puppeteer MCP 工具列表（浏览器自动化，用于截图、点击、填表等）
PUPPETEER_TOOLS = [
    "mcp__puppeteer__puppeteer_navigate",
    "mcp__puppeteer__puppeteer_screenshot",
    "mcp__puppeteer__puppeteer_click",
    "mcp__puppeteer__puppeteer_fill",
    "mcp__puppeteer__puppeteer_select",
    "mcp__puppeteer__puppeteer_hover",
    "mcp__puppeteer__puppeteer_evaluate",
]

# 内置工具列表（文件读写、搜索、执行命令）
BUILTIN_TOOLS = [
    "Read",
    "Write",
    "Edit",
    "Glob",
    "Grep",
    "Bash",
]


def create_client(project_dir: Path, model: str) -> ClaudeSDKClient:
    """
    创建一个带有多层安全防护的 Claude Agent SDK 客户端。

    Args:
        project_dir: 项目所在目录
        model: 使用的 Claude 模型名称

    Returns:
        配置完成的 ClaudeSDKClient 实例

    安全层级（纵深防御）：
    1. Sandbox（沙箱） - OS 层面隔离 bash 命令，防止文件系统逃逸
    2. Permissions（权限） - 文件操作限制在 project_dir 目录内
    3. Security hooks（安全钩子） - bash 命令在执行前通过白名单验证
       （白名单详见 security.py 的 ALLOWED_COMMANDS）
    """
    # 从环境变量读取 API Key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY environment variable not set.\n"
            "Get your API key from: https://console.anthropic.com/"
        )

    # 构建三层安全配置：
    # 1. sandbox: 启用沙箱，OS 层面隔离 bash 命令
    # 2. permissions: 文件操作只允许在项目目录内（"./**" 相对于 cwd）
    # 3. Bash 权限放行，但实际命令会被 bash_security_hook 再次验证白名单
    security_settings = {
        "sandbox": {"enabled": True, "autoAllowBashIfSandboxed": True},
        "permissions": {
            "defaultMode": "acceptEdits",  # 自动接受文件编辑操作
            "allow": [
                # 限制文件操作范围到项目目录
                "Read(./**)",
                "Write(./**)",
                "Edit(./**)",
                "Glob(./**)",
                "Grep(./**)",
                # Bash 命令在 hook 层再做白名单验证（见 security.py）
                "Bash(*)",
                # 允许 Puppeteer 浏览器自动化工具
                *PUPPETEER_TOOLS,
            ],
        },
    }

    # 确保项目目录存在
    project_dir.mkdir(parents=True, exist_ok=True)

    # 将安全配置写入项目目录下的 JSON 文件
    settings_file = project_dir / ".claude_settings.json"
    with open(settings_file, "w") as f:
        json.dump(security_settings, f, indent=2)

    print(f"Created security settings at {settings_file}")
    print("   - Sandbox enabled (OS-level bash isolation)")
    print(f"   - Filesystem restricted to: {project_dir.resolve()}")
    print("   - Bash commands restricted to allowlist (see security.py)")
    print("   - MCP servers: puppeteer (browser automation)")
    print()

    # 创建并返回 SDK 客户端实例
    return ClaudeSDKClient(
        options=ClaudeCodeOptions(
            model=model,
            system_prompt="You are an expert full-stack developer building a production-quality web application.",  # 系统提示词：扮演全栈开发专家
            allowed_tools=[
                *BUILTIN_TOOLS,
                *PUPPETEER_TOOLS,
            ],
            # 配置 Puppeteer MCP 服务（通过 npx 启动）
            mcp_servers={
                "puppeteer": {"command": "npx", "args": ["puppeteer-mcp-server"]}
            },
            # 注册 PreToolUse 钩子：每次调用 Bash 前先过安全检查
            hooks={
                "PreToolUse": [
                    HookMatcher(matcher="Bash", hooks=[bash_security_hook]),
                ],
            },
            max_turns=1000,          # 最大对话轮数
            cwd=str(project_dir.resolve()),                 # 工作目录设置为项目目录
            settings=str(settings_file.resolve()),  # 使用绝对路径指向配置文件
        )
    )
