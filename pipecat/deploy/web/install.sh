#!/bin/bash
# Web 语音助手安装脚本

set -e

echo "=================================================="
echo "  Web 语音助手安装脚本"
echo "=================================================="
echo ""

# 检查 Python 版本
echo "[1/4] 检查 Python 版本..."
python3 --version
echo ""

# 创建虚拟环境
echo "[2/4] 创建虚拟环境..."
if [ -d ".venv" ]; then
    echo "  虚拟环境已存在"
else
    python3 -m venv .venv
    echo "  ✓ 虚拟环境创建成功"
fi
echo ""

# 激活虚拟环境
echo "[3/4] 激活虚拟环境..."
source .venv/bin/activate
echo "  ✓ 虚拟环境已激活"
echo ""

# 安装依赖
echo "[4/4] 安装依赖..."
pip install --upgrade pip -q
pip install fastapi uvicorn "uvicorn[standard]" jinja2 -q
pip install pipecat-ai -q
pip install "pipecat-ai[piper]" -q
pip install python-dotenv aiohttp -q

echo "  ✓ 依赖安装完成"
echo ""

# 创建 .env 文件
if [ ! -f "../.env" ]; then
    echo "创建配置文件..."
    cp ../.env.example ../.env
    echo "  ✓ 已创建 ../.env 文件"
    echo "  ⚠️  请编辑 ../.env 文件，填写 QWEN_API_KEY"
fi
echo ""

# 完成
echo "=================================================="
echo "  安装完成！"
echo "=================================================="
echo ""
echo "下一步:"
echo "  1. 编辑 ../.env 文件，填写 QWEN_API_KEY"
echo "  2. 运行: bash run_web.sh"
echo ""
