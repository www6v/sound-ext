#!/usr/bin/env python3
"""
FunASR + Qwen + Piper 本地语音助手

这是一个完全功能的语音助手，使用:
- FunASR (本地STT): 阿里开源语音识别，中文准确率高
- Qwen API (云端LLM): 通义千问大语言模型
- Piper (本地TTS): 开源文本转语音

作者: Pipecat Deploy
日期: 2026-11-15
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

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


async def main():
    """主函数"""

    # ============================================
    # 配置区域 - 根据需要修改
    # ============================================

    # Qwen 配置
    QWEN_API_KEY = os.environ.get("QWEN_API_KEY")
    if not QWEN_API_KEY:
        logger.error("请设置环境变量 QWEN_API_KEY")
        logger.error("可以在 .env 文件中设置，或运行: export QWEN_API_KEY=sk-xxx")
        sys.exit(1)

    QWEN_MODEL = os.environ.get("QWEN_MODEL", "qwen-plus")
    QWEN_BASE_URL = os.environ.get(
        "QWEN_BASE_URL",
        "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    )

    # FunASR 配置
    FUNASR_MODEL = os.environ.get("FUNASR_MODEL", "iic/SenseVoiceSmall")
    FUNASR_LANGUAGE = os.environ.get("FUNASR_LANGUAGE", "auto")

    # Piper 配置
    PIPER_VOICE = os.environ.get("PIPER_VOICE", "zh_CN-huayan-medium")
    PIPER_LENGTH_SCALE = float(os.environ.get("PIPER_LENGTH_SCALE", "1.0"))

    # 系统提示词
    SYSTEM_PROMPT = os.environ.get(
        "SYSTEM_PROMPT",
        "你是一个友好的中文语音助手。请用简洁、自然的中文回答用户问题。"
        "回答时避免使用emoji、特殊符号或列表格式，因为你的回答会被朗读出来。"
    )

    # ============================================
    # 初始化组件
    # ============================================

    logger.info("=" * 50)
    logger.info("FunASR + Qwen + Piper 语音助手")
    logger.info("=" * 50)

    # 1. 创建本地音频传输
    logger.info("初始化音频传输...")
    transport = LocalAudioTransport(
        LocalAudioTransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            sample_rate=16000,  # FunASR 需要 16kHz
        )
    )

    # 2. 创建 FunASR STT (本地)
    logger.info(f"初始化 FunASR STT (模型: {FUNASR_MODEL})...")
    stt = FunASRSTTService(
        model=FUNASR_MODEL,
        language=FUNASR_LANGUAGE,
    )

    # 3. 创建 Qwen LLM (云端)
    logger.info(f"初始化 Qwen LLM (模型: {QWEN_MODEL})...")
    llm = QwenLLMService(
        api_key=QWEN_API_KEY,
        base_url=QWEN_BASE_URL,
        settings=QwenLLMService.Settings(
            model=QWEN_MODEL,
            system_instruction=SYSTEM_PROMPT,
        ),
    )

    # 4. 创建 Piper TTS (本地)
    logger.info(f"初始化 Piper TTS (语音: {PIPER_VOICE})...")
    tts = PiperTTSService(
        settings=PiperTTSService.Settings(
            voice=PIPER_VOICE,
            length_scale=PIPER_LENGTH_SCALE,
        ),
    )

    # 5. 创建上下文聚合器
    context = LLMContext()
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer(),
        ),
    )

    # ============================================
    # 构建管道
    # ============================================

    logger.info("构建处理管道...")
    pipeline = Pipeline([
        transport.input(),        # 音频输入 (麦克风)
        stt,                      # 语音识别 (FunASR)
        user_aggregator,          # 用户消息聚合
        llm,                      # 大语言模型 (Qwen)
        tts,                      # 文本转语音 (Piper)
        transport.output(),       # 音频输出 (扬声器)
        assistant_aggregator,     # 助手消息聚合
    ])

    # ============================================
    # 创建 Worker 和 Runner
    # ============================================

    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(
            enable_metrics=False,
            enable_usage_metrics=False,
        ),
        processor_unusable_policy=ProcessorUnusablePolicy.END,
    )

    runner = WorkerRunner()
    await runner.add_workers(worker)

    # ============================================
    # 开始对话
    # ============================================

    logger.info("=" * 50)
    logger.info("语音助手已启动！")
    logger.info("按 Ctrl+C 退出")
    logger.info("=" * 50)

    # 添加初始消息
    context.add_message({
        "role": "system",
        "content": "请向用户问好，并询问有什么可以帮助的。"
    })

    # 启动 LLM 生成
    await worker.queue_frames([LLMRunFrame()])

    # 运行
    try:
        await runner.run()
    except KeyboardInterrupt:
        logger.info("\n用户中断，正在关闭...")
        await worker.queue_frames([EndFrame()])
    except Exception as e:
        logger.error(f"运行错误: {e}")
        raise
    finally:
        logger.info("语音助手已关闭")


if __name__ == "__main__":
    # 配置日志
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
        level="INFO",
    )

    # 运行
    asyncio.run(main())
