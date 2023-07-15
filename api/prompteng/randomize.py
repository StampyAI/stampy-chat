from pathlib import Path
import csv
import random
import imgkit

data = []
with open(Path(__file__).parent / 'data/merged.csv', 'r') as f:
    reader = csv.reader(f, quoting = csv.QUOTE_MINIMAL)
    data = [row for row in reader]

rows = []
for row in data:
    if len(row[0].strip()) > 1:
        rows.append(row)
        for i in range(1, len(rows[-1])):
            rows[-1][i] += '\n\n' + '-' * 80 + '\n'
    else:
        for i in range(1, len(rows[-1])):
            rows[-1][i] += '\n' + row[i]

valid_questions = [
    'I\'m not convinced, why is this important?',
    'What are "scaling laws" and how are they relevant to safety?',
    'What does the term "x-risk" mean?',
    'What is "instrumental convergence"?',
    'What is the "orthogonality thesis"?',
    'Why would we expect AI to be "misaligned by default"?',
    'Are there any regulatory efforts aimed at addressing AI safety and alignment concerns?',
    'Can AI become conscious or have feelings?',
    'Can AI take over the world?',
    'Can we just turn off AI if it becomes dangerous?',
    'Hi, I would like to onboard into AI safety',
    'How can I help with AI safety and alignment?',
    'How can we ensure that AI systems are transparent and explainable in their decision-making processes?',
    'What are some examples of AI safety and alignment research that are currently being pursued?',
    'What does corrigibility mean?',
    'What does Paul Christiano believe?',
    'What is a mesa-optimizer?',
    'What is an Intelligence Explosion?',
    'What is Pascal\'s mugging?',
    'What is prosaic alignment?',
    'What role do policymakers and regulators play in ensuring AI safety and alignment?',
    'What was that paper where they trained an AI to drive a boat in a video game?',
    'Who is Eliezer Yudkowsky?',
    'Will AI replace all human jobs?',
    'Will you kill us all?',
]

rows = [row for row in rows if row[0].strip() in valid_questions]

is_swapped = [False] * len(rows)
for i in range(len(rows)):
    if random.random() < 0.5:
        rows[i][1], rows[i][2] = rows[i][2], rows[i][1]
        is_swapped[i] = True




# for each row, generate a png with the two side by side
width = 1200
for i in range(len(rows)):
    html = f'''
<html>
  <head>
    <style>
      body {{
        margin: 4px;
        width: {width}px;
      }}
      p {{
        white-space: pre-wrap;
        word-wrap: break-word;
        font-family: Arial, Helvetica, sans-serif;
      }}
      h2 {{
        text-align: center;
        font-family: Helvetica, sans-serif;
        font-size: 3em;
        margin: 2.5%;
      }}
      .left {{
        float: left;
        width: 45%;
        margin: 2.5%;
      }}
      .right {{
        float: right;
        width: 45%;
        margin: 2.5%;
      }}
    </style>
  </head>
  <body>
    <h2>{rows[i][0]}</h2>
    <div class="left">
      <p>{rows[i][1]}</p>
    </div>
    <div class="right">
      <p>{rows[i][2]}</p>
    </div>
  </body>
</html>
    '''
    imgkit.from_string(html, f'out/{i+1}.png', options = {'width': width})
    
# write an answer key
with open('out/answer_key.txt', 'w') as f:
    for i, swapped in enumerate(is_swapped):
        f.write(f'Q{i + 1}: {rows[i][0]}\n')
        f.write(f'Q{i + 1}: {"LEFT is gpt4, right is gpt3" if swapped else "left is gpt3, RIGHT is gpt4"}\n')

