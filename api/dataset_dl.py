import pickle
import requests
import os

print('Downloading dataset...')

url = os.environ.get('DATASET_URL')
if url is None:
    print('No dataset url provided.')
    exit()

dataset_dict_bytes = requests.get(url).content

print('Unpacking dataset...')
dataset_dict = pickle.loads(dataset_dict_bytes)

print('Writing dataset to disk...')
with open('dataset.pkl', 'wb') as f:
    pickle.dump(dataset_dict, f)

print('Done!')
