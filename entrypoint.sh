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

echo "Environment ready. Starting Streamline API..."

# 启动后端应用
exec uvicorn main:app --host 0.0.0.0 --port 8200
