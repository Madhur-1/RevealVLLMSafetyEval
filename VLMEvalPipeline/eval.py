"""
Evaluation Pipeline Module
--------------------------
This module handles the evaluation of generated conversations by interfacing with
Azure OpenAI and executing specific evaluation chains based on harm categories.
It sets up necessary configurations, initializes required directories and clients, 
and defines a main wrapper function to process conversation data into evaluations.

Workflow:
    - Setup environment by importing necessary libraries and suppressing warnings.
    - Create directories for evaluation outputs if they don't exist.
    - Authenticate with Azure via DefaultAzureCredential and get_bearer_token_provider.
    - Initialize an AzureOpenAI client with specified API parameters.
    - Process input conversation lines with a provided evaluation chain to generate evaluations.

Dependencies:
    - json, os, time, timeit, warnings, and multiprocessing for system and parallel operations.
    - azure.identity for Azure authentication.
    - openai for interacting with Azure OpenAI.
    - tqdm for progress visualization.
    - VLMEvalPipeline.EvalChains for harm-specific evaluation chains.
    - VLMEvalPipeline.utils_lang for language utility functions.
"""

import json
import os
import time
import timeit
import warnings
from multiprocessing.pool import ThreadPool

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI
from tqdm import tqdm

from VLMEvalPipeline.EvalChains.Misinformation import misinformation_chain
from VLMEvalPipeline.EvalChains.Refusal import refusal_chain
from VLMEvalPipeline.EvalChains.SexualHarm import sexualharm_chain
from VLMEvalPipeline.EvalChains.Violence import violence_chain
from VLMEvalPipeline.utils_lang import *

warnings.filterwarnings("ignore")

conv_dir = "VLMEvalPipeline/ConversationsTextPorted/"
eval_dir = "VLMEvalPipeline/EvalsTextPorted/"
os.makedirs(eval_dir, exist_ok=True)

token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "token_provider_here"
)

client = AzureOpenAI(
    api_version="2024-02-01",
    azure_endpoint="endpoint_here",
    azure_ad_token_provider=token_provider,
)


def main_wrapper(line, eval_chain):
    # print(line)
    ind, query, conv = line.split("\t")
    query = json.loads(query)
    conv = json.loads(conv)
    # print(ind, query, conv)
    # print("Eval Chain:", eval_chain)
    if skip_conversation_if_already_done(query, eval_file_name):
        return (None, None, None, None, None, None, None)

    start_time = timeit.default_timer()
    score, response, eval_conv_str = evaluate_model(conv, eval_chain, client)
    # DO the same for refusal
    refusal_score, refusal_response, _ = evaluate_model(conv, refusal_chain, client)
    elapsed = timeit.default_timer() - start_time
    print("+++++ Time Elapsed (secs):", round(elapsed, 2))
    print(ind, score, response)
    if int(ind) % 1 == 0:
        # Add one second delay
        time.sleep(1)
    return (
        ind,
        eval_conv_str,
        score,
        response,
        refusal_score,
        refusal_response,
        query,
    )


eval_chains = {
    "misinformation": misinformation_chain,
    "sexual": sexualharm_chain,
    "violence": violence_chain,
}

for dataset_name in os.listdir(conv_dir):
    if dataset_name.endswith(".tsv"):
        eval_file_name = eval_dir + dataset_name
        print("-" * 50)
        print(dataset_name)
        print("-" * 50)

        harm_name = dataset_name.split("_")[1].split(".")[0]
        eval_chain = eval_chains[harm_name]

        with open(
            eval_file_name, "a+", encoding="utf-8", errors="surrogatepass"
        ) as eval_file:

            with open(conv_dir + dataset_name, encoding="utf-8") as f:
                lines = f.readlines()
                # print(lines[0])
                # print(main_wrapper(lines[0], eval_prompt))
                with ThreadPool(5) as pool:
                    for (
                        ind,
                        eval_conv_str,
                        score,
                        response,
                        refusal_score,
                        refusal_response,
                        query,
                    ) in tqdm(
                        pool.imap_unordered(
                            lambda line: main_wrapper(line, eval_chain), lines
                        ),
                        total=len(lines),
                    ):
                        if ind is not None:
                            eval_file.write(
                                f"{ind}\t{score}\t{response}\t{refusal_score}\t{refusal_response}\t{harm_name}\t{eval_conv_str}\t{query}\n"
                            )
