#!/bin/bash
# ============================================
# 快速启动脚本
# ============================================

set -e

echo "=================================================="
echo "  FunASR + Qwen + Piper 语音助手"
echo "=================================================="
echo ""

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "错误: 未找到虚拟环境"
    echo "请先运行: bash install.sh"
    exit 1
fi

# 激活虚拟环境
source .venv/bin/activate

# 检查 API Key
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

if [ -z "$QWEN_API_KEY" ]; then
    echo "错误: 未设置 QWEN_API_KEY"
    echo "请编辑 .env 文件或运行:"
    echo "  export QWEN_API_KEY=sk-your-key-here"
    exit 1
fi

# 显示配置
echo "配置信息:"
echo "  Qwen 模型: ${QWEN_MODEL:-qwen-plus}"
echo "  FunASR 模型: ${FUNASR_MODEL:-iic/SenseVoiceSmall}"
echo "  Piper 语音: ${PIPER_VOICE:-zh_CN-huayan-medium}"
echo ""

# 选择运行模式
echo "选择运行模式:"
echo "  1. 标准模式 (推荐)"
echo "  2. 详细日志模式 (调试用)"
echo "  3. 退出"
echo ""

read -p "请输入选项 (1-3): " choice

case $choice in
    1)
        echo ""
        echo "启动标准模式..."
        python voice_assistant.py
        ;;
    2)
        echo ""
        echo "启动详细日志模式..."
        python voice_assistant_verbose.py
        ;;
    3)
        echo "退出"
        exit 0
        ;;
    *)
        echo "无效选项"
        exit 1
        ;;
esac
