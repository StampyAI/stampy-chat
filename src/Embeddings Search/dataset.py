import jsonlines
import numpy as np
from typing import List, Dict, Tuple
import openai

from settings import DATA_PATH, EMBEDDING_MODEL
import config

from helper import split_article, split_into_sentences

openai.api_key = config.OPENAI_API_KEY


class Dataset:
    def __init__(self,
            path: str,  # Path to the dataset .jsonl file.
            sources: List[str] = None,  # List of sources to include. If None, include all sources.
            max_paragraph_length: Tuple[int, int] = None  # (max number of words in a paragraph, max number of characters in a paragraph) (TBD)
        ):

        self.path = path
        self.sources = sources
        self.max_paragraph_length = max_paragraph_length
            
        self.data: List[Tuple[str, str, str]] = []  # List of tuples, each containing the title of an article, its URL, and text. E.g.: [('title', 'url', 'text'), ...]
        self.embed_split: List[str] = []  # List of strings, each being a few paragraphs from a single article (not exceeding 1000 words).
        
        self.num_articles: Dict[str, int] = {}  # Number of articles per source. E.g.: {'source1': 10, 'source2': 20, 'total': 30}
        if sources is None:
            self.num_articles['total'] = 0
        else:
            for source in sources: 
                self.num_articles[source] = 0
            self.num_articles['total'] = 0
        
        self.total_char_count = 0
        self.total_word_count = 0
        self.total_sentence_count = 0
        self.total_paragraph_count = 0
        
    def get_alignment_texts(self):
        with jsonlines.open(self.path, "r") as reader:
            for entry in reader:
                try:
                    if self.sources is None:
                        if entry['source'] not in self.num_articles:
                            self.num_articles[entry['source']] = 1
                        else:
                            self.num_articles[entry['source']] += 1
                        self.num_articles['total'] += 1
                    else:
                        if entry['source'] in self.sources:
                            self.num_articles[entry['source']] += 1
                            self.num_articles['total'] += 1
                        else:
                            continue
                    
                    # BIG PROBLEM: Very often, the post will have no URL, so this will fail. (TODO: Fix this.)
                    self.data.append((entry['title'], entry['url'], entry['text']))
                    paragraphs = split_article(entry['text'])
                    self.embed_split.extend(paragraphs)
                    
                    self.total_char_count += len(entry['text'])
                    self.total_word_count += len(entry['text'].split())
                    self.total_sentence_count += len(split_into_sentences(entry['text']))
                    self.total_paragraph_count += len(paragraphs)
                except KeyError:
                    pass
    
    def get_embedding(text: str) -> np.ndarray:
        result = openai.Embedding.create(model=EMBEDDING_MODEL, input=text)
        return result["data"][0]["embedding"]

    def get_embeddings(self):
        self.embeddings = np.array([self.get_embedding(text) for text in self.embed_split])
    
    def save_embeddings(self, path: str):
        np.save(path, self.embeddings)
        
    def load_embeddings(self, path: str):
        self.embeddings = np.load(path)
        

if __name__ == "__main__":
    dataset = Dataset(DATA_PATH)
    dataset.get_alignment_texts()
    dataset.get_embeddings()
    dataset.save_embeddings("embeddings.npy")
