import random
import nltk
from nltk.tokenize import wordpunct_tokenize
from nltk.corpus import wordnet as wn
from .core import Glitchling

nltk.download("wordnet")


def replace_noun_phrases(
    text: str, max_replacement_rate: float = 0.1, seed: int = 151
) -> str:
    """Replace noun phrases in the text with a random synonym."""
    random.seed(seed)
    nouns = list(
        set([w for w in wordpunct_tokenize(text) if wn.synsets(w, pos=wn.NOUN)])
    )
    max_replacements = int(len(nouns) * max_replacement_rate)
    random.shuffle(nouns)
    i = 0
    while i < max_replacements and nouns:
        noun = nouns.pop()
        synsets = wn.synsets(noun, pos=wn.NOUN)
        if synsets:
            synonyms = [lemma.name() for lemma in synsets[0].lemmas()]
            if synonyms:
                text = text.replace(noun, random.choice(synonyms), 1)
        i += 1
    return text


jargoyle = Glitchling(name="Jargoyle", corruption_function=replace_noun_phrases)
jargoyle.img = r"""         ,      ,
        /|      |\
       /  '.  .'  \
      |    .-.    |
      |   (o.o)   |
       \   '-'   /
        `-.---.-'
        /`-----'\
       / /     \ \
      / /       \ \
     / /         \ \
    / /           \ \
   / /             \ \
  / /               \ \
 ( (                 ) )
  `-'               `-'"""
