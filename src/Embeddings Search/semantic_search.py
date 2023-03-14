import numpy as np
from typing import List, Tuple
import pickle
import openai
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)  # for exponential backoff

import config
from dataset import Dataset
from settings import PATH_TO_DATASET, EMBEDDING_MODEL, COMPLETIONS_MODEL, MAX_LEN_PROMPT

openai.api_key = config.OPENAI_API_KEY


class AlignmentSearch:
    def __init__(self,
            dataset: Dataset,  # Dataset object containing the data.
        ):
        self.dataset = dataset
    
    @retry(wait=wait_random_exponential(min=1, max=100), stop=stop_after_attempt(10))
    def get_embedding(self, text: str) -> np.ndarray:
        result = openai.Embedding.create(model=EMBEDDING_MODEL, input=text)
        return result["data"][0]["embedding"]
    
    def get_top_k(self, query: str, k: int=10) -> List[Tuple[str, str, str]]:
        # Receives a query (str) and returns the top k articles (List[Tuple[str, str, str]]) that are most similar to the query.
        # Each tuple contains the title of an article, its URL, and text.
        query_embedding = self.get_embedding(query)
        similarities = np.dot(self.dataset.embeddings, query_embedding)
        top_k_indices = np.argsort(similarities)[::-1][:k]
        top_k = [self.dataset.embed_split[i] for i in top_k_indices]
        return top_k
    
    def construct_prompt(self, question: str, texts: List[Tuple[str]]) -> str:
        # Receives a question (str) and a list of articles (List[Tuple[str, str, str]]) and returns a prompt (str) to be used for text generation.
        context = "\n".join(texts)[:MAX_LEN_PROMPT]
        header = """Answer the question as truthfully as possible using the provided context, and if the answer is not contained within the text below, say "I don't know."\n\nContext:\n"""
        return header + "".join(context) + "\n\n Q: " + question + "\n A:"
    
    def answer_question(self, question: str, texts: List[Tuple[str, str, str]]) -> str:
        # Receives a question (str) and a list of articles (List[Tuple[str, str, str]]) and returns an answer (str) to the question.
        prompt = self.construct_prompt(question, texts)
        COMPLETIONS_API_PARAMS = {
            "temperature": 0.0,
            "max_tokens": 500,
            "model": COMPLETIONS_MODEL,
        }
        answer = openai.Completion.create(prompt=prompt, **COMPLETIONS_API_PARAMS)["choices"][0]["text"].strip(" \n")
        return answer
    
    def search_and_answer(self, question: str, k: int=10, HyDE: bool=False) -> str:
        # Receives a question (str) and returns an answer (str) to the question.
        if HyDE:
            raise NotImplementedError
        else:
            top_k = self.get_top_k(question, k)
        answer = self.answer_question(question, top_k)
        return answer    


if __name__ == "__main__":
    with open(PATH_TO_DATASET, 'rb') as f:
        dataset = pickle.load(f)
    AS = AlignmentSearch(dataset=dataset)
    prompt = "What would be an idea to solve the Alignment Problem? Name the Lesswrong post by Quintin Pope that discusses this idea."
    answer = AS.search_and_answer(prompt, 3, HyDE=False)
    print(answer)