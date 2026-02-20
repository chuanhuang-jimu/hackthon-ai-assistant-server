# --- 阶段 1: 前端编译 ---
FROM node:20-slim AS frontend-builder
WORKDIR /build/frontend
COPY chrome_extension/package*.json ./
RUN npm install
COPY chrome_extension/ .
RUN npm run build

# --- 阶段 2: 后端运行环境 ---
FROM python:3.10-slim

# 安装 Node.js (gemini-cli 运行环境) 和必要的系统工具
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    docker.io \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 全局安装 gemini-cli
RUN npm install -g @google/gemini-cli

# 设置工作目录
WORKDIR /app

# 复制后端依赖并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码 (包括从第一阶段生成的 chrome_extension/dist)
COPY . .
COPY --from=frontend-builder /build/frontend/dist ./chrome_extension/dist

# 复制并准备启动脚本
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 暴露后端端口
EXPOSE 8200

# 使用启动脚本
ENTRYPOINT ["/entrypoint.sh"]
