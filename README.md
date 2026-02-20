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

### 1. Docker 快速部署 (推荐)
通过 Docker，你可以一键完成前端编译、后端启动以及 Redis 和 Gemini CLI 的环境配置。

1. **环境准备**：
   - 确保已安装 Docker 和 Docker Compose。
   - **核心认证**：由于容器需要共享宿主机的身份，请先在宿主机终端执行：
     ```bash
     gcloud auth application-default login
     ```

2. **配置环境变量**：在项目根目录创建 `.env` 文件：
   ```bash
   # Google Cloud 项目 ID
   GOOGLE_CLOUD_PROJECT=你的项目ID
   
   # Jira 配置
   # JIRA_USERNAME 获取地址：https://jira.veevadev.com/secure/ViewProfile.jspa?selectedTab=jira.user.profile.panels:user-profile-summary-panel
   JIRA_USERNAME=你的用户名@veeva.com
   
   # JIRA_PERSONAL_TOKEN 获取地址：https://jira.veevadev.com/secure/ViewProfile.jspa?selectedTab=com.atlassian.pats.pats-plugin:jira-user-personal-access-tokens
   JIRA_PERSONAL_TOKEN=你的TOKEN
   ```

3. **一键启动**：
   ```bash
   docker compose up -d --build
   ```

4. **验证与使用**：
   - **后端 API**：访问 `http://localhost:8200/docs` 查看 Swagger 文档。
   - **前端预览**：访问 `http://localhost:3000` (支持代码修改后实时预览 UI)。可以用下面插件，这个为验证
   - **正式插件**：插件产物位于本地 `chrome_extension/dist`。打开 Chrome `chrome://extensions/`，点击“加载已解压的扩展程序”，选择该目录即可。
   - **Redis**：映射在宿主机 `6380` 端口。

### 2. Jira 看板增强 (Tampermonkey 脚本)
为了在 Jira 看板页面直接使用 AI 分析功能，你需要安装配套的油猴脚本：

1. **安装插件**：在 Chrome 商店安装 [Tampermonkey](https://chrome.google.com/webstore/detail/tampermonkey/dhdgffkkebhmkfjojejmpbldmpobfkfo) 扩展。
2. **新建脚本**：点击 Tampermonkey 图标 -> “添加新脚本”。
3. **复制代码**：将本项目根目录下的 `tampermonkey.js` 文件内容全部复制并粘贴到编辑器中。
4. **保存生效**：按 `Ctrl+S` (或 `Cmd+S`) 保存。
5. **使用**：刷新你的 Jira Board 页面，你会发现每个 Story 卡片上多出了一个“AI 分析”按钮，点击即可快速调用 Streamline 后端进行深度分析。

### 3. 手动分步部署（不推荐）
<details>
<summary>展开查看分步部署细节</summary>

#### 前置要求
- **Node.js**: v20+ (必须，gemini-cli 的正则表达式依赖需要 v20)
- **Python**: v3.10+
- **Redis**: 必须安装并运行（默认端口 6379）。
- **Gemini CLI**: 必须安装 `gemini-cli` 并在系统 PATH 中。

#### 后端部署 (Python API)
1. 安装 Python 依赖：
   ```bash
   pip install -r requirements.txt
   ```
2. 启动 API 服务（默认端口 8200）：
   ```bash
   uvicorn main:app --port 8200 --reload
   ```

#### 前端部署 (Chrome Extension)
1. 进入插件目录安装并构建：
   ```bash
   cd chrome_extension && npm install && npm run build
   ```
2. 加载 `chrome_extension/dist` 文件夹到 Chrome。

#### MCP 服务配置
确保你的 `~/.gemini/settings.json` 中配置了必要的 MCP 服务器。
</details>

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
