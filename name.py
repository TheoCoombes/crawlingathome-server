from random_word import RandomWords
import random

r = RandomWords()

def new():
    try:
        f = r.get_random_word(includePartOfSpeech="verb", hasDictionaryDef="true", minDictionaryCount=3).lower()
        s = r.get_random_word(includePartOfSpeech="noun", hasDictionaryDef="true", minDictionaryCount=3).lower()
        return f + "-" + s + "-" + str(random.randint(0, 999))
    except:
        return new()