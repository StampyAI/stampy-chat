# dataset/text_splitter.py

import re
from typing import List
import tiktoken

import re
from typing import List
import nltk


# Download the Punkt tokenizer if you haven't already. 
# If you want to save a second everytime you run this file you can comment
# it out after the first time it was downloaded.
nltk.download("punkt")



def split_into_sentences(text: str) -> List[str]:
    """
    Splits the input text into sentences.

    :param text: The input text to be split.
    :return: A list of sentences.
    """
    text = text.replace("\n", " ")    # Replace newline characters with spaces
    sentences = nltk.sent_tokenize(text)    # Use the Punkt tokenizer from the NLTK library to split the text into sentences
    sentences = [s.strip() for s in sentences]    # Strip leading and trailing whitespace from each sentence
    return sentences


class TokenSplitter:
    """Splits text into blocks of tokens according to chatgpt's tokenizer."""

    def __init__(self, min_tokens: int = 200, max_tokens: int = 300):
        self.encoding = tiktoken.get_encoding("cl100k_base")
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens
        self.default_signature = "{url, title, author} unknown"

    def _text_splitter(self, text: str, signature: str) -> List[str]:
        """Splits text into blocks of tokens according to chatgpt's tokenizer."""
        # enc = self.encoding.encode  # takes a string and returns a list of ints (tokens)
        enc = self.encoding.encode_ordinary  # takes a string and returns a list of ints (tokens)
        dec = self.encoding.decode  # takes a list of ints (tokens) and returns a string
        tok_len = lambda x: len(enc(x))  # length of a string in tokens

        max_tokens = self.max_tokens - tok_len(signature) - 10  # 10 to be safe
        assert max_tokens > 0, "max_tokens is too small for the signature"

        min_tokens = self.min_tokens - tok_len(signature) - 10  # 10 to be safe
        assert min_tokens > 0, "min_tokens is too small for the signature"

        blocks = []
        current_block = ""
        paragraphs = text.split("\n\n")
        
        for paragraph in paragraphs:
            sentences = split_into_sentences(paragraph)
            if current_block != "":
                current_block += "\n\n"

            for sentence in sentences:
                potential_new_block = f"{current_block} {sentence}"
                
                if tok_len(potential_new_block) <= max_tokens:
                    current_block = potential_new_block
                
                else:
                    blocks.append(current_block)
                    if tok_len(sentence) < max_tokens:
                        current_block = sentence
                    else:
                        blocks.append(dec(enc(sentence)[:max_tokens]))
                        current_block = ""
            
            if tok_len(current_block) > min_tokens:
                blocks.append(current_block)
                current_block = ""

        if current_block != "":
            if len(blocks) == 0:
                blocks.append(current_block)
            else:
                latest_block = blocks[-1]
                len_cur_block = tok_len(current_block)
                latest_plus_current = latest_block + current_block

                if len_cur_block > min_tokens:
                    blocks.append(current_block)
                
                else:
                    # select the last self.max_tokens tokens from the latest block
                    last_block = dec(enc(latest_plus_current)[-max_tokens:])
                    blocks.append(last_block)

        return [block.strip() for block in blocks]

    def split(self, text: str, signature: str = None) -> List[str]:
        if signature is None:
            signature = self.default_signature

        blocks = self._text_splitter(text, signature)

        # Check all block elements are strings
        assert all([isinstance(block, str) for block in blocks]), "block elements are not strings"

        output = [f'"{block}"\n- {signature}' for block in blocks]
        # Check all output elements are strings
        assert all([isinstance(block, str) for block in output]), "output elements are not strings"

        return output

if __name__ == "__main__":
    text = """This post has been recorded as part of the LessWrong Curated Podcast, and an be listened to on Spotify, Apple Podcasts, and Libsyn.

Over the last few years, deep-learning-based AI has progressed extremely rapidly in fields like natural language processing and image generation. However, self-driving cars seem stuck in perpetual beta mode, and aggressive predictions there have repeatedly been disappointing. Google's self-driving project started four years before AlexNet kicked off the deep learning revolution, and it still isn't deployed at large scale, thirteen years later. Why are these fields getting such different results?

Right now, I think the biggest answer is that ML benchmarks judge models by average-case performance, while self-driving cars (and many other applications) require matching human worst-case performance. For MNIST, an easy handwriting recognition task, performance tops out at around 99.9% even for top models; it's not very practical to design for or measure higher reliability than that, because the test set is just 10,000 images and a handful are ambiguous. Redwood Research, which is exploring worst-case performance in the context of AI alignment, got reliability rates around 99.997% for their text generation models.

By comparison, human drivers are ridiculously reliable. The US has around one traffic fatality per 100 million miles driven; if a human driver makes 100 decisions per mile, that gets you a worst-case reliability of ~1:10,000,000,000 or ~99.999999999%. That's around five orders of magnitude better than a very good deep learning model, and you get that even in an open environment, where data isn't pre-filtered and there are sometimes random mechanical failures. Matching that bar is hard! I'm sure future AI will get there, but each additional "nine" of reliability is typically another unit of engineering effort. (Note that current self-driving systems use a mix of different models embedded in a larger framework, not one model trained end-to-end like GPT-3.)

(The numbers here are only rough Fermi estimates. I'm sure one could nitpick them by going into pre-pandemic vs. post-pandemic crash rates, laws in the US vs. other countries, what percentage of crashes are drunk drivers, do drunk drivers count, how often would a really bad decision be fatal, etc. But I'm confident that whichever way you do the math, you'll still find that humans are many orders of magnitude more reliable.)

Other types of accidents are similarly rare. Eg. pre-pandemic, there were around 40 million commercial flights per year, but only a handful of fatal crashes. If each flight involves 100 chances for the pilot to crash the plane by screwing up, then that would get you a reliability rate around 1:1,000,000,000, or ~99.99999999%.

Even obviously dangerous activities can have very low critical failure rates. For example, shooting is a popular hobby in the US; the US market buys around 10 billion rounds of ammunition per year. There are around 500 accidental gun deaths per year, so shooting a gun has a reliability rate against accidental death of ~1:20,000,000, or 99.999995%. In a military context, the accidental death rate was around ten per year against ~1 billion rounds fired, for a reliability rate of ~99.9999999%. Deaths by fire are very rare compared to how often humans use candles, stoves, and so on; New York subway deaths are rare compared to several billion annual rides; out of hundreds of millions of hikers, only a tiny percentage fall off of cliffs; and so forth.

The 2016 AI Impacts survey asked hundreds of AI researchers when they thought AI would be capable of doing certain tasks, playing poker, proving theorems and so on. Some tasks have been solved or have a solution "in sight", but right now, we're nowhere close to an AI that can replace human surgeons; robot-assisted surgeries still have manual control by human operators. Cosmetic surgeries on healthy patients have a fatality rate around 1:300,000, even before excluding unpredictable problems like blood clots. If a typical procedure involves two hundred chances to kill the patient by messing up, then an AI surgeon would need a reliability rate of at least 99.999998%.

One concern with GPT-3 has been that it might accidentally be racist or offensive. Humans are, of course, sometimes racist or offensive, but in a tightly controlled Western professional context, it's pretty rare. Eg., one McDonald's employee was fired for yelling racial slurs at a customer. But McDonald's serves 70 million people a day, ~1% of the world's population. Assuming that 10% of such incidents get a news story and there's about one story per year, a similar language model would need a reliability rate of around 1:2,500,000,000, or 99.99999996%, to match McDonald's workers. When I did AI for the McDonald's drive-thru, the language model wasn't allowed to generate text at all. All spoken dialog had to be pre-approved and then manually engineered in. Reliability is hard!

On the one hand, this might seem slightly optimistic for AI alignment research, since commercial AI teams will have to get better worst-case bounds on AI behavior for immediate economic reasons. On the other hand, because so much of the risk of AI is concentrated into a small number of very bad outcomes, it seems like such engineering might get us AIs that appear safe, and almost always are safe, but will still cause catastrophic failure in conditions that weren't anticipated. That seems bad."""
    text = """Imagine it's late autumn of 332 BC. You're Alexander the Great, and your armies are marching toward Egypt from Gaza. There’s just one little problem: you need to cross the Sinai peninsula - 150 miles of hot, barren desert. How will you carry food and water for the troops?


Green triangle on the left is the Nile river delta in Egypt; green chunk in the upper right is Israel. The big desert peninsula between them is the Sinai.

Option 1: carry it

A physically-active human needs about 3 lbs of food per day. (Modern hikers can probably find lighter calorie-dense foodstuffs, but we’re talking ancient history here.) Water requirements vary; 5 lbs is a minimum, but the US Army Quartermaster Corps recommends 20 lbs/day when marching through a hot desert. Alexander’s army crossed the desert in 7 days. Food might be reasonable, but to carry the water would mean 7*20 = 140 lbs per person, plus 50+ lbs of armor, weapons, etc.

When I go hiking, I aim for a 20-30 lb pack. US marines are apparently expected to be able to carry 150 lbs for 9 miles - quite a bit less than the 20+ miles/day Alexander’s army managed, and with no comment on how long the marine in question might need to rest afterwards. (Also, I’m not sure I trust that source - 150 lbs for 9 miles sounds unrealistic to me, and if it’s true then I’m very impressed by marines.)

Suffice to say that carrying that much water across that much desert is not a realistic option, even if we drink it along the way.

Option 2: horses

A horse consumes 20 lbs of food (half of which may be forage) and 80 lbs of water per day. In exchange, it can carry about 200 lbs (surprisingly, my source claims that horses can carry more than they can pull). Of course, that 200 lbs has to include the horse’s own food and water, plus whatever useful load it’s carrying. So, marching through a desert, a horse can only transport (200 lbs)/(80+20 lbs/day) = 2 days of supplies for itself, and that’s before whatever useful things actually need to be transported.

In other words, there’s a hard upper limit on how far goods can be transported by horse without refilling supplies along the way. That limit is around 2 days travel time without any refill, 10 days if there’s plenty of fresh water along the route, or 20 days if there’s both water and forage. At 20 miles/day, that’s 40, 200, or 400 miles. Realistically, if we want the number of horses to be reasonable, the limit is more like half that much - 20 miles, 100 miles, or 200 miles, respectively.

So horses also won’t work.

Option 2.5: camels or other pack animals

Contrary to popular image, camels actually need more water than horses. They can go a couple days without, but then need to fill up all at once. They can also carry a bit more weight, but they eat more food. At the end of the day, the numbers end up quite similar.

Mules also end up with similar numbers, and cattle are generally worse.

Option 3: ships

Assuming the army marches along the coast, a supply fleet can sail alongside. At the time, a single large merchant ship could carry 400 tons - in other words, as much as about 4000 horses. Presumably the ship would cost a lot less than the horses, too.

Well then, there’s our answer. Ships are clearly a vastly superior way to move goods. Range is a non-issue, capacity is far larger, and they’re far cheaper. They’re perfect for crossing the Sinai, which runs right along the coast anyway.

Fast forward a few years to 327 BC, and Alexander is marching his armies back from India. He plans to cross the Gedrosian desert, along the coast of modern-day Pakistan and Iran. The plan is much like the Sinai: a supply fleet will sail alongside the army. Unfortunately, neither Alexander nor his commanders knows about the monsoons: across most of south Asia, the wind blows consistently southwest for half the year, and consistently northeast for the other half. There is nothing like it in the Mediterranean. And so, Alexander marches out expecting the fleet to catch up as soon as the winds turn - not realizing that the winds will not turn for months. Three quarters of his soldiers die in the desert.

Thus end the campaigns of Alexander.

Generalization
The above numbers are drawn from Donald Engels’ book Alexander the Great and the Logistics of Macedonian Army. But it tells us a lot more about the world than just the logistics of one particular ancient army.

First, this highlights the importance of naval dominance in premodern warfare. A fleet was a far superior supply train, capable of moving a high volume of food and water over long distance at relatively low cost. Without a fleet, transport of food became expensive at best, regular resupply became a strategic necessity, and long routes through arid terrain became altogether impassable. Destroying an enemy’s fleet meant starving the army. Likewise, controlling ports wasn’t just for show - without a port, feeding the army became a serious problem.

Another interesting insight into premodern warfare: away from friendly seas and rivers, the only way to keep an army fed was to either seize grain from enemies, or buy it from allies, either of whom needed to already be nearby. In Alexander’s case, deals were often struck to establish supply caches along the army’s intended route.

An interesting exercise: to what extent was transportation a binding constraint on the size of premodern towns/cities? (One number you may want: Braudel (pg 121) estimates that 5000 square meters of land growing wheat would provide one person-year of food, not accounting for crop rotation.) Leave a comment if you try a calculation here; I'm curious to see how other peoples' models compare to my own.

Modern Day
Today we have trains and trucks and roads, so the transportation constraint has relaxed somewhat. But here’s an interesting comparison: a modern 18-wheeler in the US is legally limited to haul 40 tons, while a panamax ship could carry about 50k tons through the canal (prior to the opening of the new locks in 2016). That’s a ratio of a bit over 1000 - surprisingly similar to the ship/horse ratio of antiquity, especially considering the much larger new-panamax and super-panamax ships also in use today.


Can we get a quick-and-dirty feel for tautness of the transportation constraint today? Here are a few very different angles:

This USDA study shows rates on produce transport, typically about 7-20 cents per pound (see figure 6). The Smart & Final grocery store near me sells the cheaper produce items looked at in that study (bell peppers, cantaloupes, tomatoes, oranges) for 70-100 cents per pound, so transport alone is roughly 10-20% of the cost-to-consumer.
What about transporting humans? Average commute in the US is ~30 minutes each way; driving is usually in the 20-30 minute range, while public transit is usually 30-50. Assuming 8 hr workdays, that means commutes are typically ~10-20% of our work-hours.
The bureau of transportation estimates transport at 5.6% of the US economy for a very narrow measure, or 8.9% with a broader measure (though this still excludes non-market transport costs like e.g. commute time).
My interpretation: the transportation constraint becomes taut when it accounts for 10-20% of cost. If it’s less than that, it usually doesn’t limit production - we see plenty of goods which aren’t transportation-dependent or which are higher-value-per-weight, and the transportation constraint is generally slack for those. But once transportation hits about 10-20%, people start looking for alternatives, i.e. producing the goods somewhere else or using alternative goods. Obviously this is not based on very much data, but I find it intuitively plausible.

Compared to ancient times, transportation constraints have obviously relaxed quite a lot. Yet qualitatively, the world today still does not look like a world of fully slack transportation constraints. To wrap up, let’s discuss what that would look like.

Extreme Slackness
In Material Goods as an Abundant Resource, we discussed the world of the duplicator - a device capable of copying any item placed on it. In such a world, material scarcity is removed as an economic constraint - all material constraints are completely slack.

What would be a corresponding sci-fi device for transportation constraints, and what would that world look like?

I suggest portals: imagine we can create pairs of devices capable of transporting things from one device to the other, across any distance, at the speed of light. (We could instead imagine teleporters, removing the need for a pre-installed device at either end, but then the entire discussion would be about security.) What does the world of the portal look like?

First, there’s complete geographical decoupling of production from consumption. People have no need to live near where they work; companies can put offices and factories wherever real estate is cheap. We can enjoy miles of wilderness on the back porch and a downtown district on the front porch; a swimming pool can open right into the ocean. Buying direct from the farm or factory is standard for most material goods.

What are now tourist destinations would become options for an evening activity. Disneyworld would sell a park-hopper ticket that includes Disneyland California, Paris, and Shanghai, but the price of that ticket would be high enough to prevent the parks from becoming unpleasantly crowded - probably quite a bit more expensive than today, though possibly cheaper than today’s flights to Orlando.

Obviously roads would cease to exist. Huge amounts of land would revert from asphalt to wilderness, but buildings would also be much more spread out. Buildings would be built close together more for show than for function - e.g. to provide the ambiance of a downtown or a community to those who want it. Physical life, in general, would look more like the structure of the internet rather than the structure of geography; “cities” would be clusters very spread out in space but very tightly connected via the portal network. Filter bubbles would be a much more physically tangible phenomenon.

Geographically-defined governments would likely be replaced by some other form of government - governments based around access to portal hubs/networks are one natural possibility. Security would be a priority, early on - carrying an unauthorized portal into an area would earn a facefull of high explosives. On the other hand, it would be hard to prevent a high degree of mobility between areas controlled by different governments; the implications for government behavior are conceptually similar to seasteading.

The structure of space near portal networks would be different in a big-O sense; the amount of space at a distance of about 
r
 would increase exponentially, rather than like 
r
2
. A nuclear warhead could go off five hundred feet away and you’d feel a breeze through a fast-branching portal network. On the other hand, viruses could spread much more rapidly.

Anyway, at this point we’re getting into specifics of portals, so I’ll cut off the speculation. The point is: if transportation continues to get cheaper and more efficient over time, then we will converge to the world of the portal, or at least something like it. The details do matter - portals are different from teleportation or whatever might actually happen - but any method of fully relaxing transportation constraints will have qualitatively similar results, to a large extent."""
   
    signature = "Title: Humans are very reliable agents, Author: alyssavance"

    splitting = TokenSplitter(max_tokens=200, min_tokens=300)
    blocks = splitting.split(text, signature)
    context = "Context: " + "\n\n---\n\n".join(blocks)
    print(context)
