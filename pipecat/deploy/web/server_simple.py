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
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger
from starlette.requests import Request

# 加载环境变量
load_dotenv()

# ============================================
# FastAPI 应用
# ============================================

app = FastAPI(title="语音助手")

# 静态文件和模板
BASE_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# 全局 LLM 和 TTS 实例
llm_service = None
tts_service = None


def init_services():
    """初始化服务"""
    global llm_service, tts_service

    from pipecat.services.qwen.llm import QwenLLMService
    from pipecat.services.piper.tts import PiperTTSService

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

    # TTS: Piper
    tts_service = PiperTTSService(
        settings=PiperTTSService.Settings(
            voice=os.environ.get("PIPER_VOICE", "zh_CN-huayan-medium"),
            length_scale=1.0,
        ),
    )

    logger.info("服务初始化成功")
    return True


# ============================================
# 页面路由
# ============================================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """主页"""
    return templates.TemplateResponse("index.html", {"request": request})


# ============================================
# WebSocket 端点
# ============================================

@app.websocket("/ws/text/{client_id}")
async def websocket_text_endpoint(websocket: WebSocket, client_id: str):
    """纯文本 WebSocket 端点"""

    await websocket.accept()
    logger.info(f"客户端连接: {client_id}")

    if llm_service is None:
        await websocket.send_json({"type": "error", "message": "服务器未配置 QWEN_API_KEY"})
        await websocket.close()
        return

    await websocket.send_json({"type": "connected", "message": "文字助手已连接"})

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
                    # 构建消息列表
                    messages = [
                        {"role": "system", "content": "你是一个友好的中文语音助手。请用简洁、自然的中文回答问题。回答控制在50字以内。"},
                    ] + conversation[-10:]  # 只保留最近10轮对话

                    # 使用 OpenAI 兼容接口调用 Qwen
                    import aiohttp

                    async with aiohttp.ClientSession() as session:
                        headers = {
                            "Authorization": f"Bearer {os.environ.get('QWEN_API_KEY')}",
                            "Content-Type": "application/json",
                        }
                        payload = {
                            "model": os.environ.get("QWEN_MODEL", "qwen-plus"),
                            "messages": messages,
                        }

                        async with session.post(
                            "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
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
                    assistant_text = "抱歉，出现了错误。"

                # 添加到对话历史
                conversation.append({"role": "assistant", "content": assistant_text})

                # 发送文字回复
                await websocket.send_json({
                    "type": "response",
                    "text": assistant_text,
                })

                # 调用 TTS 生成语音
                try:
                    # 使用 Piper 合成语音
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
                            wav_file.setsampwidth(2)  # 16-bit
                            wav_file.setframerate(22050)  # Piper 默认采样率
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

    if not init_services():
        logger.warning("服务初始化失败，请检查 QWEN_API_KEY")

    logger.info("")
    logger.info("打开浏览器访问: http://localhost:8000")
    logger.info("")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        log_level="info",
    )
