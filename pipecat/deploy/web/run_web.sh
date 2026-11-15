#!/bin/bash
# 启动 Web 语音助手

set -e

cd "$(dirname "$0")"

# 激活虚拟环境
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "错误: 未找到虚拟环境，请先运行 install.sh"
    exit 1
fi

# 加载环境变量
if [ -f "../.env" ]; then
    export $(grep -v '^#' ../.env | xargs)
fi

# 检查 API Key
if [ -z "$QWEN_API_KEY" ]; then
    echo "错误: 未设置 QWEN_API_KEY"
    echo "请编辑 ../.env 文件"
    exit 1
fi

# 启动服务器
echo "=================================================="
echo "  Web 语音助手"
echo "=================================================="
echo ""
echo "打开浏览器访问: http://localhost:8000"
echo "按 Ctrl+C 停止"
echo ""

python server_simple.py
