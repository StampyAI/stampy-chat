import numpy as np
from typing import List
import pickle
import openai
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)  # for exponential backoff
import tiktoken

import config
from dataset import Dataset
from settings import PATH_TO_DATASET, EMBEDDING_MODEL, COMPLETIONS_MODEL

openai.api_key = config.OPENAI_API_KEY


"""
TODO:
Add a moderation call to not be prompt-hacked: https://platform.openai.com/docs/guides/moderation/quickstart
"""

"""
TODO:
Add a moderation call to not be prompt-hacked: https://platform.openai.com/docs/guides/moderation/quickstart
"""

class AlignmentSearch:
    def __init__(self,
            dataset: Dataset,  # Dataset object containing the data.
        ):
        self.metadataset = dataset
    
    @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(4))
    def get_embedding(self, text: str) -> np.ndarray:
        result = openai.Embedding.create(model=EMBEDDING_MODEL, input=text)
        print(f"Embedding created for query: {text}")
        return result["data"][0]["embedding"]
        # except openai.RateLimitError as e:
        #     print("Rate limit exceeded. Retrying in 30 seconds.")
        #     time.sleep(30)
        #     raise e
    
    def get_top_k(self, query: str, k: int=10) -> List[str]:
        # Receives a query (str) and returns the top k blocks that are most semantically similar to the query.
        # Each tuple contains the title of an article, its URL, and text.
        query_embedding = self.get_embedding(query)
        similarities = np.dot(self.metadataset.embeddings, query_embedding)
        top_k_indices = np.argsort(similarities)[::-1][:k]
        top_k = [self.metadataset.embedding_strings[i] for i in top_k_indices]
        return top_k
    
    def limit_tokens(self, text: str, max_tokens: int, encoding_name: str = "cl100k_base") -> str:
        encoding = tiktoken.get_encoding(encoding_name)
        tokens = encoding.encode(text)[:max_tokens]
        return encoding.decode(tokens)
    
    def construct_messages(self, question: str, blocks: List[str] = None, mode: str = "balanced") -> str:
        # Receives a question (str) and a list of blocks and returns a prompt (str) to be used for text generation.
        if blocks:
            context = ""
            for i, block in enumerate(blocks):
                context += f'Context #{i+1}: """{block}"""\n\n'
            context = self.limit_tokens(context, 2000)
        else:
            context = ""

        if mode == "creative":
            raise NotImplementedError

        elif mode == "balanced":
            system = '''You are a helpful assistant.'''
            user_prompt = '''You help users by answering questions and providing information about AI Alignment and AI Safety. You are extremely knowledgeable, yet you know the limits of your knowledge. Answer the questions as truthfully as possible using the provided context blocks, and if the answer is not contained within them, say, "I don't know." You can also ask the user questions to clarify their query.'''
            
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": f"{user_prompt}\n\n{context}\n\nQuestion: {question}"}
            ]
        
        elif mode == "precise":
            raise NotImplementedError

        elif mode == "HyDE":
            assistant_prompt = "You are a helpful assistant, and you help users by answering questions and providing information about AI Alignment and AI Safety, on which you are extremely knowledgeable. Answer the user's question even if you are not certain of the answer; it is supremely important that you do attempt to offer an answer related to the user's query."
            messages = [
                {"role": "system", "content": assistant_prompt},
                {"role": "user", "content": question},
            ]
            
        else:
            raise ValueError("Mode must be one of 'balanced', 'precise', 'creative', or 'HyDE'.")
        
        return messages
    
    def answer_question(self, question: str, blocks: List[str]) -> str:
        # Receives a question (str) and a list of blocks and returns an answer (str) to the question.
        messages = self.construct_messages(question, blocks, mode="balanced")
        answer = openai.ChatCompletion.create(
            model=COMPLETIONS_MODEL, 
            messages=messages
        )
        return answer["choices"][0]["message"]["content"]
    
    def search_and_answer(self, question: str, k: int=10, HyDE: bool=False) -> str:
        # Receives a question (str) and returns an answer (str) to the question.
        if HyDE:
            messages = self.construct_messages(question, mode="HyDE")
            hyde_completion = openai.ChatCompletion.create(
                model=COMPLETIONS_MODEL, 
                messages=messages
            )
            top_k = self.get_top_k(f"{question}\n{hyde_completion}", k)
        else:
            top_k = self.get_top_k(question, k)
        answer = self.answer_question(question, top_k)
        return answer, top_k# , sources
if __name__ == "__main__":
    with open(PATH_TO_DATASET, 'rb') as f:
        dataset = pickle.load(f)
    k = 4
    AS = AlignmentSearch(dataset=dataset)
    query = "Within the area of mitigating AI risk, there are several broad classes of action being taken. What does Technical safety research focus on?"
    answer, top_k_sources = AS.search_and_answer(query, k)#, HyDE=True)
    print(answer)
    print(top_k_sources)