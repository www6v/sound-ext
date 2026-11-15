# 快速开始指南

## 3步运行语音助手

### 1. 安装

```bash
cd /home/wangwei/wei/workspacePy/sound/sound-ext/pipecat/deploy
bash install.sh
```

### 2. 配置 API Key

编辑 `.env` 文件，填入你的 Qwen API Key：

```bash
# 获取地址: https://bailian.console.aliyun.com/
QWEN_API_KEY=sk-your-api-key-here
```

### 3. 运行

```bash
# 方式1: 使用启动脚本 (推荐)
bash run.sh

# 方式2: 直接运行
source .venv/bin/activate
python voice_assistant.py
```

---

## 手动安装

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install pipecat-ai
pip install "pipecat-ai[funasr]"
pip install "pipecat-ai[piper]"
pip install python-dotenv loguru

# 运行
export QWEN_API_KEY=sk-your-api-key-here
python voice_assistant.py
```

---

## 文件说明

| 文件 | 说明 |
|------|------|
| `README.md` | 完整文档 |
| `install.sh` | 一键安装脚本 |
| `run.sh` | 快速启动脚本 |
| `voice_assistant.py` | 基础版代码 |
| `voice_assistant_verbose.py` | 详细日志版 |
| `.env.example` | 配置模板 |

---

## 常见问题

**Q: 模型下载慢？**
```bash
export HF_ENDPOINT=https://hf-mirror.com
```

**Q: 没有音频设备？**
```bash
# 检查设备
python -c "import sounddevice; print(sounddevice.query_devices())"
```

**Q: 如何更换语音？**

编辑 `.env`:
```bash
PIPER_VOICE=zh_CN-huayan-medium  # 中文女声
# 或
PIPER_VOICE=en_US-ryan-high      # 英文男声
```
