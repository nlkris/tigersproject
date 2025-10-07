import os
import json

DATA_DIR = 'data'
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
TWEETS_FILE = os.path.join(DATA_DIR, 'tweets.json')

def init_files():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    for path in [USERS_FILE, TWEETS_FILE]:
        if not os.path.exists(path):
            with open(path, 'w') as f:
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

