from pathlib import Path
import csv
import sys
import json

sys.path = [str(Path(__file__).parent.parent)] + sys.path
from env import PINECONE_INDEX
from chat import talk_to_robot_simple, set_debug_print
set_debug_print(False)

# read in a list of questions from questions.csv
questions = []
with open(Path(__file__).parent / 'questions.csv', 'r') as f:
    reader = csv.reader(f, quoting = csv.QUOTE_MINIMAL)
    for row in reader:
        questions.append(row[0])

for i, question in enumerate(questions):
    print(f'{i+1}/{len(questions)}: {question}')

answers = []
for i, question in enumerate(questions):
    print(f'{i+1}/{len(questions)}: {question}')
    response = talk_to_robot_simple(PINECONE_INDEX, question, log = lambda x: None)
    answers.append(json.loads(response))
    print(' --- done --- ')

# write answers to answers.csv
with open(Path(__file__).parent / 'answers.csv', 'w') as f:
    writer = csv.writer(f, quoting = csv.QUOTE_MINIMAL)

    # write header
    writer.writerow(['question', 'answer'] + [chr(i) for i in range(ord('a'), ord('z') + 1)])

    for question, answer in zip(questions, answers):

        row = [question, answer['response']]
        citations = answer['citations']

        for c in (chr(i) for i in range(ord('a'), ord('z') + 1)):
            if c not in citations: break
            citation = []
            if 'title' in citations[c]: citation.append(citations[c]['title'])
            if 'author' in citations[c]: citation.append(citations[c]['author'])
            if 'date' in citations[c]: citation.append(citations[c]['date'])
            if 'url' in citations[c]: citation.append(citations[c]['url'])
            citation = [x.strip() for x in citation]
            citation = [x for x in citation if x != '']
            row.append(' --- '.join(citation))


        writer.writerow(row)


