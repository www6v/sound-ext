#!/bin/bash
# ============================================
# FunASR + Qwen + Piper 语音助手安装脚本
# ============================================

set -e

echo "=================================================="
echo "  Pipecat 语音助手安装脚本"
echo "  FunASR + Qwen + Piper"
echo "=================================================="
echo ""

# 检查 Python 版本
echo "[1/6] 检查 Python 版本..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "  Python 版本: $PYTHON_VERSION"

# 检查是否 >= 3.11
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    echo "  错误: 需要 Python 3.11 或更高版本"
    exit 1
fi
echo "  ✓ Python 版本符合要求"
echo ""

# 创建虚拟环境
echo "[2/6] 创建虚拟环境..."
if [ -d ".venv" ]; then
    echo "  虚拟环境已存在，跳过创建"
else
    python3 -m venv .venv
    echo "  ✓ 虚拟环境创建成功"
fi
echo ""

# 激活虚拟环境
echo "[3/6] 激活虚拟环境..."
source .venv/bin/activate
echo "  ✓ 虚拟环境已激活"
echo ""

# 升级 pip
echo "[4/6] 升级 pip..."
pip install --upgrade pip -q
echo "  ✓ pip 升级完成"
echo ""

# 安装依赖
echo "[5/6] 安装依赖包..."
echo "  这可能需要几分钟，请耐心等待..."
echo ""

# 安装 pipecat
echo "  安装 pipecat-ai..."
pip install pipecat-ai -q

# 安装 FunASR
echo "  安装 FunASR (本地STT)..."
pip install "pipecat-ai[funasr]" -q

# 安装 Piper
echo "  安装 Piper (本地TTS)..."
pip install "pipecat-ai[piper]" -q

# 安装其他依赖
echo "  安装其他依赖..."
pip install python-dotenv loguru -q

echo "  ✓ 依赖安装完成"
echo ""

# 创建 .env 文件
echo "[6/6] 配置环境变量..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "  ✓ 已创建 .env 文件"
    echo ""
    echo "  ⚠️  请编辑 .env 文件，填写你的 QWEN_API_KEY"
    echo "     获取地址: https://bailian.console.aliyun.com/"
else
    echo "  .env 文件已存在，跳过"
fi
echo ""

# 完成
echo "=================================================="
echo "  安装完成！"
echo "=================================================="
echo ""
echo "下一步:"
echo "  1. 编辑 .env 文件，填写 QWEN_API_KEY"
echo "  2. 激活虚拟环境: source .venv/bin/activate"
echo "  3. 运行语音助手: python voice_assistant.py"
echo ""
echo "快速开始:"
echo "  source .venv/bin/activate"
echo "  export QWEN_API_KEY=sk-your-key-here"
echo "  python voice_assistant.py"
echo ""
