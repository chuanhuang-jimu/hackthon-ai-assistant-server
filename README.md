# Streamline (工作助手·Pro) - 基于 Gemini 的全能 AI 智能工作助理

**Streamline** 是一款旨在消除开发者与管理人员在日常工作中“信息碎化”与“管理内耗”的 AI 办公套件。它以 **Chrome Extension** 为入口，深度集成 Jira、GitLab、Wiki 和 Gmail，利用 Google Gemini 模型和 MCP (Model Context Protocol) 协议提供智能化的工作流辅助。

---

## 🌟 核心功能

### 1. 晨间速览 (Morning Brief)
- **智能过滤**：自动抓取多渠道信息（Jira, Wiki, GitLab, Email），AI 智能过滤“与你有关”的内容。
- **动态提醒**：实时同步外部工作流，标记“高优”与“@提及”事项。
- **一键待办**：支持将关键邮件或通知直接转化为本地待办清单 (Todo List)。

### 2. 今日总结 (Daily Summary)
- **无感工时记录**：自动拉取个人名下进行中的 Jira 任务，支持在同一界面批量填写工时 (Worklog) 与进度备注。
- **进度可视化**：实时同步 Jira 状态，计算任务 Logged/Remaining 比例，一键完成同步。

### 3. AI 项目经理 (Meeting Genie / Scrum Master)
- **标签引擎**：基于 Redis 存储的可配置规则，自动识别任务风险（如：延期风险、阻塞风险）。
- **智能分析报告**：AI 深度阅读 Story 下的所有评论与子任务进展，生成一键式分析摘要，显著缩短早会同步时间。
- **看板同步**：一键同步活跃 Sprint 的所有 Story 状态。

---

## 🛠️ 技术架构

-   **前端**：React 19 + TypeScript + Tailwind CSS (Vite 构建，Chrome MV3 架构)
-   **后端**：FastAPI (Python 3.10+)
-   **AI 引擎**：Google Gemini (通过 gemini-cli 调用)
-   **协议**：MCP (Model Context Protocol)
-   **缓存/持久化**：Redis

---

## 🚀 部署指南

### 1. 前置要求
-   **Node.js**: v18+
-   **Python**: v3.10+
-   **Redis**: 必须安装并运行（默认端口 6379）。
-   **Gemini CLI**: 必须安装 `gemini-cli` 并在系统 PATH 中。

### 2. 后端部署 (Python API)
1. 安装 Python 依赖：
   ```bash
   pip install -r requirements.txt
   ```
2启动 API 服务（默认端口 8200）：
   ```bash
   uvicorn main:app --port 8200 --reload
   ```

### 3. 前端部署 (Chrome Extension)
1. 进入插件目录：
   ```bash
   cd chrome_extension
   ```
2. 安装依赖并构建：
   ```bash
   npm install
   npm run build
   npm run dev
   ```
3. 加载扩展：
   - 打开 Chrome 浏览器，访问 `chrome://extensions/`。
   - 开启“开发者模式”。
   - 点击“加载已解压的扩展程序”，选择 `chrome_extension/dist` 文件夹。

### 4. MCP 服务配置
当前项目依赖 Jira MCP 服务，请按照以下步骤配置：

1. **Jira MCP 镜像拉取**：
   ```bash
   docker pull ghcr.io/sooperset/mcp-atlassian:latest
   ```

2. **Gemini CLI 全局配置**：
   编辑 `~/.gemini/settings.json`（如果没有则创建），添加或修改内容如下：
   ```json
   {
     "extensions": {
       "disabled": []
     },
     "mcpServers": {
       "geminix": {
         "httpUrl": "http://geminix.crmdev.veevasfa.com/mcp"
       },
       "jira": {
         "command": "docker",
         "args": [
           "run",
           "-i",
           "--rm",
           "-e", "JIRA_URL=https://jira.veevadev.com",
           "-e", "JIRA_USERNAME=xxx.xxx@veeva.com",
           "-e", "JIRA_PERSONAL_TOKEN=xxxxxx",
           "-e", "JIRA_SSL_VERIFY=false",
           "ghcr.io/sooperset/mcp-atlassian:latest"
         ]
       }
     },
     "selectedAuthType": "oauth-personal",
     "vimMode": true
   }
   ```
   **注意**：
   - `JIRA_USERNAME`: 请前往 [Jira 个人资料](https://jira.veevadev.com/secure/ViewProfile.jspa?selectedTab=jira.user.profile.panels:user-profile-summary-panel) 获取。
   - `JIRA_PERSONAL_TOKEN`: 请前往 [Jira 个人访问令牌](https://jira.veevadev.com/secure/ViewProfile.jspa?selectedTab=com.atlassian.pats.pats-plugin:jira-user-personal-access-tokens) 创建并获取。

3. **其他 MCP 服务**：
   - **mail**: 用于读取 Gmail 动态（详见 `mcp/mail-mcp/`）。

---

## ⚙️ 配置说明

在插件的“设置 (Settings)”中，你需要配置以下信息以确保功能正常：
-   **个人邮箱**：你的公司邮箱（如 `xxxx@veeva.com`），用于晨间分拣。
-   **看板 ID**：Jira Board 的 ID，用于 Scrum Master 看板同步。
-   **Mock 模式**：如果你没有连接后端，可以开启此模式预览 UI。

---

## 📖 开发者说明
-   **后端接口文档**：访问 `http://localhost:8200/docs` 查看 Swagger UI。
-   **Redis 数据流**：前端通过后端 API 与 Redis 交互，存储风险判定逻辑与个人缓存。
-   **MCP 集成**：项目根目录下的 `mcp/` 文件夹包含了自定义的邮件分拣工具。
