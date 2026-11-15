"""
No-TTS 部署钩子（纯配置方式，不修改任何源代码）

原理：
1. 用 import hook 在 modeling_minicpmo 模块加载后修补 MiniCPMODuplex
2. 修改 _default_duplex_params 字典（generate_audio=False, ls_mode=implicit）
3. 修补 MiniCPMO.as_duplex 强制传递 generate_audio=False
4. 8-bit 量化：文本质量优于 4-bit

效果：
- 不生成语音 token（generate_audio=False）
- 持续监听模式（ls_mode=implicit）
- TTS 模块不加载（model_type=omni 时不会 init_tts）

显存占用：~12GB（LLM 8-bit ~10GB + 系统开销 ~2GB）
"""
import sys
import torch
from transformers import BitsAndBytesConfig
from transformers.modeling_utils import PreTrainedModel

# 1. 注入 8-bit 量化配置
_orig = PreTrainedModel.from_pretrained.__func__


def _wrapped(cls, *args, **kwargs):
    if "quantization_config" not in kwargs and "torch_dtype" in kwargs:
        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_8bit=True,
            llm_int8_threshold=6.0,
            llm_int8_skip_modules=["tts", "head_code", "emb_code", "emb_text",
                                   "projector", "audio_tokenizer", "Token2wav"],
        )
        kwargs.pop("torch_dtype", None)
        print("[no-tts-hook] 8-bit 量化 for", cls.__name__, flush=True)
    return _orig(cls, *args, **kwargs)


PreTrainedModel.from_pretrained = classmethod(_wrapped)

# 2. 禁用 .cuda() 报错（8-bit 模型已由 bitsandbytes 放到 GPU）
_orig_cuda = PreTrainedModel.cuda


def _safe_cuda(self, *args, **kwargs):
    if (hasattr(self, "is_loaded_in_8bit") and self.is_loaded_in_8bit) or \
       (hasattr(self, "is_loaded_in_4bit") and self.is_loaded_in_4bit):
        return self
    return _orig_cuda(self, *args, **kwargs)


PreTrainedModel.cuda = _safe_cuda


# 3. 延迟修补：在 adapter 的 _load_real_blocking 执行后修补
# 我们修补 AutoModel.from_pretrained，在模型加载后立即修补模块
import importlib

_orig_from_pretrained = PreTrainedModel.from_pretrained.__func__


def _patched_from_pretrained(cls, *args, **kwargs):
    # 调用原始 from_pretrained
    result = _orig_from_pretrained(cls, *args, **kwargs)

    # 加载后立即修补 modeling_minicpmo 模块
    try:
        # 模块名格式：transformers_modules.<repo_name>.modeling_minicpmo
        for name in list(sys.modules.keys()):
            if "modeling_minicpmo" in name:
                module = sys.modules[name]
                if hasattr(module, "MiniCPMODuplex"):
                    # 修改默认参数
                    module.MiniCPMODuplex._default_duplex_params["generate_audio"] = False
                    module.MiniCPMODuplex._default_duplex_params["sliding_window_mode"] = "context"
                    module.MiniCPMODuplex._default_duplex_params["context_previous_max_tokens"] = 500
                    print("[no-tts-hook] 已修改 _default_duplex_params: generate_audio=False, sliding_window_mode=context", flush=True)

                    # 修补 as_duplex 方法
                    orig_as_duplex = module.MiniCPMO.as_duplex

                    def patched_as_duplex(self, device=None, **kwargs):
                        kwargs["generate_audio"] = False
                        kwargs.setdefault("sliding_window_mode", "context")
                        return orig_as_duplex(self, device=device, **kwargs)

                    module.MiniCPMO.as_duplex = patched_as_duplex
                    print("[no-tts-hook] 已修补 MiniCPMO.as_duplex", flush=True)
                    break
    except Exception as e:
        print(f"[no-tts-hook] 修补失败: {e}", flush=True)

    return result


PreTrainedModel.from_pretrained = classmethod(_patched_from_pretrained)

print("[no-tts-hook] 安装完成 (8-bit + from_pretrained hook + 安全 cuda)", flush=True)
