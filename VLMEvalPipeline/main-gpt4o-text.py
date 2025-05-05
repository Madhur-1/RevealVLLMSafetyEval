import json
import os
import warnings
from multiprocessing.pool import ThreadPool

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI
from tqdm import tqdm

from VLMEvalPipeline.utils_lang import (
    converse,
    init_conversation,
    skip_conversation_if_already_done,
)

warnings.filterwarnings("ignore")
import timeit

import pandas as pd

model_name = "gpt-4o"

print("-" * 50)
print(model_name)
print("-" * 50)

token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "token_provider_here"
)

client = AzureOpenAI(
    api_version="2024-02-01",
    azure_endpoint="endpoint_here",
    azure_ad_token_provider=token_provider,
)
model = model_name
tokenizer = client
device = "cuda"


def main_wrapper(line):
    line = line[1]
    if skip_conversation_if_already_done(line, conversation_file_name):
        return (None, None)
    start_time = timeit.default_timer()
    conversation_init = init_conversation(model_name)
    conversation = converse(
        model_name=model_name,
        conversation=conversation_init,
        model=model,
        tokenizer=tokenizer,
        datarow=line,
        device=device,
    )
    elapsed = timeit.default_timer() - start_time
    print("+++++ Time Elapsed (mins):", round(elapsed / 60, 2))
    return line, conversation


input_dir = "SetCreationPipeline/Data/ConvGenTextPorted/"
conv_dir = "VLMEvalPipeline/ConversationsTextPorted/"
os.makedirs(conv_dir, exist_ok=True)
for dataset_name in os.listdir(input_dir):
    if dataset_name.endswith(".tsv"):
        conversation_file_name = conv_dir + model_name + "_" + dataset_name
        print("-" * 50)
        print(dataset_name)
        print("-" * 50)

        with open(
            conversation_file_name, "a+", encoding="utf-8", errors="surrogatepass"
        ) as conversation_file:
            dataset = pd.read_csv(input_dir + dataset_name, sep="\t")
            dataset.dropna(subset=["GenConv"], inplace=True)
            with ThreadPool(1) as pool:
                for line, conversation in tqdm(
                    pool.imap_unordered(main_wrapper, dataset.iterrows()),
                    total=len(dataset),
                ):
                    if isinstance(line, pd.Series):
                        conversation_file.write(
                            f"{line['Index']}\t{json.dumps(line.to_dict())}\t{json.dumps(conversation)}\n"
                        )
