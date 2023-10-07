# [https://chat.stampy.ai](https://chat.stampy.ai)
# stampy-chat

The Stampy conversational chatbot answers questions about AI Safety & Alignment based on information retrieved from the [Alignment Research Dataset (ARD)](https://github.com/moirage/alignment-research-dataset). The project has 2 components:

1. `api/` **Backend API** - Given a user's query and chat history, the most semantically similar chunks are retrieved from the vector store then a large language model is prompted to answer the query based on the retrieved context. The generated answer is returned along with cited sources.

2. `web/` **Frontend GUI** - Web app that calls the backend API and displaying the conversation flow.

## What is the purpose of Stampy?

With the recent development in AI, growing concern and interest in AI Safety & Alignment is coupled with tons of information and misinformation. Sifting through all the text while trying to identify quality sources is a daunting barrier for entry. Stampy not only strives to provide quality information but also allows people to contribute while learning. The FAQs are hand curated and limited by volunteer bandwidth. This chatbot leverages LLM to synthesize & summarize the ever expanding literature.

## Usage

### Environment Setup

In the `api/` directory, rename `.env.example` to `.env`. Edit this file and
fill in the placeholder values with valid credentials. Message the
`#stampy-dev` channel on the [Rob Miles AI
Discord](https://discord.com/invite/Bt8PaRTDQC) if you need help with this.

Install `npm`, `python 3.11`, and [`pipenv`](https://pipenv.pypa.io/en/latest/).

### Database setup

Some things (e.g. logging) require a database connection to work correctly. To make this easier, there is a script to set one up locally via Docker. To get this working:

* Install mysql on your local machine
* [Install Docker](https://docs.docker.com/get-docker/)
* Run the script: `./local_db.sh`

This should start the database, make sure it's up to date, then as a final step display a command that will allow you to connect to it directly if you want to.

### Running a local version

Open two terminal windows. In the first, run:

```bash
cd api
pipenv install --dev --ignore-pipfile # (skip this line after the first time)
pipenv run python3 main.py
```

In the second, run:

```bash
cd web
npm install # (skip this line after the first time)
npm run dev
```

In the second window, a URL will be printed. Probably `http://localhost:3000`.
Paste this into your browser to see the app.

## Original Prototypes

The prototypes below were developed in response to a [bounty on LessWrong](https://www.lesswrong.com/posts/SLRLuiuDykfTdmesK/speed-running-everyone-through-the-bad-alignement-bingo).
The teams collaborated and key features were combined into one project.

Name | Demo App | Code Notes
-- | -- | --
McGill's AlignmentSearch | https://alignmentsearch.up.railway.app/ | https://github.com/FraserLee/AlignmentSearch<br>https://www.lesswrong.com/posts/bGn9ZjeuJCg7HkKBj/introducing-alignmentsearch-an-ai-alignment-informed
Craig's AlignmentGPT | http://tidblitz.com/ | https://github.com/cvarrichio/alignmentchat
Stampy's Chat | http://chat.stampy.ai/ | https://github.com/ccstan99/stampy-chat<br>https://github.com/stampyAI/stampy-nlp/
