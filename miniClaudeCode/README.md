# miniClaudeCode

**从 50 万行蒸馏到 ~800 行 -- Claude Code 核心架构的最小可运行复现**

miniClaudeCode 是对 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 核心 Agent 架构的蒸馏（distillation）实现。它保留了 Claude Code 最核心的四大模块——Agent Loop、Tool System、Permission System、Context Management——同时将代码量从原版的 ~500K 行精简到 ~800 行纯 Python。

## 架构总览

```
用户输入
   │
   ▼
┌─────────────────────────────────┐
│         Agent Loop              │
│  ┌───────────────────────────┐  │
│  │  1. 构建 System Prompt    │  │
│  │  2. 调用 Claude API       │  │
│  │  3. 解析 tool_use blocks  │  │
│  │  4. 权限检查 (2层)        │  │
│  │  5. 执行工具              │  │
│  │  6. 结果追加到上下文      │  │
│  │  7. 循环直到无工具调用    │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
   │
   ▼
最终文本输出
```

### Claude Code 原版 vs miniClaudeCode

| 模块 | Claude Code 原版 | miniClaudeCode |
|------|-----------------|----------------|
| **Agent Loop** | SSE 流式 + 多并行 tool_use | 同步循环 + 顺序工具链 |
| **工具数量** | 26+ 内置工具 + MCP 扩展 | 6 个核心工具 |
| **权限系统** | 5 层 (工具自检 / allowlist / sandbox / 模式 / hooks) | 2 层 (工具自检 + 模式) |
| **上下文管理** | 会话持久化 + 压缩 + CLAUDE.md + 记忆 | 消息列表 + 截断 + CLAUDE.md |
| **终端 UI** | React/Ink 渲染 | 简单 REPL |
| **代码量** | ~500,000 行 TypeScript | ~800 行 Python |

## 快速开始

### 安装

```bash
cd miniClaudeCode
pip install -r requirements.txt
```

### 设置 API Key

```bash
export ANTHROPIC_API_KEY="your-api-key"
```

### 交互模式

```bash
python -m miniclaudecode
```

### 单次执行

```bash
python -m miniclaudecode "帮我查看当前目录下有哪些 Python 文件"
```

### 指定模式

```bash
# 自动模式 (无需确认)
python -m miniclaudecode --mode auto "列出所有 .py 文件"

# 只读模式 (禁止写操作)
python -m miniclaudecode --mode plan "分析项目结构"
```

## 内置工具

miniClaudeCode 保留了 Claude Code 最核心的 6 个工具：

| 工具 | 对应原版 | 功能 |
|------|---------|------|
| `bash` | BashTool | 执行 shell 命令 |
| `read_file` | FileReadTool | 读取文件内容（带行号） |
| `write_file` | FileWriteTool | 写入文件 |
| `edit_file` | FileEditTool | 字符串替换编辑 |
| `glob` | GlobTool | 按模式搜索文件 |
| `grep` | GrepTool | 正则搜索文件内容 |

## 蒸馏笔记

### 什么是"蒸馏"？

蒸馏 (Distillation) 是指从一个大型复杂系统中提取核心架构和关键逻辑，去掉非本质的复杂性，保留最小可运行的版本。

### 蒸馏过程

1. **分析原版架构**：研究 claw-code 的 28 个子系统、100+ 工具、150+ 命令
2. **识别核心模式**：Agent Loop 是灵魂，Tool 接口是骨架，Permission 是安全网
3. **保留本质**：6 个工具覆盖 90% 的编码场景
4. **去除复杂性**：去掉 MCP、SubAgent、Teams、React UI、Hooks 等

### 去掉了什么？

- **MCP 服务器集成**：自定义工具扩展（miniClaudeCode 用固定工具集）
- **SubAgent/Task 并行系统**：子智能体分叉（miniClaudeCode 用单线程循环）
- **Team/tmux 多进程协作**：多 Agent 协同（超出 mini 范围）
- **Ink/React 终端 UI**：复杂渲染（miniClaudeCode 用 print）
- **Hooks 系统**：PreToolUse/PostToolUse 钩子（简化为直接权限检查）
- **远程/SSH/Teleport 模式**：远程连接能力
- **Plugin/Skill 加载系统**：运行时扩展

## 项目结构

```
miniClaudeCode/
├── miniclaudecode/
│   ├── __init__.py          # 包入口
│   ├── __main__.py          # python -m 入口
│   ├── agent_loop.py        # 核心 Agent 循环 (灵魂)
│   ├── cli.py               # CLI 交互界面
│   ├── config.py            # 配置定义
│   ├── context.py           # 上下文/消息管理
│   ├── permissions.py       # 2 层权限系统
│   ├── system_prompt.py     # 系统提示构建
│   └── tools/
│       ├── __init__.py
│       ├── base.py          # Tool 基类 + Registry
│       ├── bash_tool.py     # Bash 执行
│       ├── file_read.py     # 文件读取
│       ├── file_write.py    # 文件写入
│       ├── file_edit.py     # 文件编辑
│       ├── glob_tool.py     # 文件搜索
│       └── grep_tool.py     # 内容搜索
├── tests/
│   ├── test_agent_loop.py   # 权限/上下文/提示测试
│   └── test_tools.py        # 工具功能测试
├── docs/
│   └── architecture.md      # 架构详解
├── comic/                   # 漫画讲解
├── requirements.txt
└── README.md
```

## 运行测试

```bash
python -m pytest tests/ -v
```

## 参考资料

- [Claude Code 架构解析](https://dev.to/oldeucryptoboi/inside-claude-codes-architecture-the-agentic-loop-that-codes-for-you-cmk)
- [Anthropic Harness Design](https://www.anthropic.com/engineering/harness-design-long-running-apps)
- [claw-code](https://github.com/instructkr/claw-code) - Python 移植工作区

## License

MIT
