"""
进度追踪工具模块
================

追踪并展示自主编码 Agent 运行进度的相关函数。
"""

import json
from pathlib import Path


def count_passing_tests(project_dir: Path) -> tuple[int, int]:
    """
    统计 feature_list.json 中通过的测试数量。

    参数：
        project_dir: 包含 feature_list.json 的目录

    返回：
        (passing_count, total_count) 通过数量和总数量
    """
    tests_file = project_dir / "feature_list.json"

    # 文件不存在说明初始化 agent 还没运行完
    if not tests_file.exists():
        return 0, 0

    try:
        with open(tests_file, "r") as f:
            tests = json.load(f)

        total = len(tests)
        # 统计 passes 字段为 True 的测试用例数量
        passing = sum(1 for test in tests if test.get("passes", False))

        return passing, total
    except (json.JSONDecodeError, IOError):
        return 0, 0


def print_session_header(session_num: int, is_initializer: bool) -> None:
    """打印格式化的会话标题。"""
    # 第一次运行显示 INITIALIZER，后续显示 CODING AGENT
    session_type = "INITIALIZER" if is_initializer else "CODING AGENT"

    print("\n" + "=" * 70)
    print(f"  SESSION {session_num}: {session_type}")
    print("=" * 70)
    print()


def print_progress_summary(project_dir: Path) -> None:
    """打印当前进度摘要。"""
    passing, total = count_passing_tests(project_dir)

    if total > 0:
        # 显示已通过/总数和百分比
        percentage = (passing / total) * 100
        print(f"\nProgress: {passing}/{total} tests passing ({percentage:.1f}%)")
    else:
        # feature_list.json 尚未生成
        print("\nProgress: feature_list.json not yet created")
