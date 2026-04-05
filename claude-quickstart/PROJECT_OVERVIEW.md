# claude-quickstarts-main 项目概览

> Anthropic 官方示例仓库，包含 6 个独立子项目，展示如何用 Claude API / Agent SDK 构建不同类型的 AI 应用。

---

## 子项目一览

| 子项目 | 技术栈 | 一句话说明 |
|---|---|---|
| [agents](#agents) | Python | 用 ~300 行代码演示如何从零构建 LLM Agent 的最小教学参考实现 |
| [autonomous-coding](#autonomous-coding) | Python + Agent SDK | 双 Agent 模式，能跨多个会话自主构建一个完整应用 |
| [browser-use-demo](#browser-use-demo) | Python + Playwright + Docker | 让 Claude 驱动浏览器完成网页操作任务 |
| [computer-use-demo](#computer-use-demo) | Python + Docker + VNC | 让 Claude 控制整个 Linux 桌面环境（鼠标/键盘/截图） |
| [customer-support-agent](#customer-support-agent) | Next.js + Bedrock RAG | 带知识库检索的客服聊天界面 |
| [financial-data-analyst](#financial-data-analyst) | Next.js + Recharts | 上传财务文件后通过对话生成交互式图表 |

---

## agents/

**用途**：教学级 Agent 实现，展示 Claude API 调用 + 工具执行循环的核心模式。

| 文件 | 说明 |
|---|---|
| `agent.py` | Agent 核心：管理 Claude API 调用和工具执行主循环 |
| `agent_demo.ipynb` | Jupyter Notebook 演示 |
| `tools/base.py` | 工具抽象基类 |
| `tools/think.py` | Think 工具：让 Claude 在回答前做内部推理 |
| `tools/web_search.py` | 网页搜索工具 |
| `tools/code_execution.py` | 代码执行工具 |
| `tools/file_tools.py` | 文件读写工具 |
| `tools/mcp_tool.py` | 将 MCP 协议工具包装为本地可用工具 |
| `tools/calculator_mcp.py` | MCP 计算器工具示例 |
| `utils/connections.py` | 管理 MCP 服务器连接 |
| `utils/history_util.py` | 对话历史管理 |
| `utils/tool_util.py` | 工具调用结果处理工具函数 |

---

## autonomous-coding/

**用途**：用 Claude Agent SDK 实现"初始化 Agent + 编程 Agent"双 Agent 模式，进度通过 git 和 `feature_list.json` 持久化，能自主构建完整应用。

| 文件 | 说明 |
|---|---|
| `autonomous_agent_demo.py` | 主入口：启动自主编程 Agent，管理多会话循环 |
| `agent.py` | 单次 Agent 会话逻辑（调用 Claude Agent SDK） |
| `client.py` | Claude SDK 客户端配置，含沙箱和安全钩子 |
| `security.py` | Bash 命令白名单校验，防止 Agent 执行危险命令 |
| `progress.py` | 读写会话进度状态的工具函数 |
| `prompts.py` | 从文件加载 Prompt 的工具函数 |
| `test_security.py` | 安全模块单元测试 |
| `prompts/app_spec.txt` | 待构建应用的功能规格说明（Agent 的目标输入） |
| `prompts/initializer_prompt.md` | 首次会话用的初始化 Prompt（生成特性列表） |
| `prompts/coding_prompt.md` | 后续编程会话的 Prompt（继续实现功能） |

---

## browser-use-demo/

**用途**：用 Playwright 驱动 Claude 操控浏览器（DOM 读取、导航、表单填写、截图），通过 Docker + Streamlit + NoVNC 提供可视化界面。

| 文件 | 说明 |
|---|---|
| `browser_use_demo/loop.py` | Claude API 调用主循环，处理 Agent 与浏览器工具的交互 |
| `browser_use_demo/streamlit.py` | Streamlit 聊天 UI |
| `browser_use_demo/message_handler.py` | 处理 API 响应消息的逻辑 |
| `browser_use_demo/message_renderer.py` | 将消息渲染到 Streamlit 界面 |
| `browser_use_demo/tools/browser.py` | 浏览器工具核心（封装所有 Playwright 操作） |
| `browser_use_demo/tools/collection.py` | 管理所有可用工具的集合 |
| `browser_use_demo/tools/coordinate_scaling.py` | 将 Claude 坐标映射到实际浏览器视口坐标 |
| `browser_tool_utils/browser_dom_script.js` | JS 脚本：提取页面 DOM 树并生成元素 ref 标识符 |
| `browser_tool_utils/browser_element_script.js` | JS 脚本：通过 ref 定位和操作页面元素 |
| `browser_tool_utils/browser_form_input_script.js` | JS 脚本：直接设置表单元素的值 |
| `browser_tool_utils/browser_text_script.js` | JS 脚本：提取页面全文内容 |
| `browser_tool_utils/browser_key_map.py` | 键盘按键名到 Playwright 键值的映射 |
| `Dockerfile` | 构建含 Chromium + Playwright + VNC 虚拟桌面的容器镜像 |
| `docker-compose.yml` | 一键启动完整 Demo 环境 |
| `validate_env.py` | 启动前检查环境变量是否配置正确 |
| `image/` | Docker 内虚拟桌面启动脚本（XVFB、VNC、NoVNC、tint2） |
| `tests/` | 集成测试和单元测试 |

---

## computer-use-demo/

**用途**：让 Claude 通过计算机使用工具（鼠标、键盘、截图、文件编辑、bash）控制完整桌面环境，运行在 Docker 中并通过 VNC/Streamlit 交互。

| 文件 | 说明 |
|---|---|
| `computer_use_demo/loop.py` | Agent 主循环：持续调用 Claude API 并执行计算机操作工具 |
| `computer_use_demo/streamlit.py` | Streamlit 交互界面 |
| `computer_use_demo/tools/computer.py` | 计算机工具：鼠标点击、键盘输入、截图等桌面控制 |
| `computer_use_demo/tools/bash.py` | Bash 工具：在沙箱中执行 shell 命令 |
| `computer_use_demo/tools/edit.py` | 文件编辑工具（基于字符串替换） |
| `computer_use_demo/tools/collection.py` | 按模型版本组合工具集的管理器 |
| `computer_use_demo/tools/groups.py` | 定义不同 Claude 模型版本支持的工具组合 |
| `computer_use_demo/tools/run.py` | 异步运行 shell 命令的底层工具函数 |
| `computer_use_demo/tools/base.py` | 工具抽象基类及 ToolResult 数据结构 |
| `setup.sh` | 一键配置本地开发环境（venv、依赖、pre-commit） |
| `Dockerfile` | 构建含完整 Linux 桌面（XFCE + VNC + Streamlit）的容器 |
| `tests/` | 各工具及 Agent 循环的单元/集成测试 |

---

## customer-support-agent/

**用途**：基于 Next.js + Claude + Amazon Bedrock RAG 的客服聊天界面，支持知识库检索、情绪检测和高度可定制的 UI。

| 文件 | 说明 |
|---|---|
| `app/api/chat/route.ts` | API 路由：调用 Claude + Bedrock RAG，流式返回结果 |
| `app/page.tsx` | 应用首页，组合各 UI 组件 |
| `app/lib/customer_support_categories.json` | 预定义的客服问题分类数据 |
| `components/ChatArea.tsx` | 核心聊天区域组件 |
| `components/LeftSidebar.tsx` | 左侧边栏（会话列表/导航） |
| `components/RightSidebar.tsx` | 右侧边栏（知识库来源和调试信息） |
| `components/TopNavBar.tsx` | 顶部导航栏 |
| `components/FullSourceModal.tsx` | 弹窗：展示知识库检索到的完整文档来源 |
| `config.ts` | 通过环境变量控制侧边栏显示的配置文件 |
| `styles/themes.js` | 可切换的 UI 主题颜色配置 |
| `amplify.yml` | AWS Amplify 部署流水线配置 |

---

## financial-data-analyst/

**用途**：基于 Next.js + Claude 的金融数据分析工具，支持上传 CSV/PDF/图片后通过对话生成折线图、柱状图、饼图等交互式图表。

| 文件 | 说明 |
|---|---|
| `app/api/finance/route.ts` | API 路由：接收文件和消息，调用 Claude 分析并返回图表数据 |
| `app/finance/page.tsx` | 金融分析主页面（文件上传 + 聊天交互） |
| `components/ChartRenderer.tsx` | 根据 Claude 返回配置，用 Recharts 动态渲染各类图表 |
| `components/FilePreview.tsx` | 显示已上传文件的预览组件 |
| `types/chart.ts` | 图表数据结构的 TypeScript 类型定义 |
| `utils/fileHandling.ts` | 处理文件上传、格式转换并准备发给 API 的工具函数 |
| `hooks/use-toast.ts` | Toast 通知的 React 自定义 Hook |

---

## 根目录文件

| 文件 | 说明 |
|---|---|
| `README.md` | 整个仓库入口说明，列出所有子项目链接 |
| `CLAUDE.md` | 面向 Claude Code 的开发指南（构建、测试、代码风格命令） |
| `LICENSE` | MIT 开源协议 |
| `pyproject.toml` | 根目录 Python 项目配置（工具链用） |
| `.pre-commit-config.yaml` | pre-commit 钩子配置，提交前自动检查代码质量 |
| `.github/workflows/build.yaml` | CI：构建所有子项目的 Docker 镜像 |
| `.github/workflows/tests.yaml` | CI：运行各子项目的测试套件 |
| `.github/workflows/reusable_build_step.yaml` | 被其他 CI 工作流复用的通用 Docker 构建步骤 |
