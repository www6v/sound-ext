#!/bin/bash
# Realtime-Venus Demo 一键部署脚本
# 用法: bash setup.sh
set -e

DEPLOY_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="/home/wangwei/wei/workspacePy/sound/Realtime-Venus"
MODEL_DIR="/data1/disk1"

export PATH="/home/wangwei/bin:$PATH"

echo "====================================="
echo "  Realtime-Venus Demo 部署"
echo "====================================="
echo ""

# 1. 检查 Python 3.13
echo "📋 Step 1: 检查 Python..."
if ! command -v python3.13 &>/dev/null; then
    echo "❌ 需要 Python 3.13"
    exit 1
fi
echo "  ✅ $(python3.13 --version)"

# 2. 检查 FFmpeg
echo "📋 Step 2: 检查 FFmpeg..."
if ! command -v ffmpeg &>/dev/null; then
    echo "  安装 FFmpeg (via imageio-ffmpeg)..."
    pip3 install --user imageio-ffmpeg 2>/dev/null
    FFMPEG_BIN=$(python3.13 -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())")
    mkdir -p /home/wangwei/bin
    ln -sf "$FFMPEG_BIN" /home/wangwei/bin/ffmpeg
    echo "  ✅ FFmpeg: $(/home/wangwei/bin/ffmpeg -version 2>&1 | head -1 | cut -d' ' -f1-3)"
else
    echo "  ✅ FFmpeg: $(ffmpeg -version 2>&1 | head -1 | cut -d' ' -f1-3)"
fi

# 3. 创建 venv
echo "📋 Step 3: 创建 Python 虚拟环境..."
if [ ! -f "$PROJECT_DIR/runtime/venv/bin/python" ]; then
    python3.13 -m venv "$PROJECT_DIR/runtime/venv"
fi
echo "  ✅ $($PROJECT_DIR/runtime/venv/bin/python --version)"

# 4. 安装依赖
echo "📋 Step 4: 安装 Python 依赖..."
"$PROJECT_DIR/runtime/venv/bin/pip" install --upgrade pip -q
echo "  安装 PyTorch (CUDA 12.4)..."
"$PROJECT_DIR/runtime/venv/bin/pip" install torch torchaudio torchvision --index-url https://download.pytorch.org/whl/cu124 -q
echo "  安装其他依赖..."
"$PROJECT_DIR/runtime/venv/bin/pip" install -r "$DEPLOY_DIR/requirements-compat.txt" -q
echo "  ✅ 依赖安装完成"

# 5. 下载模型
echo "📋 Step 5: 下载模型到 $MODEL_DIR..."
if [ -f "$MODEL_DIR/Realtime-Venus-Audio/config.json" ]; then
    echo "  ✅ Audio 模型已存在"
else
    echo "  从 ModelScope 下载..."
    pip3 install --user modelscope -q
    modelscope download --model inclusionAI/Realtime-Venus --local_dir "$MODEL_DIR" --include "Realtime-Venus-Audio/*"
    echo "  ✅ 模型下载完成"
fi

# 6. 创建 workspace
echo "📋 Step 6: 创建工作目录..."
mkdir -p "$MODEL_DIR/workspace"
echo "  ✅ $MODEL_DIR/workspace"

# 7. 检查 Tailscale
echo "📋 Step 7: 检查网络..."
TS_IP=$(tailscale ip -4 2>/dev/null | head -1)
if [ -n "$TS_IP" ]; then
    echo "  ✅ Tailscale IP: $TS_IP"
else
    echo "  ⚠️  Tailscale 未连接"
fi

echo ""
echo "====================================="
echo "  ✅ 部署完成！"
echo "====================================="
echo ""
echo "  启动命令: bash $DEPLOY_DIR/start-demo.sh"
echo ""
if [ -n "$TS_IP" ]; then
    echo "  笔记本访问: http://$TS_IP:8032"
    echo ""
fi
echo "  配置文件:"
echo "    Demo:    $DEPLOY_DIR/demo-config.json"
echo "    Harness: $DEPLOY_DIR/harness-config.json"
echo ""
