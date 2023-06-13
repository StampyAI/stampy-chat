# ------------------------------- env, constants -------------------------------
from followups import multisearch_authored
from get_blocks import get_top_k_blocks, Block

from dataclasses import asdict
from typing import List, Dict, Callable
import openai
import re
import tiktoken
import time

# OpenAI models
EMBEDDING_MODEL = "text-embedding-ada-002"
COMPLETIONS_MODEL = "gpt-3.5-turbo"
# COMPLETIONS_MODEL = "gpt-4"

STANDARD_K = 20 if COMPLETIONS_MODEL == 'gpt-4' else 10

# parameters

# NOTE: All this is approximate, there's bits I'm intentionally not counting. Leave a buffer beyond what you might expect.
NUM_TOKENS = 8191 if COMPLETIONS_MODEL == 'gpt-4' else 4095
HISTORY_FRACTION = 0.25 # the (approximate) fraction of num_tokens to use for history text before truncating
CONTEXT_FRACTION = 0.5  # the (approximate) fraction of num_tokens to use for context text before truncating

ENCODER = tiktoken.get_encoding("cl100k_base")

DEBUG_PRINT = True

# --------------------------------- prompt code --------------------------------



# limit a string to a certain number of tokens
def cap(text: str, max_tokens: int) -> str:

    if max_tokens <= 0: return "..."

    encoded_text = ENCODER.encode(text)

    if len(encoded_text) <= max_tokens: return text
    else: return ENCODER.decode(encoded_text[:max_tokens]) + " ..."




def construct_prompt(query: str, history: List[Dict[str, str]], context: List[Block]) -> List[Dict[str, str]]:

    prompt = []

    # History takes the format: history=[
    #     {"role": "user", "content": "Die monster. You don’t belong in this world!"},
    #     {"role": "assistant", "content": "It was not by my hand I am once again given flesh. I was called here by humans who wished to pay me tribute."},
    #     {"role": "user", "content": "Tribute!?! You steal men's souls and make them your slaves!"},
    #     {"role": "assistant", "content": "Perhaps the same could be said of all religions..."},
    #     {"role": "user", "content": "Your words are as empty as your soul! Mankind ill needs a savior such as you!"},
    #     {"role": "assistant", "content": "What is a man? A miserable little pile of secrets. But enough talk... Have at you!"},
    # ]

    source_prompt = "You are a helpful assistant knowledgeable about AI Alignment and Safety. " \
        "Please give a clear and coherent answer to the user's questions.(written after \"Q:\") " \
        "using the following sources. Each source is labeled with a letter. Feel free to " \
        "use the sources in any order, and try to use multiple sources in your answers.\n\n"

    token_count = len(ENCODER.encode(source_prompt))

    # Context from top-k blocks
    for i, block in enumerate(context):
        block_str = f"[{chr(ord('a') + i)}] {block.title} - {block.author} - {block.date}\n{block.text}\n\n"
        block_tc = len(ENCODER.encode(block_str))

        if token_count + block_tc > int(NUM_TOKENS * CONTEXT_FRACTION):
            source_prompt += cap(block_str, int(NUM_TOKENS * CONTEXT_FRACTION) - token_count)
            break
        else:
            source_prompt += block_str
            token_count += block_tc

    source_prompt = source_prompt.strip();
    if len(history) > 0:
        source_prompt += "\n\n"\
            "Before the question (\"Q: \"), there will be a history of previous questions and answers. " \
            "These sources only apply to the last question. Any sources used in previous answers " \
            "are invalid."

    prompt.append({"role": "system", "content": source_prompt.strip()})


    # Write a version of the last 10 messages into history, cutting things off when we hit the token limit.
    token_count = 0
    history_trnc = []
    for message in history[:-10:-1]:
        if message["role"] == "user":
            history_trnc.append({"role": "user", "content": "Q: " + message["content"]})
            token_count += len(ENCODER.encode("Q: " + message["content"]))
        else:
            content = cap(message["content"], int(NUM_TOKENS * HISTORY_FRACTION) - token_count)

            # censor all source letters into [x]
            content = re.sub(r"\[[0-9]+\]", "[x]", content)

            history_trnc.append({"role": "assistant", "content": content})
            token_count += len(ENCODER.encode(content))

        if token_count > int(NUM_TOKENS * HISTORY_FRACTION):
            break

    prompt.extend(history_trnc[::-1])


    question_prompt = f"In your answer, please cite any claims you make back to each source " \
                    f"using the format: [a], [b], etc. If you use multiple sources to make a claim " \
                    f"cite all of them. For example: \"AGI is concerning [c, d, e].\"\n\nQ: " + query

    prompt.append({"role": "user", "content": question_prompt})

    return prompt

# ------------------------------- completion code -------------------------------
import time
import json

def talk_to_robot_internal(index, query: str, history: List[Dict[str, str]], k: int = STANDARD_K, log: Callable = print):
    try:
        # 1. Find the most relevant blocks from the Alignment Research Dataset
        yield {"state": "loading", "phase": "semantic"}
        top_k_blocks = get_top_k_blocks(index, query, k)

        yield {"state": "loading", "phase": "semantic", 'citations': [{'title': block.title, 'author': block.author, 'date': block.date, 'url': block.url} for block in top_k_blocks]}

        # 2. Generate a prompt
        yield {"state": "loading", "phase": "prompt"}
        prompt = construct_prompt(query, history, top_k_blocks)

        # 3. Count number of tokens left for completion (-50 for a buffer)
        max_tokens_completion = NUM_TOKENS - sum([len(ENCODER.encode(message["content"]) + ENCODER.encode(message["role"])) for message in prompt]) - 50

        # 4. Answer the user query
        yield {"state": "loading", "phase": "llm"}
        t1 = time.time()
        response = ''

        for chunk in openai.ChatCompletion.create(
            model=COMPLETIONS_MODEL,
            messages=prompt,
            max_tokens=max_tokens_completion,
            stream=True,
            temperature=0, # may or may not be a good idea
        ):
            res = chunk["choices"][0]["delta"]
            if res is not None and res.get("content") is not None:
                response += res["content"]
                yield {"state": "streaming", "content": res["content"]}


        t2 = time.time()
        print("Time to get response: ", t2 - t1, " s")

        if DEBUG_PRINT:
            print('\n' * 10)
            print(" ------------------------------ prompt: -----------------------------")
            for message in prompt:
                print(f"----------- {message['role']}: ------------------")
                print(message['content'])

            print('\n' * 10)

            print(' ------------------------------ response: -----------------------------')
            print(response)

        log(query)
        log(response)

        # yield done state, possibly with followup questions
        fin_json = {'state': 'done'}
        followups = multisearch_authored([query, response], DEBUG_PRINT)
        for i, followup in enumerate(followups):
            fin_json[f'followup_{i}'] = asdict(followup)
        yield fin_json

    except Exception as e:
        print(e)
        yield {'state': 'error', 'error': str(e)}

# convert talk_to_robot_internal from dict generator into json generator
def talk_to_robot(index, query: str, history: List[Dict[str, str]], k: int = STANDARD_K, log: Callable = print):
    yield from (json.dumps(block) for block in talk_to_robot_internal(index, query, history, k, log))

# wayyy simplified api
def talk_to_robot_simple(index, query: str):
    res = {'response': ''}

    for block in talk_to_robot_internal(index, query, []):
        if block['state'] == 'loading' and block['phase'] == 'semantic' and 'citations' in block:
            citations = {}
            for i, c in enumerate(block['citations']):
                citations[chr(ord('a') + i)] = c
            res['citations'] = citations

        elif block['state'] == 'streaming':
            res['response'] += block['content']

        elif block['state'] == 'error':
            res['response'] = block['error']

    return json.dumps(res)
