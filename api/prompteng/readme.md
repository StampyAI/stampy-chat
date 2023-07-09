# Prompt Engineering Workflow

As I had said previously, our prompt is a function - not a template. Certain
parameters like what goes in a system vs a user prompt, how we delineate
sources, where to break messages, how to handle history, etc - it's too much
weight to be cleanly represented with anything but code. That said, this
process should be fairly simple and straightforwards even to non-technical
people:

1. Edit the function `construct_prompt` in `api/chat.py`
2. `cd api`
3. run `pipenv run python3 prompteng/prompteng.py`
4. open the google sheet
5. click `file->import`. Click `upload`. Drag and drop the file `api/prompteng/data/answers.csv`
6. press `cmd + a`. Click `format->wrapping->wrap`. Adjust column widths to preference.
