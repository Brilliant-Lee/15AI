# Autonomous Coding Agent — 项目架构

## 概览

本项目是一个**自主编码 Agent 框架**，让 Claude 在无人监督的情况下持续迭代开发一个 Web 应用。
核心思路：每轮启动一个新的、上下文独立的 Claude session，通过 `feature_list.json` 在多个 session 之间共享状态，实现跨 session 的进度追踪。

## 运行方式

```bash
pip install -r requirements.txt

# 全新项目（无限运行直到完成）
ANTHROPIC_API_KEY=<key> python autonomous_agent_demo.py --project-dir ./my_project

# 限制迭代次数（测试用）
ANTHROPIC_API_KEY=<key> python autonomous_agent_demo.py --project-dir ./my_project --max-iterations 5

# 中断后继续（检测到 feature_list.json 自动续跑）
ANTHROPIC_API_KEY=<key> python autonomous_agent_demo.py --project-dir ./my_project
```

## 文件结构

```
autonomous-coding/
├── autonomous_agent_demo.py   # 入口：解析 CLI 参数，启动主循环
├── agent.py                   # 核心：两阶段 Agent 主循环逻辑
├── client.py                  # SDK 客户端：三层安全配置
├── security.py                # 安全 Hook：bash 命令白名单验证
├── progress.py                # 进度展示：读取 feature_list.json 统计
├── prompts.py                 # Prompt 加载：从 prompts/ 目录读取模板
├── requirements.txt           # 依赖：claude-code-sdk
│
├── prompts/
│   ├── initializer_prompt.md  # 初始化 Agent 的指令（第一次运行）
│   ├── coding_prompt.md       # 编码 Agent 的指令（后续每轮）
│   └── app_spec.txt           # 应用需求文档（被复制到项目目录）
│
└── generations/               # 生成的项目存放位置（运行时创建）
    └── <project-dir>/
        ├── app_spec.txt       # 需求文档副本
        ├── feature_list.json  # 200个测试用例（跨session共享状态）
        ├── .claude_settings.json  # 安全权限配置
        ├── init.sh            # 由 Agent 生成的环境启动脚本
        └── claude-progress.txt    # 由 Agent 维护的进度备注
```

## 两阶段 Agent 模式

### 阶段一：初始化 Agent（仅第一次）

触发条件：`feature_list.json` 不存在

任务（见 `prompts/initializer_prompt.md`）：
1. 读取 `app_spec.txt` 理解需求
2. 生成 `feature_list.json`（200+ 端到端测试用例，全部 `"passes": false`）
3. 创建 `init.sh`（环境启动脚本）
4. 初始化 git 仓库，提交初始结构
5. 若有余量，开始实现最高优先级功能

### 阶段二：编码 Agent（后续每轮）

触发条件：`feature_list.json` 已存在

每轮任务（见 `prompts/coding_prompt.md`）：
1. 定位（读 spec、feature list、progress、git log）
2. 启动服务（`./init.sh`）
3. 回归验证已通过的测试（防止引入新 bug）
4. 挑选一个 `"passes": false` 的功能实现
5. 用 Puppeteer 做浏览器自动化验证
6. 将通过的测试改为 `"passes": true`
7. git commit + 更新 `claude-progress.txt`

## 状态管理

`feature_list.json` 是唯一的跨 session 共享状态：

```json
[
  {
    "category": "functional",
    "description": "用户可以发送消息并获得回复",
    "steps": ["打开应用", "输入消息", "验证回复显示"],
    "passes": false   ← 只有这个字段可以被修改（false → true）
  }
]
```

**严格约束**：只能将 `passes` 从 `false` 改为 `true`，禁止删除、修改、重排任何测试用例。

## 每轮 Session 独立上下文

```
主循环（agent.py）
  ↓
每轮创建新 ClaudeSDKClient（新上下文，防止 token 溢出）
  ↓
发送 prompt → 接收响应（流式打印工具调用和文本）
  ↓
session 结束后等待 3 秒 → 开始下一轮
```

## 安全架构（三层纵深防御）

```
第一层：Sandbox（client.py）
  OS 层面隔离 bash，防止文件系统逃逸

第二层：Permissions（.claude_settings.json）
  文件操作限制在 project_dir（./**）内
  acceptEdits 模式自动接受范围内的编辑

第三层：bash_security_hook（security.py）
  PreToolUse hook，每次 Bash 调用前验证白名单
  白名单：ls/cat/grep/npm/node/git/ps/sleep 等
  敏感命令额外验证：
    - pkill：只能杀 node/npm/npx/vite/next
    - chmod：只允许 +x 模式
    - init.sh：只允许 ./init.sh
```

## 可用工具

| 工具 | 用途 |
|------|------|
| Read / Write / Edit | 文件读写 |
| Glob / Grep | 文件搜索 |
| Bash | Shell 命令（受白名单限制） |
| puppeteer_navigate/screenshot/click/fill | 浏览器自动化验证 |

## 进度追踪

```bash
# 查看通过率
cat generations/<project>/feature_list.json | python3 -c \
  "import json,sys; d=json.load(sys.stdin); p=sum(1 for t in d if t['passes']); print(f'{p}/{len(d)} 通过')"

# 查看日志
tail -f /tmp/agent_run.log
```
