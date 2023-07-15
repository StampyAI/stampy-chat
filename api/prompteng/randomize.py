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

rows = rows[:5]

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
        f.write(f'{i + 1}: {"LEFT is gpt4, right is gpt3" if swapped else "left is gpt3, RIGHT is gpt4"}\n')

