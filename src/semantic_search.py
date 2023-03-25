import numpy as np
from typing import List
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

openai.api_key = config.OPENAI_API_KEY


"""
TODO:
Add a moderation call to not be prompt-hacked: https://platform.openai.com/docs/guides/moderation/quickstart
"""
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


if __name__ == "__main__":
    with open(PATH_TO_DATASET, 'rb') as f:
        dataset = pickle.load(f)
    k = 4
    AS = AlignmentSearch(dataset=dataset)
    query = "Within the area of mitigating AI risk, there are several broad classes of action being taken. What does Technical safety research focus on?"
    answer, top_k_sources = AS.search_and_answer(query, k)#, HyDE=True)
    print(answer)
    print(top_k_sources)