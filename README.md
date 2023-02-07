# AlignmentSearch

This project creates embeddings for every set of a few paragraphs from the source dataset, in order to do real-time semantic search and question answering on them.

The very barebones of the project is currently in src/testing.ipynb. file which contains: 

To try out, add a src/config.py file which contains your OPENAI_API_KEY.

## TODO:
- Getting data:
    - Figure out the right format for the dataset
    - Get entirety of data
    - Searches for new posts/papers/etc and scrape them, runs once a day
    - Async API calls for embeddings (otherwise it is going to take years)
- Semantic search:
    - Test out other techniques than just vector similarity (e.g. LSH-index, see Dense Retrieval methods (here)[https://medium.com/@aikho/deep-learning-in-information-retrieval-part-ii-dense-retrieval-1f9fecb47de9])
    - Test other embeddings models ((SimCSE)[https://github.com/princeton-nlp/SimCSE] possibly SOTA?)
- Question answering:
    - Test out other models prompts to see which is best
- Summarization:
    - Test out other models and prompts to see which is best (Forefront?)
- Info extraction from PDF:
    - Specifically mentioned by Anson. Look into methods by Mely.ai to extract tables from PDFs maybe?
    - Test various techniques to make it more performant
- Finetuning:
    - Finetune embeddings model
    - Finetune q&a model
    - Finetune summarization model
    - Finetune info extraction model
- Other:
    - Create website/other. Not sure what would be most helpful here (Find someone that can figure this out)
    - Document search (give descriptions of a post/document/video/article/book/etc related to alignment, and get top semantically related result)

## Ideas
- The whole dataset with embeddings doesn't fit on the frontend, but requests take a while. Solution: have a useful but small fraction of the dataset on the front end, get similarity score for embeddings, and do real time semantic search. However, every time the user presses space or enter, do the call to do semantic search over the full dataset.


Source dataset: Kirchner, J. H., Smith, L., Thibodeau, J., McDonnell, K., and Reynolds, L. "Understanding AI alignment research: A Systematic Analysis." arXiv preprint arXiv:2022.4338861 (2022).
