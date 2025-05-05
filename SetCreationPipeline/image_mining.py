"""
Image Mining Module
-------------------
This module handles Bing Image Search API operations. It is responsible for fetching and
filtering images based on search queries. This module is a part of the Image LLM Evaluation
Pipeline.

The module reads the Bing Search V7 subscription key and endpoint from environment variables
to make authenticated API calls to Bing's image search service. It provides functionality to
fetch images (e.g., thumbnails) based on the specified query and additional parameters.

Functions:
    call_bing_search_api(ind: int, query: str, policy_file_name: str, num_images_per_query: int = 1)
        Makes an API call to the Bing Image Search API and extracts image data from the response.
"""

# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

# -*- coding: utf-8 -*-

import argparse
import os
from io import BytesIO

import pandas as pd
import requests
from PIL import Image

"""
This sample makes a call to the Bing Web Search API with a query and returns relevant web search.
Documentation: https://docs.microsoft.com/en-us/bing/search-apis/bing-web-search/overview
"""


# # Add your Bing Search V7 subscription key and endpoint to your environment variables.
subscription_key = os.environ["BING_SEARCH_V7_SUBSCRIPTION_KEY"]
endpoint = os.environ["BING_SEARCH_V7_ENDPOINT"]


def call_bing_search_api(
    ind: int, query: str, policy_file_name: str, num_images_per_query: int = 1
):
    """
    Call the Bing Image Search API and retrieve a list of image thumbnails and names.

    Args:
        ind (int): An index used as an identifier for this API call.
        query (str): The search query string for Bing Image Search.
        policy_file_name (str): The name of the file containing policy details.
        num_images_per_query (int, optional): Number of images to fetch per query. Defaults to 1.

    Returns:
        tuple: A tuple containing two lists:
            - image_list: List of image thumbnail URLs.
            - name_list: List of image names or titles.

    Raises:
        requests.HTTPError: If the API response contains an HTTP error status code.
    """
    mkt = "en-IN"

    params = {
        "q": query,
        # "license": "public",
        # "imageType": "photo",
        "safeSearch": "Off",
        "isFamilyFriendly": "false",
        "mkt": mkt,
        # "cc": cc,
        "count": num_images_per_query,
    }
    headers = {
        "Ocp-Apim-Subscription-Key": subscription_key,
        "Pragma": "no-cache",
    }
    try:
        response = requests.get(endpoint, headers=headers, params=params)

        response.raise_for_status()
        response = response.json()

        thumbnail_urls = [img["thumbnailUrl"] for img in response["value"]]
        thumbnail_names = [img["name"] for img in response["value"]]

        image_list = []
        name_list = []
        # Get the first num_images_per_query images
        for i in range(num_images_per_query):
            try:
                image_data = requests.get(thumbnail_urls[i])
                image_data.raise_for_status()
                image = Image.open(BytesIO(image_data.content))
            except:
                try:
                    token_id = thumbnail_urls[i].split("th?id=")[1].split("&")[0]
                    new_url = f"https://th.bing.com/th/id/{token_id}"
                    image_data = requests.get(new_url)
                    image = Image.open(BytesIO(image_data.content))
                except:
                    print("Error in fetching image")
                    continue

            # Save the image
            image_file_name = f"{ind}_{i}.jpg"
            image_save_dir = (
                f"SetCreationPipeline/Data/MinedImages/{policy_file_name}_images"
            )
            os.makedirs(image_save_dir, exist_ok=True)
            image_save_path = f"{image_save_dir}/{image_file_name}"
            image.save(image_save_path)
            image_list.append(image_save_path)
            name_list.append(thumbnail_names[i])
        return image_list, name_list

    except Exception as ex:
        print(f"Coudn't fetch images for query: {query}, Exception {ex}")
        return None, None


if __name__ == "__main__":
    """
    Main entry point for the image_mining module when run as a script.
    This block parses command-line arguments and triggers the image search functionality.
    """

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
    # Load the ImageSearchQuery data
    query_df = pd.read_csv(
        f"SetCreationPipeline/Data/ImageSearchQueries/{policy_file_name}.tsv",
        sep="\t",
    )

    query_df["MinedImages"] = None
    query_df["Index"] = query_df.index
    # Call the Bing Search API for each query
    for ind, row in query_df.iterrows():
        query = row["ImageSearchQuery"]
        mined_images, image_names = call_bing_search_api(
            row["Index"], query, policy_file_name, num_images_per_query=1
        )

        if mined_images:
            # Add the mined images to the dataframe
            query_df.at[ind, "MinedImages"] = mined_images[0]
            query_df.at[ind, "ImageNames"] = image_names[0]

    # Remove null rows
    query_df = query_df.dropna()

    # Save the dataframe
    save_dir = "SetCreationPipeline/Data/MinedImages"
    os.makedirs(save_dir, exist_ok=True)
    query_df.to_csv(
        f"{save_dir}/{policy_to_filename[policy_name]}.tsv", sep="\t", index=False
    )
