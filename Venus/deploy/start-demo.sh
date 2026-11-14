#!/bin/bash
# Realtime-Venus Demo 启动脚本
# 所有配置在 deploy 目录，不修改源代码
set -e

DEPLOY_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="/home/wangwei/wei/workspacePy/sound/Realtime-Venus"
DEMO_CONFIG="$DEPLOY_DIR/demo-config.json"
HARNESS_CONFIG="$DEPLOY_DIR/harness-config.json"

# 确保 PATH 包含 ffmpeg
export PATH="/home/wangwei/bin:$PATH"

# venv 在 /data1/disk1（/home 空间不够放 PyTorch）
export VENUS_PYTHON="/data1/disk1/venv/bin/python"

# 8-bit 量化钩子（减少 VRAM ~10GB，给 TTS 留空间）
export PYTHONPATH="$DEPLOY_DIR:$PYTHONPATH"

# CUDA 内存碎片优化
export PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True"

echo "====================================="
echo "  Realtime-Venus 远程语音 Demo"
echo "====================================="
echo ""
echo "  部署目录: $DEPLOY_DIR"
echo "  项目目录: $PROJECT_DIR"
echo "  Demo 配置: $DEMO_CONFIG"
echo "  Harness 配置: $HARNESS_CONFIG"
echo ""

# 检查前置条件
echo "🔍 检查环境..."

# Python
if [ ! -x "$VENUS_PYTHON" ]; then
    echo "❌ venv 不存在: $VENUS_PYTHON"
    echo "   请先运行: bash $DEPLOY_DIR/setup.sh"
    exit 1
fi
echo "  ✅ Python: $($VENUS_PYTHON --version)"

# FFmpeg
if ! command -v ffmpeg &>/dev/null; then
    echo "❌ ffmpeg 未找到"
    exit 1
fi
echo "  ✅ FFmpeg: $(ffmpeg -version 2>&1 | head -1 | cut -d' ' -f1-3)"

# 模型
MODEL_PATH=$(python3 -c "import json; print(json.load(open('$DEMO_CONFIG'))['model']['path'])")
if [ ! -f "$MODEL_PATH/config.json" ]; then
    echo "❌ 模型未找到: $MODEL_PATH"
    exit 1
fi
echo "  ✅ 模型: $MODEL_PATH"

# Tailscale
TS_IP=$(tailscale ip -4 2>/dev/null | head -1)
if [ -n "$TS_IP" ]; then
    echo "  ✅ Tailscale: $TS_IP"
    echo ""
    echo "  📋 在笔记本浏览器中打开: http://$TS_IP:8032"
else
    echo "  ⚠️  Tailscale 未连接"
fi

echo ""
echo "  正在启动服务..."
echo "====================================="
echo ""

cd "$PROJECT_DIR"
exec bash start.sh --config "$DEMO_CONFIG" "$@"
