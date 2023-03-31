# ------------------------------- env, constants -------------------------------

from get_blocks import get_top_k_blocks, Block

from typing import List, Dict
import openai
import os
import tiktoken

# OpenAI models
EMBEDDING_MODEL = "text-embedding-ada-002"
COMPLETIONS_MODEL = "gpt-3.5-turbo"
MODERATION_ENDPOINT = "https://api.openai.com/v1/moderations"

# OpenAI parameters
LEN_EMBEDDINGS = 1536
MAX_TOKEN_LEN_PROMPT = 4095 # This may be 8191, unsure.
TRUNCATE_CONTEXT = 2000

# --------------------------------- prompt code --------------------------------

def limit_tokens(text: str, max_tokens: int, encoding_name: str = "cl100k_base") -> str:
    encoding = tiktoken.get_encoding(encoding_name)
    tokens = encoding.encode(text)[:max_tokens]
    return encoding.decode(tokens)

def construct_prompt(query: str, history: List[Dict[str, str]], context: List[Block]) -> List[Dict[str, str]]:
    # History takes the format: history=[
    #     {"role": "system", "content": "You are a helpful assistant."},
    #     {"role": "user", "content": "Who won the world series in 2020?"},
    #     {"role": "assistant", "content": "The Los Angeles Dodgers won the World Series in 2020."},
    #     {"role": "user", "content": "Where was it played?"}
    #     {"role": "assistant", "content": "Los Angeles, California."}
    # ]

    # Initialize prompt with system description
    prompt = [{"role": "system", "content": "You are a helpful assistant knowledgeable about AI Alignment and Safety."}]

    # Add previous dialogue
    prompt.extend(history) 

    instruction_prompt = \
        "Please give a clear and coherent answer to my question (written after \"Q:\") " \
        "using the following sources. Each source is labeled with a letter. Feel free to " \
        "use the sources in any order, and try to use multiple sources in your answer."

    prompt.append({"role": "user", "content": instruction_prompt})
    
    # Add context from top-k blocks
    context_prompt = ""
    for i, block in enumerate(context):
        context_prompt += f"[{chr(ord('a') + i)}] {block.title} - {block.author} - {block.date}\n\n{block.text}\n\n\n"

    context_prompt = context_prompt[:-2] # trim last two newlines

    context_prompt = limit_tokens(context_prompt, TRUNCATE_CONTEXT) # truncate to about 2k tokens

    prompt.append({"role": "user", "content": f"{context_prompt}"})
    
    # Add user query
    question_prompt = "In your answer, please cite any claims you make back to each source " \
                      "using the format: [a], [b], etc. If you use multiple sources to make a claim " \
                      "cite all of them. For example: \"AGI is concerning [c, d, e].\""

    question_prompt += "\n\n\nQ: " + query

    prompt.append({"role": "user", "content": question_prompt})
    
    return prompt




# ------------------------------------------------------------------------------

        
def normal_completion(prompt: List[Dict[str, str]]) -> str:
    try:
        return openai.ChatCompletion.create(
            model=COMPLETIONS_MODEL,
            messages=prompt
        )["choices"][0]["message"]["content"]
    except Exception as e:
        print(e)
        return "I'm sorry, I failed to process your query. Please try again. If the problem persists, please contact the administrator."

def talk_to_robot(query: str, history: List[Dict[str, str]] = [], k: int = 10):

    # 1. Find the most relevant blocks from the Alignment Research Dataset
    top_k_blocks: List[Block] = get_top_k_blocks(query, k)
    
    # 2. Generate a prompt for the ChatCompletions API
    prompt: List[Dict[str, str]] = construct_prompt(query, history, top_k_blocks)
    
    # 3. Answer the user query
    return (normal_completion(prompt), top_k_blocks)
