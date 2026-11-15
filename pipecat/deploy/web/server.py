#!/usr/bin/env python3
"""
Web 语音助手服务器

使用 FastAPI + WebSocket 实现浏览器端的语音交互
- 浏览器录音 → WebSocket → 服务器
- 服务器处理 → WebSocket → 浏览器播放
"""

import asyncio
import base64
import json
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger
from starlette.requests import Request

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import EndFrame, LLMRunFrame, TextFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker, ProcessorUnusablePolicy
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.services.funasr.stt import FunASRSTTService
from pipecat.services.piper.tts import PiperTTSService
from pipecat.services.qwen.llm import QwenLLMService
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from pipecat.workers.runner import WorkerRunner

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

# 存储活动的 WebSocket 连接和对应的 Worker
active_connections: dict[str, dict] = {}


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

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket 端点 - 处理语音流"""

    await websocket.accept()
    logger.info(f"客户端连接: {client_id}")

    # 获取配置
    QWEN_API_KEY = os.environ.get("QWEN_API_KEY")
    if not QWEN_API_KEY:
        await websocket.send_json({"type": "error", "message": "服务器未配置 QWEN_API_KEY"})
        await websocket.close()
        return

    # 创建管道组件
    try:
        # STT: FunASR
        stt = FunASRSTTService(
            model=os.environ.get("FUNASR_MODEL", "iic/SenseVoiceSmall"),
            language="auto",
        )

        # LLM: Qwen
        llm = QwenLLMService(
            api_key=QWEN_API_KEY,
            settings=QwenLLMService.Settings(
                model=os.environ.get("QWEN_MODEL", "qwen-plus"),
                system_instruction="你是一个友好的中文语音助手。请用简洁、自然的中文回答问题。",
            ),
        )

        # TTS: Piper
        tts = PiperTTSService(
            settings=PiperTTSService.Settings(
                voice=os.environ.get("PIPER_VOICE", "zh_CN-huayan-medium"),
                length_scale=1.0,
            ),
        )

        # 上下文
        context = LLMContext()
        user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
            context,
            user_params=LLMUserAggregatorParams(
                vad_analyzer=SileroVADAnalyzer(),
            ),
        )

        # 简单的管道: STT → LLM → TTS
        pipeline = Pipeline([
            stt,
            user_aggregator,
            llm,
            tts,
            assistant_aggregator,
        ])

        # Worker
        worker = PipelineWorker(
            pipeline,
            params=PipelineParams(),
            processor_unusable_policy=ProcessorUnusablePolicy.END,
        )

        runner = WorkerRunner()
        await runner.add_workers(worker)

        # 存储连接信息
        active_connections[client_id] = {
            "websocket": websocket,
            "worker": worker,
            "runner": runner,
            "context": context,
        }

        # 发送连接成功消息
        await websocket.send_json({"type": "connected", "message": "语音助手已连接"})

        # 初始问候
        context.add_message({
            "role": "system",
            "content": "请向用户问好，简短地介绍自己，并询问有什么可以帮忙的。"
        })
        await worker.queue_frames([LLMRunFrame()])

        # 处理消息
        async def process_messages():
            """处理来自 TTS 的音频帧"""
            try:
                while True:
                    # 等待音频帧
                    frame = await asyncio.sleep(0.1)
                    # 这里需要从管道获取音频输出
            except Exception as e:
                logger.error(f"消息处理错误: {e}")

        # 接收消息循环
        try:
            while True:
                # 接收来自浏览器的消息
                data = await websocket.receive()

                if "text" in data:
                    # 文本消息
                    message = json.loads(data["text"])
                    msg_type = message.get("type")

                    if msg_type == "audio":
                        # 音频数据 (base64 编码的 PCM)
                        audio_data = base64.b64decode(message["data"])
                        # TODO: 处理音频输入

                    elif msg_type == "text":
                        # 文本输入 (备用)
                        text = message.get("content", "")
                        if text:
                            context.add_message({"role": "user", "content": text})
                            await worker.queue_frames([LLMRunFrame()])

                    elif msg_type == "interrupt":
                        # 中断信号
                        logger.info("收到中断信号")

                elif "bytes" in data:
                    # 二进制音频数据
                    audio_data = data["bytes"]
                    # 创建音频帧并推送到管道

        except WebSocketDisconnect:
            logger.info(f"客户端断开: {client_id}")
        except Exception as e:
            logger.error(f"WebSocket 错误: {e}")
        finally:
            # 清理
            if client_id in active_connections:
                conn = active_connections.pop(client_id)
                await conn["worker"].queue_frames([EndFrame()])
                await conn["runner"].cancel()

    except Exception as e:
        logger.error(f"初始化错误: {e}")
        await websocket.send_json({"type": "error", "message": str(e)})
        await websocket.close()


# ============================================
# 简化的 WebSocket 端点 (纯文本模式)
# ============================================

@app.websocket("/ws/text/{client_id}")
async def websocket_text_endpoint(websocket: WebSocket, client_id: str):
    """纯文本 WebSocket 端点 - 用于调试"""

    await websocket.accept()
    logger.info(f"文本客户端连接: {client_id}")

    QWEN_API_KEY = os.environ.get("QWEN_API_KEY")
    if not QWEN_API_KEY:
        await websocket.send_json({"type": "error", "message": "服务器未配置 QWEN_API_KEY"})
        await websocket.close()
        return

    try:
        # 创建 LLM
        llm = QwenLLMService(
            api_key=QWEN_API_KEY,
            settings=QwenLLMService.Settings(
                model=os.environ.get("QWEN_MODEL", "qwen-plus"),
            ),
        )

        # 创建 TTS
        tts = PiperTTSService(
            settings=PiperTTSService.Settings(
                voice=os.environ.get("PIPER_VOICE", "zh_CN-huayan-medium"),
            ),
        )

        await websocket.send_json({"type": "connected", "message": "文本助手已连接"})

        while True:
            data = await websocket.receive_json()

            if data.get("type") == "text":
                user_text = data.get("content", "")

                # 调用 LLM
                # 这里需要实现 LLM 调用逻辑

                # 调用 TTS
                # 返回音频

                await websocket.send_json({
                    "type": "response",
                    "text": f"你说的是: {user_text}",
                })

    except WebSocketDisconnect:
        logger.info(f"文本客户端断开: {client_id}")
    except Exception as e:
        logger.error(f"错误: {e}")


# ============================================
# 启动
# ============================================

if __name__ == "__main__":
    import uvicorn

    logger.info("=" * 50)
    logger.info("Web 语音助手服务器")
    logger.info("=" * 50)
    logger.info("")
    logger.info("打开浏览器访问: http://localhost:8000")
    logger.info("")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        log_level="info",
    )
