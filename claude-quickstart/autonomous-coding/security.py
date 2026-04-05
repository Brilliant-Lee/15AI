"""
自主编码 Agent 安全钩子模块
============================

在工具调用前验证 bash 命令的安全 hook。
采用白名单机制，只有明确允许的命令才能执行。
"""

import os
import shlex


# 允许执行的 bash 命令白名单（最小权限原则）
ALLOWED_COMMANDS = {
    # 文件查看
    "ls",
    "cat",
    "head",
    "tail",
    "wc",
    "grep",
    # 文件操作（大多数文件操作通过 SDK 工具完成，cp/mkdir 偶尔需要）
    "cp",
    "mkdir",
    "chmod",  # 仅允许 +x（见 validate_chmod_command）
    # 目录
    "pwd",
    # Node.js 开发
    "npm",
    "node",
    # 版本控制
    "git",
    # 进程管理
    "ps",
    "lsof",
    "sleep",
    "pkill",  # 仅允许杀死开发相关进程（见 validate_pkill_command）
    # 脚本执行
    "init.sh",  # 仅允许 ./init.sh（见 validate_init_script）
}

# 在白名单内但还需要额外验证的命令
COMMANDS_NEEDING_EXTRA_VALIDATION = {"pkill", "chmod", "init.sh"}


def split_command_segments(command_string: str) -> list[str]:
    """
    将复合命令拆分为独立的命令段。

    处理 &&、||、; 连接的命令链，但不拆分管道（| 两侧视为同一命令）。

    参数：
        command_string: 完整的 shell 命令字符串

    返回：
        拆分后的命令段列表
    """
    import re

    # 按 && 和 || 拆分（管道 | 不拆，视为单条命令）
    segments = re.split(r"\s*(?:&&|\|\|)\s*", command_string)

    # 再按分号拆分（跳过引号内的分号）
    result = []
    for segment in segments:
        sub_segments = re.split(r'(?<!["\'])\s*;\s*(?!["\'])', segment)
        for sub in sub_segments:
            sub = sub.strip()
            if sub:
                result.append(sub)

    return result


def extract_commands(command_string: str) -> list[str]:
    """
    从 shell 命令字符串中提取所有命令名。

    处理管道、命令链（&&、||、;）等情况，返回不含路径前缀的命令基名。

    参数：
        command_string: 完整的 shell 命令字符串

    返回：
        命令名列表
    """
    commands = []

    import re

    # 先按分号拆分（shlex 不处理分号）
    segments = re.split(r'(?<!["\'])\s*;\s*(?!["\'])', command_string)

    for segment in segments:
        segment = segment.strip()
        if not segment:
            continue

        try:
            tokens = shlex.split(segment)
        except ValueError:
            # 命令解析失败（如未闭合的引号），返回空列表触发拦截（安全优先）
            return []

        if not tokens:
            continue

        expect_command = True  # 标记下一个 token 是否为命令名

        for token in tokens:
            # 遇到管道/逻辑运算符，下一个 token 是新命令
            if token in ("|", "||", "&&", "&"):
                expect_command = True
                continue

            # 跳过 shell 控制关键字
            if token in (
                "if", "then", "else", "elif", "fi",
                "for", "while", "until", "do", "done",
                "case", "esac", "in", "!", "{", "}",
            ):
                continue

            # 跳过 flags（如 -r、--verbose）
            if token.startswith("-"):
                continue

            # 跳过环境变量赋值（如 NODE_ENV=production）
            if "=" in token and not token.startswith("="):
                continue

            if expect_command:
                # 提取命令基名（去掉路径前缀，如 /usr/bin/node -> node）
                cmd = os.path.basename(token)
                commands.append(cmd)
                expect_command = False

    return commands


def validate_pkill_command(command_string: str) -> tuple[bool, str]:
    """
    验证 pkill 命令，只允许杀死开发相关进程。

    使用 shlex 解析命令，避免正则绕过漏洞。

    返回：
        (is_allowed, reason_if_blocked) 是否允许及拦截原因
    """
    # 只允许杀死这些开发相关进程
    allowed_process_names = {
        "node",
        "npm",
        "npx",
        "vite",
        "next",
    }

    try:
        tokens = shlex.split(command_string)
    except ValueError:
        return False, "Could not parse pkill command"

    if not tokens:
        return False, "Empty pkill command"

    # 收集非 flag 参数
    args = []
    for token in tokens[1:]:
        if not token.startswith("-"):
            args.append(token)

    if not args:
        return False, "pkill requires a process name"

    # 目标通常是最后一个非 flag 参数
    target = args[-1]

    # 处理 -f 参数（全命令行匹配）：取第一个词作为进程名
    # 例：pkill -f 'node server.js' -> target = 'node'
    if " " in target:
        target = target.split()[0]

    if target in allowed_process_names:
        return True, ""
    return False, f"pkill only allowed for dev processes: {allowed_process_names}"


def validate_chmod_command(command_string: str) -> tuple[bool, str]:
    """
    验证 chmod 命令，只允许通过 +x 赋予执行权限。

    返回：
        (is_allowed, reason_if_blocked) 是否允许及拦截原因
    """
    try:
        tokens = shlex.split(command_string)
    except ValueError:
        return False, "Could not parse chmod command"

    if not tokens or tokens[0] != "chmod":
        return False, "Not a chmod command"

    mode = None
    files = []

    for token in tokens[1:]:
        if token.startswith("-"):
            # 不允许递归 chmod 等 flag
            return False, "chmod flags are not allowed"
        elif mode is None:
            mode = token
        else:
            files.append(token)

    if mode is None:
        return False, "chmod requires a mode"

    if not files:
        return False, "chmod requires at least one file"

    # 只允许 +x 相关模式（如 +x、u+x、a+x、ug+x 等），不允许修改其他权限位
    import re
    if not re.match(r"^[ugoa]*\+x$", mode):
        return False, f"chmod only allowed with +x mode, got: {mode}"

    return True, ""


def validate_init_script(command_string: str) -> tuple[bool, str]:
    """
    验证 init.sh 脚本执行，只允许运行 ./init.sh。

    返回：
        (is_allowed, reason_if_blocked) 是否允许及拦截原因
    """
    try:
        tokens = shlex.split(command_string)
    except ValueError:
        return False, "Could not parse init script command"

    if not tokens:
        return False, "Empty command"

    script = tokens[0]

    # 只允许 ./init.sh 或路径以 /init.sh 结尾的脚本
    if script == "./init.sh" or script.endswith("/init.sh"):
        return True, ""

    return False, f"Only ./init.sh is allowed, got: {script}"


def get_command_for_validation(cmd: str, segments: list[str]) -> str:
    """
    在命令段列表中找到包含指定命令名的那一段。

    参数：
        cmd: 要查找的命令名
        segments: 命令段列表

    返回：
        包含该命令的命令段字符串，找不到则返回空字符串
    """
    # 找到包含该命令的具体命令段，用于精确验证
    for segment in segments:
        segment_commands = extract_commands(segment)
        if cmd in segment_commands:
            return segment
    return ""


async def bash_security_hook(input_data, tool_use_id=None, context=None):
    """
    工具调用前的安全 hook，通过白名单验证 bash 命令。

    只有 ALLOWED_COMMANDS 中的命令才被允许执行。

    参数：
        input_data: 包含 tool_name 和 tool_input 的字典
        tool_use_id: 可选的工具调用 ID
        context: 可选的上下文信息

    返回：
        允许执行返回空 dict，拦截则返回 {"decision": "block", "reason": "..."}
    """
    # 只处理 Bash 工具调用
    if input_data.get("tool_name") != "Bash":
        return {}

    command = input_data.get("tool_input", {}).get("command", "")
    if not command:
        return {}

    # 提取命令字符串中所有出现的命令名
    commands = extract_commands(command)

    if not commands:
        # 无法解析命令，安全起见直接拦截
        return {
            "decision": "block",
            "reason": f"Could not parse command for security validation: {command}",
        }

    # 拆分为多个命令段（用于后续精确验证）
    segments = split_command_segments(command)

    # 逐一检查每个命令是否在白名单内
    for cmd in commands:
        if cmd not in ALLOWED_COMMANDS:
            return {
                "decision": "block",
                "reason": f"Command '{cmd}' is not in the allowed commands list",
            }

        # 白名单内但需要额外验证的命令（pkill/chmod/init.sh）
        if cmd in COMMANDS_NEEDING_EXTRA_VALIDATION:
            # 找到该命令对应的具体命令段
            cmd_segment = get_command_for_validation(cmd, segments)
            if not cmd_segment:
                cmd_segment = command  # 找不到时回退到完整命令

            if cmd == "pkill":
                allowed, reason = validate_pkill_command(cmd_segment)
                if not allowed:
                    return {"decision": "block", "reason": reason}
            elif cmd == "chmod":
                allowed, reason = validate_chmod_command(cmd_segment)
                if not allowed:
                    return {"decision": "block", "reason": reason}
            elif cmd == "init.sh":
                allowed, reason = validate_init_script(cmd_segment)
                if not allowed:
                    return {"decision": "block", "reason": reason}

    # 所有检查通过，返回空 dict 表示允许执行
    return {}
