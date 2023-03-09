from dataset import Dataset
from semantic_search import AlignmentSearch

from settings import DATA_PATH

def main():
    dataset = Dataset(DATA_PATH)
    dataset.get_alignment_texts()
    dataset.load_embeddings()
    search_and_answer = AlignmentSearch(dataset)
    question = "What is an agent?"
    answer = search_and_answer.search_and_answer(question)
    print(answer)
    
if __name__ == "__main__":
    main()