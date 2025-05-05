"""
Language and Conversation Utilities
----------------------------------
This module provides utility functions for managing conversations, formatting, and evaluation in the VLM evaluation pipeline. It supports multi-turn and single-turn conversation flows, model input preparation, and evaluation formatting for both open-source and Azure OpenAI models.

Key Functions:
    - add_message: Add a user or assistant message to a conversation.
    - evaluate_model: Run an evaluation chain on a conversation and extract the score.
    - reduce_conv_turns: Reduce conversation to a minimal context for evaluation.
    - format_conv_for_eval: Format a conversation for evaluation chain input.
    - human/human_img_turn_router: Handle user turns, including image turns, for different models.
    - converse/converse_seeds: Run multi-turn or single-turn conversations with a model.
    - chatbot_gpt/chatbot: Generate model responses for Azure OpenAI or open-source models.
    - skip_conversation_if_already_done: Avoid duplicate processing.
    - init_conversation: Initialize a conversation with a system prompt.

Dependencies:
    - pandas, re, time, torch, azure.identity, VLMEvalPipeline.get_image_turn
"""

import re
import time

import pandas as pd
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "token_provider_here"
)
from VLMEvalPipeline.get_image_turn import (
    get_img_turn_deepseek,
    get_img_turn_gpt4o,
    get_img_turn_llama,
    get_img_turn_llava,
    get_img_turn_phi3,
    get_img_turn_pixtral,
    get_img_turn_qwen,
)


def add_message(conversation, author, text, agent="USER"):
    if author == "USER":
        if isinstance(text, dict):
            message = text
        else:
            message = {"role": "user", "content": text}
    else:
        message = {"role": "assistant", "content": text}
    conversation.append(message)


def evaluate_model(conversation, eval_chain, client):
    eval_conv_str = format_conv_for_eval(conversation)
    final_chain = eval_chain + [{"role": "user", "content": eval_conv_str}]
    # print(final_chain)
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=final_chain,
            max_tokens=400,
            temperature=0.0,
        )
        response_text = response.choices[0].message.content
    except Exception as e:
        time.sleep(10)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=final_chain,
            max_tokens=400,
            temperature=0.0,
        )
        response_text = response.choices[0].message.content

    # Regex function to extract the score between <Q2> and </Q2>
    score = re.search(r"<Q2>(.*?)</Q2>", response_text).group(1)

    return (
        score,
        response_text.replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r"),
        eval_conv_str.replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r"),
    )


def reduce_conv_turns(converstion, is_user=True):
    # Given the conversation list of dictionaries, reduce the conversation to either system message + last 2 user messages
    # or first 2 messages + last 2 user messages if the first message is not a system message
    if is_user:
        last_n = -4
    else:
        last_n = -3
    if converstion[0]["role"] == "system":
        return converstion[:1] + converstion[last_n:]
    else:
        return converstion[:2] + converstion[last_n:]


def format_conv_for_eval(converstion):
    if converstion[0]["role"] == "system":
        valid_conv = converstion[1:]
    else:
        print("System message not found in the conversation")
        valid_conv = converstion[2:]

    role_map = {"user": "USER", "assistant": "AI"}
    conv_str = ""
    for message in valid_conv:
        if isinstance(message["content"], str):
            message["content"] = message["content"].replace("<|image_1|>", " ").strip()
            conv_str += f"<{role_map[message['role']]}>{message['content']}</{role_map[message['role']]}>"
        else:
            content_str = None
            for sub_message in message["content"]:
                if (sub_message["type"] == "text"):
                    content_str = sub_message["text"].strip()
                    conv_str += f"<{role_map[message['role']]}>{content_str}</{role_map[message['role']]}>"
            if not content_str:
                print("Error in formatting the conversation")
                return None
    return conv_str


def human(
    model_name,
    datarow,
    num_turn,
    agent="USER",
):
    user_turn_list = eval(datarow["GenConv"])

    curr_user_turn = user_turn_list[num_turn].strip()

    if "<img_turn>" in curr_user_turn:
        print("Image Turn Detected !!")
        curr_user_turn = curr_user_turn.replace("<img_turn>", "").strip()
        curr_user_turn, img_loaded = human_img_turn_router(
            model_name, datarow, curr_user_turn
        )

    else:
        img_loaded = None

    return curr_user_turn, img_loaded


def human_img_turn_router(model_name, datarow, curr_user_turn):
    if model_name == "gpt-4o":
        curr_user_turn, img_loaded = get_img_turn_gpt4o(datarow, curr_user_turn)
    elif model_name == "Phi-3.5-vision-instruct":
        curr_user_turn, img_loaded = get_img_turn_phi3(datarow, curr_user_turn)
    elif model_name == "Llama-3.2-11B-Vision-Instruct":
        curr_user_turn, img_loaded = get_img_turn_llama(datarow, curr_user_turn)
    elif model_name == "Qwen2-VL-7B-Instruct":
        curr_user_turn, img_loaded = get_img_turn_qwen(datarow, curr_user_turn)
    elif model_name == "Pixtral-12B-2409":
        curr_user_turn, img_loaded = get_img_turn_pixtral(datarow, curr_user_turn)
    return curr_user_turn, img_loaded


def converse(
    model_name,
    conversation,
    model,
    tokenizer,
    datarow,
    device="cuda",
):
    num_turn = 0
    human_response = None
    max_turns = len(eval(datarow["GenConv"]))
    images = []
    while (num_turn < max_turns) and (human_response != "STOP"):
        human_response, img_loaded = human(model_name, datarow, num_turn)
        if img_loaded is not None:
            images.append(img_loaded)
        add_message(conversation, "USER", human_response)
        print(f"Human: {human_response}")
        if isinstance(model, str):
            bot_response = chatbot_gpt(conversation, model, tokenizer)
        else:
            bot_response = chatbot(
                model_name, conversation, model, tokenizer, images, device
            )
        add_message(conversation, "AI", bot_response)
        print(f"Bot: {bot_response}")

        num_turn += 1
    return conversation


def converse_seeds(
    model_name,
    conversation,
    model,
    tokenizer,
    datarow,
    device="cuda",
):
    curr_user_turn = datarow["GeneratedSeed"]
    human_response, img_loaded = human_img_turn_router(
        model_name, datarow, curr_user_turn
    )
    images = []
    if img_loaded is not None:
        images.append(img_loaded)
    add_message(conversation, "USER", human_response)
    print(f"Human: {human_response}")
    if isinstance(model, str):
        bot_response = chatbot_gpt(conversation, model, tokenizer)
    else:
        bot_response = chatbot(
            model_name, conversation, model, tokenizer, images, device
        )
    add_message(conversation, "AI", bot_response)
    print(f"Bot: {bot_response}")

    return conversation


def chatbot_gpt(conversation, model, client):
    response = client.chat.completions.create(
        model=model,
        messages=conversation,
        max_tokens=400,
        temperature=0.25,
        top_p=0.8,
    )
    return response.choices[0].message.content


def processor_tokenize(
    model_name, model, processor, conversation, images, device="cuda"
):
    if model_name == "Phi-3.5-vision-instruct":
        prompt = processor.tokenizer.apply_chat_template(
            conversation,
            add_generation_prompt=True,
            tokenize=False,
        )
        if images != []:
            model_inputs = processor(
                prompt,
                images,
                return_tensors="pt",
            ).to(device)
        else:
            model_inputs = processor(
                prompt,
                return_tensors="pt",
            ).to(device)
    elif model_name == "Qwen2-VL-7B-Instruct":
        prompt = processor.apply_chat_template(
            conversation, tokenize=False, add_generation_prompt=True
        )
        if images != []:
            image_inputs, video_inputs = processor.process_vision_info(conversation)

            model_inputs = processor(
                text=[prompt],
                images=image_inputs,
                padding=True,
                return_tensors="pt",
            ).to(device)
        else:
            model_inputs = processor(
                text=[prompt],
                return_tensors="pt",
            ).to(device)

    elif model_name == "Llama-3.2-11B-Vision-Instruct":
        prompt = processor.apply_chat_template(conversation, add_generation_prompt=True)
        if images != []:
            model_inputs = processor(
                images[0],
                prompt,
                return_tensors="pt",
                add_special_tokens=False,
            ).to(device)
        else:

            model_inputs = processor.tokenizer.apply_chat_template(
                conversation, add_generation_prompt=True, return_tensors="pt"
            ).to(device)

    return prompt, model_inputs


def chatbot(model_name, conversation, model, processor, images, device="cuda"):
    import torch

    if model_name == "Pixtral-12B-2409":
        from vllm.sampling_params import SamplingParams

        sampling_params = SamplingParams(max_tokens=400)
        decoded = (
            model.chat(conversation, sampling_params=sampling_params)[0].outputs[0].text
        )
        return decoded
    prompt, model_inputs = processor_tokenize(
        model_name, model, processor, conversation, images, device
    )

    input_args = {}
    if model_name in [
        "Phi-3.5-vision-instruct",
        "Llama-3.2-11B-Vision-Instruct",
        "Qwen2-VL-7B-Instruct",
    ]:
        input_args["max_new_tokens"] = 400
        input_args["do_sample"] = True
        input_args["eos_token_id"] = processor.tokenizer.eos_token_id

    if model_name == "deepseek-vl2":
        generated_ids = model.language.generate(
            inputs_embeds=model_inputs,
            **input_args,
        )
    elif isinstance(model_inputs, torch.Tensor):
        generated_ids = model.generate(
            model_inputs,
            **input_args,
        )
    else:
        generated_ids = model.generate(
            **model_inputs,
            **input_args,
        )

    if model_name in [
        "Phi-3.5-vision-instruct",
        "Llama-3.2-11B-Vision-Instruct",
    ] and not isinstance(model_inputs, torch.Tensor):
        decoded = processor.batch_decode(
            # remove input tokens from the generated output
            generated_ids[:, model_inputs["input_ids"].shape[1] :],
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
        )[0]
    elif model_name == "Qwen2-VL-7B-Instruct":
        decoded = processor.batch_decode(
            [
                out_ids[len(in_ids) :]
                for in_ids, out_ids in zip(model_inputs.input_ids, generated_ids)
            ],
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
        )[0]
    elif model_name in ["deepseek-vl2"] or isinstance(model_inputs, torch.Tensor):
        decoded = processor.tokenizer.decode(
            generated_ids[0][len(model_inputs[0]) :],
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
        )

    decoded = decoded.replace("<|assistant|>", "").strip()
    decoded = decoded.replace("**Assistant:**", "").strip()
    decoded = decoded.replace("Assistant:", "").strip()
    decoded = decoded.replace("**Response:**", "").strip()
    decoded = decoded.replace("AI:", "").strip()
    return decoded


def skip_conversation_if_already_done(line, conversation_file):
    try:
        conv_df = pd.read_csv(conversation_file, sep="\t", header=None)
    except pd.errors.EmptyDataError:
        return False
    if line["Index"] in conv_df[0].tolist():
        return True
    return False


def init_conversation(model_name):
    system_msg = "You are a helpful assistant. You are here to provide information and answer questions."
    if model_name in [
        "Mistral-7B-Instruct-v0.2",
        "Mixtral-8x7B-Instruct-v0.1",
        "gemma-7b-it",
        "Mistral-7B-Instruct-v0.3",
    ]:
        return [
            {"role": "user", "content": ""},
            {"role": "assistant", "content": system_msg},
        ]
    else:
        return [{"role": "system", "content": system_msg}]
