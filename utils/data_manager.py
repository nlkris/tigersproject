import json
import os

USERS_FILE = 'data/users.json'
TWEETS_FILE = 'data/tweets.json'

def init_files():
    if not os.path.exists('data'):
        os.makedirs('data')
    for file in [USERS_FILE, TWEETS_FILE]:
        if not os.path.exists(file):
            with open(file, 'w') as f:
                json.dump([], f)

def read_users():
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def write_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def read_tweets():
    with open(TWEETS_FILE, 'r') as f:
        return json.load(f)

def write_tweets(tweets):
    with open(TWEETS_FILE, 'w') as f:
        json.dump(tweets, f, indent=4)

