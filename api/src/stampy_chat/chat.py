import time
import json
import re
import time
from dataclasses import asdict
from typing import List, Dict

import openai

from stampy_chat import logging
from stampy_chat.followups import multisearch_authored
from stampy_chat.get_blocks import get_top_k_blocks, Block
from stampy_chat.settings import Settings


logger = logging.getLogger(__name__)


# limit a string to a certain number of tokens
def cap(text: str, max_tokens: int, encoder) -> str:
    if max_tokens <= 0:
        return "..."

    encoded_text = encoder.encode(text)

    if len(encoded_text) <= max_tokens:
        return text
    return encoder.decode(encoded_text[:max_tokens]) + " ..."


Prompt = List[Dict[str, str]]


def prompt_context(context: List[Block], settings: Settings) -> str:
    source_prompt = settings.source_prompt_prefix
    max_tokens = settings.context_tokens
    encoder = settings.encoder

    token_count = len(encoder.encode(source_prompt))

    # Context from top-k blocks
    for i, block in enumerate(context):
        block_str = f"[{chr(ord('a') + i)}] {block.title} - {','.join(block.authors)} - {block.date}\n{block.text}\n\n"
        block_tc = len(encoder.encode(block_str))

        if token_count + block_tc > max_tokens:
            source_prompt += cap(block_str, max_tokens - token_count, encoder)
            break
        else:
            source_prompt += block_str
            token_count += block_tc
    return source_prompt.strip()


def prompt_history(history: Prompt, settings: Settings) -> Prompt:
    max_tokens = settings.history_tokens
    encoder = settings.encoder
    token_count = 0
    prompt = []

    # Get the n_items last messages, starting from the last one. This is because it's assumed
    # that more recent messages are more important. The `-1` is because of how slicing works
    messages = history[:-settings.maxHistory - 1:-1]
    for message in messages:
        if message["role"] == "user":
            prompt.append({"role": "user", "content": "Q: " + message["content"]})
            token_count += len(encoder.encode("Q: " + message["content"]))
        else:
            content = message["content"]
            # censor all source letters into [x]
            content = re.sub(r"\[[0-9]+\]", "[x]", content)
            content = cap(content, max_tokens - token_count, encoder)

            prompt.append({"role": "assistant", "content": content})
            token_count += len(encoder.encode(content))

        if token_count > max_tokens:
            break
    return prompt[::-1]


def construct_prompt(query: str, settings: Settings, history: Prompt, context: List[Block]) -> Prompt:
    # History takes the format: history=[
    #     {"role": "user", "content": "Die monster. You don’t belong in this world!"},
    #     {"role": "assistant", "content": "It was not by my hand I am once again given flesh. I was called here by humans who wished to pay me tribute."},
    #     {"role": "user", "content": "Tribute!?! You steal men's souls and make them your slaves!"},
    #     {"role": "assistant", "content": "Perhaps the same could be said of all religions..."},
    #     {"role": "user", "content": "Your words are as empty as your soul! Mankind ill needs a savior such as you!"},
    #     {"role": "assistant", "content": "What is a man? A miserable little pile of secrets. But enough talk... Have at you!"},
    # ]

    # Context from top-k blocks
    source_prompt = prompt_context(context, settings)
    if history:
        source_prompt += settings.source_prompt_suffix
    source_prompt = [{"role": "system", "content": source_prompt.strip()}]

    # Write a version of the last 10 messages into history, cutting things off when we hit the token limit.
    history_prompt = prompt_history(history, settings)
    question_prompt = [{"role": "user", "content": settings.question_prompt(query)}]

    return source_prompt + history_prompt + question_prompt

# ------------------------------- completion code -------------------------------

def check_openai_moderation(prompt: Prompt, query: str):
    prompt_string = '\n\n'.join([message["content"] for message in prompt])
    mod_res = openai.Moderation.create(input=[query, prompt_string])

    if any(map(lambda x: x["flagged"], mod_res["results"])):
        logger.moderation_issue(query, prompt_string, mod_res)

        raise ValueError("This conversation was rejected by OpenAI's moderation filter. Sorry.")


def remaining_tokens(prompt: Prompt, settings: Settings):
    # Count number of tokens left for completion (-50 for a buffer)
    encoder = settings.encoder
    used_tokens = sum([
        len(encoder.encode(message["content"]) + encoder.encode(message["role"]))
        for message in prompt
    ])
    return max(0, settings.numTokens - used_tokens - settings.tokensBuffer)


def talk_to_robot_internal(index, query: str, history: Prompt, session_id: str, settings: Settings=Settings()):
    try:
        # 1. Find the most relevant blocks from the Alignment Research Dataset
        yield {"state": "loading", "phase": "semantic"}
        top_k_blocks = get_top_k_blocks(index, query, settings.topKBlocks)

        yield {
            "state": "citations",
            "citations": [
                {'title': block.title, 'author': block.authors, 'date': block.date, 'url': block.url}
                for block in top_k_blocks
            ]
        }

        # 2. Generate a prompt
        yield {"state": "loading", "phase": "prompt"}
        prompt = construct_prompt(query, settings, history, top_k_blocks)

        # 3. Run both the standalone query and the full prompt through
        # moderation to see if it will be accepted by OpenAI's api
        check_openai_moderation(prompt, query)

        # 4. Count number of tokens left for completion (-50 for a buffer)
        max_tokens_completion = remaining_tokens(prompt, settings)
        if max_tokens_completion < 40:
            raise ValueError(f"{max_tokens_completion} tokens left for the actual query after constructing the context - aborting, as that's not going to be enough")

        # 5. Answer the user query
        yield {"state": "loading", "phase": "llm"}
        t1 = time.time()
        response = ''

        for chunk in openai.ChatCompletion.create(
            model=settings.completions,
            messages=prompt,
            max_tokens=max_tokens_completion,
            stream=True,
            temperature=0, # may or may not be a good idea
        ):
            res = chunk["choices"][0]["delta"]
            if res and res.get("content"):
                response += res["content"]
                yield {"state": "streaming", "content": res["content"]}

        t2 = time.time()
        logger.debug(f'Time to get response: {time.time() - t1:.2f}s')
        if logger.is_debug():
            logger.debug('\n' * 10)
            logger.debug(" ------------------------------ prompt: -----------------------------")
            for message in prompt:
                logger.debug("----------- %s: ------------------", message['role'])
                logger.debug(message['content'])
            logger.debug('\n' * 10)
            logger.debug(' ------------------------------ response: -----------------------------')
            logger.debug(response)

        logger.interaction(session_id, query, response, history, prompt, top_k_blocks)

        yield {"state": "loading", "phase": "followups"}
        # yield optional followups
        followups = multisearch_authored([query, response])
        if followups:
            yield {'state': 'followups', 'followups': list(map(asdict, followups))}

        # yield done state
        fin_json = {'state': 'done'}
        yield fin_json

    except Exception as e:
        logger.error(e)
        yield {'state': 'error', 'error': str(e)}
        raise


# convert talk_to_robot_internal from dict generator into json generator
def talk_to_robot(index, query: str, history: List[Dict[str, str]], session_id: str, settings: Settings):
    yield from (json.dumps(block) for block in talk_to_robot_internal(index, query, history, session_id, settings))


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
