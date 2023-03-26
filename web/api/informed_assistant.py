# ---------------------------------- web code ----------------------------------

import json

from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):

    # post request = calculate factorial of passed number
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data)

        results = {}

        for i, link in enumerate(get_top_k_blocks(data['query'])):
            results[i] = json.dumps(link.__dict__)

        self.wfile.write(json.dumps(results).encode('utf-8'))


# -------------------------------- non-web-code --------------------------------
import time
import os
import openai

# OpenAI API key
try:
    import config
    OPENAI_API_KEY = config.OPENAI_API_KEY
except ImportError:
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
openai.api_key = OPENAI_API_KEY

# OpenAI models
EMBEDDING_MODEL = "text-embedding-ada-002"
COMPLETIONS_MODEL = "gpt-3.5-turbo"

# OpenAI parameters
LEN_EMBEDDINGS = 1536
MAX_LEN_PROMPT = 4095 # This may be 8191, unsure.

# Paths
from pathlib import Path
project_path = Path(__file__).parent.parent.parent
PATH_TO_DATA = project_path / "web" / "api" / "data" / "alignment_texts.jsonl" # Path to the dataset .jsonl file.
PATH_TO_EMBEDDINGS = project_path / "web" / "api" / "data" / "embeddings.npy" # Path to the saved embeddings (.npy) file.
PATH_TO_DATASET = project_path / "web" / "api" / "data" / "dataset.pkl" # Path to the saved dataset (.pkl) file, containing the dataset class object.

import numpy as np
import requests
from typing import List, Dict
import pickle
import openai
import tiktoken

import config
from semantic_search import get_top_k_blocks


class Dataset:
    pass

class Block:
    def __init__(self, title: str, author: str, date: str, url: str, tags: str, text: str):
        self.title = title
        self.author = author
        self.date = date
        self.url = url
        self.tags = tags
        self.text = text


MODERATION_ENDPOINT = "https://api.openai.com/v1/moderations"
def moderate_query(query: str) -> List[str]:
    """This function uses the OpenAI Moderation API to check if a query contains any offensive language.

    Args:
        query (str): The query to be checked.

    Raises:
        Exception: If the API call fails.

    Returns:
        List[str]: A list of categories that the query was flagged for.
    """
    
    headers = {"Content-Type": "application/json","Authorization": f"Bearer {OPENAI_API_KEY}"}

    data = {"input": query}

    response = requests.post(MODERATION_ENDPOINT, headers=headers, data=json.dumps(data))
    flagged_categories = []

    if response.status_code == 200:
        moderation_results = response.json()
        flagged = moderation_results['results'][0]['flagged']
        categories = moderation_results['results'][0]['categories']

        if flagged:
            for category, is_flagged in categories.items():
                if is_flagged:
                    flagged_categories.append(category)
    else:
        raise Exception(f"Error: {response.status_code} {response.reason}")

    return flagged_categories

def limit_tokens(text: str, max_tokens: int, encoding_name: str = "cl100k_base") -> str:
    encoding = tiktoken.get_encoding(encoding_name)
    tokens = encoding.encode(text)[:max_tokens]
    return encoding.decode(tokens)

def generate_prompt(user_query: str, previous_dialogue: List[Dict[str, str]] = [], blocks: List[Block] = [], mode: str = "standard") -> List[Dict[str, str]]:
    """
    This function generates a prompt in messages format for the OpenAI ChatCompletions API.
    First, it picks a system description using the mode.
    Second, it adds the previous dialogue to the prompt.
    Third, it adds an instruction to the prompt based on the mode.
    Fourth, it adds the context from the top-k most relevant blocks from the Alignment Research Dataset to the prompt.
    Fifth, it adds the user query to the prompt.

    Messages take the following format:
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Who won the world series in 2020?"},
        {"role": "assistant", "content": "The Los Angeles Dodgers won the World Series in 2020."},
        {"role": "user", "content": "Where was it played?"}
    ]
    
    Args:
        user_query (str): The user query.
        previous_dialogue (List[Dict[str, str]]): The previous dialogue. Defaults to [].
        blocks (List[Block]): The top-k most relevant blocks from the Alignment Research Dataset. Defaults to [].
        mode (str): The mode of the assistant. Can be "standard", etc. Defaults to "standard".

    Returns:
        List[Dict[str, str]]: The prompt in messages format.
    """
    # Initialize prompt
    prompt = []
    
    # Generate system description
    if mode == "standard":
        prompt.append({"role": "system", "content": "You are a helpful assistant knowledgeable about AI Alignment and Safety."})
    # elif mode == "other":
    else:
        raise Exception(f"Invalid mode: {mode}")

    # Add previous dialogue
    for message in previous_dialogue:
        prompt.append(message)
    
    # Add instruction
    if mode == "standard":
        instruction_prompt = "Please answer my question (after the Q:) using the provided context."
        prompt.append({"role": "assistant", "content": instruction_prompt})
    # elif mode == "other":
    else:
        raise Exception(f"Invalid mode: {mode}")
    
    # Add context from top-k blocks
    if blocks is None:
        return "Context missing."
    context_prompt = "Context:\n\n"
    for i, block in enumerate(blocks):
        context_prompt += f"[{i}] {block.text}\n\n"
    context_prompt = context_prompt[:-2]
    context_prompt = limit_tokens(context_prompt, 2000)
    prompt.append({"role": "user", "content": f"{context_prompt}"})
    
    # Add user query
    prompt.append({"role": "user", "content": f"Q: {user_query}"})
    
    return prompt
        
def normal_completion(prompt: List[Dict[str, str]]) -> str:
    """
    This function uses the OpenAI ChatCompletions API to answer a user query.

    Args:
        messages (Dict[str, str]): A dictionary containing the system prompt and user prompt, in addition to any previous dialogue.

    Returns:
        str: The answer generated by the API.
        
    Raises:
        Exception: If the API call fails.
    """
    try:
        return openai.ChatCompletion.create(
            model=COMPLETIONS_MODEL,
            messages=prompt
        )["choices"][0]["message"]["content"]
    except Exception as e:
        print(e)
        return "I'm sorry, I failed to process your query. Please try again. If the problem persists, please contact the administrator."

async def stream_completion(prompt: List[Dict[str, str]], stream_delay: float = 0.1) -> str:
    """
    This function uses the OpenAI ChatCompletions API to answer a user query, streaming the response.

    Args:
        messages (Dict[str, str]): A dictionary containing the system prompt and user prompt, in addition to any previous dialogue.

    Returns:
        str: The answer generated by the API.
        
    Raises:
        Exception: If the API call fails.
    """
    try:
        async for part in await openai.ChatCompletion.acreate(
            model=COMPLETIONS_MODEL,
            messages=prompt,
            stream=True
        ):
            finish_reason = part["choices"][0]["finish_reason"]
            if "content" in part["choices"][0]["delta"]:
                content = part["choices"][0]["delta"]["content"]
                yield content
            elif finish_reason:
                print(f"Stream finished: {finish_reason}")
                break
    except Exception as e:
        print(e)
        response = "I'm sorry, I failed to process your query. Please try again. If the problem persists, please contact the administrator."
        for word in response.split():
            time.sleep(stream_delay)
            yield f"{word} "

def informed_assistant(user_query: str, previous_dialogue: List[Dict[str, str]] = [], k: str = 10, mode: str = "standard", HyDE: bool = False, stream: bool = True, stream_delay: float = 0.1) -> str:
    """
    This function uses the OpenAI ChatCompletions API to answer a user query.
    It first checks if the query is offensive, and if so, raises an exception.
    Then, it finds the top-k most relevant blocks from the Alignment Research Dataset and uses them as context for the ChatCompletions API.
    It uses the blocks to generate a prompt for the ChatCompletions API.
    Finally, it uses the ChatCompletions API to generate an answer to the user query.

    Args:
        user_query (str): The user query.
        previous_dialogue (List[Dict[str, str]]): The previous dialogue. Defaults to [].
        k (str): The number of blocks to use as context.
        mode (str): The mode to use for the ChatCompletions API. Defaults to "standard".
        HyDE (bool): Whether to use the HyDE technique for semantic search. This makes search slower, but better. Defaults to False.
        stream (bool): Whether to stream the results from the ChatCompletions API. Defaults to True.
        stream_delay (float): The delay between each word in the streamed response when streaming a hard-coded response. Defaults to 0.1.

    Returns:
        str: The answer to the user query.
    
    Raises:
        Exception: If the query is offensive.
    """
    # 1. Check if the query is offensive
    flagged_categories: List[str] = moderate_query(user_query)
    if len(flagged_categories) > 0:
        response = f"Your query contains offensive language. Please try again."
        if stream:
            for word in response.split():
                time.sleep(stream_delay)
                yield f"{word} "
        else:
            return response

    # 2. Find the top-k most relevant blocks from the Alignment Research Dataset
    top_k_blocks: List[Block] = get_top_k_blocks(user_query, k, HyDE)
    
    # 3. Generate a prompt for the ChatCompletions API
    prompt: List[Dict[str, str]] = generate_prompt(user_query, previous_dialogue, top_k_blocks, mode)
    
    # 4. Use the top-k most relevant blocks as context for the ChatCompletions API, and generate an answer to the user query
    if stream:
        return stream_completion(prompt)
    else:
        return normal_completion(prompt)


if __name__ == "__main__":
    # Test the question answering function
    user_query = "Within the area of mitigating AI risk, there are several broad classes of action being taken. What does Technical safety research focus on?"
    previous_dialogue = [
        {"role": "assistant", "content": "Hi! I know all about AI Alignment. Ask me a question!"},
    ]
    k = 10
    mode = "standard"
    HyDE = True
    stream = False # Doesn't quite work yet
    
    import asyncio
    chat_completion = asyncio.run(informed_assistant(user_query, previous_dialogue, k, mode, HyDE, stream))
    print(chat_completion)
        
    # if stream:
    #     for part in informed_assistant(user_query, previous_dialogue, k, mode, HyDE, stream):
    #         print(part, end="")
    # else:
    #     print(informed_assistant(user_query, previous_dialogue, k, mode, HyDE, stream))