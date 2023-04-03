# ------------------------------- env, constants -------------------------------

from get_blocks import get_top_k_blocks, Block

from typing import List, Dict
import openai
import os
import tiktoken

# OpenAI models
EMBEDDING_MODEL = "text-embedding-ada-002"
COMPLETIONS_MODEL = "gpt-3.5-turbo"
# COMPLETIONS_MODEL = "gpt-4"

# parameters

# NOTE: All this is approximate, there's bits I'm intentionally not counting. Leave a buffer beyond what you might expect.
NUM_TOKENS = 8191 if COMPLETIONS_MODEL == 'gpt-4' else 4095
PROMPT_FRACTION = 0.25 # the (approximate) fraction of num_tokens to use for non-context prompt text before truncating
CONTEXT_FRACTION = 0.45 # the (approximate) fraction of num_tokens to use for context text before truncating

ENCODER = tiktoken.get_encoding("cl100k_base")

# --------------------------------- prompt code --------------------------------



# limit a string to a certain number of tokens
def cap(text: str, max_tokens: int) -> str:

    if max_tokens <= 0: return "..."

    encoded_text = ENCODER.encode(text)

    if len(encoded_text) <= max_tokens: return text
    else: return ENCODER.decode(encoded_text[:max_tokens]) + " ..."




def construct_prompt(query: str, history: List[Dict[str, str]], context: List[Block]) -> List[Dict[str, str]]:

    # History takes the format: history=[
    #     {"role": "user", "content": "Who won the world series in 2020?"},
    #     {"role": "assistant", "content": "The Los Angeles Dodgers won the World Series in 2020."},
    #     {"role": "user", "content": "Where was it played?"}
    #     {"role": "assistant", "content": "Los Angeles, California."}
    # ]

    token_count = 0
    prompt = []

    system_prompt = "You are a helpful assistant knowledgeable about AI Alignment and Saftey."
    token_count += len(ENCODER.encode(system_prompt))
    prompt.append({"role": "system", "content": system_prompt})

    # Get past user queries
    past_user_queries = [message["content"] for message in history if message["role"] == "user"][-5 * 2:] # get the last 5 user queries
    if len(past_user_queries) > 0:
        for i, q in enumerate(past_user_queries):
            prompt.append({"role": "user", "content": "Q: " + q})
            token_count += len(ENCODER.encode("Q: " + q))

            # for all but the last query, just add the system message mentioning that there has been a response.
            if i < len(past_user_queries) - 1:
                response = "the assistant's response has been left out for brevity."
                prompt.append({"role": "system", "content": response})
                token_count += len(ENCODER.encode(response))

    # Add the response to the latest query, if there was one. Possibly truncate it.
    if len(history) > 0 and history[-1]["role"] == "assistant":
        last_response = cap(history[-1]["content"], int(NUM_TOKENS * PROMPT_FRACTION) - token_count)
        prompt.append({"role": "assistant", "content": last_response})
        token_count += len(ENCODER.encode(last_response))








    # Instruction prompt
    main_prompt = \
        "Please give a clear and coherent answer to my question (written after \"Q:\") " \
        "using the following sources. Each source is labeled with a letter. Feel free to " \
        "use the sources in any order, and try to use multiple sources in your answer.\n\n"

    token_count = len(ENCODER.encode(main_prompt))

    # Context from top-k blocks
    for i, block in enumerate(context):
        block_str = f"[{chr(ord('a') + i)}] {block.title} - {block.author} - {block.date}\n{block.text}\n\n"
        block_tc = len(ENCODER.encode(block_str))

        if token_count + block_tc > int(NUM_TOKENS * CONTEXT_FRACTION):
            main_prompt += cap(block_str, int(NUM_TOKENS * CONTEXT_FRACTION) - token_count)
            break
        else:
            main_prompt += block_str
            token_count += block_tc

    main_prompt = main_prompt.strip() + "\n\n\n"







    main_prompt += f"In your answer, please cite any claims you make back to each source " \
                    f"using the format: [a], [b], etc. If you use multiple sources to make a claim " \
                    f"cite all of them. For example: \"AGI is concerning [c, d, e].\"\n\nQ: " + query

    prompt.append({"role": "user", "content": main_prompt})

    return prompt

# ------------------------------------------------------------------------------

# returns either (True, reply string, embeddings) or (False, error message string, None)
def talk_to_robot(dataset_dict, query: str, history: List[Dict[str, str]], k: int = 10):


    # 1. Find the most relevant blocks from the Alignment Research Dataset
    top_k_blocks: List[Block] = get_top_k_blocks(dataset_dict, query, k)
    


    # 2. Generate a prompt
    prompt = construct_prompt(query, history, top_k_blocks)
    print('\n' * 10)
    print(" ------------------------------ prompt: -----------------------------")
    for message in prompt:
        print(f"----------- {message['role']}: ------------------")
        print(message['content'])

    print('\n' * 10)



    # 3. Count number of tokens left for completion (-50 for a buffer)
    max_tokens_completion = NUM_TOKENS - sum([len(ENCODER.encode(message["content"]) + ENCODER.encode(message["role"])) for message in prompt]) - 50


    # 4. Answer the user query
    try:
        return (True, openai.ChatCompletion.create(
            model=COMPLETIONS_MODEL,
            messages=prompt,
            max_tokens=max_tokens_completion
        )["choices"][0]["message"]["content"], top_k_blocks)
    except Exception as e:
        print(e)
        return (False, "Error: " + str(e), None)

