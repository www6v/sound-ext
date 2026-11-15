#!/bin/bash
# No-TTS 纯文本模式启动脚本
#
# 原则：不修改任何 Venus 源代码，纯配置方式
# 原理：通过 sitecustomize.py 钩子修改 MiniCPMODuplex._default_duplex_params
#
# 用法:
#   bash start-demo.sh              # 前台启动
#   bash start-demo.sh --detach     # 后台启动
#   bash start-demo.sh --stop       # 停止服务
#
# 访问:
#   笔记本 SSH 隧道: ssh -N -L 8042:127.0.0.1:8042 wangwei@<server>
#   浏览器: http://localhost:8042

set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="/home/wangwei/wei/workspacePy/sound/Realtime-Venus"
CONFIG_FILE="$DEPLOY_DIR/demo-config.json"

cd "$PROJECT_DIR"

# 环境设置
export PATH="/home/wangwei/bin:$PATH"
export VENUS_PYTHON="/data1/disk1/venv/bin/python"

# No-TTS 钩子（纯配置方式：修改 _default_duplex_params）
export PYTHONPATH="$DEPLOY_DIR${PYTHONPATH:+:$PYTHONPATH}"

# CUDA 内存优化
export PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True"

echo "=== No-TTS 纯文本模式 ==="
echo "配置: $CONFIG_FILE"
echo "钩子: $DEPLOY_DIR/sitecustomize.py"
echo "端口: Model=8041, Web=8042"
echo "量化: 8-bit (文本质量优于 4-bit)"
echo "原理: 修改 _default_duplex_params (不改源代码)"
echo ""

# 清理之前的备份文件（如果存在）
rm -f "$PROJECT_DIR/demos/model/adapter.py.bak"
rm -f "$HOME/.cache/huggingface/modules/transformers_modules/Realtime-Venus-Audio/modeling_minicpmo.py.bak"

# 启动（复用原始 start.sh）
bash start.sh --config "$CONFIG_FILE" "$@"
