"""
Seed Generator Module
---------------------
This module uses the GPT-4o model via the Azure OpenAI client to generate image seeds
and corresponding metadata for the Image LLM Evaluation Pipeline. The module builds a
chat-completion chain for generating a seed based on an image and processes
the response to extract the generated seed, full API response, and image description.

After processing the results, it sanitizes the data before writing it to a TSV file located in
the SeedGen data directory.

Functions/Workflow Steps:
    - Generate a chat completion response using the GPT-4o model.
    - Parse the response to extract:
        • Generated seed (delimited by <query> and </query> tags)
        • Full API response.
        • Cleaned image description.
    - Sanitize the resulting data and write it to a TSV file.
    
Dependencies:
    - Azure OpenAI client for interacting with the GPT-4o model.
    - pandas for dataframe operations.
    - os for file system operations.
"""

import argparse
import base64
import os
import random
from mimetypes import guess_type

import pandas as pd
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI
from tqdm import tqdm

from SetCreationPipeline.Prompts.seed_gen import seed_gen_chain

token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "token_provider_here"
)

client = AzureOpenAI(
    api_version="2024-02-01",
    azure_endpoint="add_your_endpoint_here",
    azure_ad_token_provider=token_provider,
)


# Function to encode a local image into data URL
def local_image_to_data_url(image_path):
    # Guess the MIME type of the image based on the file extension
    mime_type, _ = guess_type(image_path)
    if mime_type is None:
        mime_type = "application/octet-stream"  # Default MIME type if none is found

    # Read and encode the image file
    with open(image_path, "rb") as image_file:
        base64_encoded_data = base64.b64encode(image_file.read()).decode("utf-8")

    # Construct the data URL
    return f"data:{mime_type};base64,{base64_encoded_data}"


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
    # Load the MiningResults data
    mining_results_df = pd.read_csv(
        f"SetCreationPipeline/Data/MinedImages/{policy_file_name}.tsv", sep="\t"
    )

    seed_gen_pmpt_user = open(
        "./SetCreationPipeline/Prompts/seed_gen_user.md", "r", encoding="utf-8"
    ).read()

    mining_results_df["GeneratedSeed"] = None
    mining_results_df["GenSeedFullResponse"] = None
    mining_results_df["ImageDescription"] = None

    for ind, row in tqdm(mining_results_df.iterrows(), total=len(mining_results_df)):
        image_path = row["MinedImages"]
        data_url = local_image_to_data_url(image_path)
        query_tone = random.choice(
            [
                "positive",
                "neutral",
                "negative",
                "flirty",
                "angry",
                "suspicious",
                "sad",
                "joyous",
                "excited",
                "dismissive",
                "sarcastic",
                "optimistic",
                "pessimistic",
                "cautious",
                "hopeful",
                "anxious",
                "sympathetic",
                "empathetic",
                "ironic",
                "humorous",
                "melancholic",
                "reflective",
                "indifferent",
                "determined",
                "encouraging",
                "frustrated",
                "confident",
                "nostalgic",
                "inquisitive",
                "defensive",
                "apprehensive",
            ]
        )

        seed_gen_pmpt_fmtd = seed_gen_pmpt_user.format(
            HarmName=policy_name,
            Policy=row["SubPolicy"],
            ImageSearchQuery=row["ImageSearchQuery"],
            ImageHeader=row["ImageNames"],
            QueryTone=query_tone,
        )
        final_chain = seed_gen_chain + [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": seed_gen_pmpt_fmtd},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": data_url,
                        },
                    },
                ],
            }
        ]

        response = client.chat.completions.create(
            model="gpt-4o-2",
            messages=final_chain,
            max_tokens=1000,
            temperature=0.25,
        )

        response_text = response.choices[0].message.content

        try:
            generated_seed = (
                response_text.split("<query>")[1].split("</query>")[0].strip()
            )
        except:
            generated_seed = None

        mining_results_df.at[ind, "GeneratedSeed"] = generated_seed
        mining_results_df.at[ind, "GenSeedFullResponse"] = response_text
        mining_results_df.at[ind, "ImageDescription"] = (
            response_text.split("Query:")[0].replace("Image Description:", "").strip()
        )

    mining_results_df = mining_results_df.applymap(
        lambda x: (
            x.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
            if isinstance(x, str)
            else x
        )
    )
    # Write the output to a file
    OUT_DIR = "./SetCreationPipeline/Data/SeedGen/"
    os.makedirs(OUT_DIR, exist_ok=True)
    mining_results_df.to_csv(
        f"{OUT_DIR}{policy_file_name}.tsv",
        sep="\t",
        index=False,
        encoding="utf-8",
    )

    print(f"Done generating seeds for {policy_name}!")
