# 项目需求说明 — Claude.ai 克隆版

## 项目概述

构建一个功能完整的 **claude.ai 克隆**，即 Anthropic 的对话式 AI 界面。
应用需提供简洁现代的聊天界面，通过 API 与 Claude 交互，包含会话管理、制品渲染、
项目组织、多模型选择和高级设置等功能。
UI 应使用 Tailwind CSS 紧密还原 claude.ai 的设计风格，注重出色的用户体验和响应式设计。

---

## 技术栈

### 前端
- 框架：React + Vite
- 样式：Tailwind CSS（CDN 引入）
- 状态管理：React hooks + Context
- 路由：React Router
- Markdown 渲染：React Markdown
- 代码高亮：语法高亮组件
- 端口：仅在 `{frontend_port}` 端口启动

### 后端
- 运行时：Node.js + Express
- 数据库：SQLite（better-sqlite3）
- API 集成：Claude API（流式输出）
- 流式传输：SSE（Server-Sent Events）

### 通信
- API 风格：RESTful
- 实时流：SSE
- Claude 集成：Anthropic SDK

---

## 核心功能

### 1. 聊天界面
- 居中布局，带消息气泡
- 流式响应，带打字指示器
- Markdown 渲染（标准格式）
- 代码块语法高亮 + 复制按钮
- LaTeX/数学公式渲染
- 图片上传与显示
- 多轮对话（带上下文）
- 消息编辑与重新生成
- 流式生成时的停止按钮
- 自动扩展的多行输入框
- 字符计数与 token 估算
- 快捷键（Enter 发送，Shift+Enter 换行）

### 2. 制品系统（Artifacts）
- 检测并在侧边面板渲染制品
- 代码制品查看器（语法高亮）
- HTML/SVG 实时预览
- React 组件预览
- Mermaid 图表渲染
- 文本文档制品
- 制品编辑与追问
- 全屏模式
- 下载制品内容
- 制品版本历史

### 3. 会话管理
- 新建会话
- 侧边栏会话列表
- 重命名会话
- 删除会话
- 按标题/内容搜索会话
- 置顶重要会话
- 归档会话
- 会话文件夹/分组
- 复制会话
- 导出会话（JSON、Markdown、PDF）
- 会话时间戳（创建时间、最后更新时间）
- 未读消息提示

### 4. 项目管理
- 创建项目，对相关会话分组
- 项目知识库（上传文档）
- 项目专属自定义指令
- 分享项目给团队（模拟功能）
- 项目设置
- 会话在项目间移动
- 项目模板
- 项目分析（使用统计）

### 5. 模型选择
- 模型选择下拉菜单，包含以下模型：
  - Claude Sonnet 4.5（claude-sonnet-4-5-20250929）— 默认
  - Claude Haiku 4.5（claude-haiku-4-5-20251001）
  - Claude Opus 4.1（claude-opus-4-1-20250805）
- 模型能力说明
- 上下文窗口大小展示
- 模型定价信息（仅展示）
- 对话中途切换模型
- 模型对比视图

### 6. 自定义指令
- 全局自定义指令
- 项目专属自定义指令
- 单个会话的系统提示词
- 自定义指令模板
- 预览指令对回复的影响

### 7. 设置与偏好
- 主题选择（亮色/暗色/自动）
- 字体大小调节
- 消息密度（紧凑/舒适/宽松）
- 代码主题选择
- 语言偏好
- 无障碍选项
- 键盘快捷键参考
- 数据导出选项
- 隐私设置
- API Key 管理

### 8. 高级功能
- Temperature 滑块控制
- Max tokens 调节
- Top-p（核采样）控制
- 系统提示词覆盖
- 思考/推理模式开关
- 多模态输入（文字+图片）
- 语音输入（可选，模拟 UI）
- 回复建议
- 相关 prompt 推荐
- 会话分支

### 9. 分享与协作
- 通过链接分享会话（只读）
- 多格式导出会话
- 会话模板
- Prompt 库
- 分享制品
- 团队工作区（模拟 UI）

### 10. 搜索与发现
- 全局搜索所有会话
- 按项目、日期、模型筛选
- 分类 Prompt 库
- 示例会话
- 快速操作菜单
- 命令面板（Cmd/Ctrl+K）

### 11. 用量追踪
- 每条消息的 token 用量显示
- 会话费用估算
- 日/月用量仪表盘
- 用量限制与警告
- API 配额追踪

### 12. 引导流程（Onboarding）
- 新用户欢迎界面
- 功能亮点导览
- 快速开始示例 prompt
- 使用技巧与最佳实践
- 键盘快捷键教程

### 13. 无障碍（Accessibility）
- 完整键盘导航
- 屏幕阅读器支持
- ARIA 标签与角色
- 高对比度模式
- 焦点管理
- 减少动画支持

### 14. 响应式设计
- 移动优先的响应式布局
- 触摸优化界面
- 移动端可折叠侧边栏
- 滑动手势导航
- 自适应制品展示
- PWA 支持

---

## 数据库表结构

| 表名 | 主要字段 |
|------|---------|
| `users` | id, email, name, avatar_url, preferences(JSON), custom_instructions |
| `projects` | id, user_id, name, color, custom_instructions, knowledge_base_path |
| `conversations` | id, user_id, project_id, title, model, settings(JSON), token_count |
| `messages` | id, conversation_id, role, content, tokens, images(JSON), parent_message_id |
| `artifacts` | id, message_id, type, title, language, content, version |
| `shared_conversations` | id, conversation_id, share_token, expires_at, view_count |
| `prompt_library` | id, user_id, title, prompt_template, category, tags(JSON) |
| `conversation_folders` | id, user_id, project_id, name, parent_folder_id |
| `usage_tracking` | id, user_id, model, input_tokens, output_tokens, cost_estimate |
| `api_keys` | id, user_id, key_name, api_key_hash, last_used_at |

---

## API 接口汇总

### 认证
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `PUT /api/auth/profile`

### 会话
- `GET/POST /api/conversations`
- `GET/PUT/DELETE /api/conversations/:id`
- `POST /api/conversations/:id/duplicate`
- `POST /api/conversations/:id/export`
- `PUT /api/conversations/:id/archive`
- `PUT /api/conversations/:id/pin`
- `POST /api/conversations/:id/branch`

### 消息
- `GET/POST /api/conversations/:id/messages`
- `PUT/DELETE /api/messages/:id`
- `POST /api/messages/:id/regenerate`
- `GET /api/messages/stream`（SSE 流式端点）

### 制品
- `GET /api/conversations/:id/artifacts`
- `GET/PUT/DELETE /api/artifacts/:id`
- `POST /api/artifacts/:id/fork`
- `GET /api/artifacts/:id/versions`

### 项目
- `GET/POST /api/projects`
- `GET/PUT/DELETE /api/projects/:id`
- `POST /api/projects/:id/knowledge`
- `GET /api/projects/:id/conversations`

### 分享
- `POST /api/conversations/:id/share`
- `GET /api/share/:token`
- `DELETE/PUT /api/share/:token`

### Prompt 库
- `GET/POST /api/prompts/library`
- `GET/PUT/DELETE /api/prompts/:id`
- `GET /api/prompts/categories`

### 搜索
- `GET /api/search/conversations?q=`
- `GET /api/search/messages?q=`
- `GET /api/search/artifacts?q=`

### 设置 & 用量
- `GET/PUT /api/settings`
- `GET/PUT /api/settings/custom-instructions`
- `GET /api/usage/daily`
- `GET /api/usage/monthly`

### Claude API 代理
- `POST /api/claude/chat`
- `POST /api/claude/chat/stream`
- `GET /api/claude/models`
- `POST /api/claude/images/upload`

---

## UI 布局

### 整体结构
- 三栏布局：左侧边栏（会话列表）、中间主区域（聊天）、右侧面板（制品）
- 侧边栏可折叠，带拖拽调整宽度手柄
- 响应式断点：移动端（单列）/ 平板（双列）/ 桌面（三列）

### 左侧边栏
- 新建对话按钮（醒目位置）
- 项目选择下拉
- 搜索框
- 会话列表（按日期分组：今天/昨天/过去7天/更早）
- 文件夹树状视图（可折叠）
- 底部设置图标
- 底部用户信息

### 主聊天区域
- 会话标题（可内联编辑）
- 模型选择徽章
- 消息历史（可滚动）
- 空状态的欢迎界面和示例 prompt
- 带工具栏的输入框
- 图片附件按钮
- 发送按钮（带加载状态）
- 流式生成中的停止按钮

### 制品面板（右侧）
- 制品标题 + 类型徽章
- 代码编辑器或预览面板
- 多制品标签页
- 全屏切换
- 下载按钮
- 编辑/追问按钮
- 版本选择器
- 关闭面板按钮

---

## 设计系统

### 配色
- 主色：橙色/琥珀色（#CC785C，claude 风格）
- 背景：白色（亮色模式）/ 深灰（#1A1A1A，暗色模式）
- 表面：浅灰（#F5F5F5，亮色）/ 较深灰（#2A2A2A，暗色）
- 文字：近黑（#1A1A1A，亮色）/ 近白（#E5E5E5，暗色）
- 边框：浅灰（#E5E5E5，亮色）/ 深灰（#404040，暗色）
- 代码块：Monaco 编辑器主题

### 字体
- 无衬线系统字体栈（Inter, SF Pro, Roboto, system-ui）
- 标题：font-semibold
- 正文：font-normal, leading-relaxed
- 代码：等宽字体（JetBrains Mono, Consolas, Monaco）

---

## 实现步骤（按优先级）

1. **基础设置 + 数据库** — Express 服务、SQLite schema、认证、CORS
2. **核心聊天界面** — 布局、Markdown 渲染、SSE 流式、输入框
3. **会话管理** — 列表、新建、切换、重命名、删除、搜索
4. **制品系统** — 检测、渲染面板、代码/HTML 预览、版本管理
5. **项目与组织** — 项目 CRUD、文件夹、拖拽整理
6. **高级功能** — 模型选择、参数控制、图片上传、消息编辑
7. **设置与自定义** — 主题、自定义指令、快捷键、Prompt 库
8. **分享与协作** — 会话分享链接、多格式导出
9. **打磨与优化** — 移动端适配、命令面板、无障碍、性能

---

## 验收标准

### 功能性
- 流式聊天响应流畅
- 制品检测与渲染准确
- 会话管理直观可靠
- 项目组织清晰实用
- 图片上传与显示正常
- 所有 CRUD 操作可用

### 用户体验
- 界面风格与 claude.ai 一致
- 在所有设备尺寸上响应正常
- 动画与过渡流畅
- 响应速度快，延迟低
- 导航与操作流程直观
- 所有操作有清晰反馈

### 代码质量
- 代码结构清晰、易维护
- 全局错误处理
- API Key 安全管理
- 数据库查询优化
- 流式传输实现高效

### 设计精度
- 与 claude.ai 视觉设计一致
- 排版和间距美观
- 动画与微交互流畅
- 对比度好、无障碍
- 暗色模式完整实现
