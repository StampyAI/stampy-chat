import numpy as np
import pickle
import openai

import config
from semantic_search import AlignmentSearch
from settings import PATH_TO_DATASET

openai.api_key = config.OPENAI_API_KEY


def main():
    with open(PATH_TO_DATASET, 'rb') as f:
        dataset = pickle.load(f)
    AS = AlignmentSearch(dataset=dataset)
    prompt = "What would be an idea to solve the Alignment Problem? Name the Lesswrong post by Quintin Pope that discusses this idea."
    answer = AS.search_and_answer(prompt, 3, HyDE=False)
    print(answer)
    
if __name__ == "__main__":
    main()