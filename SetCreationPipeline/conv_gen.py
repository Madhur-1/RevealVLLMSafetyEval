"""
Conversation Generator Module
-----------------------------
This module sets up a conversation generation pipeline that aids in producing dialogues 
(or conversations) related to different harm policies using the Azure OpenAI client.

The module performs the following tasks:
    - Authenticates with Azure using DefaultAzureCredential.
    - Initializes an AzureOpenAI client with the necessary API version, endpoint, and token provider.
    - Processes command-line arguments to determine which harm policy to generate conversations for.
    - Maps the specified policy name to a corresponding filename for subsequent processing.

Usage:
    Run the script with the --policy_name argument to specify the policy, for example:
        python conv_gen.py --policy_name "Sexual Harm"

Dependencies:
    - argparse for command-line argument parsing.
    - os and random for miscellaneous operations.
    - pandas for data processing.
    - azure.identity for Azure authentication.
    - openai for interacting with the Azure OpenAI client.
    - tqdm for progress tracking.
"""

import argparse
import os
import random

import pandas as pd
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI
from tqdm import tqdm

token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "token_provider_here"
)

client = AzureOpenAI(
    api_version="2024-02-01",
    azure_endpoint="add_your_endpoint_here",
    azure_ad_token_provider=token_provider,
)

if __name__ == "__main__":
    # Get the arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--policy_name",
        type=str,
        default="Sexual Harm",
        help="The policy to generate search queries for",
        choices=["Sexual Harm", "Violence Harm", "Misinformation Harm"],
    )
    args = parser.parse_args()
    policy_name = args.policy_name

    policy_to_filename = {
        "Sexual Harm": "sexual_harm",
        "Violence Harm": "violence_harm",
        "Misinformation Harm": "misinformation_harm",
    }

    policy_file_name = policy_to_filename[policy_name]
    # Load the Seed Generation data
    seed_df = pd.read_csv(
        f"SetCreationPipeline/Data/SeedGen/{policy_file_name}.tsv",
        sep="\t",
    )
    seed_df.dropna(subset=["GeneratedSeed"], inplace=True)
    seed_df["NumTurns"] = random.choices([5, 6, 7], k=seed_df.shape[0])

    conv_gen_pmpt_system = open(
        "./SetCreationPipeline/Prompts/conv_gen_system.md", "r", encoding="utf-8"
    ).read()
    conv_gen_pmpt_user = open(
        "./SetCreationPipeline/Prompts/conv_gen_user.md", "r", encoding="utf-8"
    ).read()

    seed_df["GenConv"] = None

    for ind, row in tqdm(seed_df.iterrows(), total=seed_df.shape[0]):
        conv_gen_pmpt_fmtd = conv_gen_pmpt_user.format(
            Seed=row["GeneratedSeed"],
            NumTurns=row["NumTurns"],
            Policy=row["SubPolicy"],
            HarmName=policy_name,
            ImageDesc=row["ImageDescription"],
        )

        final_chain = [
            {"role": "system", "content": conv_gen_pmpt_system},
            {"role": "user", "content": conv_gen_pmpt_fmtd},
        ]
        response = client.chat.completions.create(
            model="gpt-4o-2",
            messages=final_chain,
            max_tokens=1000,
            temperature=0.25,
        )
        response_text = response.choices[0].message.content

        try:
            generated_conv = eval(response_text.strip())
        except:
            print(f"Error in response: {response_text}")
            generated_conv = None

        seed_df.at[ind, "GenConv"] = generated_conv

    seed_df = seed_df.applymap(
        lambda x: (
            x.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
            if isinstance(x, str)
            else x
        )
    )

    # Write the output to a file
    OUT_DIR = "./SetCreationPipeline/Data/ConvGen/"
    os.makedirs(OUT_DIR, exist_ok=True)
    seed_df.to_csv(
        f"{OUT_DIR}{policy_file_name}.tsv",
        sep="\t",
        index=False,
        encoding="utf-8",
    )

    print(f"Conversation Generation for {policy_name} policy completed.")
