import requests
import random
import json

def new():
    try:
        words = requests.get("https://random-word-api.herokuapp.com/word?number=2&swear=0").json()
        f = words[0].lower()
        s = words[1].lower()
        return f + "-" + s + "-" + str(random.randint(0, 999))
    except:
        return new()
