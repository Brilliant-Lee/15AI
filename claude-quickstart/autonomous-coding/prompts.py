"""
Prompt 加载工具模块
===================

从 prompts 目录加载 prompt 模板的相关函数。
"""

import shutil
from pathlib import Path


# prompts 目录路径（与当前文件同级）
PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_prompt(name: str) -> str:
    """从 prompts 目录加载指定名称的 prompt 模板文件。"""
    # 拼接文件路径并读取 .md 文件内容
    prompt_path = PROMPTS_DIR / f"{name}.md"
    return prompt_path.read_text()


def get_initializer_prompt() -> str:
    """加载初始化 Agent 的 prompt。"""
    # 初始化 Agent 使用的 prompt：负责读取需求、生成测试用例列表
    return load_prompt("initializer_prompt")


def get_coding_prompt() -> str:
    """加载编码 Agent 的 prompt。"""
    # 编码 Agent 使用的 prompt：负责根据测试用例逐步实现功能
    return load_prompt("coding_prompt")


def copy_spec_to_project(project_dir: Path) -> None:
    """将应用需求文件复制到项目目录，供 Agent 读取。"""
    spec_source = PROMPTS_DIR / "app_spec.txt"
    spec_dest = project_dir / "app_spec.txt"
    # 仅在目标文件不存在时才复制（避免覆盖 agent 可能修改过的版本）
    if not spec_dest.exists():
        shutil.copy(spec_source, spec_dest)
        print("Copied app_spec.txt to project directory")
