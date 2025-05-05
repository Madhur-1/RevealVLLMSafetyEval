"""
Search Query Generator Module
-----------------------------
This module is responsible for generating image search queries using the GPT-4o model via
the Azure OpenAI service. It processes the model output and extracts queries along with
associated policy names and subpolicies.

The module sets up Azure authentication using [`azure.identity.DefaultAzureCredential`](https://learn.microsoft.com/en-us/python/api/azure-identity/azure.identity.defaultazurecredential)
and initializes an [`openai.AzureOpenAI`](https://pypi.org/project/openai/) client. It also
imports harm policy segments from [`Common.Policy.SubPolicySegments`](Common/Policy/SubPolicySegments.py).

Functions:
    parse_output_queries(out_store, NUM_QUERIES_GENERATED_PER_CALL)
        Parses the output from the GPT-4o model into a structured dictionary containing image
        search queries, policy names, and subpolicy details.
"""

import argparse
import math
import os
import re
import warnings

import pandas as pd
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI
from tqdm import tqdm

from Common.Policy.SubPolicySegments import (
    misinformation_harm,
    sexual_harm,
    violence_harm,
)

# Ignore all warnings
warnings.filterwarnings("ignore")

# Get the token provider for Azure authentication
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "token_provider_here"
)

# Initialize the Azure OpenAI client
client = AzureOpenAI(
    api_version="2024-02-01",
    azure_endpoint="add_your_endpoint_here",
    azure_ad_token_provider=token_provider,
)


def parse_output_queries(out_store, NUM_QUERIES_GENERATED_PER_CALL):
    """
    Parse the output queries from the GPT-4o model.

    This function takes the raw output from the GPT-4o model and extracts the relevant search
    queries, policy names, and subpolicy details. The expected format in the output is a string
    divided by a header marker (e.g., '## 3 Queries').

    Args:
        out_store (list): List of model output rows, where each row is expected to contain a string response.
        NUM_QUERIES_GENERATED_PER_CALL (int): The number of queries generated in a single model call.

    Returns:
        dict: A dictionary with the following keys:
            - "ImageSearchQuery": List of image search queries.
            - "PolicyName": List of corresponding policy names.
            - "SubPolicy": List of subpolicy details.
    """
    # Initialize a dictionary to store the parsed queries
    query_dict = {
        "ImageSearchQuery": [],
        "PolicyName": [],
        "SubPolicy": [],
    }
    # Iterate over each row in the output store
    for row in out_store:
        resp = row[0]
        try:
            # Extract the relevant part of the response
            resp = resp.split(f"## {NUM_QUERIES_GENERATED_PER_CALL} Queries")[1].strip()
        except:
            print(resp)
            continue
        # Split the string by numbers 1. 2. 3. etc using regex
        queries = re.split(r"\d+\. ", resp)
        # Remove empty strings
        queries = [query for query in queries if len(query) > 2]
        # print(queries)
        for query in queries:
            try:
                img_query = query.strip()
            except:
                continue
            if img_query == "":
                continue

            # Remove quotes
            if img_query[0] == '"' and img_query[-1] == '"':
                img_query = img_query[1:-1]

            img_query = img_query.replace("**", "")
            img_query = img_query.replace("```", "").strip()
            img_query = (
                img_query.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
            )

            query_dict["ImageSearchQuery"].append(img_query)
            query_dict["PolicyName"].append(row[1])
            query_dict["SubPolicy"].append(row[2])
    query_df = pd.DataFrame(query_dict)
    # Remove duplicates
    query_df = query_df.drop_duplicates()
    return query_df


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
    parser.add_argument(
        "--num_queries",
        type=int,
        default=300,
        help="The number of search queries to generate",
    )
    topic_to_policy = {
        "Sexual Harm": sexual_harm,
        "Violence Harm": violence_harm,
        "Misinformation Harm": misinformation_harm,
    }
    args = parser.parse_args()
    policy_name = args.policy_name
    num_queries = args.num_queries

    # Main code
    search_query_gen_pmpt = open(
        "./SetCreationPipeline/Prompts/search_query_gen.md", "r", encoding="utf-8"
    ).read()
    # print(search_query_gen_pmpt)
    meta_policy = topic_to_policy[policy_name]
    NUM_QUERIES_GENERATED_PER_CALL = 10

    queries_per_policy = math.ceil(
        (num_queries / len(meta_policy) / NUM_QUERIES_GENERATED_PER_CALL) * 1.2
    )  # 1.2 times the number of queries to account for duplicates

    out_store = []

    for policy in tqdm(meta_policy):
        # Run the search query generation pipeline queries_per_policy times
        for _ in range(queries_per_policy):
            search_query_gen_pmpt_fmtd = search_query_gen_pmpt.format(
                Policy=policy, Topic=policy_name, D1=NUM_QUERIES_GENERATED_PER_CALL
            )

            final_chain = [{"role": "system", "content": search_query_gen_pmpt_fmtd}]
            # print(final_chain)
            response = client.chat.completions.create(
                model="gpt-4o-2",
                messages=final_chain,
                max_tokens=1000,
                temperature=0.25,
            )
            response_text = response.choices[0].message.content
            out_store.append((response_text, policy_name, policy))

    query_df = parse_output_queries(out_store, NUM_QUERIES_GENERATED_PER_CALL)

    # Write the output to a file
    OUT_DIR = "./SetCreationPipeline/Data/ImageSearchQueries/"
    os.makedirs(OUT_DIR, exist_ok=True)
    query_df.to_csv(
        f"{OUT_DIR}{policy_name.replace(' ', '_').lower()}.tsv",
        sep="\t",
        index=False,
        encoding="utf-8",
    )
    print(f"Done generating {len(query_df)} search queries for {policy_name}")
