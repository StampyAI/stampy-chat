import numpy as np
from typing import List, Tuple
import openai

from settings import EMBEDDING_MODEL, COMPLETIONS_MODEL, MAX_LEN_PROMPT, DATA_PATH
import config

from dataset import Dataset


class AlignmentSearch:
    def __init__(self,
            dataset: Dataset,  # Dataset object containing the data.
        ):
        self.dataset = dataset
        
    def get_embedding(self, text: str) -> np.ndarray:
        result = openai.Embedding.create(model=EMBEDDING_MODEL, input=text)
        return result["data"][0]["embedding"]
    
    def get_top_k(self, query: str, k: int=10) -> List[Tuple[str, str, str]]:
        # Receives a query (str) and returns the top k articles (List[Tuple[str, str, str]]) that are most similar to the query.
        # Each tuple contains the title of an article, its URL, and text.
        query_embedding = self.get_embedding(query)
        similarities = np.dot(self.dataset.embeddings, query_embedding)
        top_k_indices = np.argsort(similarities)[::-1][:k]
        top_k = [self.dataset.data[i] for i in top_k_indices]
        return top_k
    
    def construct_prompt(self, question: str, texts: List[Tuple[str, str, str]]) -> str:
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
    
    def search_and_answer(self, question: str, k: int=10) -> str:
        # Receives a question (str) and returns an answer (str) to the question.
        top_k = self.get_top_k(question, k)
        answer = self.answer_question(question, top_k)
        return answer
    
    def summarize(self, article: str) -> str:
        COMPLETIONS_API_PARAMS = {
            "temperature": 0.0,
            "max_tokens": 300,
            "model": COMPLETIONS_MODEL,
        }
        response = openai.Completion.create(prompt=article, **COMPLETIONS_API_PARAMS)
        return response["choices"][0]["text"].strip(" \n")
    

if __name__ == "__main__":
    dataset = Dataset(DATA_PATH)
    dataset.get_alignment_texts()
    dataset.load_embeddings()
    search_and_answer = AlignmentSearch(dataset)
    question = "What is an agent?"
    answer = search_and_answer.search_and_answer(question)
    print(answer)