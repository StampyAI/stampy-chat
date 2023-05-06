# stampy-chat

The Stampy conversational chatbot answers questions about AI Safety & Alignment based on information retrieved from the [Alignment Research Dataset (ARD)](https://github.com/moirage/alignment-research-dataset). The project has 3 components:

1. `src/` **Data** - ARD is ingested by splitting text into chunks then embedded and uploaded into a vector store along with relevant metadata about the chunk of text.
2. `api/` **Backend API** - Given a user's query and chat history, the most semantically similar chunks are retrieved from the vector store then a large language model is prompted to answer the query based on the retrieved context. The generated answer is returned along with cited sources.
3. `web/` **Frontend GUI** - Web app that calls the backend API and displaying the conversation flow.

## What is the purpose of Stampy?

With the recent development in AI, growing concern and interest in AI Safety & Alignment is coupled with tons of information and misinformation. Sifting through all the text while trying to identify quality sources is a daunting barrier for entry. Stampy not only strives to provide quality information but also allows people to contribute while learning. The FAQs are hand curated and limited by volunteer bandwidth. A chatbot can leverage LLMs to synthesize & summarize the ever expanding literature.

## Who are the users?

In general, the Stampy project serves users at 3 levels of understanding:

- **New** - People completely new to AI Safety & Alignment. Many volunteers have technical backgrounds but not necessarily much experience with ML per se. The website & chatbot should be accessible by the general public, so jargon should be minimized where possible.

- **Moderate** - However, there should also be enough “meaty” content for people who are ready to delve deeper. Beyond raising general awareness about the field, another objective for the project is to engage & build a community for those hoping to upskill or transition into the field. People can contribute by answering questions, developing software, or offering skills they have.

- **Knowledgeable** experts who might want to share their research by answering questions.

Given the disparate backgrounds of users, for both the website and chatbot, we should consider having users identify their starting level (new, moderate, knowledgeable). On the website, the list of starter and recommended questions would be tuned to the user’s level. Similarly, the chatbot's usage of technical terminology could be adjusted to their level.

## Original Prototypes

The prototypes below were developed in response to a [bounty on LessWrong](https://www.lesswrong.com/posts/SLRLuiuDykfTdmesK/speed-running-everyone-through-the-bad-alignement-bingo).
The teams collaborated and key features were combined into one project.

Name | Demo App | Code Notes
-- | -- | --
McGill's AlignmentSearch | https://alignmentsearch.up.railway.app/ | https://github.com/FraserLee/AlignmentSearch<br>https://tinyurl.com/alignmentsearchgdocs
Craig's AlignmentGPT | http://tidblitz.com/ | https://github.com/cvarrichio/alignmentchat
Stampy's Chat | http://chat.stampy.ai/ | https://github.com/ccstan99/stampy-chat<br>https://github.com/stampyAI/stampy-nlp/