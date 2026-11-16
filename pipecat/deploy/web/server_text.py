#!/usr/bin/env python3
"""
Web 语音助手服务器 (纯文字版)

支持文字聊天，不需要 TTS 模型
"""

import asyncio
import json
import os
import sys
from pathlib import Path

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

# 全局 LLM 实例
llm_service = None


def init_llm():
    """初始化 LLM 服务"""
    global llm_service

    QWEN_API_KEY = os.environ.get("QWEN_API_KEY")
    if not QWEN_API_KEY:
        logger.warning("未设置 QWEN_API_KEY，LLM 功能不可用")
        return False

    logger.info(f"QWEN_API_KEY: {QWEN_API_KEY[:10]}...")
    logger.info(f"QWEN_MODEL: {os.environ.get('QWEN_MODEL', 'qwen-plus')}")
    return True


# ============================================
# 页面路由
# ============================================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """主页"""
    return templates.TemplateResponse("index.html", {"request": request})


# ============================================
# 健康检查
# ============================================

@app.get("/health")
async def health():
    """健康检查"""
    return {
        "status": "ok",
        "llm": llm_service is not None,
    }


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
                        {"role": "system", "content": "你是一个友好的中文语音助手。请用简洁、自然的中文回答问题。回答控制在100字以内。"},
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

                        logger.info(f"调用 Qwen API...")

                        async with session.post(
                            "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
                            headers=headers,
                            json=payload,
                            timeout=aiohttp.ClientTimeout(total=30),
                        ) as resp:
                            if resp.status == 200:
                                result = await resp.json()
                                assistant_text = result["choices"][0]["message"]["content"]
                                logger.info(f"Qwen 回复: {assistant_text[:50]}...")
                            else:
                                error_text = await resp.text()
                                logger.error(f"LLM 调用失败: {resp.status} - {error_text}")
                                assistant_text = f"抱歉，API 返回错误: {resp.status}"

                except asyncio.TimeoutError:
                    logger.error("LLM 调用超时")
                    assistant_text = "抱歉，响应超时。"
                except Exception as e:
                    logger.error(f"LLM 调用错误: {e}")
                    assistant_text = f"抱歉，出现了错误: {str(e)}"

                # 添加到对话历史
                conversation.append({"role": "assistant", "content": assistant_text})

                # 发送文字回复
                await websocket.send_json({
                    "type": "response",
                    "text": assistant_text,
                })

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
    logger.info("Web 语音助手服务器 (纯文字版)")
    logger.info("=" * 50)

    if init_llm():
        logger.info("LLM 服务初始化成功")
    else:
        logger.warning("LLM 初始化失败，请检查 QWEN_API_KEY")

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
