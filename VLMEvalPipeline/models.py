"""
Model Loader Utilities
----------------------
This module handles the initialization and retrieval of various vision-language models and their processors/tokenizers for the evaluation pipeline. It supports multiple model architectures and provides a unified interface for loading models and processors.

Key Functions:
    - get_model_and_tokenizer: Load the specified model and its processor/tokenizer for evaluation.

Dependencies:
    - transformers, torch, vllm, qwen_vl_utils
"""

from transformers import (
    AutoModelForCausalLM,
    AutoProcessor,
    MllamaForConditionalGeneration,
    Qwen2VLForConditionalGeneration,
)
import torch

from qwen_vl_utils import process_vision_info
from vllm import LLM


def get_model_and_tokenizer(model_name, device="auto", max_memory=None):

    if model_name == "Phi-3.5-vision-instruct":
        model_id = "microsoft/Phi-3.5-vision-instruct"

        # Note: set _attn_implementation='eager' if you don't have flash_attn installed
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            device_map="cuda",
            trust_remote_code=True,
            torch_dtype="auto",
            _attn_implementation="eager",
        )

        # for best performance, use num_crops=4 for multi-frame, num_crops=16 for single-frame.
        processor = AutoProcessor.from_pretrained(
            model_id, trust_remote_code=True, num_crops=16
        )

    elif model_name == "Llama-3.2-11B-Vision-Instruct":
        model_id = "meta-llama/Llama-3.2-11B-Vision-Instruct"

        model = MllamaForConditionalGeneration.from_pretrained(
            model_id,
            torch_dtype=torch.bfloat16,
            device_map="auto",
        )
        processor = AutoProcessor.from_pretrained(model_id)

    elif model_name == "Qwen2-VL-7B-Instruct":
        model = Qwen2VLForConditionalGeneration.from_pretrained(
            "Qwen/Qwen2-VL-7B-Instruct", torch_dtype=torch.float16, device_map="auto"
        )
        processor = AutoProcessor.from_pretrained("Qwen/Qwen2-VL-7B-Instruct")
        processor.process_vision_info = process_vision_info

    elif model_name == "Pixtral-12B-2409":
        model_name = "mistralai/Pixtral-12B-2409"

        model = LLM(
            model=model_name,
            tokenizer_mode="mistral",
            dtype="float16",
            max_model_len=8192,
        )
        processor = None

    return model, processor
