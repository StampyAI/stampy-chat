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

        for i, link in enumerate(informed_assistant(data['query'])):
            results[i] = json.dumps(link.__dict__)

        self.wfile.write(json.dumps(results).encode('utf-8'))


# -------------------------------- non-web-code --------------------------------
import time
import pickle
import os

import numpy as np

import openai
from openai.error import RateLimitError

# OpenAI API key
try:
    import config
    OPENAI_API_KEY = config.OPENAI_API_KEY
except ImportError:
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
openai.api_key = OPENAI_API_KEY

# OpenAI models
EMBEDDING_MODEL = "text-embedding-ada-002"
COMPLETIONS_MODEL = "text-davinci-003"

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
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)
import tiktoken

import config
from dataset import Dataset
from settings import PATH_TO_DATASET, EMBEDDING_MODEL, COMPLETIONS_MODEL

from semantic_search import get_top_k_blocks


# ----- delete -----
class AlignmentSearch:
    """
    A class for searching and answering questions related to AI Alignment and AI Safety using OpenAI's API.
    """

    def __init__(self,
            dataset: Dataset,  # Dataset object containing the data.
            context_length_limit: int = 2000,  # Maximum number of tokens for the context.
        ):
        """
        Initialize the AlignmentSearch class with the provided dataset.
        """
        self.metadataset = dataset
        self.context_length_limit = context_length_limit
    
    @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(4))
    def get_embedding(self, text: str) -> np.ndarray:
        result = openai.Embedding.create(model=EMBEDDING_MODEL, input=text)
        return result["data"][0]["embedding"]
    
    def get_top_k_blocks(self, query: str, k: int, HyDE: bool = False) -> List[str]:
        """Get the top k blocks that are most semantically similar to the query, using the provided dataset. 

        Args:
            query (str): The query to be searched for.
            k (int): The number of blocks to return.
            HyDE (bool, optional): Whether to use HyDE or not. Defaults to False.

        Returns:
            List[str]: A list of the top k blocks that are most semantically similar to the query.
        """
        # Get the embedding for the query.
        query_embedding = self.get_embedding(query)
        
        # If HyDE is enabled, produce a no-context ChatCompletion to the query.
        if HyDE:
            messages = [
                {"role": "system", "content": "You are a knowledgeable AI Alignment assistant. Do your best to answer the user's question, even if you don't know the answer for sure."},
                {"role": "user", "content": query},
            ]
            HyDE_completion = openai.ChatCompletion.create(
                model=COMPLETIONS_MODEL,
                messages=messages,
                temperature=0.0,
                max_tokens=100
            )["choices"][0]["text"]
            HyDe_completion_embedding = self.get_embedding(f"Question: {query}\n\nAnswer: {HyDE_completion}")
            
            similarity_scores = np.dot(self.metadataset.embeddings, HyDe_completion_embedding)        
        else:
            similarity_scores = np.dot(self.metadataset.embeddings, query_embedding)
        
        ordered_blocks = np.argsort(similarity_scores)[::-1]
        top_k_indices = ordered_blocks[:k]
        top_k = [self.metadataset.embedding_strings[i] for i in top_k_indices]
        return top_k
    
    def limit_tokens(self, text: str, max_tokens: int, encoding_name: str = "cl100k_base") -> str:
        encoding = tiktoken.get_encoding(encoding_name)
        tokens = encoding.encode(text)[:max_tokens]
        return encoding.decode(tokens)
    
    def get_context_prompt(self, blocks: List[str]) -> str:
        """Get the prompt for the context of the user's question.

        Args:
            blocks (List[str]): A list of blocks to use as context.

        Returns:
            str: The prompt for the context of the user's question.
        """
        if blocks is None:
            return "No context provided."
        
        context_prompt = "Context: \n\n"
        for block in blocks:
            context_prompt += f"{block}\n\n"

        context_prompt = self.limit_tokens(context_prompt, self.context_length_limit)  # Limit the context to the specified number of tokens.
        return context_prompt
    
    def get_expertise_prompt(self, level_of_expertise: int = 0) -> str:
        """Get the prompt for the level of expertise of the user."""        
        
        explanation_prompt = f"Explain AI Alignment research at a level {level_of_expertise}/5 of understanding. "
        if level_of_expertise == 0:
            explanation_prompt += "Assume the user is a complete beginner without any knowledge of the subject. "
        elif level_of_expertise == 1:
            explanation_prompt += "Assume the user has a basic understanding of AI Alignment but may not be familiar with advanced concepts or technical details. "
        elif level_of_expertise == 2:
            explanation_prompt += "Assume the user has a moderate understanding of AI Alignment and is familiar with some advanced concepts, but may still need clarification on technical details. "
        elif level_of_expertise == 3:
            explanation_prompt += "Assume the user has a good understanding of AI Alignment, including some technical details, but may not be familiar with the nuances of specific subfields. "
        elif level_of_expertise == 4:
            explanation_prompt += "Assume the user has a strong understanding of AI Alignment and its subfields, including technical details, but may not be an expert researcher. "
        elif level_of_expertise == 5:
            explanation_prompt += "Assume the user is an expert researcher in the subfield they are asking about. "
        return explanation_prompt

    def get_user_prompt(self, user_query: str, mode: str) -> str:
    
    def create_messages(self, system_prompt: str, user_prompt: str, context: str, question: str):
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{user_prompt}\n\n{context}\n\nQuestion: {question}"}
    ]
        
    def construct_messages(self, user_query: str, blocks: List[str] = None, level_of_expertise: int = 0, mode: str = "balanced") -> List[dict, str]:
        """
        Construct a list of messages to be used as a prompt for the OpenAI API, based on the input question and a list of context blocks.
        
        :param user_query: The user's question (str) to be answered by the AI assistant.
        :param blocks: A list of context blocks (str) containing relevant information to answer the question. Defaults to None.
        :param level_of_knowledge: The level of knowledge of the AI assistant. Integer between 0 and 5, where 0 is the lowest and 5 is the highest. Defaults to 0.
        :param mode: The mode of operation for the AI assistant. Can be one of 'balanced', 'precise', 'creative', or 'HyDE'. Defaults to 'balanced'.
            - 'balanced': The AI assistant provides helpful and knowledgeable answers while acknowledging the limits of its knowledge.
            - 'precise': The AI assistant provides accurate and specific answers, strictly using the provided context blocks.
            - 'creative': The AI assistant provides creative and imaginative answers, thinking outside the box when necessary.
            - 'debate': The AI assistant is a skilled debater, and it is important that it attempts to answer the user's question.
            - 'comment': The AI assistant is a skilled commenter, and it is important that it attempts to answer the user's question.
            - 'synthesis': The AI assistant is a skilled synthesizer, and it is important that it attempts to answer the user's question.
        :return: A list of messages (dict) to be used as a prompt for the OpenAI API, and a temperature.
        """

        context = self.get_context_prompt(blocks)  # Construct the context prompt.
        explanation_prompt = self.get_expertise_prompt(level_of_expertise)  # Construct the explanation prompt.

        temperature = 0.5
        user_prompt = explanation_prompt + f"Answer the following question: {question}\n\n"

        if mode == "creative":
            system_prompt = '''You are a creative and imaginative assistant.'''
            user_prompt += '''Use the provided context blocks and think outside the box to come up with unique insights. Feel free to use your imagination if the answer is not contained within the context blocks. You can also ask the user questions to clarify their query.'''
            temperature = 0.8

        elif mode == "balanced":
            system_prompt = '''You are a helpful assistant.'''
            user_prompt += '''Use the provided context blocks to answer the questions as truthfully as possible. If the answer is not contained within the context blocks, say, "I don't know." You can also ask the user questions to clarify their query.'''
            temperature = 0.5

        elif mode == "precise":
            system_prompt = '''You are a precise and accurate assistant.'''
            user_prompt += '''Your answers should be as accurate and specific as possible. Only use the provided context blocks as your source of information. If the answer is not contained within them, say, "I don't know." You can also ask the user questions to clarify their query.'''
            temperature = 0.3


        if mode == "creative":
            system = '''You are a creative and imaginative assistant.'''
            user_prompt = '''You help users by answering questions and providing information about AI Alignment and AI Safety. While being knowledgeable, you also think outside the box and come up with unique insights. Answer the questions as creatively as possible using the provided context blocks, and if the answer is not contained within them, feel free to use your imagination. You can also ask the user questions to clarify their query.'''
            messages = self.create_messages(system, user_prompt, context, question)

        elif mode == "balanced":
            system = '''You are a helpful assistant.'''
            user_prompt = '''You help users by answering questions and providing information about AI Alignment and AI Safety. You are extremely knowledgeable, yet you know the limits of your knowledge. Answer the questions as truthfully as possible using the provided context blocks, and if the answer is not contained within them, say, "I don't know." You can also ask the user questions to clarify their query.'''
            messages = self.create_messages(system, user_prompt, context, question)

        elif mode == "precise":
            system = '''You are a precise and accurate assistant.'''
            user_prompt = '''You help users by answering questions and providing information about AI Alignment and AI Safety. Your answers should be as accurate and specific as possible. Only use the provided context blocks as your source of information. If the answer is not contained within them, say, "I don't know." You can also ask the user questions to clarify their query.'''
            messages = self.create_messages(system, user_prompt, context, question)

        elif mode == "HyDE":
            assistant_prompt = "You are a helpful assistant, and you help users by answering questions and providing informationabout AI Alignment and AI Safety, on which you are extremely knowledgeable. Answer the user's question even if you are not certain of the answer; it is supremely important that you do attempt to offer an answer related to the user's query."
            messages = [
                {"role": "system", "content": assistant_prompt},
                {"role": "user", "content": question},
            ]
            
        elif mode == "debate":
            system = '''You are a skilled debater with expertise in AI Alignment and AI Safety.'''
            user_prompt = '''Your task is to analyze the given argument or point related to AI Alignment and provide thoughtful criticism and counter-arguments. Draw upon your deep understanding of the field to engage in a meaningful and insightful debate. You may also ask the user for further clarification or provide alternative perspectives.'''
            
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": f"{user_prompt}\n\n{context}\n\nArgument: {question}"}
            ]

        elif mode == "comment":
            system = '''You are a knowledgeable assistant with expertise in AI Alignment and AI Safety.'''
            user_prompt = '''Your task is to provide thoughtful comments on the given idea related to AI Alignment. Offer insights, perspectives, and suggestions that may push the user in various interesting directions, fostering deeper understanding and exploration of the topic.'''
            
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": f"{user_prompt}\n\n{context}\n\nIdea: {question}"}
            ]

        elif mode == "synthesis":
            system = '''You are an insightful assistant with expertise in AI Alignment and AI Safety.'''
            user_prompt = '''Your task is to synthesize information from the provided context blocks and answer the given question. Create a concise and coherent answer that combines different perspectives and insights, offering a well-rounded understanding of the topic.'''
            
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": f"{user_prompt}\n\n{context}\n\nQuestion: {question}"}
            ]

        else:
            raise ValueError("Mode must be one of 'balanced', 'precise', 'creative', 'HyDE', 'debate', 'comment', or 'synthesis'.")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        return messages, temperature
    
    def answer_question(self, user_query: str, k: int=10, HyDE: bool=False, mode: str="balanced") -> Tuple[str, List[str], List[str]]:
        # Receives a user query (str) and returns an answer (str) to the query, along with the top-n most relevant blocks from the Alignment Research Dataset, and the top-m most relevant sources from the Alignment Research Dataset.
        messages = self.construct_messages(user_query, mode="balanced")
        answer = openai.ChatCompletion.create(
            model=COMPLETIONS_MODEL, 
            messages=messages
        )
        return answer["choices"][0]["message"]["content"]
    
    def search_and_answer(self, user_query: str, n: int=10, m: int = 3, HyDE: bool=False, mode: str="balanced") -> Tuple[str, List[str], List[str]]:
        # Receives a user query (str) and returns an answer (str) to the query, along with the top-n most relevant blocks from the Alignment Research Dataset, and the top-m most relevant sources from the Alignment Research Dataset.
        answer, top_k_semantic_search_results, top_k_sources = self.answer_question(user_query, k, HyDE, mode)
        
        answer = openai.ChatCompletion.create(
            model=COMPLETIONS_MODEL, 
            messages=messages
        )
        
        return answer["choices"][0]["message"]["content"]

        
        return answer, top_k_semantic_search_results, top_k_sources

# ----- delete -----


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
        Dict[str, str]: The prompt for the ChatCompletions API.
    """
    # Initialize prompt
    prompt = {}
    
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



def informed_assistant(user_query: str, previous_dialogue: str, k: str, mode: str = "standard", HyDE: bool = False, stream: bool = True, stream_delay: float = 0.1) -> str:
    """
    This function uses the OpenAI ChatCompletions API to answer a user query.
    It first checks if the query is offensive, and if so, raises an exception.
    Then, it finds the top-k most relevant blocks from the Alignment Research Dataset and uses them as context for the ChatCompletions API.
    It uses the blocks to generate a prompt for the ChatCompletions API.
    Finally, it uses the ChatCompletions API to generate an answer to the user query.

    Args:
        user_query (str): The user query.
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


if __name__ == "__main__":
    # Test the question answering function
    user_query = "Within the area of mitigating AI risk, there are several broad classes of action being taken. What does Technical safety research focus on?"
    previous_dialogue = [
        {"role": "assistant", "content": "Hi! I know all about AI Alignment. Ask me a question!"},
    ]
    k = 5
    mode = "standard"
    HyDE = True
    stream = True
    
    for response in informed_assistant(user_query, previous_dialogue, k, mode, HyDE, stream):
        print(response, end="")