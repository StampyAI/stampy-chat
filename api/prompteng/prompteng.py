from pathlib import Path
import csv
import sys

sys.path = [str(Path(__file__).parent.parent)] + sys.path
from env import PINECONE_INDEX
from chat import talk_to_robot_simple, set_debug_print
set_debug_print(False)

# read in a list of questions from questions.csv
questions = []
with open(Path(__file__).parent / 'questions.txt', 'r') as f:
    for line in f:
        questions.append(line.strip())

answers = []
for i, question in enumerate(questions):
    print(f'{i}/{len(questions)}: {question}')
    answers.append(talk_to_robot_simple(PINECONE_INDEX, question, log = lambda x: None))
    print(' --- done --- ')

# write answers to answers.csv
with open(Path(__file__).parent / 'answers.csv', 'w') as f:
    writer = csv.writer(f, quoting = csv.QUOTE_MINIMAL)
    writer.writerow(['question', 'answer'])
    writer.writerows(zip(questions, answers))
