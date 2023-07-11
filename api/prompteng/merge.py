from pathlib import Path
import csv

# write answers to answers.csv
with open(Path(__file__).parent / 'data/gpt3.csv', 'r') as f3, \
     open(Path(__file__).parent / 'data/gpt4.csv', 'r') as f4:

    reader3 = csv.reader(f3, quoting = csv.QUOTE_MINIMAL)
    rows3 = [row for row in reader3]

    reader4 = csv.reader(f4, quoting = csv.QUOTE_MINIMAL)
    rows4 = [row for row in reader4]

# [ X ] [ X ]    [ X ] [ X ]
# [ a ] [ 1 ]    [ a ] [ 1 ]
# [ b ] [ 2 ]    [ b ] [ 2 ]
# [ Y ] [ 3 ]          [ 3 ]
# [ a ] [ Y ] -> [ Y ] [ Y ]
# [ b ] [ 1 ]    [ a ] [ 1 ]
# [ c ] [ Z ]    [ b ]
# [ Z ]          [ c ]
#                [ Z ] [ Z ]

indexes3 = {row[0]: i for i, row in enumerate(rows3)}
indexes4 = {row[0]: i for i, row in enumerate(rows4)}

i3 = 0
i4 = 0
rows = []

while i3 < len(rows3) and i4 < len(rows4):
    # simplest case: we're currently matching
    if rows3[i3][0] == rows4[i4][0]:
        rows.append(rows3[i3] + rows4[i4][1:])
        i3 += 1
        i4 += 1
    
    # if we're not matching, we need to find which one is earlier
    else:
        if rows3[i3][0] in indexes4 and indexes4[rows3[i3][0]] > i4:
            rows.append([rows4[i4][0]] + [""] * (len(rows3[i3]) - 1) + rows4[i4][1:])
            i4 += 1
        else:
            rows.append(rows3[i3] + [""] * len(rows4[i4]))
            i3 += 1
    
with open(Path(__file__).parent / 'data/merged.csv', 'w') as f:
    writer = csv.writer(f, quoting = csv.QUOTE_MINIMAL)
    writer.writerows(rows)
