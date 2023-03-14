import jsonlines
import numpy as np
from typing import List, Dict, Tuple
import re
import time
import random
import pickle
import openai
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)  # for exponential backoff

import config

from text_splitter import TextSplitter, split_into_sentences


LEN_EMBEDDINGS = 1536
PATH_TO_DATA = r"C:\Users\Henri\Documents\GitHub\AlignmentSearch\src\Embeddings Search\data\alignment_texts.jsonl"
PATH_TO_EMBEDDINGS = r"C:\Users\Henri\Documents\GitHub\AlignmentSearch\src\Embeddings Search\data\embeddings.npy"
PATH_TO_DATASET = r"C:\Users\Henri\Documents\GitHub\AlignmentSearch\src\Embeddings Search\data\dataset.pkl"

COMPLETIONS_MODEL = "text-davinci-003"
EMBEDDING_MODEL = "text-embedding-ada-002"

openai.api_key = config.OPENAI_API_KEY

MAX_LEN_PROMPT = 5000

error_count_dict = {
    "Entry has no source.": 0,
    "Entry has no title.": 0,
    "Entry has no text.": 0,
    "Entry has no URL.": 0,
    "Entry has wrong citation level.": 0
}


class MissingDataException(Exception):
    pass


class Dataset:
    def __init__(self,
            path: str,  # Path to the dataset .jsonl file.
            sources: List[str] = None,  # List of sources to include. If None, include all sources.
            rate_limit_per_minute: int = 60,  # Rate limit for the OpenAI API.
            block_min_max_size: Tuple[int, int] = None,  # Tuple of (min_block_size, max_block_size), used for the text splitter. If None, use default values.
        ):
        self.path = path
        self.sources = sources
        self.rate_limit_per_minute = rate_limit_per_minute
        self.delay_in_seconds = 60.0 / self.rate_limit_per_minute
        
        # Set up text splitter
        if block_min_max_size is None: self.block_min_max_size = (400, 600)
        else: self.block_min_max_size = block_min_max_size
        self.text_splitter = TextSplitter(block_maxsize=self.block_min_max_size[1], block_minsize=self.block_min_max_size[0])
        
        self.data: List[Tuple[str]] = []  # List of tuples, each containing the title of an article, its URL, and text. E.g.: [('title', 'url', 'text'), ...]
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
        self.total_block_count = 0
        
    def get_info_tmp(self):
        self.sources_so_far = []
        self.info_types: Dict[str, List[str]] = {}
        with jsonlines.open(self.path, "r") as reader:
            for entry in reader:
                if 'source' not in entry: entry['source'] = 'None'
                
                if entry['source'] not in self.sources_so_far:
                    self.sources_so_far.append(entry['source'])
                    self.info_types[entry['source']] = entry.keys()
                
                if 'tags' in entry:
                    print(entry['tags'])
                    
                """
                {
                'text', 
                'title', 'book_title', # If there is both, take title, otherwise take book_title
                'author', 'authors', # If there is both, take author, otherwise take authors, otherwise take author
                'citation_level', # must be 0 or 1
                'date_published', 'published', # take first 10 chars of date_published, if it exists; else take first 16 chars of published, if it exists
                'doi', 'link', 'links', 'url', # if link, take link; elif url, take url; elif doi, take doi
                'tags'
                }
                """
    
    def get_alignment_texts(self):
        with jsonlines.open(self.path, "r") as reader:
            for entry in reader:
                # Only get one in a thousand articles
                # if random.randint(0, 3000) != 19: continue
                try:
                    if 'source' not in entry: raise MissingDataException("Entry has no source.")
                    
                    if self.sources is None:
                        if entry['source'] not in self.num_articles: self.num_articles[entry['source']] = 1
                        else: self.num_articles[entry['source']] += 1
                        self.num_articles['total'] += 1
                    else:
                        if entry['source'] in self.sources:
                            self.num_articles[entry['source']] += 1
                            self.num_articles['total'] += 1
                        else: continue
                    
                    text=title=author=citation_level=date_published=url=tags=None
                    
                    # Get text
                    if 'text' in entry and entry['text'] != '': text = entry['text']
                    else: raise MissingDataException(f"Entry has no text.")
                    
                    # Get title
                    if 'title' in entry and 'book_title' in entry and entry['title'] != '': title = entry['title']
                    elif 'book_title' in entry and entry['book_title'] != '': title = entry['book_title']
                    else: title = None
                        
                    # Get author
                    if 'author' in entry and 'authors' in entry and entry['author'] != '': author = entry['author']
                    elif 'authors' in entry and entry['authors'] != '': author = entry['authors']
                    elif 'author' in entry and entry['author'] != '': author = entry['author']
                    else: author = None
                        
                    # Get citation level
                    if 'citation_level' in entry:
                        if entry['citation_level'] != 0: raise MissingDataException(f"Entry has citation_level {entry['citation_level']}.")
                    
                    # Get date published
                    if 'date_published' in entry and entry['date_published'] != '': date_published = entry['date_published'][:10]
                    elif 'published' in entry and entry['published'] != '': date_published = entry['published'][:16]
                    else: date_published = None
                        
                    # Get URL
                    if 'link' in entry and entry['link'] != '': url = entry['link']
                    elif 'url' in entry and entry['url'] != '': url = entry['url']
                    elif 'doi' in entry and entry['doi'] != '': url = entry['doi']
                    else: url = None
                        
                    # Get tags
                    if 'tags' in entry and entry['tags'] != '':
                        if type(entry['tags']) == list: tags = ', '.join([val['term'] for val in entry['tags']])
                        elif type(entry['tags']) == str: tags = entry['tags']
                        else: tags = None
                    
                    signature = ""
                    if title: signature += f"Title: {title}, "
                    if author: signature += f"Author: {author}, "
                    if date_published: signature += f"Date published: {date_published}, "
                    if url: signature += f"URL: {url}, "
                    if tags: signature += f"Tags: {tags}, "
                    signature = signature[:-2]

                    self.data.append((title, author, date_published, url, tags, text))
                    
                    blocks = self.text_splitter.split(text, signature)
                    self.embed_split.extend(blocks)
                    
                    self.total_char_count += len(entry['text'])
                    self.total_word_count += len(entry['text'].split())
                    self.total_sentence_count += len(split_into_sentences(entry['text']))
                    self.total_block_count += len(blocks)
                
                except MissingDataException as e:
                    if str(e) not in error_count_dict:
                        error_count_dict[str(e)] = 0
                    error_count_dict[str(e)] += 1

    @retry(wait=wait_random_exponential(min=1, max=100), stop=stop_after_attempt(10))
    def get_embedding(self, text: str, delay_in_seconds: float = 0) -> np.ndarray:
        time.sleep(delay_in_seconds)
        result = openai.Embedding.create(model=EMBEDDING_MODEL, input=text)
        return result["data"][0]["embedding"]

    def get_embeddings(self):
        self.embeddings = np.array([self.get_embedding(text, delay_in_seconds=self.delay_in_seconds) for text in self.embed_split])
    
    def save_embeddings(self, path: str):
        np.save(path, self.embeddings)
        
    def load_embeddings(self, path: str):
        self.embeddings = np.load(path)
        
    def save_class(self, path: str):
        with open(path, 'wb') as f:
            pickle.dump(self, f)        

if __name__ == "__main__":
    dataset = Dataset(path=PATH_TO_DATA, sources=None)
    dataset.get_alignment_texts()
    dataset.get_embeddings()
    dataset.save_embeddings(PATH_TO_EMBEDDINGS)
    dataset.save_class(PATH_TO_DATASET)