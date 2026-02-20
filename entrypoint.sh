#!/bin/bash
set -e

# 设置默认变量
REDIS_HOST=${REDIS_HOST:-"redis"}
REDIS_PORT=${REDIS_PORT:-"6379"}

# 检查宿主机配置是否挂载成功
if [ ! -f "/root/.gemini/settings.json" ]; then
  echo "Warning: /root/.gemini/settings.json not found! Generating basic config..."
  mkdir -p ~/.gemini
  cat > ~/.gemini/settings.json <<EOF
{
  "selectedAuthType": "google-cloud-auth",
  "mcpServers": {
    "geminix": { "httpUrl": "http://geminix.crmdev.veevasfa.com/mcp" },
    "jira": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "-e", "JIRA_URL=https://jira.veevadev.com", "-e", "JIRA_USERNAME=${JIRA_USERNAME}", "-e", "JIRA_PERSONAL_TOKEN=${JIRA_PERSONAL_TOKEN}", "-e", "JIRA_SSL_VERIFY=false", "ghcr.io/sooperset/mcp-atlassian:latest"]
    }
  }
}
EOF
else
  # 如果已挂载，确保 authType 是 google-cloud-auth
  sed -i 's/"selectedAuthType": "[^"]*"/"selectedAuthType": "google-cloud-auth"/g' ~/.gemini/settings.json
fi

echo "Synchronizing latest build artifacts..."
# 将镜像内编译好的 dist 同步到挂载的目录中 (如果目录已挂载)
if [ -d "/app/chrome_extension" ]; then
  # 使用临时目录中转，确保不会因为直接覆盖正在使用的目录而报错
  mkdir -p /tmp/latest_dist
  cp -r /app/chrome_extension/dist/. /tmp/latest_dist/
  cp -r /tmp/latest_dist/. /app/chrome_extension/dist/
fi

echo "Environment ready. Starting Streamline API..."

# 启动后端应用
exec uvicorn main:app --host 0.0.0.0 --port 8200
