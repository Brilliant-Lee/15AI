"""
Agent 会话逻辑模块
==================

运行自主编码会话的核心交互函数。
"""

import asyncio
from pathlib import Path
from typing import Optional

from claude_code_sdk import ClaudeSDKClient

from client import create_client
from progress import print_session_header, print_progress_summary
from prompts import get_initializer_prompt, get_coding_prompt, copy_spec_to_project


# 每次会话结束后自动继续前的等待时间（秒）
AUTO_CONTINUE_DELAY_SECONDS = 3


async def run_agent_session(
    client: ClaudeSDKClient,
    message: str,
    project_dir: Path,
) -> tuple[str, str]:
    """
    使用 Claude Agent SDK 运行单次会话。

    参数：
        client: Claude SDK 客户端实例
        message: 发送给 Claude 的 prompt
        project_dir: 项目目录路径

    返回：
        (status, response_text)，其中 status 取值：
        - "continue"：会话正常结束，可继续下一轮
        - "error"：发生了异常
    """
    print("Sending prompt to Claude Agent SDK...\n")

    try:
        # 向 Claude 发送 prompt
        await client.query(message)

        response_text = ""
        # 异步迭代接收所有消息
        async for msg in client.receive_response():
            msg_type = type(msg).__name__

            # AssistantMessage：Claude 返回的文本或工具调用
            if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                for block in msg.content:
                    block_type = type(block).__name__

                    if block_type == "TextBlock" and hasattr(block, "text"):
                        # 文本块：累积响应并实时打印
                        response_text += block.text
                        print(block.text, end="", flush=True)
                    elif block_type == "ToolUseBlock" and hasattr(block, "name"):
                        # 工具调用块：打印工具名和输入（超 200 字符则截断）
                        print(f"\n[Tool: {block.name}]", flush=True)
                        if hasattr(block, "input"):
                            input_str = str(block.input)
                            if len(input_str) > 200:
                                print(f"   Input: {input_str[:200]}...", flush=True)
                            else:
                                print(f"   Input: {input_str}", flush=True)

            # UserMessage：工具执行结果回传给 Claude
            elif msg_type == "UserMessage" and hasattr(msg, "content"):
                for block in msg.content:
                    block_type = type(block).__name__

                    if block_type == "ToolResultBlock":
                        result_content = getattr(block, "content", "")
                        is_error = getattr(block, "is_error", False)

                        # 命令被安全 hook 拦截
                        if "blocked" in str(result_content).lower():
                            print(f"   [BLOCKED] {result_content}", flush=True)
                        elif is_error:
                            # 工具执行出错，打印截断后的错误信息
                            error_str = str(result_content)[:500]
                            print(f"   [Error] {error_str}", flush=True)
                        else:
                            # 工具执行成功
                            print("   [Done]", flush=True)

        print("\n" + "-" * 70 + "\n")
        return "continue", response_text

    except Exception as e:
        print(f"Error during agent session: {e}")
        return "error", str(e)


async def run_autonomous_agent(
    project_dir: Path,
    model: str,
    max_iterations: Optional[int] = None,
) -> None:
    """
    运行自主 Agent 主循环。

    参数：
        project_dir: 项目目录
        model: 使用的 Claude 模型名称
        max_iterations: 最大迭代次数（None 表示无限循环直到完成）
    """
    print("\n" + "=" * 70)
    print("  AUTONOMOUS CODING AGENT DEMO")
    print("=" * 70)
    print(f"\nProject directory: {project_dir}")
    print(f"Model: {model}")
    if max_iterations:
        print(f"Max iterations: {max_iterations}")
    else:
        print("Max iterations: Unlimited (will run until completion)")
    print()

    # 确保项目目录存在
    project_dir.mkdir(parents=True, exist_ok=True)

    # 通过检查 feature_list.json 是否存在来判断是全新项目还是继续上次
    tests_file = project_dir / "feature_list.json"
    is_first_run = not tests_file.exists()

    if is_first_run:
        # 首次运行：使用初始化 Agent（生成测试用例列表）
        print("Fresh start - will use initializer agent")
        print()
        print("=" * 70)
        print("  NOTE: First session takes 10-20+ minutes!")
        print("  The agent is generating 200 detailed test cases.")
        print("  This may appear to hang - it's working. Watch for [Tool: ...] output.")
        print("=" * 70)
        print()
        # 把 app_spec.txt 复制到项目目录，供 Agent 读取需求
        copy_spec_to_project(project_dir)
    else:
        # 继续上次进度
        print("Continuing existing project")
        print_progress_summary(project_dir)

    # ---- 主循环：每轮创建新客户端（新上下文），选 prompt，运行 session ----
    iteration = 0

    while True:
        iteration += 1

        # 超过最大迭代次数则退出循环
        if max_iterations and iteration > max_iterations:
            print(f"\nReached max iterations ({max_iterations})")
            print("To continue, run the script again without --max-iterations")
            break

        print_session_header(iteration, is_first_run)

        # 每轮都创建全新客户端，保证上下文独立（防止上下文过长）
        client = create_client(project_dir, model)

        # 第一轮使用初始化 prompt（生成测试列表），后续使用编码 prompt
        if is_first_run:
            prompt = get_initializer_prompt()
            is_first_run = False  # 初始化只执行一次
        else:
            prompt = get_coding_prompt()

        # 用 async context manager 管理客户端生命周期
        async with client:
            status, response = await run_agent_session(client, prompt, project_dir)

        # 根据返回状态决定下一步
        if status == "continue":
            # 正常完成，等待后继续下一轮
            print(f"\nAgent will auto-continue in {AUTO_CONTINUE_DELAY_SECONDS}s...")
            print_progress_summary(project_dir)
            await asyncio.sleep(AUTO_CONTINUE_DELAY_SECONDS)

        elif status == "error":
            # 出错后等待，然后用新 session 重试
            print("\nSession encountered an error")
            print("Will retry with a fresh session...")
            await asyncio.sleep(AUTO_CONTINUE_DELAY_SECONDS)

        # 每轮之间短暂间隔
        if max_iterations is None or iteration < max_iterations:
            print("\nPreparing next session...\n")
            await asyncio.sleep(1)

    # 打印最终结果摘要
    print("\n" + "=" * 70)
    print("  SESSION COMPLETE")
    print("=" * 70)
    print(f"\nProject directory: {project_dir}")
    print_progress_summary(project_dir)

    print("\n" + "-" * 70)
    print("  TO RUN THE GENERATED APPLICATION:")
    print("-" * 70)
    print(f"\n  cd {project_dir.resolve()}")
    print("  ./init.sh           # Run the setup script")
    print("  # Or manually:")
    print("  npm install && npm run dev")
    print("\n  Then open http://localhost:3000 (or check init.sh for the URL)")
    print("-" * 70)

    print("\nDone!")
