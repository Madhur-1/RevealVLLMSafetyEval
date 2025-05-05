"""
Single-Turn Open Source Evaluation Pipeline
-------------------------------------------
This script runs single-turn conversation evaluation using open-source models for the VLMEval project.
It loads the model, processes the seed datasets, and generates single-turn conversations for evaluation.

Workflow:
    - Load open-source model and tokenizer.
    - Load seed datasets for each harm policy.
    - Generate and evaluate single-turn conversations.
    - Save results to the appropriate output directory.

Dependencies:
    - os, json, timeit, warnings for system-level operations.
    - pandas for data processing.
    - tqdm for progress visualization.
    - VLMEvalPipeline.models for model and tokenizer retrieval.
    - VLMEvalPipeline.utils_lang for conversation management utilities.
"""

import os

import gc
import json
import timeit
import warnings

import pandas as pd
import torch
from tqdm import tqdm

from VLMEvalPipeline.models import get_model_and_tokenizer
from VLMEvalPipeline.utils_lang import (
    converse_seeds,
    init_conversation,
    skip_conversation_if_already_done,
)

warnings.filterwarnings("ignore")

device = "cuda"

model_list = [
    "Pixtral-12B-2409",
    "Qwen2-VL-7B-Instruct",
    "Llama-3.2-11B-Vision-Instruct",
    "Phi-3.5-vision-instruct",
]


def main_wrapper(line):
    # print(conversation_file_name)
    line = line[1]
    if skip_conversation_if_already_done(line, conversation_file_name):
        return (None, None)

    start_time = timeit.default_timer()
    conversation_init = init_conversation(model_name)
    # code you want to evaluate
    conversation = converse_seeds(
        model_name=model_name,
        conversation=conversation_init,
        model=model,
        tokenizer=processor,
        datarow=line,
        device=device,
    )
    elapsed = timeit.default_timer() - start_time
    print("+++++ Time Elapsed (mins):", round(elapsed / 60, 2))
    return line, conversation


input_dir = "SetCreationPipeline/Data/ConvGen/"
conv_dir = "VLMEvalPipeline/ConversationsSeeds/"
os.makedirs(conv_dir, exist_ok=True)

for model_name in model_list:
    print("-" * 50)
    print(model_name)
    print("-" * 50)
    model, processor = get_model_and_tokenizer(model_name, "auto")
    for dataset_name in os.listdir(input_dir):
        if dataset_name.endswith(".tsv"):  # and dataset_name.startswith("van-ch"):
            conversation_file_name = conv_dir + model_name + "_" + dataset_name
            print("-" * 50)
            print(dataset_name)
            print("-" * 50)
            with open(
                conversation_file_name, "a+", encoding="utf-8", errors="surrogatepass"
            ) as conversation_file:
                dataset = pd.read_csv(input_dir + dataset_name, sep="\t")
                dataset.dropna(subset=["GenConv"], inplace=True)
                # print(lines)
                for line in tqdm(dataset.iterrows(), total=len(dataset)):
                    line, conversation = main_wrapper(line)
                    if isinstance(line, pd.Series):
                        conversation_file.write(
                            f"{line['Index']}\t{json.dumps(line.to_dict())}\t{json.dumps(conversation)}\n"
                        )

    del model, processor
    torch.cuda.empty_cache()
    gc.collect()
