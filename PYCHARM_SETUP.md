# PyCharm 启动指南

## 首次设置

### 1. 配置 Python 解释器

1. 打开 PyCharm
2. 打开项目：`File` → `Open` → 选择项目文件夹
3. 配置解释器：
   - `File` → `Settings` (Windows/Linux) 或 `PyCharm` → `Preferences` (Mac)
   - 导航到 `Project: hackathon-personal-assistant` → `Python Interpreter`
   - 点击齿轮图标 → `Add...`
   - 选择 `Existing environment`
   - 解释器路径：`$PROJECT_DIR$/ai-assistant/bin/python`
   - 点击 `OK`

### 2. 安装依赖（如果还没安装）

在 PyCharm 终端中运行：

```bash
source ai-assistant/bin/activate
pip install -r requirements.txt
```

## 启动项目

### 方式一：使用运行配置（推荐）

1. 点击右上角的运行配置下拉菜单
2. 选择 **"FastAPI Server"** 或 **"FastAPI Server (Debug)"**
3. 点击绿色运行按钮 ▶️ 或按 `Shift+F10`

### 方式二：手动创建运行配置

1. 点击右上角运行配置下拉菜单 → `Edit Configurations...`
2. 点击 `+` → 选择 `Python`
3. 配置如下：
   - **Name**: `FastAPI Server`
   - **Script path**: `$PROJECT_DIR$/ai-assistant/bin/uvicorn`
   - **Parameters**: `main:app --reload --host 0.0.0.0 --port 8000`
   - **Python interpreter**: 选择 `ai-assistant/bin/python`
   - **Working directory**: `$PROJECT_DIR$`
4. 点击 `OK` 保存

### 方式三：使用终端

在 PyCharm 底部终端中运行：

```bash
source ai-assistant/bin/activate
uvicorn main:app --reload
```

## 调试项目

### 设置断点

1. 在代码行号左侧点击设置断点（红色圆点）
2. 例如在 `main.py` 的 `chat_with_gemini` 函数中设置断点

### 启动调试

1. 选择 **"FastAPI Server (Debug)"** 配置
2. 点击调试按钮 🐛 或按 `Shift+F9`
3. 发送请求时会在断点处暂停

### 调试快捷键

- `Shift+F9` - 开始调试
- `F8` - 单步跳过（Step Over）
- `F7` - 单步进入（Step Into）
- `Shift+F8` - 单步跳出（Step Out）
- `F9` - 继续执行（Resume）
- `Ctrl+F8` - 切换断点

## 测试调试

1. 在 `main.py` 第 58 行设置断点：
   ```python
   result = gemini_client.chat(...)  # 在这里设置断点
   ```

2. 启动调试（`Shift+F9`）

3. 在 PyCharm 终端或外部终端运行：
   ```bash
   curl -X POST "http://localhost:8000/api/gemini/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "测试"}'
   ```

4. 代码会在断点处暂停，可以：
   - 查看变量值（鼠标悬停或使用 Variables 面板）
   - 单步执行（F8）
   - 继续执行（F9）
   - 查看调用堆栈（Debugger 面板）

## 常见问题

### 1. 找不到 uvicorn

确保虚拟环境已正确配置，并且已安装依赖：
```bash
source ai-assistant/bin/activate
pip install -r requirements.txt
```

### 2. 端口被占用

如果 8000 端口被占用，可以：
- 修改运行配置中的端口号（例如改为 8001）
- 或者在终端中手动指定端口：
  ```bash
  uvicorn main:app --reload --port 8001
  ```

### 3. 模块导入错误

确保：
- Python 解释器指向 `ai-assistant/bin/python`
- Working directory 设置为项目根目录
- 已勾选 `Add content roots to PYTHONPATH`

## 项目结构

```
hackathon-personal-assistant/
├── .idea/                    # PyCharm 配置目录
│   └── runConfigurations/    # 运行配置
├── ai-assistant/             # 虚拟环境
├── main.py                   # FastAPI 主文件
├── gemini_client.py          # Gemini 客户端
├── requirements.txt          # 依赖列表
└── README.md                # 项目说明
```

## 访问服务

启动后访问：
- API 文档：http://localhost:8000/docs
- 替代文档：http://localhost:8000/redoc
- Hello World：http://localhost:8000/
