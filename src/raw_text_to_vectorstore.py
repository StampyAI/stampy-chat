import pickle

from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import TokenTextSplitter
from langchain.vectorstores.faiss import FAISS

def get_documents_without_signature_from_raw_text(text, chunk_size=300, chunk_overlap=0):
    text_splitter = TokenTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=0
        )
    return text_splitter.split_text(text)

def get_documents_from_raw_text(text, signature, chunk_size=300, chunk_overlap=0):
    #signature is a string like : "{link}: {title} by {author}\n\n"
    documents = get_documents_without_signature_from_raw_text(text, chunk_size, chunk_overlap)
    return [signature + document for document in documents]




#untested
def save_documents_as_vectorstore(documents):
    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_documents(documents, embeddings)
    
    #save vectorstore
    with open('vectorstore.pickle', 'wb') as f:
        pickle.dump(vectorstore, f)

def load_vectorstore():
    with open('vectorstore.pickle', 'rb') as f:
        vectorstore = pickle.load(f)
    return vectorstore



if __name__ == "__main__":

    example_raw_text = """ Today, we're going to talk about Dark rationalist techniques: productivity tools which seem incoherent, mad, and downright irrational. These techniques include:

Willful Inconsistency
Intentional Compartmentalization
Modifying Terminal Goals
I expect many of you are already up in arms. It seems obvious that consistency is a virtue, that compartmentalization is a flaw, and that one should never modify their terminal goals.

I claim that these 'obvious' objections are incorrect, and that all three of these techniques can be instrumentally rational.

In this article, I'll promote the strategic cultivation of false beliefs and condone mindhacking on the values you hold most dear. Truly, these are Dark Arts. I aim to convince you that sometimes, the benefits are worth the price.


Changing your Terminal Goals
In many games there is no "absolutely optimal" strategy. Consider the Prisoner's Dilemma. The optimal strategy depends entirely upon the strategies of the other players. Entirely.

Intuitively, you may believe that there are some fixed "rational" strategies. Perhaps you think that even though complex behavior is dependent upon other players, there are still some constants, like "Never cooperate with DefectBot". DefectBot always defects against you, so you should never cooperate with it. Cooperating with DefectBot would be insane. Right?

Wrong. If you find yourself on a playing field where everyone else is a TrollBot (players who cooperate with you if and only if you cooperate with DefectBot) then you should cooperate with DefectBots and defect against TrollBots.

Consider that. There are playing fields where you should cooperate with DefectBot, even though that looks completely insane from a naïve viewpoint. Optimality is not a feature of the strategy, it is a relationship between the strategy and the playing field.

Take this lesson to heart: in certain games, there are strange playing fields where the optimal move looks completely irrational.

I'm here to convince you that life is one of those games, and that you occupy a strange playing field right now.

Here's a toy example of a strange playing field, which illustrates the fact that even your terminal goals are not sacred:

Imagine that you are completely self-consistent and have a utility function. For the sake of the thought experiment, pretend that your terminal goals are distinct, exclusive, orthogonal, and clearly labeled. You value your goals being achieved, but you have no preferences about how they are achieved or what happens afterwards (unless the goal explicitly mentions the past/future, in which case achieving the goal puts limits on the past/future). You possess at least two terminal goals, one of which we will call A.

Omega descends from on high and makes you an offer. Omega will cause your terminal goal A to become achieved over a certain span of time, without any expenditure of resources. As a price of taking the offer, you must switch out terminal goal A for terminal goal B. Omega guarantees that B is orthogonal to A and all your other terminal goals. Omega further guarantees that you will achieve B using less time and resources than you would have spent on A. Any other concerns you have are addressed via similar guarantees.

Clearly, you should take the offer. One of your terminal goals will be achieved, and while you'll be pursuing a new terminal goal that you (before the offer) don't care about, you'll come out ahead in terms of time and resources which can be spent achieving your other goals.

So the optimal move, in this scenario, is to change your terminal goals.

There are times when the optimal move of a rational agent is to hack its own terminal goals.

You may find this counter-intuitive. It helps to remember that "optimality" depends as much upon the playing field as upon the strategy.

Next, I claim that such scenarios not restricted to toy games where Omega messes with your head. Humans encounter similar situations on a day-to-day basis.

Humans often find themselves in a position where they should modify their terminal goals, and the reason is simple: our thoughts do not have direct control over our motivation.

Unfortunately for us, our "motivation circuits" can distinguish between terminal and instrumental goals. It is often easier to put in effort, experience inspiration, and work tirelessly when pursuing a terminal goal as opposed to an instrumental goal. It would be nice if this were not the case, but it's a fact of our hardware: we're going to do X more if we want to do X for its own sake as opposed to when we force X upon ourselves.

Consider, for example, a young woman who wants to be a rockstar. She wants the fame, the money, and the lifestyle: these are her "terminal goals". She lives in some strange world where rockstardom is wholly dependent upon merit (rather than social luck and network effects), and decides that in order to become a rockstar she has to produce really good music.

But here's the problem: She's a human. Her conscious decisions don't directly affect her motivation.

In her case, it turns out that she can make better music when "Make Good Music" is a terminal goal as opposed to an instrumental goal.

When "Make Good Music" is an instrumental goal, she schedules practice time on a sitar and grinds out the hours. But she doesn't really like it, so she cuts corners whenever akrasia comes knocking. She lacks inspiration and spends her spare hours dreaming of stardom. Her songs are shallow and trite.

When "Make Good Music" is a terminal goal, music pours forth, and she spends every spare hour playing her sitar: not because she knows that she "should" practice, but because you couldn't pry her sitar from her cold dead fingers. She's not "practicing", she's pouring out her soul, and no"""
    raw_text_signature = "https://www.lesswrong.com: Misalignment Failures by Paul Christiano\n\n"

    documents = get_documents_from_raw_text(
        example_raw_text, raw_text_signature, chunk_size=5000, chunk_overlap=100
        )
    save_documents_as_vectorstore(documents)
    vectorstore = load_vectorstore()