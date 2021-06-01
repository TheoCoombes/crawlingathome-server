import random
import json

with open("words.json", "r") as f:
    words = json.load(f)

def new():
    words = [random.choice(words) for i in range(2)]
    f = words[0].lower()
    s = words[1].lower()
    return f + "-" + s + "-" + str(random.randint(0, 999))
