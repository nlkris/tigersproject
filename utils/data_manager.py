import json
import os

# Le dossier data est à la racine du projet
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
USERS_FILE = os.path.join(BASE_DIR, 'users.json')
TWEETS_FILE = os.path.join(BASE_DIR, 'tweets.json')

def init_files():
    """Crée le dossier 'data' et les fichiers JSON seulement s'ils n'existent pas."""
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR)
        print(f"Dossier {BASE_DIR} créé.")

    for file in [USERS_FILE, TWEETS_FILE]:
        if not os.path.exists(file):
            with open(file, 'w') as f:
                json.dump([], f, indent=4)
            print(f"Fichier {file} créé avec une liste vide.")
        else:
            print(f"Fichier {file} existe déjà → aucune modification.")

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

def ensure_likes_field():
    """Ajoute le champ 'likes' aux tweets existants si absent."""
    tweets = read_tweets()
    modified = False
    for tweet in tweets:
        if 'likes' not in tweet:
            tweet['likes'] = []
            modified = True
            print(f"Champ 'likes' ajouté pour le tweet id={tweet.get('id')}")
    if modified:
        write_tweets(tweets)
        print("Tweets mis à jour avec le champ 'likes'.")
