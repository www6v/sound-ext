#!/usr/bin/env python3
"""
Web 语音助手服务器 (简化版)

支持:
- 文字聊天
- 语音输入 (浏览器录音 → 服务器识别)
- 语音输出 (服务器合成 → 浏览器播放)
"""

import asyncio
import base64
import io
import json
import os
import sys
import wave
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger

# 加载环境变量
load_dotenv()

# ============================================
# FastAPI 应用
# ============================================

app = FastAPI(title="语音助手")

# 静态文件和模板
BASE_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# 使用正确的 Jinja2 初始化
from jinja2 import Environment, FileSystemLoader
templates_dir = BASE_DIR / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(templates_dir)))

# 全局 LLM 和 TTS 实例
llm_service = None
tts_service = None
tts_ready = False


def init_llm():
    """初始化 LLM 服务"""
    global llm_service

    from pipecat.services.qwen.llm import QwenLLMService

    QWEN_API_KEY = os.environ.get("QWEN_API_KEY")
    if not QWEN_API_KEY:
        logger.warning("未设置 QWEN_API_KEY，LLM 功能不可用")
        return False

    # LLM: Qwen
    llm_service = QwenLLMService(
        api_key=QWEN_API_KEY,
        settings=QwenLLMService.Settings(
            model=os.environ.get("QWEN_MODEL", "qwen-plus"),
            system_instruction="你是一个友好的中文语音助手。请用简洁、自然的中文回答问题。回答控制在50字以内。",
        ),
    )

    logger.info("LLM 服务初始化成功")
    return True


def init_tts():
    """初始化 TTS 服务"""
    global tts_service, tts_ready

    try:
        from pipecat.services.piper.tts import PiperTTSService

        # 使用自定义模型路径
        piper_model_path = "/data1/disk1/piper-models/zh_CN-huayan-medium/zh_CN-huayan-medium"

        # TTS: Piper
        tts_service = PiperTTSService(
            settings=PiperTTSService.Settings(
                voice=piper_model_path,
                length_scale=1.0,
            ),
        )

        tts_ready = True
        logger.info(f"TTS 服务初始化成功 (模型: {piper_model_path})")
        return True
    except Exception as e:
        logger.error(f"TTS 初始化失败: {e}")
        return False


# ============================================
# 页面路由
# ============================================

@app.get("/", response_class=HTMLResponse)
async def index():
    """主页"""
    try:
        template = jinja_env.get_template("index.html")
        return HTMLResponse(content=template.render())
    except Exception as e:
        logger.error(f"模板错误: {e}")
        return HTMLResponse(content=f"<h1>错误</h1><p>{str(e)}</p>", status_code=500)


# ============================================
# 健康检查
# ============================================

@app.get("/health")
async def health():
    """健康检查"""
    return JSONResponse(content={
        "status": "ok",
        "llm": llm_service is not None,
        "tts": tts_ready,
    })


# ============================================
# WebSocket 端点
# ============================================

@app.websocket("/ws/text/{client_id}")
async def websocket_text_endpoint(websocket: WebSocket, client_id: str):
    """纯文本 WebSocket 端点"""

    await websocket.accept()
    logger.info(f"客户端连接: {client_id}")

    QWEN_API_KEY = os.environ.get("QWEN_API_KEY")
    if not QWEN_API_KEY:
        await websocket.send_json({"type": "error", "message": "服务器未配置 QWEN_API_KEY"})
        await websocket.close()
        return

    await websocket.send_json({
        "type": "connected",
        "message": "文字助手已连接",
        "tts_ready": tts_ready,
    })

    # 对话历史
    conversation = []

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "text":
                user_text = data.get("content", "")
                logger.info(f"收到用户输入: {user_text}")

                if not user_text:
                    continue

                # 添加到对话历史
                conversation.append({"role": "user", "content": user_text})

                # 调用 LLM
                try:
                    import aiohttp

                    # 构建消息列表
                    messages = [
                        {"role": "system", "content": "你是一个友好的中文语音助手。请用简洁、自然的中文回答问题。回答控制在50字以内。"},
                    ] + conversation[-10:]

                    async with aiohttp.ClientSession() as session:
                        headers = {
                            "Authorization": f"Bearer {QWEN_API_KEY}",
                            "Content-Type": "application/json",
                        }
                        payload = {
                            "model": os.environ.get("QWEN_MODEL", "qwen-plus"),
                            "messages": messages,
                        }

                        async with session.post(
                            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                            headers=headers,
                            json=payload,
                        ) as resp:
                            if resp.status == 200:
                                result = await resp.json()
                                assistant_text = result["choices"][0]["message"]["content"]
                            else:
                                error_text = await resp.text()
                                logger.error(f"LLM 调用失败: {error_text}")
                                assistant_text = "抱歉，我暂时无法回答。"

                except Exception as e:
                    logger.error(f"LLM 调用错误: {e}")
                    assistant_text = f"抱歉，出现了错误: {str(e)[:50]}"

                # 添加到对话历史
                conversation.append({"role": "assistant", "content": assistant_text})

                # 发送文字回复
                await websocket.send_json({
                    "type": "response",
                    "text": assistant_text,
                })

                # 调用 TTS 生成语音 (如果就绪)
                if tts_ready and tts_service:
                    try:
                        from pipecat.frames.frames import TextFrame

                        # 创建音频数据
                        audio_chunks = []
                        async for chunk in tts_service.run_tts(TextFrame(text=assistant_text)):
                            if hasattr(chunk, 'audio') and chunk.audio:
                                audio_chunks.append(chunk.audio)

                        if audio_chunks:
                            # 合并音频
                            full_audio = b''.join(audio_chunks)

                            # 转为 WAV 格式
                            wav_buffer = io.BytesIO()
                            with wave.open(wav_buffer, 'wb') as wav_file:
                                wav_file.setnchannels(1)
                                wav_file.setsampwidth(2)
                                wav_file.setframerate(22050)
                                wav_file.writeframes(full_audio)

                            wav_data = wav_buffer.getvalue()

                            # 发送音频
                            await websocket.send_json({
                                "type": "audio",
                                "data": base64.b64encode(wav_data).decode(),
                            })

                    except Exception as e:
                        logger.error(f"TTS 错误: {e}")

    except WebSocketDisconnect:
        logger.info(f"客户端断开: {client_id}")
    except Exception as e:
        logger.error(f"错误: {e}")


# ============================================
# 启动
# ============================================

@app.on_event("startup")
async def startup():
    """启动时初始化服务"""
    logger.info("=" * 50)
    logger.info("Web 语音助手服务器")
    logger.info("=" * 50)

    # 初始化 LLM
    init_llm()

    # 异步初始化 TTS
    import threading
    def init_tts_thread():
        init_tts()

    threading.Thread(target=init_tts_thread, daemon=True).start()
    logger.info("TTS 服务正在后台初始化...")

    logger.info("")
    logger.info("打开浏览器访问: http://localhost:8000")
    logger.info("")


if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="Web 语音助手服务器")
    parser.add_argument("--ssl-certfile", type=str, help="SSL 证书文件路径")
    parser.add_argument("--ssl-keyfile", type=str, help="SSL 私钥文件路径")
    parser.add_argument("--port", type=int, default=8000, help="服务器端口")
    args = parser.parse_args()

    ssl_config = {}
    if args.ssl_certfile and args.ssl_keyfile:
        ssl_config["ssl_certfile"] = args.ssl_certfile
        ssl_config["ssl_keyfile"] = args.ssl_keyfile
        logger.info(f"启用 HTTPS (端口: {args.port})")
    else:
        logger.info(f"使用 HTTP (端口: {args.port})")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=args.port,
        log_level="info",
        **ssl_config,
    )
