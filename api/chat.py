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
MAX_TOKEN_LEN_PROMPT = 8191 if COMPLETIONS_MODEL == 'gpt-4' else 4095
TRUNCATE_CONTEXT_LEN = 1500
TRUNCATE_HISTORY_LEN = 500
MAX_RESPONSE_LEN = 900

# -------------------------------- prompt code --------------------------------

def limit_tokens(text: str, max_tokens: int, encoding_name: str = "cl100k_base") -> str:
    encoding = tiktoken.get_encoding(encoding_name)
    tokens = encoding.encode(text)[:max_tokens]
    return encoding.decode(tokens)

def construct_prompt(query: str, history: List[Dict[str, str]], context: List[Block], encoding_name: str = "cl100k_base") -> List[Dict[str, str]]:
    # Encoder to count tokens
    enc = tiktoken.get_encoding(encoding_name)
    total_tokens = 0
    
    prompt = []
    
    system_prompt = "You are a helpful assistant knowledgeable about AI Alignment. You are provided with a question and a set of sources. Your job is to answer the question using the sources, and cite the sources you use."
    total_tokens += len(enc.encode(system_prompt))
    
    # Get past user queries
    past_user_queries = "\n".join([message["content"] for message in history if message["role"] == "user"][-5:-1])
    past_queries_prompt = f"My previous queries were:\n{past_user_queries}"
    
    # Instruction prompt
    instruction_context_query_prompt = \
        "Please give a clear and coherent answer to my question (written after \"Q:\") " \
        "using the following sources. Each source is labeled with a letter. Feel free to " \
        "use the sources in any order, and try to use multiple sources in your answer."

    # Context from top-k blocks
    context_prompt = ""
    for i, block in enumerate(context):
        context_prompt += f"[{chr(ord('a') + i)}] {block.title} - {block.author} - {block.date}\n\n{block.text}\n\n\n"
    context_prompt = context_prompt[:-2] # trim last two newlines
    context_prompt = limit_tokens(context_prompt, TRUNCATE_CONTEXT_LEN)  # truncate the context_prompt to max TRUNCATE_CONTEXT tokens
    context_prompt += "\n" if (context_prompt[-1] != "\n") else ""
    
    # Question prompt
    question_prompt = f"In your answer, please cite any claims you make back to each source " \
                    f"using the format: [a], [b], etc. If you use multiple sources to make a claim " \
                    f"cite all of them. For example: \"AGI is concerning [c, d, e].\"" \
                    f"" \
                    f"" \
                    f"Q: {query}"

    instruction_context_query_prompt = f"{instruction_context_query_prompt}\n\n{context_prompt}\n\n{question_prompt}"
    
    total_tokens += len(enc.encode(past_queries_prompt))
    total_tokens += len(enc.encode(history[-2]["content"]))  # Get past user query
    total_tokens += len(enc.encode(history[-1]["content"]))
    total_tokens += len(enc.encode(instruction_context_query_prompt))
    
    # If the prompt is too long, truncate the last answer
    if total_tokens > MAX_TOKEN_LEN_PROMPT - TRUNCATE_HISTORY_LEN:
        tokens_left = MAX_TOKEN_LEN_PROMPT - total_tokens
        print(f"WARNING: Prompt is too long! Prompt length: {total_tokens} tokens")
        last_assistant_reply_trunctated = limit_tokens(prompt[-1]["content"], tokens_left)
        prompt[-1]["content"] = f"{last_assistant_reply_trunctated}"
    
    prompt.append({"role": "system", "content": system_prompt})
    prompt.append({"role": "user", "content": past_queries_prompt})
    prompt.extend(history[-2:])
    prompt.append({"role": "user", "content": instruction_context_query_prompt})
    
    return prompt, MAX_TOKEN_LEN_PROMPT - (total_tokens + 50)  # add 50 tokens for safety

# ------------------------------------------------------------------------------
        
def normal_completion(prompt: List[Dict[str, str]], max_tokens_completion: int) -> str:
    try:
        return openai.ChatCompletion.create(
            model=COMPLETIONS_MODEL,
            messages=prompt,
            max_tokens=max_tokens_completion
        )["choices"][0]["text"]
    except Exception as e:
        print(e)
        return "I'm sorry, I failed to process your query. Please try again. If the problem persists, please contact the administrator."


def talk_to_robot(dataset_dict, query: str, history: List[Dict[str, str]] = [], k: int = 10):

    # 1. Find the most relevant blocks from the Alignment Research Dataset
    top_k_blocks: List[Block] = get_top_k_blocks(dataset_dict, query, k)
    
    # 2. Generate a prompt for the ChatCompletions API
    prompt, max_tokens_completion = construct_prompt(query, history, top_k_blocks)
    
    # 3. Answer the user query
    return (normal_completion(prompt, max_tokens_completion), top_k_blocks)


if __name__ == "__main__":
    import config
    openai.api_key = config.OPENAI_API_KEY
    
    completion = openai.ChatCompletion.create(
        model=COMPLETIONS_MODEL,
        messages=[
            {"role": "system", "content": "?" * 8 * 2045},
        ]
    )