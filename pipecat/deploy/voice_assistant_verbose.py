#!/usr/bin/env python3
"""
FunASR + Qwen + Piper 语音助手 (详细日志版)

带详细日志输出的版本，用于调试和排查问题。
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import EndFrame, LLMRunFrame
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
from pipecat.transports.local.audio import LocalAudioTransport, LocalAudioTransportParams
from pipecat.workers.runner import WorkerRunner

# 加载环境变量
load_dotenv()


class FrameLogger:
    """帧日志记录器"""

    @staticmethod
    async def log_frame(frame, direction="→"):
        """记录帧信息"""
        frame_type = type(frame).__name__

        # 根据帧类型记录不同信息
        if hasattr(frame, 'text'):
            logger.debug(f"{direction} {frame_type}: {frame.text[:50]}...")
        elif hasattr(frame, 'audio'):
            logger.debug(f"{direction} {frame_type}: {len(frame.audio)} bytes")
        elif hasattr(frame, 'image'):
            logger.debug(f"{direction} {frame_type}: image data")
        else:
            logger.debug(f"{direction} {frame_type}")


async def main():
    """主函数"""

    # ============================================
    # 配置区域
    # ============================================

    # 检查 API Key
    QWEN_API_KEY = os.environ.get("QWEN_API_KEY")
    if not QWEN_API_KEY:
        logger.error("=" * 60)
        logger.error("错误: 未设置 QWEN_API_KEY")
        logger.error("=" * 60)
        logger.error("")
        logger.error("请通过以下任一方式设置:")
        logger.error("1. 在 .env 文件中添加: QWEN_API_KEY=sk-xxx")
        logger.error("2. 运行命令: export QWEN_API_KEY=sk-xxx")
        logger.error("")
        logger.error("获取 API Key:")
        logger.error("https://bailian.console.aliyun.com/")
        logger.error("")
        sys.exit(1)

    # 其他配置
    QWEN_MODEL = os.environ.get("QWEN_MODEL", "qwen-plus")
    FUNASR_MODEL = os.environ.get("FUNASR_MODEL", "iic/SenseVoiceSmall")
    PIPER_VOICE = os.environ.get("PIPER_VOICE", "zh_CN-huayan-medium")

    # ============================================
    # 初始化日志
    # ============================================

    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>",
        level="DEBUG",  # 详细日志
    )

    logger.info("=" * 60)
    logger.info("FunASR + Qwen + Piper 语音助手 (详细日志版)")
    logger.info("=" * 60)

    # ============================================
    # 打印配置
    # ============================================

    logger.info("配置信息:")
    logger.info(f"  Qwen 模型: {QWEN_MODEL}")
    logger.info(f"  FunASR 模型: {FUNASR_MODEL}")
    logger.info(f"  Piper 语音: {PIPER_VOICE}")
    logger.info("")

    # ============================================
    # 初始化组件
    # ============================================

    # 1. 音频传输
    logger.info("[1/5] 初始化音频传输...")
    try:
        transport = LocalAudioTransport(
            LocalAudioTransportParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                sample_rate=16000,
            )
        )
        logger.success("  ✓ 音频传输初始化成功")
    except Exception as e:
        logger.error(f"  ✗ 音频传输初始化失败: {e}")
        raise

    # 2. FunASR STT
    logger.info("[2/5] 初始化 FunASR STT...")
    logger.info(f"  模型: {FUNASR_MODEL}")
    logger.info("  首次运行会下载模型，请耐心等待...")
    try:
        stt = FunASRSTTService(
            model=FUNASR_MODEL,
            language="auto",
        )
        logger.success("  ✓ FunASR STT 初始化成功")
    except Exception as e:
        logger.error(f"  ✗ FunASR STT 初始化失败: {e}")
        logger.error("  提示: 设置 HF_ENDPOINT=https://hf-mirror.com 可能有助于下载")
        raise

    # 3. Qwen LLM
    logger.info("[3/5] 初始化 Qwen LLM...")
    logger.info(f"  模型: {QWEN_MODEL}")
    logger.info(f"  API: https://dashscope-intl.aliyuncs.com")
    try:
        llm = QwenLLMService(
            api_key=QWEN_API_KEY,
            settings=QwenLLMService.Settings(
                model=QWEN_MODEL,
                system_instruction="你是一个友好的中文语音助手。请用简洁、自然的中文回答问题。",
            ),
        )
        logger.success("  ✓ Qwen LLM 初始化成功")
    except Exception as e:
        logger.error(f"  ✗ Qwen LLM 初始化失败: {e}")
        raise

    # 4. Piper TTS
    logger.info("[4/5] 初始化 Piper TTS...")
    logger.info(f"  语音: {PIPER_VOICE}")
    logger.info("  首次运行会下载语音模型...")
    try:
        tts = PiperTTSService(
            settings=PiperTTSService.Settings(
                voice=PIPER_VOICE,
                length_scale=1.0,
            ),
        )
        logger.success("  ✓ Piper TTS 初始化成功")
    except Exception as e:
        logger.error(f"  ✗ Piper TTS 初始化失败: {e}")
        raise

    # 5. 上下文聚合器
    logger.info("[5/5] 初始化上下文聚合器...")
    try:
        context = LLMContext()
        user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
            context,
            user_params=LLMUserAggregatorParams(
                vad_analyzer=SileroVADAnalyzer(),
            ),
        )
        logger.success("  ✓ 上下文聚合器初始化成功")
    except Exception as e:
        logger.error(f"  ✗ 上下文聚合器初始化失败: {e}")
        raise

    # ============================================
    # 构建管道
    # ============================================

    logger.info("")
    logger.info("构建处理管道:")
    logger.info("  麦克风 → VAD → FunASR → Qwen → Piper → 扬声器")
    logger.info("")

    pipeline = Pipeline([
        transport.input(),
        stt,
        user_aggregator,
        llm,
        tts,
        transport.output(),
        assistant_aggregator,
    ])

    # ============================================
    # 创建 Worker
    # ============================================

    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        processor_unusable_policy=ProcessorUnusablePolicy.END,
    )

    runner = WorkerRunner()
    await runner.add_workers(worker)

    # ============================================
    # 事件处理
    # ============================================

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.success("客户端已连接")
        logger.info("")
        logger.info("=" * 60)
        logger.info("语音助手已就绪！")
        logger.info("请开始说话，按 Ctrl+C 退出")
        logger.info("=" * 60)
        logger.info("")

        # 初始问候
        context.add_message({
            "role": "system",
            "content": "请向用户问好，简短地介绍自己，并询问有什么可以帮忙的。"
        })
        await worker.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.warning("客户端已断开")
        await runner.cancel()

    # ============================================
    # 运行
    # ============================================

    try:
        await runner.run()
    except KeyboardInterrupt:
        logger.info("")
        logger.info("收到中断信号，正在关闭...")
        await worker.queue_frames([EndFrame()])
    except Exception as e:
        logger.exception(f"运行错误: {e}")
        raise
    finally:
        logger.info("")
        logger.info("=" * 60)
        logger.info("语音助手已关闭")
        logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
