# Web 语音助手

基于 Web 的语音助手，支持浏览器录音和文字输入。

## 架构

```
┌─────────────────┐     WebSocket     ┌─────────────────┐
│     浏览器      │ ◄──────────────► │     服务器      │
│  ┌───────────┐  │                   │  ┌───────────┐  │
│  │ 麦克风录音 │  │    音频数据      │  │  FunASR   │  │
│  │  (WebRTC)  │  │ ──────────────► │  │   (STT)   │  │
│  └───────────┘  │                   │  └─────┬─────┘  │
│                 │                   │        │        │
│  ┌───────────┐  │                   │  ┌─────▼─────┐  │
│  │ 音频播放  │  │    音频数据      │  │   Qwen    │  │
│  │  (HTML5)  │  │ ◄────────────── │  │   (LLM)   │  │
│  └───────────┘  │                   │  └─────┬─────┘  │
│                 │                   │        │        │
│  ┌───────────┐  │                   │  ┌─────▼─────┐  │
│  │  文字输入  │  │    文字数据      │  │  Piper    │  │
│  │  (备用)   │  │ ──────────────► │  │  (TTS)    │  │
│  └───────────┘  │                   │  └───────────┘  │
└─────────────────┘                   └─────────────────┘
```

## 功能

- ✅ **语音输入**: 浏览器录音，发送到服务器识别
- ✅ **文字输入**: 支持文字聊天模式
- ✅ **语音输出**: 服务器合成语音，浏览器播放
- ✅ **实时交互**: WebSocket 双向通信

## 安装

```bash
cd /home/wangwei/wei/workspacePy/sound/sound-ext/pipecat/deploy/web

# 安装依赖
bash install.sh

# 配置 API Key
echo "QWEN_API_KEY=sk-your-key-here" >> ../.env
```

## 运行

```bash
# 启动服务器
bash run_web.sh

# 或手动启动
source .venv/bin/activate
export QWEN_API_KEY=sk-your-key-here
python server_simple.py
```

访问: http://localhost:8000

## 文件说明

```
web/
├── server_simple.py      # 简化版服务器 (推荐)
├── server.py             # 完整版服务器
├── templates/
│   └── index.html        # 前端页面
├── static/               # 静态资源
├── install.sh            # 安装脚本
└── run_web.sh            # 启动脚本
```

## 使用方式

### 语音模式

1. 点击「语音模式」按钮
2. 点击麦克风按钮开始录音
3. 说话完毕后再点击停止
4. 等待助手回复

### 文字模式

1. 点击「文字模式」按钮
2. 在文本框输入问题
3. 按 Enter 或点击发送
4. 查看文字和语音回复

## 自定义

### 更换语音

编辑 `../.env`:
```bash
PIPER_VOICE=zh_CN-huayan-medium  # 中文女声
# 或
PIPER_VOICE=en_US-ryan-high      # 英文男声
```

### 更换 LLM 模型

```bash
QWEN_MODEL=qwen-plus    # 平衡
# 或
QWEN_MODEL=qwen-turbo   # 快速
# 或
QWEN_MODEL=qwen-max     # 最强
```

## 故障排查

### 无法访问麦克风

确保:
- 浏览器有麦克风权限
- 使用 HTTPS 或 localhost
- 浏览器支持 WebRTC

### 音频播放失败

检查:
- 浏览器是否允许自动播放
- 音频格式是否支持

### 连接失败

检查:
- 服务器是否运行
- 端口 8000 是否被占用
- 防火墙设置
