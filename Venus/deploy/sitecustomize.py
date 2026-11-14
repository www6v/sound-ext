"""
Startup hook: inject 4-bit NF4 quantization into all model from_pretrained calls.
Place the deploy/ directory in PYTHONPATH before starting the demo.
Reduces VRAM from ~21GB to ~8GB so TTS (~2GB) fits on RTX 3090 (24GB).
"""
import torch
from transformers import BitsAndBytesConfig
from transformers.modeling_utils import PreTrainedModel

_orig = PreTrainedModel.from_pretrained.__func__


def _wrapped(cls, *args, **kwargs):
    if "quantization_config" not in kwargs and "torch_dtype" in kwargs:
        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_quant_type="fp4",
            bnb_4bit_use_double_quant=False,
            llm_int8_skip_modules=["tts", "head_code", "emb_code", "emb_text",
                                   "projector", "audio_tokenizer", "Token2wav"],
        )
        kwargs.pop("torch_dtype", None)
        print("[quantize-hook] 4-bit FP4 for", cls.__name__, flush=True)
    return _orig(cls, *args, **kwargs)


PreTrainedModel.from_pretrained = classmethod(_wrapped)

# Patch .cuda() to be a no-op for quantized models
# (bitsandbytes already places the model on GPU; calling .cuda() raises an error)
_orig_cuda = PreTrainedModel.cuda


def _safe_cuda(self, *args, **kwargs):
    if (hasattr(self, "is_loaded_in_8bit") and self.is_loaded_in_8bit) or \
       (hasattr(self, "is_loaded_in_4bit") and self.is_loaded_in_4bit):
        return self
    return _orig_cuda(self, *args, **kwargs)


PreTrainedModel.cuda = _safe_cuda

print("[quantize-hook] Installed (4-bit NF4 + safe cuda)", flush=True)
